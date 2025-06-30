# PDF Spy - Dynamic TypeScript Interface PDF Extractor

A smart PDF data extraction tool that takes any TypeScript interface and extracts corresponding data from PDF files. The system dynamically adapts to different PDF formats and field naming conventions.

## How It Works

1. **Define your data structure** in a TypeScript interface
2. **Feed it a PDF** - the system will scan for fields matching your interface
3. **Get structured JSON** output matching your TypeScript interface exactly

## Key Features

- **Truly Dynamic**: Works with any TypeScript interface, not hardcoded for specific formats
- **Smart Field Matching**: Uses semantic variations and synonyms to find fields (e.g., "productName" matches "Product Name", "Product Identifier", "Substance Name", etc.)
- **Adaptive**: Analyzes PDF structure to understand different formatting styles
- **Flexible Arrays**: Automatically extracts arrays of objects from tabular data
- **Type Aware**: Respects TypeScript types (string, number, boolean, arrays)

## Quick Start

### 1. Create your TypeScript interface

```typescript
// interface.ts
interface ProductData {
  name: string;
  manufacturer: string;
  version: string;
  components: {
    substance: string;
    casNumber: string;
    percentage: number;
  }[];
}
```

### 2. Run the extraction

```bash
python main.py interface.ts path/to/your.pdf
```

### 3. Get your data

```json
{
  "name": "SODIUM BICARBONATE",
  "manufacturer": "M-I Australia Pty Ltd",
  "version": "7",
  "components": [
    {
      "substance": "Sodium hydrogen carbonate",
      "casNumber": "144-55-8",
      "percentage": 60
    }
  ]
}
```

## How the Smart Matching Works

The system automatically generates variations and synonyms for your field names:

- **productName** → "Product Name", "Product Identifier", "Substance Name", "Material Name", etc.
- **casNumber** → "CAS No", "CAS Number", "CAS-No", "Chemical Abstracts", etc.
- **manufacturer** → "Supplier", "Producer", "Company", "Vendor", etc.

## Examples

### Simple Document Info

```typescript
interface DocumentInfo {
  title: string;
  documentNumber: string;
  revisionDate: string;
}
```

### Chemical Safety Data

```typescript
interface SafetyData {
  productName: string;
  signalWord: string;
  hazardStatements: string[];
  substances: {
    component: string;
    CAS: string;
    REACH_registration_number: string;
  }[];
}
```

### Custom Business Document

```typescript
interface Invoice {
  invoiceNumber: string;
  customerName: string;
  totalAmount: number;
  lineItems: {
    description: string;
    quantity: number;
    unitPrice: number;
  }[];
}
```

## Installation

```bash
# Install dependencies
pip install pymupdf

# Or if using uv
uv sync
```

## Usage

```bash
# Basic usage
python main.py interface.ts document.pdf

# Using different files
python main.py my_interface.ts path/to/document.pdf
```

## Technical Details

### Smart Field Detection

- Analyzes PDF structure to understand formatting patterns
- Generates semantic variations using domain knowledge
- Uses fuzzy matching to handle slight naming differences
- Adapts to different PDF layouts and styles

### Array Handling

- Automatically detects tabular data
- Maps table columns to TypeScript interface fields
- Handles nested objects within arrays
- Supports both simple arrays and complex object arrays

### Type Conversion

- Automatically converts extracted strings to appropriate types
- Numbers: Extracts numeric values from text
- Booleans: Interprets yes/no, true/false patterns
- Arrays: Handles both simple lists and object collections

This approach makes the tool truly universal - it can work with any PDF format and any data structure you define in TypeScript!
