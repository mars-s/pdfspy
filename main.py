"""
Main PDF SDS data extraction script.
Orchestrates the extraction and mapping of PDF data to TypeScript interfaces.

Workflow:
1. Load TypeScript interface from file
2. Parse interface to understand structure and field names
3. Extract text from PDF
4. Dynamically search for interface field names in PDF text
5. Return JSON matching the TypeScript interface structure
"""
import json
import sys
import os
from app.parse_ts_interface import parse_ts_interface
from app.utils import extract_text_from_pdf, load_typescript_interface
from app.mappers import map_schema_to_data


def main(interface_file: str = "interface.ts", pdf_file: str = "samples/sample3.pdf"):
    """
    Main entry point for PDF SDS data extraction.
    
    Args:
        interface_file: Path to TypeScript interface file (relative to interfaces/ folder or absolute path)
        pdf_file: Path to PDF file to extract data from
    """
    try:
        # If interface_file doesn't contain a path separator, look in interfaces folder
        if os.sep not in interface_file and not os.path.isabs(interface_file):
            interface_file = os.path.join("interfaces", interface_file)
        
        print(f"Loading TypeScript interface from: {interface_file}")
        ts_code = load_typescript_interface(interface_file)
        
        print("Parsing interface structure...")
        schema = parse_ts_interface(ts_code)
        
        print(f"Extracting text from PDF: {pdf_file}")
        text = extract_text_from_pdf(pdf_file)
        
        print("Mapping PDF data to interface structure...")
        data = map_schema_to_data(schema, text)
        
        print("\nExtracted data:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        return data
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        print("Note: TypeScript interface files should be placed in the 'interfaces/' folder")
        print("Available interfaces:")
        if os.path.exists("interfaces"):
            for f in os.listdir("interfaces"):
                if f.endswith(".ts"):
                    print(f"  - {f}")
        return None
    except Exception as e:
        print(f"Error during extraction: {e}")
        return None


if __name__ == "__main__":
    # Allow command line arguments for interface and PDF files
    interface_file = sys.argv[1] if len(sys.argv) > 1 else "interface.ts"
    pdf_file = sys.argv[2] if len(sys.argv) > 2 else "samples/sample3.pdf"
    
    main(interface_file, pdf_file)
