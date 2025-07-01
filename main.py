"""
High-Performance PDF SDS Data Extraction System
Orchestrates PDF processing with chemical NER, Donut integration, and parallel processing.

Usage:
    uv run main.py <interface_file> <pdf_file>
    uv run main.py --batch <interface_file> <pdf_directory>
    uv run main.py --help

Features:
- pdfplumber-based extraction (3-5x faster than PyMuPDF)
- Chemical NER for accurate chemical entity recognition
- Donut document understanding with fallback
- Parallel processing for batch operations
- Intelligent caching system
- Performance monitoring and statistics
"""
import json
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import argparse

# Import core modules
from app.parse_ts_interface import parse_ts_interface
from app.utils import (
    extract_pdf_content, 
    load_typescript_interface, 
    get_pdf_info,
    is_pdf_processable
)
from app.mappers import map_schema_to_data

# Import performance enhancement modules
try:
    from app.chemical_ner import ChemicalNER
    from app.hazard_classifier import HazardClassifier
    from app.cache_manager import ExtractionCache, cached_extraction, with_cache_stats
    from app.dynamic_extractor import extract_fields_from_interface, extract_all_chemical_entities, get_extraction_stats
    ENHANCED_FEATURES = True
except ImportError as e:
    print(f"Warning: Enhanced features not available: {e}")
    ENHANCED_FEATURES = False

# Import optional Donut processor
try:
    from app.donut_processor import try_donut_extraction, is_donut_available, get_donut_device_info
    DONUT_AVAILABLE = True
except ImportError:
    DONUT_AVAILABLE = False
    print("Warning: Donut processor not available")


