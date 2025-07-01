"""
Core utility functions for PDF processing and TypeScript interface loading.
Optimized with pdfplumber for better performance and table extraction.
"""
import warnings
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import pdfplumber with fallback
try:
    import pdfplumber
    import pandas as pd
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("Warning: pdfplumber not available. Install with: pip install pdfplumber pandas")


def extract_pdf_content(pdf_path: str) -> Dict[str, Any]:
    """
    Fast PDF extraction with layout awareness and table detection.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing text, tables, and metadata
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber is required for PDF processing")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extract text with position info
            full_text = ""
            tables = []
            page_info = []

            for page_num, page in enumerate(pdf.pages):
                # Get text with layout preservation
                page_text = page.extract_text(layout=True)
                if page_text:
                    full_text += f"\n--- Page {page_num + 1} ---\n"
                    full_text += page_text

                # Extract tables separately
                page_tables = page.extract_tables()
                if page_tables:
                    for table_num, table in enumerate(page_tables):
                        tables.append({
                            'page': page_num + 1,
                            'table_number': table_num + 1,
                            'data': table,
                            'dataframe': _table_to_dataframe(table)
                        })

                # Store page information
                page_info.append({
                    'page_number': page_num + 1,
                    'width': page.width,
                    'height': page.height,
                    'has_text': bool(page_text),
                    'table_count': len(page_tables) if page_tables else 0
                })

            return {
                'text': full_text.strip(),
                'tables': tables,
                'metadata': pdf.metadata or {},
                'page_info': page_info,
                'total_pages': len(pdf.pages)
            }
        
    except Exception as e:
        print(f"Error extracting content from PDF: {e}")
        return {
            'text': '',
            'tables': [],
            'metadata': {},
            'page_info': [],
            'total_pages': 0,
            'error': str(e)
        }


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file (legacy function for compatibility).
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    content = extract_pdf_content(pdf_path)
    return content.get('text', '')


def _table_to_dataframe(table: List[List[str]]) -> Optional[Any]:
    """Convert table data to pandas DataFrame"""
    if not table or not PDFPLUMBER_AVAILABLE:
        return None
    
    try:
        # Use first row as headers if it looks like headers
        if len(table) > 1:
            headers = table[0]
            data = table[1:]
            
            # Check if first row looks like headers (contains mostly strings)
            if headers and any(isinstance(cell, str) and cell.strip() for cell in headers):
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame(table)
        else:
            df = pd.DataFrame(table)
        
        return df
    except Exception:
        return None


def extract_structured_content(pdf_path: str, extract_tables: bool = True) -> Dict[str, Any]:
    """
    Extract structured content with enhanced processing.
    
    Args:
        pdf_path: Path to PDF file
        extract_tables: Whether to extract and process tables
        
    Returns:
        Enhanced structured content
    """
    content = extract_pdf_content(pdf_path)
    
    if not extract_tables:
        content['tables'] = []
    
    # Add text analysis
    text = content.get('text', '')
    content['text_analysis'] = {
        'total_characters': len(text),
        'total_words': len(text.split()) if text else 0,
        'total_lines': len(text.split('\n')) if text else 0,
        'contains_tables': len(content.get('tables', [])) > 0,
        'avg_words_per_page': round(len(text.split()) / max(content.get('total_pages', 1), 1), 2)
    }
    
    return content


def load_typescript_interface(interface_path: str) -> str:
    """
    Load TypeScript interface from file.
    
    Args:
        interface_path: Path to the TypeScript interface file
        
    Returns:
        Interface content as string
    """
    try:
        interface_file = Path(interface_path)
        if not interface_file.exists():
            # Try in interfaces directory
            interfaces_path = Path("interfaces") / interface_path
            if interfaces_path.exists():
                interface_file = interfaces_path
            else:
                raise FileNotFoundError(f"Interface file not found: {interface_path}")
        
        with open(interface_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"Error loading TypeScript interface: {e}")
        return ""


def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    """
    Get comprehensive PDF information without full extraction.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        PDF information dictionary
    """
    if not PDFPLUMBER_AVAILABLE:
        return {'error': 'pdfplumber not available'}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            info = {
                'file_path': pdf_path,
                'file_size_mb': round(Path(pdf_path).stat().st_size / (1024 * 1024), 2),
                'total_pages': len(pdf.pages),
                'metadata': pdf.metadata or {},
                'page_dimensions': [],
                'estimated_processing_time': 0
            }
            
            # Get page dimensions
            for page in pdf.pages:
                info['page_dimensions'].append({
                    'width': page.width,
                    'height': page.height
                })
            
            # Estimate processing time (rough calculation)
            # Base time per page + additional time for complex pages
            base_time = len(pdf.pages) * 0.5  # 0.5 seconds per page
            size_factor = info['file_size_mb'] * 0.1  # Additional time based on file size
            info['estimated_processing_time'] = round(base_time + size_factor, 2)
            
            return info
            
    except Exception as e:
        return {'error': str(e), 'file_path': pdf_path}


def is_pdf_processable(pdf_path: str) -> bool:
    """
    Check if PDF can be processed.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        True if PDF can be processed
    """
    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            return False
        
        if not PDFPLUMBER_AVAILABLE:
            return False
        
        # Try to open the PDF
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages) > 0
            
    except Exception:
        return False
