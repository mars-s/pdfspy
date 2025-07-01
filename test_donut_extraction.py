"""
Test script for the enhanced dynamic extractor with Donut integration.
"""

import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.dynamic_extractor import extract_fields_from_pdf_with_donut, DynamicExtractor, ExtractionConfig, get_extraction_stats
from app.parse_ts_interface import parse_ts_interface

def parse_interface_file(file_path):
    """Helper function to parse a TypeScript interface file."""
    with open(file_path, 'r') as f:
        content = f.read()
    return parse_ts_interface(content)

def test_donut_dynamic_extraction():
    """Test the Donut-enhanced dynamic extraction."""
    print("Testing Donut-enhanced dynamic extraction...")
    
    # Parse the user example interface
    interface_path = "interfaces/user_example_interface.ts"
    if not os.path.exists(interface_path):
        print(f"Interface file not found: {interface_path}")
        return
    
    print(f"Parsing interface: {interface_path}")
    interface_schema = parse_interface_file(interface_path)
    print(f"Interface schema: {interface_schema}")
    
    # Test with sample PDF
    pdf_path = "samples/sample.pdf"
    if not os.path.exists(pdf_path):
        print(f"Sample PDF not found: {pdf_path}")
        return
    
    print(f"\nExtracting from PDF: {pdf_path}")
    print("\n=== Testing Original Donut Method ===")
    result1 = extract_fields_from_pdf_with_donut(pdf_path, interface_schema, page_num=0, timeout=15)
    
    print("\n=== Testing New Dynamic Extractor ===")
    extractor = DynamicExtractor(ExtractionConfig(donut_timeout=15))
    extraction_result = extractor.extract_from_pdf(pdf_path, interface_schema, page_num=0)
    result2 = extraction_result.data
    
    # Let's also test direct Donut output
    print(f"\n--- Testing Direct Donut Output ---")
    try:
        from app.donut_processor import FastDonutProcessor
        donut_processor = FastDonutProcessor()
        donut_result = donut_processor.process_pdf_page(pdf_path, page_num=0, timeout=10)
        if donut_result and donut_result.get('success'):
            donut_text = donut_result.get('structured_text', '')
            print(f"Donut extracted text (first 500 chars):")
            print(f"'{donut_text[:500]}{'...' if len(donut_text) > 500 else ''}'")
        else:
            print(f"Donut failed: {donut_result}")
    except Exception as e:
        print(f"Error testing direct Donut: {e}")
    
    print(f"\n--- Extraction Results ---")
    print(f"Original method result: {result1}")
    print(f"New extractor result: {result2}")
    print(f"Extraction metadata: method={extraction_result.method_used}, confidence={extraction_result.confidence:.2f}, fields={extraction_result.field_count}, time={extraction_result.processing_time:.2f}s")
    
    print(f"\nExtraction stats:")
    stats = get_extraction_stats()
    print(f"Stats: {stats}")
    
    # Check if we got meaningful results
    if result2:
        print(f"\n✅ Extraction successful!")
        print(f"🤖 Method used: {extraction_result.method_used}")
        print(f"📊 Confidence: {extraction_result.confidence:.2f}")
        print(f"� Fields extracted: {extraction_result.field_count}")
        if extraction_result.errors:
            print(f"⚠️ Errors: {extraction_result.errors}")
    else:
        print(f"\n❌ Extraction failed")

if __name__ == "__main__":
    test_donut_dynamic_extraction()
