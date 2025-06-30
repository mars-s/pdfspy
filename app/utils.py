"""
Utility functions for PDF processing and text extraction.
"""
import warnings
import pymupdf

# Suppress PyMuPDF warnings
warnings.filterwarnings("ignore", message="builtin type.*has no __module__ attribute")


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    doc = pymupdf.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def load_typescript_interface(interface_path):
    """
    Load TypeScript interface from file.
    
    Args:
        interface_path: Path to the TypeScript interface file
        
    Returns:
        Interface content as string
    """
    with open(interface_path, 'r', encoding='utf-8') as f:
        return f.read()


def is_ingredient_related(key):
    """Check if a key is related to ingredients/chemicals"""
    if not key:
        return False
    key_lower = key.lower()
    return any(term in key_lower for term in [
        'ingredient', 'chemical', 'component', 'substance', 'compound'
    ])


def is_hazard_related(key):
    """Check if a key is related to hazards"""
    if not key:
        return False
    key_lower = key.lower()
    return any(term in key_lower for term in [
        'hazard', 'danger', 'warning', 'statement', 'risk'
    ])
