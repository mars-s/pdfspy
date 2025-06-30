"""
Main PDF SDS data extraction script.
Orchestrates the extraction and mapping of PDF data to TypeScript interfaces.
"""
import json
from app.parse_ts_interface import parse_ts_interface
from app.utils import extract_text_from_pdf, load_typescript_interface
from app.mappers import map_schema_to_data


def main():
    """Main entry point for PDF SDS data extraction."""
    # Configuration
    interface_file = "interface.ts"
    pdf_file = "samples/sample3.pdf"
    
    # Load TypeScript interface and parse schema
    ts_code = load_typescript_interface(interface_file)
    schema = parse_ts_interface(ts_code)
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_file)
    
    # Map schema to extracted data
    data = map_schema_to_data(schema, text)
    
    # Output results
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
