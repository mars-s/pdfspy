"""
Donut-based document understanding processor with timeout and fallback.
Provides advanced document structure extraction for complex PDFs.
"""
import time
from typing import Optional, Dict, Any
from pathlib import Path

# Optional imports - will fallback gracefully if not available
try:
    from transformers import DonutProcessor, VisionEncoderDecoderModel
    import torch
    from PIL import Image
    import pdf2image
    DONUT_AVAILABLE = True
except ImportError:
    DONUT_AVAILABLE = False
    print("Warning: Donut dependencies not available. Install with: pip install transformers torch pdf2image pillow")


class FastDonutProcessor:
    def __init__(self, model_name="naver-clova-ix/donut-base-finetuned-docvqa"):
        if not DONUT_AVAILABLE:
            raise ImportError("Donut dependencies not available")
            
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        try:
            self.processor = DonutProcessor.from_pretrained(model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
            self.model.to(self.device)

            # Enable optimizations
            if self.device == "cuda":
                try:
                    self.model.half()  # Use FP16 for speed
                    print("Enabled FP16 optimization for GPU")
                except Exception as e:
                    print(f"Could not enable FP16: {e}")
            
            # Set model to evaluation mode
            self.model.eval()
            print("Donut model loaded successfully")
            
        except Exception as e:
            print(f"Failed to load Donut model: {e}")
            raise

    def process_pdf_page(self, pdf_path: str, page_num: int = 0, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Process single PDF page with timeout"""
        start_time = time.time()

        try:
            # Convert PDF page to image
            images = pdf2image.convert_from_path(
                pdf_path, 
                first_page=page_num + 1, 
                last_page=page_num + 1,
                dpi=150  # Reasonable DPI for speed
            )
            
            if not images:
                return {
                    'error': 'No images extracted from PDF',
                    'processing_time': time.time() - start_time,
                    'success': False
                }

            image = images[0]

            # Check timeout after image conversion
            if time.time() - start_time > timeout:
                return {
                    'error': 'Timeout during image conversion',
                    'processing_time': time.time() - start_time,
                    'success': False
                }

            # Resize image if too large (for speed)
            max_size = 1024
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Process with Donut
            pixel_values = self.processor(image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)

            # Check timeout before generation
            if time.time() - start_time > timeout:
                return {
                    'error': 'Timeout before model generation',
                    'processing_time': time.time() - start_time,
                    'success': False
                }

            # Generate with timeout and optimized settings
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=512,
                    num_beams=1,  # Faster than beam search
                    do_sample=False,
                    early_stopping=True,
                    pad_token_id=self.processor.tokenizer.pad_token_id,
                    eos_token_id=self.processor.tokenizer.eos_token_id,
                )

            # Check timeout after generation
            processing_time = time.time() - start_time
            if processing_time > timeout:
                return {
                    'error': 'Timeout during model generation',
                    'processing_time': processing_time,
                    'success': False
                }

            # Decode results
            sequence = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

            return {
                'structured_text': sequence,
                'processing_time': processing_time,
                'success': True,
                'page_processed': page_num,
                'device_used': self.device
            }

        except Exception as e:
            return {
                'error': str(e),
                'processing_time': time.time() - start_time,
                'success': False
            }

    def process_multiple_pages(self, pdf_path: str, max_pages: int = 3, timeout_per_page: int = 5) -> Dict[str, Any]:
        """Process multiple pages from PDF"""
        results = []
        total_start_time = time.time()
        
        for page_num in range(max_pages):
            page_result = self.process_pdf_page(pdf_path, page_num, timeout_per_page)
            if page_result and page_result.get('success'):
                results.append(page_result)
            else:
                # Stop on first failed page to save time
                break
        
        # Combine results
        combined_text = ""
        for result in results:
            if result.get('structured_text'):
                combined_text += result['structured_text'] + "\n"
        
        return {
            'combined_text': combined_text,
            'pages_processed': len(results),
            'total_processing_time': time.time() - total_start_time,
            'success': len(results) > 0,
            'individual_results': results
        }


def try_donut_extraction(pdf_path: str, fallback_extractor=None, timeout: int = 5) -> Optional[str]:
    """
    Try Donut extraction with fallback to alternative extractor.
    
    Args:
        pdf_path: Path to PDF file
        fallback_extractor: Function to call if Donut fails
        timeout: Maximum time to spend on Donut processing
    
    Returns:
        Extracted text or None if all methods fail
    """
    if not DONUT_AVAILABLE:
        print("Donut not available, using fallback extractor")
        if fallback_extractor:
            return fallback_extractor(pdf_path)
        return None
    
    try:
        donut = FastDonutProcessor()
        result = donut.process_pdf_page(pdf_path, timeout=timeout)

        if result and result.get('success') and result.get('processing_time', 0) < timeout:
            print(f"Donut extraction successful in {result['processing_time']:.2f}s")
            return result.get('structured_text', '')
        else:
            print(f"Donut failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Donut processor failed: {e}")
    
    # Fallback to alternative extractor
    if fallback_extractor:
        print("Using fallback extractor")
        return fallback_extractor(pdf_path)
    
    return None


def is_donut_available() -> bool:
    """Check if Donut dependencies are available"""
    return DONUT_AVAILABLE


def get_donut_device_info() -> Dict[str, Any]:
    """Get information about available compute devices"""
    info = {
        'donut_available': DONUT_AVAILABLE,
        'cuda_available': False,
        'device_count': 0,
        'recommended_device': 'cpu'
    }
    
    if DONUT_AVAILABLE and torch:
        info['cuda_available'] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info['device_count'] = torch.cuda.device_count()
            info['recommended_device'] = 'cuda'
            info['gpu_name'] = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else 'Unknown'
    
    return info
