"""
Complete demonstration of Donut-enhanced dynamic extraction.
This shows how to use the new Donut integration with the dynamic extractor.
"""

import sys
import os
import json
from pathlib import Path

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.dynamic_extractor import (
    extract_fields_from_pdf_with_donut, 
    extract_fields_hybrid, 
    get_extraction_stats
)
from app.parse_ts_interface import parse_ts_interface

def parse_interface_file(file_path):
    """Helper function to parse a TypeScript interface file."""
    with open(file_path, 'r') as f:
        content = f.read()
    return parse_ts_interface(content)

def demonstrate_donut_extraction():
    """Demonstrate the Donut-enhanced extraction capabilities."""
    print("🚀 Donut-Enhanced Dynamic PDF Extraction Demo")
    print("=" * 50)
    
    # Available interfaces
    interface_dir = Path("interfaces")
    available_interfaces = list(interface_dir.glob("*.ts"))
    
    print(f"\n📋 Available interfaces:")
    for i, interface_file in enumerate(available_interfaces, 1):
        print(f"  {i}. {interface_file.name}")
    
    # Available PDFs
    sample_dir = Path("samples")
    available_pdfs = list(sample_dir.glob("*.pdf"))
    
    print(f"\n📄 Available PDFs:")
    for i, pdf_file in enumerate(available_pdfs, 1):
        print(f"  {i}. {pdf_file.name}")
    
    # Use the user example interface and first available PDF
    if available_interfaces and available_pdfs:
        interface_file = interface_dir / "user_example_interface.ts"
        pdf_file = available_pdfs[0]
        
        print(f"\n🔍 Processing:")
        print(f"  Interface: {interface_file.name}")
        print(f"  PDF: {pdf_file.name}")
        
        # Parse interface
        print(f"\n⚙️  Parsing interface schema...")
        interface_schema = parse_interface_file(interface_file)
        
        # Show schema structure
        print(f"📊 Interface structure:")
        for field_name, field_info in interface_schema.items():
            if not field_name.startswith('_'):
                field_type = field_info.get('_type', 'unknown') if isinstance(field_info, dict) else 'unknown'
                print(f"  • {field_name}: {field_type}")
        
        print(f"\n🤖 Running Donut-enhanced extraction...")
        
        # Method 1: Donut-first approach
        print(f"\n--- Method 1: Donut-First Extraction ---")
        result1 = extract_fields_from_pdf_with_donut(str(pdf_file), interface_schema, timeout=20)
        
        # Method 2: Hybrid approach
        print(f"\n--- Method 2: Hybrid Extraction ---")
        result2 = extract_fields_hybrid(str(pdf_file), interface_schema, timeout=20)
        
        # Show results
        print(f"\n📊 Results Summary:")
        print(f"=" * 30)
        
        def count_meaningful_fields(result):
            count = 0
            def count_recursive(obj):
                nonlocal count
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if not key.startswith('_') and value and str(value).strip():
                            count += 1
                        if isinstance(value, (dict, list)):
                            count_recursive(value)
                elif isinstance(obj, list) and obj:
                    count += 1
                    for item in obj:
                        count_recursive(item)
            count_recursive(result)
            return count
        
        method1_fields = count_meaningful_fields(result1)
        method2_fields = count_meaningful_fields(result2)
        
        print(f"Method 1 (Donut-first): {method1_fields} meaningful fields extracted")
        print(f"Method 2 (Hybrid): {method2_fields} meaningful fields extracted")
        
        # Show extraction stats
        stats = get_extraction_stats()
        print(f"\n📈 Extraction Statistics:")
        print(f"  • Donut used: {'✅' if stats.get('donut_used') else '❌'}")
        print(f"  • Hybrid mode: {'✅' if stats.get('hybrid_mode') else '❌'}")
        print(f"  • Fields extracted: {stats.get('fields_extracted', 0)}")
        print(f"  • Fuzzy matches: {stats.get('fuzzy_matches', 0)}")
        print(f"  • Pattern matches: {stats.get('pattern_matches', 0)}")
        
        # Show best result in detail
        best_result = result2 if method2_fields > method1_fields else result1
        best_method = "Hybrid" if method2_fields > method1_fields else "Donut-first"
        
        print(f"\n🏆 Best Result ({best_method} method):")
        print(f"=" * 40)
        print(json.dumps(best_result, indent=2, ensure_ascii=False))
        
        print(f"\n✅ Demonstration completed!")
        print(f"💡 Recommendation: Use the {'hybrid' if method2_fields > method1_fields else 'Donut-first'} method for best results")
        
    else:
        print(f"\n❌ Missing required files:")
        if not available_interfaces:
            print(f"  • No interface files found in {interface_dir}")
        if not available_pdfs:
            print(f"  • No PDF files found in {sample_dir}")

if __name__ == "__main__":
    demonstrate_donut_extraction()
