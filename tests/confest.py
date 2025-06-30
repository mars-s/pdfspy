# conftest.py - Pytest configuration and shared fixtures
import pytest
import json
import os
from unittest.mock import MagicMock

# Sample SDS text for testing
SAMPLE_SDS_TEXT = """
SAMPLE SAFETY DATA SHEET
Product Name XXXXX Regular-Bleach
Signal word Danger
Hazard Statements
Causes severe skin burns and eye damage
Causes serious eye damage
May cause severe irritation to skin
Harmful if swallowed

Chemical Name CAS-No Weight %
Sodium hypochlorite 7681-52-9 5 - 10
"""

@pytest.fixture
def sample_pdf_text():
    """Fixture providing sample PDF text content"""
    return SAMPLE_SDS_TEXT

@pytest.fixture
def sample_ts_interfaces():
    """Fixture providing various TypeScript interface schemas"""
    return {
        "minimal": {
            "name": "productName"
        },
        "basic": {
            "productName": "productName",
            "signalWord": "signalWord"
        },
        "standard": {
            "productName": "productName",
            "hazard": {
                "signalWord": "signalWord",
                "hazardStatements": "hazardStatements"
            },
            "ingredients": [
                {
                    "chemicalName": "chemicalName",
                    "casNumber": "casNumber",
                    "weightPercent": "weightPercent"
                }
            ]
        },
        "nested": {
            "document": {
                "identification": {
                    "productName": "productName"
                },
                "hazards": {
                    "classification": "signalWord",
                    "statements": "hazardStatements"
                }
            }
        },
        "arrays_only": {
            "chemicals": [
                {
                    "name": "chemicalName",
                    "cas": "casNumber",
                    "percent": "weightPercent"
                }
            ],
            "hazards": "hazardStatements"
        }
    }

@pytest.fixture
def mock_pdf_document():
    """Fixture providing a mocked PDF document"""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = SAMPLE_SDS_TEXT
    mock_doc.__iter__.return_value = [mock_page]
    return mock_doc

# pytest.ini configuration content (save as separate file)
PYTEST_INI_CONTENT = """
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
    slow: Tests that take a long time to run
    smoke: Basic smoke tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
"""

# Performance and stress tests
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests") 
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "smoke: Smoke tests")

# Test utilities
class TestUtils:
    """Utility class for test helpers"""
    
    @staticmethod
    def assert_valid_json_structure(data, expected_keys=None):
        """Assert data is valid JSON structure with optional key validation"""
        assert isinstance(data, (dict, list))
        
        if expected_keys and isinstance(data, dict):
            for key in expected_keys:
                assert key in data, f"Expected key '{key}' not found in data"
    
    @staticmethod
    def assert_consistent_results(func, args, iterations=5):
        """Assert that a function produces consistent results across multiple calls"""
        results = []
        for _ in range(iterations):
            result = func(*args)
            results.append(json.dumps(result, sort_keys=True) if isinstance(result, (dict, list)) else result)
        
        assert all(r == results[0] for r in results), "Function produced inconsistent results"
    
    @staticmethod
    def create_test_interface(interface_type="basic"):
        """Create test interface schemas"""
        interfaces = {
            "basic": {
                "productName": "productName",
                "signalWord": "signalWord"
            },
            "with_arrays": {
                "productName": "productName",
                "ingredients": [
                    {
                        "chemicalName": "chemicalName",
                        "casNumber": "casNumber",
                        "weightPercent": "weightPercent"
                    }
                ]
            },
            "deeply_nested": {
                "level1": {
                    "level2": {
                        "level3": {
                            "productName": "productName"
                        }
                    }
                }
            }
        }
        return interfaces.get(interface_type, interfaces["basic"])

# Custom assertions
def assert_extraction_quality(result, min_fields=1):
    """Assert that extraction result meets quality standards"""
    assert isinstance(result, dict)
    assert len(result) >= min_fields
    
    # Check for non-empty string values where applicable
    for key, value in result.items():
        if isinstance(value, str):
            assert value.strip(), f"Field '{key}' should not be empty"
        elif isinstance(value, list):
            assert len(value) >= 0  # Lists can be empty
        elif isinstance(value, dict):
            assert_extraction_quality(value, min_fields=0)  # Recursive check

def assert_ingredient_structure(ingredients):
    """Assert ingredient list has proper structure"""
    assert isinstance(ingredients, list)
    
    for ingredient in ingredients:
        assert isinstance(ingredient, dict)
        required_fields = ["chemicalName", "casNumber", "weightPercent"]
        
        for field in required_fields:
            assert field in ingredient
            if ingredient[field] is not None:
                assert isinstance(ingredient[field], str)
                assert ingredient[field].strip()  # Non-empty if not None

# Save pytest.ini content to file (for reference)
def create_pytest_ini_file():
    """Create pytest.ini configuration file"""
    with open("pytest.ini", "w") as f:
        f.write(PYTEST_INI_CONTENT)

if __name__ == "__main__":
    create_pytest_ini_file()
    print("Created pytest.ini configuration file")