class PDFBatchProcessor:
    """High-performance batch processor for multiple PDFs"""
    
    def __init__(self, max_workers: Optional[int] = None, use_cache: bool = True, 
                 enable_donut: bool = True, donut_timeout: int = 5):
        self.max_workers = max_workers or min(cpu_count(), 8)
        self.use_cache = use_cache
        self.enable_donut = enable_donut and DONUT_AVAILABLE
        self.donut_timeout = donut_timeout
        
        # Initialize components
        self.cache = ExtractionCache() if use_cache and ENHANCED_FEATURES else None
        self.chemical_ner = ChemicalNER() if ENHANCED_FEATURES else None
        self.hazard_classifier = HazardClassifier() if ENHANCED_FEATURES else None
        
        print(f"PDFBatchProcessor initialized:")
        print(f"  Max workers: {self.max_workers}")
        print(f"  Cache enabled: {use_cache and ENHANCED_FEATURES}")
        print(f"  Donut enabled: {self.enable_donut}")
        print(f"  Enhanced features: {ENHANCED_FEATURES}")

    def process_single_pdf(self, pdf_path: Path, interface_path: Path) -> Dict[str, Any]:
        """Process a single PDF with all optimizations"""
        start_time = time.time()
        
        try:
            # Validate inputs
            if not is_pdf_processable(str(pdf_path)):
                return {
                    'error': f'PDF not processable: {pdf_path}',
                    'processing_time': time.time() - start_time
                }
            
            # Load and parse interface
            print(f"Loading TypeScript interface from: {interface_path}")
            ts_code = load_typescript_interface(str(interface_path))
            if not ts_code:
                return {
                    'error': f'Could not load interface: {interface_path}',
                    'processing_time': time.time() - start_time
                }
            
            schema = parse_ts_interface(ts_code)
            
            # Check cache first
            if self.cache:
                cached_result = self.cache.get(str(pdf_path), schema)
                if cached_result:
                    cached_result['cache_hit'] = True
                    cached_result['processing_time'] = time.time() - start_time
                    print(f"Cache hit for: {pdf_path}")
                    return cached_result
            
            # Extract content with interface-based field extraction
            print(f"Extracting content from: {pdf_path}")
            result = self._extract_with_fallback(str(pdf_path), schema)
            
            # Enhance with additional chemical analysis if available
            if ENHANCED_FEATURES and result.get('raw_text') or result.get('raw_content', {}).get('text'):
                text_content = result.get('raw_text') or result.get('raw_content', {}).get('text', '')
                if text_content:
                    print("Applying additional chemical analysis...")
                    additional_entities = extract_all_chemical_entities(text_content)
                    if additional_entities:
                        # Merge with existing extracted data
                        if 'chemical_analysis' not in result['extracted_data']:
                            result['extracted_data']['chemical_analysis'] = additional_entities
            
            # Prepare final result
            final_result = {
                'pdf_path': str(pdf_path),
                'interface_path': str(interface_path),
                'extracted_data': result['extracted_data'],
                'extraction_metadata': {
                    'processing_method': result.get('processing_method', 'pdfplumber'),
                    'donut_used': result.get('donut_used', False),
                    'extraction_stats': result.get('extraction_stats', {}),
                    'text_length': len(result.get('raw_text', '') or result.get('raw_content', {}).get('text', '')),
                    'total_pages': result.get('raw_content', {}).get('total_pages', 0),
                    'tables_found': len(result.get('raw_content', {}).get('tables', [])),
                },
                'processing_time': time.time() - start_time,
                'cache_hit': False
            }
            if 'hazard_analysis' in result:
                final_result['hazard_analysis'] = result['hazard_analysis']
            
            # Cache the result
            if self.cache:
                self.cache.set(str(pdf_path), schema, final_result)
            
            return final_result
            
        except Exception as e:
            return {
                'error': f'Processing failed: {str(e)}',
                'pdf_path': str(pdf_path),
                'processing_time': time.time() - start_time
            }

    def _extract_with_fallback(self, pdf_path: str, interface_schema: Dict) -> Dict[str, Any]:
        """Extract content using Donut with pdfplumber fallback and interface-based field extraction"""
        
        # Try Donut first if enabled
        if self.enable_donut and DONUT_AVAILABLE:
            print(f"Attempting Donut extraction (timeout: {self.donut_timeout}s)...")
            
            def fallback_extractor(path):
                return extract_pdf_content(path)
            
            donut_text = try_donut_extraction(pdf_path, fallback_extractor, self.donut_timeout)
            
            if donut_text and isinstance(donut_text, str) and len(donut_text.strip()) > 100:
                # Donut succeeded - extract fields using interface schema
                print("Donut extraction successful, extracting fields...")
                
                if ENHANCED_FEATURES:
                    extracted_fields = extract_fields_from_interface(donut_text, interface_schema)
                else:
                    extracted_fields = map_schema_to_data(interface_schema, {'text': donut_text})
                
                result = {
                    'extracted_data': extracted_fields,
                    'raw_text': donut_text,
                    'processing_method': 'donut',
                    'donut_used': True,
                    'extraction_stats': get_extraction_stats() if ENHANCED_FEATURES else {}
                }
                return result
            else:
                print("Donut extraction failed or insufficient, using pdfplumber fallback")
        
        # Fallback to pdfplumber
        print("Using pdfplumber extraction...")
        content = extract_pdf_content(pdf_path)
        
        # Extract fields using interface schema
        if ENHANCED_FEATURES:
            extracted_fields = extract_fields_from_interface(content.get('text', ''), interface_schema)
        else:
            extracted_fields = map_schema_to_data(interface_schema, content)
        
        result = {
            'extracted_data': extracted_fields,
            'raw_content': content,
            'processing_method': 'pdfplumber',
            'donut_used': False,
            'extraction_stats': get_extraction_stats() if ENHANCED_FEATURES else {}
        }
        
        return result

    def process_batch(self, pdf_paths: List[Path], interface_path: Path) -> Dict[str, Any]:
        """Process multiple PDFs in parallel"""
        print(f"Processing batch of {len(pdf_paths)} PDFs with {self.max_workers} workers")
        
        batch_start_time = time.time()
        results = {}
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_pdf = {
                executor.submit(self._process_single_pdf_worker, str(pdf_path), str(interface_path)): pdf_path
                for pdf_path in pdf_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pdf):
                pdf_path = future_to_pdf[future]
                try:
                    result = future.result(timeout=60)  # 60 second timeout per PDF
                    results[str(pdf_path)] = result
                    
                    # Progress indicator
                    completed = len(results)
                    total = len(pdf_paths)
                    print(f"Progress: {completed}/{total} PDFs processed ({completed/total*100:.1f}%)")
                    
                except Exception as e:
                    results[str(pdf_path)] = {
                        'error': f'Batch processing error: {str(e)}',
                        'pdf_path': str(pdf_path)
                    }
        
        batch_time = time.time() - batch_start_time
        
        # Calculate statistics
        successful = sum(1 for r in results.values() if 'error' not in r)
        failed = len(results) - successful
        avg_time = sum(r.get('processing_time', 0) for r in results.values()) / len(results) if results else 0
        
        batch_summary = {
            'batch_results': results,
            'batch_statistics': {
                'total_pdfs': len(pdf_paths),
                'successful': successful,
                'failed': failed,
                'success_rate': successful / len(pdf_paths) * 100 if pdf_paths else 0,
                'total_batch_time': batch_time,
                'average_time_per_pdf': avg_time,
                'pdfs_per_minute': len(pdf_paths) / (batch_time / 60) if batch_time > 0 else 0
            }
        }
        
        return batch_summary

    @staticmethod
    def _process_single_pdf_worker(pdf_path: str, interface_path: str) -> Dict[str, Any]:
        """Worker function for parallel processing"""
        # Create a new processor instance for this worker
        processor = PDFBatchProcessor(max_workers=1, use_cache=False)
        return processor.process_single_pdf(Path(pdf_path), Path(interface_path))


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="High-Performance PDF SDS Data Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run main.py interface.ts sample.pdf
  uv run main.py --batch interface.ts samples/
  uv run main.py --workers 4 --no-cache interface.ts sample.pdf
  uv run main.py --stats
        """
    )
    
    parser.add_argument('interface_file', nargs='?', 
                       help='TypeScript interface file (in interfaces/ folder or absolute path)')
    parser.add_argument('pdf_input', nargs='?',
                       help='PDF file or directory containing PDFs')
    parser.add_argument('--batch', action='store_true',
                       help='Process all PDFs in the specified directory')
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers (default: auto)')
    parser.add_argument('--no-cache', action='store_true',
                       help='Disable caching')
    parser.add_argument('--no-donut', action='store_true',
                       help='Disable Donut processor')
    parser.add_argument('--donut-timeout', type=int, default=5,
                       help='Donut processing timeout in seconds (default: 5)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output JSON file path')
    parser.add_argument('--stats', action='store_true',
                       help='Show system statistics and capabilities')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Clear the extraction cache')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.stats:
        show_system_stats()
        return
    
    if args.clear_cache:
        clear_cache()
        return
    
    # Validate required arguments for normal operation
    if not args.interface_file or not args.pdf_input:
        print("Error: Both interface_file and pdf_input are required")
        print("Usage: uv run main.py <interface_file> <pdf_file>")
        print("   or: uv run main.py --batch <interface_file> <pdf_directory>")
        print("   or: uv run main.py --help")
        sys.exit(1)
    if not args.interface_file or not args.pdf_input:
        parser.print_help()
        sys.exit(1)
    
    # Process interface file path
    interface_path = Path(args.interface_file)
    if not interface_path.exists():
        # Try in interfaces directory
        interfaces_path = Path("interfaces") / args.interface_file
        if interfaces_path.exists():
            interface_path = interfaces_path
        else:
            print(f"Error: Interface file not found: {args.interface_file}")
            print("Available interfaces:")
            if Path("interfaces").exists():
                for f in Path("interfaces").glob("*.ts"):
                    print(f"  - {f.name}")
            sys.exit(1)
    
    # Process PDF input
    pdf_input_path = Path(args.pdf_input)
    if not pdf_input_path.exists():
        print(f"Error: PDF input not found: {args.pdf_input}")
        sys.exit(1)
    
    # Initialize processor
    processor = PDFBatchProcessor(
        max_workers=args.workers,
        use_cache=not args.no_cache,
        enable_donut=not args.no_donut,
        donut_timeout=args.donut_timeout
    )
    
    start_time = time.time()
    
    try:
        if args.batch or pdf_input_path.is_dir():
            # Batch processing
            if pdf_input_path.is_file():
                print("Warning: --batch specified but input is a file, processing single file")
                pdf_files = [pdf_input_path]
            else:
                pdf_files = list(pdf_input_path.glob("*.pdf"))
                if not pdf_files:
                    print(f"No PDF files found in: {pdf_input_path}")
                    sys.exit(1)
            
            print(f"Found {len(pdf_files)} PDF files to process")
            result = processor.process_batch(pdf_files, interface_path)
            
        else:
            # Single file processing
            if pdf_input_path.is_dir():
                print("Error: Directory specified but --batch not used")
                sys.exit(1)
            
            result = processor.process_single_pdf(pdf_input_path, interface_path)
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Results saved to: {output_path}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Print summary
        total_time = time.time() - start_time
        print(f"\nProcessing completed in {total_time:.2f} seconds")
        
        if args.batch and 'batch_statistics' in result:
            stats = result['batch_statistics']
            print(f"Batch Summary:")
            print(f"  Success rate: {stats['success_rate']:.1f}%")
            print(f"  Average time per PDF: {stats['average_time_per_pdf']:.2f}s")
            print(f"  Processing rate: {stats['pdfs_per_minute']:.1f} PDFs/minute")
        
        # Show cache stats if enhanced features available
        if ENHANCED_FEATURES and not args.no_cache:
            cache = ExtractionCache()
            cache_stats = cache.get_cache_stats()
            print(f"\nCache Statistics:")
            print(f"  Files: {cache_stats['total_files']}")
            print(f"  Size: {cache_stats['total_size_mb']} MB")
            print(f"  Total hits: {cache_stats['total_hits']}")
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def show_system_stats():
    """Show system capabilities and statistics"""
    print("PDFSpy System Information")
    print("=" * 40)
    
    print(f"Enhanced Features Available: {ENHANCED_FEATURES}")
    print(f"Donut Available: {DONUT_AVAILABLE}")
    
    if DONUT_AVAILABLE:
        device_info = get_donut_device_info()
        print(f"Recommended Device: {device_info['recommended_device']}")
        if device_info.get('gpu_name'):
            print(f"GPU: {device_info['gpu_name']}")
    
    print(f"CPU Cores: {cpu_count()}")
    
    if ENHANCED_FEATURES:
        extraction_stats = get_extraction_stats()
        print(f"Extraction Cache Size: {extraction_stats['cache_size']}")
        print(f"Supported Patterns: {len(extraction_stats['supported_patterns'])}")
        
        # Show cache statistics
        cache = ExtractionCache()
        cache_stats = cache.get_cache_stats()
        print(f"Cache Files: {cache_stats['total_files']}")
        print(f"Cache Size: {cache_stats['total_size_mb']} MB")
    
    # Show available interfaces
    if Path("interfaces").exists():
        interfaces = list(Path("interfaces").glob("*.ts"))
        print(f"\nAvailable Interfaces ({len(interfaces)}):")
        for interface in interfaces:
            print(f"  - {interface.name}")
    
    # Show sample PDFs
    if Path("samples").exists():
        samples = list(Path("samples").glob("*.pdf"))
        print(f"\nSample PDFs ({len(samples)}):")
        for sample in samples:
            print(f"  - {sample.name}")


def clear_cache():
    """Clear the extraction cache"""
    if not ENHANCED_FEATURES:
        print("Enhanced features not available, no cache to clear")
        return
    
    cache = ExtractionCache()
    stats_before = cache.get_cache_stats()
    cache.clear_cache()
    print(f"Cache cleared. Freed {stats_before['total_size_mb']} MB ({stats_before['total_files']} files)")


if __name__ == "__main__":
    main()
