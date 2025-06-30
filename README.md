# PDFSpy - Dynamic PDF Data Extraction

A Python tool that dynamically extracts data from PDFs based on TypeScript interface definitions. The tool automatically searches for field names defined in your TypeScript interface and extracts corresponding values from PDF documents.

## Workflow

1. **Define TypeScript Interface**: Create a TypeScript interface that defines the structure and field names you want to extract
2. **Scan PDF**: The tool searches the PDF text for your interface field names using intelligent pattern matching
3. **Return Structured JSON**: Get back a JSON object that matches your TypeScript interface structure with extracted data

## Features

- **Dynamic Field Detection**: Automatically searches for interface field names in PDF text
- **Flexible Pattern Matching**: Handles various text formats (camelCase, spaced, uppercase, etc.)
- **Nested Object Support**: Supports complex nested structures and arrays
- **Type-Aware Extraction**: Respects TypeScript types (string, number, boolean, arrays)
- **Intelligent Text Parsing**: Extracts tabular data and list items automatically

## Installation

```bash
# Install dependencies
pip install pymupdf

# Or using uv
uv sync
```

## Usage

### Basic Usage

```bash
python main.py interface.ts samples/sample.pdf
```

Note: TypeScript interface files should be placed in the `interfaces/` folder. The tool will automatically look there for your interface files.

### Example Interface

Create a TypeScript interface file in the `interfaces/` folder (e.g., `interfaces/product_data.ts`):

```typescript
interface ProductData {
  productName: string;
  version: string;
  hazard: {
    signalWord: string;
    hazardStatements: string[];
  };
  substances: {
    component: string;
    CAS: string;
    REACH_registration_number: string;
  }[];
}
```

### Run Extraction

```bash
python main.py product_data.ts my_document.pdf
```

The tool will look for `interfaces/product_data.ts` automatically.

### Output

The tool will return a JSON structure matching your interface:

```json
{
  "productName": "SODIUM BICARBONATE",
  "version": "7",
  "hazard": {
    "signalWord": "None",
    "hazardStatements": ["Not classified"]
  },
  "substances": [
    {
      "component": "Sodium hydrogen carbonate",
      "CAS": "144-55-8",
      "REACH_registration_number": "01-2119457606-32-x"
    }
  ]
}
```

## How It Works

1. **Interface Parsing**: The tool parses your TypeScript interface to understand the expected structure and field names
2. **Dynamic Field Search**: For each field in your interface, it generates multiple search patterns:
   - Exact field name matches
   - camelCase to spaced conversion ("productName" → "Product Name")
   - Case variations (uppercase, lowercase, title case)
   - Common domain-specific variations (e.g., "CAS" → "CAS No", "CAS Number")
3. **Context-Aware Extraction**: Uses regex patterns to find field values in various document formats
4. **Structure Assembly**: Builds the final JSON structure matching your TypeScript interface

## Supported Types

- `string`: Text extraction with cleaning and formatting
- `number`: Numeric value extraction and conversion
- `boolean`: Boolean value parsing
- `array`: List item extraction (bullets, numbered lists, etc.)
- `object`: Nested structure support
- `array of objects`: Tabular data extraction

## Examples

### Simple Interface

```typescript
interface BasicInfo {
  name: string;
  version: string;
  date: string;
}
```

### Complex Interface

```typescript
interface SDSData {
  identification: {
    productName: string;
    productCode: string;
    recommendedUse: string;
  };
  hazards: {
    classification: string;
    signalWord: string;
    hazardStatements: string[];
    pictograms: string[];
  };
  composition: {
    substances: {
      name: string;
      casNumber: string;
      ecNumber: string;
      concentration: string;
      classification: string;
    }[];
  };
}
```

## Project Structure

```
pdfspy/
├── app/
│   ├── parse_ts_interface.py    # TypeScript interface parser
│   ├── dynamic_extractor.py     # Dynamic field extraction engine
│   ├── mappers.py              # Schema to data mapping
│   └── utils.py                # PDF text extraction utilities
├── interfaces/                 # TypeScript interface files
│   ├── interface.ts           # Example SDS interface
│   ├── simple_interface.ts    # Simple document interface
│   ├── custom_interface.ts    # Custom fields example
│   └── comprehensive_interface.ts # Complex nested example
├── samples/                    # Sample PDF files
└── main.py                     # Main entry point
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request
