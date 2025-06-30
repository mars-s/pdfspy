# PDF Scrapper Testing Suite

This comprehensive testing suite validates your PDF scrapper application with various TypeScript interface configurations.

## 📁 Test Files Overview

- **`test_pdf_scrapper.py`** - Main test suite covering interface variations, consistency, and core functionality
- **`test_performance_edge_cases.py`** - Performance tests, edge cases, and regression tests
- **`conftest.py`** - Pytest configuration and shared fixtures
- **`test_runner.py`** - Test execution script with reporting capabilities

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install pytest pytest-cov psutil
```

### 2. Run Basic Tests

```bash
# Quick smoke test
python test_runner.py --test-type smoke

# Run all tests
python test_runner.py --test-type all
```

## 🧪 Test Categories

### Interface Variation Tests

Tests your scrapper with different TypeScript interface structures:

```python
# Original interface
interface SDSData {
  productName: string;
  hazard: {
    signalWord: string;
    hazardStatements: string[];
  };
  ingredients: { chemicalName: string; casNumber: string; weightPercent: string; }[];
}

# Simplified interface
interface SimpleData {
  name: string;
  signal: string;
}

# Complex nested interface
interface ComplexData {
  identification: {
    product: { name: string; code: string; };
    company: { name: string; address: string; };
  };
  // ... more nesting
}
```

### Consistency Tests

Ensures deterministic output for the same input:

```bash
python -m pytest test_pdf_scrapper.py::TestConsistencyAndDeterminism -v
```

### Performance Tests

Validates performance with large documents and complex interfaces:

```bash
python -m pytest test_performance_edge_cases.py -m performance -v
```

### Edge Case Tests

Tests malformed data, Unicode characters, and error conditions:

```bash
python -m pytest test_performance_edge_cases.py::TestEdgeCasesAndErrorHandling -v
```

## 🎯 Specific Test Examples

### Test Different Interface Structures

```python
def test_custom_interface():
    """Example of testing a custom interface"""
    custom_interface = {
        "document": {
            "title": "productName",
            "classification": "signalWord"
        },
        "components": [
            {
                "substance": "chemicalName",
                "identifier": "casNumber",
                "amount": "weightPercent"
            }
        ]
    }

    result = fill_fields(custom_interface, sample_pdf_text)

    # Validate structure matches expectation
    assert "document" in result
    assert "components" in result
    assert isinstance(result["components"], list)
```

### Test Consistency Across Runs

```python
def test_interface_determinism():
    """Ensure same interface produces identical results"""
    interface = {"productName": "productName", "signal": "signalWord"}

    # Run multiple times
    results = []
    for _ in range(5):
        result = fill_fields(interface, pdf_text)
        results.append(json.dumps(result, sort_keys=True))

    # All results should be identical
    assert all(r == results[0] for r in results)
```

## 📊 Test Execution Options

### Using the Test Runner Script

```bash
# Run specific test categories
python test_runner.py --test-type basic
python test_runner.py --test-type performance
python test_runner.py --test-type edge-cases
python test_runner.py --test-type consistency
python test_runner.py --test-type interface-variations

# Generate coverage report
python test_runner.py --test-type all --generate-coverage

# Verbose output
python test_runner.py --test-type all --verbose
```

### Using Pytest Directly

```bash
# Run all tests
pytest -v

# Run specific test class
pytest test_pdf_scrapper.py::TestInterfaceVariations -v

# Run with coverage
pytest --cov=main --cov-report=html

# Run only fast tests (skip performance tests)
pytest -m "not performance" -v

# Run specific test method
pytest test_pdf_scrapper.py::TestInterfaceVariations::test_original_interface -v
```

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    smoke: Basic smoke tests
```

### Custom Fixtures

The test suite includes several fixtures for consistent testing:

- `sample_pdf_text` - Sample SDS document text
- `sample_ts_interfaces` - Various interface configurations
- `mock_pdf_document` - Mocked PDF document for isolated testing

## 📈 Expected Test Outputs

### Successful Test Run

```
✅ Original interface produces correct structure
✅ Simplified interface extracts basic fields
✅ Complex nested interface handles deep nesting
✅ Array-only interface processes lists correctly
✅ Same interface produces identical results across runs
✅ Performance tests complete within time limits
```

### Sample Output Structure

```json
{
  "productName": "XXXXX Regular-Bleach1",
  "hazard": {
    "signalWord": "Danger",
    "hazardStatements": [
      "Causes severe skin burns and eye damage",
      "Causes serious eye damage"
    ]
  },
  "ingredients": [
    {
      "chemicalName": "Sodium hypochlorite",
      "casNumber": "7681-52-9",
      "weightPercent": "5 - 10"
    }
  ]
}
```

## 🚨 Common Issues and Solutions

### Missing Dependencies

```bash
# Install required packages
pip install pytest pytest-cov psutil
```

### Missing Test Files

```bash
# Create sample files
python test_runner.py --create-files
```

### Import Errors

```bash
# Ensure main.py and parse_ts_interface.py are in the same directory
# Check that all required modules are available
```

### Performance Test Timeouts

```bash
# Run performance tests separately with longer timeout
pytest test_performance_edge_cases.py -m performance --timeout=600
```

## 📝 Adding New Tests

### Testing a New Interface Type

```python
def test_your_custom_interface():
    """Test your specific interface structure"""
    your_interface = {
        # Your interface structure
        "customField": "productName",
        "nestedData": {
            "subField": "signalWord"
        }
    }

    result = fill_fields(your_interface, sample_pdf_text)

    # Add your specific assertions
    assert "customField" in result
    assert result["customField"] == "XXXXX Regular-Bleach"
    assert "nestedData" in result
    assert isinstance(result["nestedData"], dict)
```

### Testing Edge Cases

```python
def test_your_edge_case():
    """Test specific edge case for your use case"""
    problematic_text = "Your problematic input here"

    result = fill_fields(your_interface, problematic_text)

    # Should handle gracefully
    assert isinstance(result, dict)
    # Add specific validations
```

## 📊 Test Metrics

The test suite tracks:

- **Interface Compatibility** - How many interface types work correctly
- **Consistency Score** - Percentage of identical results across runs
- **Performance Benchmarks** - Processing time for various document sizes
- **Error Handling** - Graceful handling of malformed inputs
- **Coverage** - Code coverage percentage

## 🎯 Test Goals

1. **Determinism** - Same interface + same PDF = same output every time
2. **Flexibility** - Support for arbitrary TypeScript interface structures
3. **Robustness** - Graceful handling of malformed or edge case inputs
4. **Performance** - Reasonable processing times for large documents
5. **Accuracy** - Correct extraction of data according to interface specifications

## 📞 Support

If tests fail or you need to add new test cases:

1. Check the test report in `test_report.json`
2. Run individual test categories to isolate issues
3. Use `--verbose` flag for detailed output
4. Add new test cases following the existing patterns

Run `python test_runner.py --help` for all available options.
