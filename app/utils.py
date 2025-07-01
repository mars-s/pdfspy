"""
Core utility functions for PDF processing and TypeScript interface loading.
"""
import warnings
import pymupdf

# Suppress PyMuPDF warnings
warnings.filterwarnings("ignore", message="builtin type.*has no __module__ attribute")


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file with optimized text processing.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    try:
        doc = pymupdf.open(pdf_path)
        text_parts = []
        
        for page in doc:
            page_text = page.get_text()
            if page_text.strip():  # Only add non-empty pages
                text_parts.append(page_text)
        
        doc.close()
        return "\n".join(text_parts)
        
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""


def load_typescript_interface(interface_path: str) -> str:
    """
    Load TypeScript interface from file.
    
    Args:
        interface_path: Path to the TypeScript interface file
        
    Returns:
        Interface content as string
    """
    try:
        with open(interface_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"Error loading TypeScript interface: {e}")
        return ""
