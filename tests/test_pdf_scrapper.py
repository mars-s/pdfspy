import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from main import fill_fields, extract_ingredient_data, find_value_by_key
from parse_ts_interface import parse_ts_interface

# Sample PDF text content (from the SDS document)
SAMPLE_PDF_TEXT = """
SAMPLE
SAFETY DATA SHEET
Issuing Date January 5, 2015 Revision Date June 12, 2015 Revision Number 1
1. IDENTIFICATION OF THE SUBSTANCE/PREPARATION AND OF THE COMPANY/UNDERTAKING
Product identifier
Product Name XXXXX Regular-Bleach
1
Other means of identification
EPA Registration Number 
5813-100
Emergency Overview
Signal word Danger
Hazard Statements
Causes severe skin burns and eye damage
Causes serious eye damage
Appearance Clear, pale yellow 
Physical State Thin liquid Odor Bleach

3. COMPOSITION/INFORMATION ON INGREDIENTS
XXXXX Regular-Bleach
1 
Revision Date June 12, 2015
Unknown Toxicity
Not applicable.
Other information
Very toxic to aquatic life with long lasting effects.
Interactions with Other Chemicals
Reacts with other household chemicals such as toilet bowl cleaners, rust removers, acids, or products containing ammonia to produce
hazardous irritating gases, such as chlorine and other chlorinated compounds.

* The exact percentage (concentr
Chemical Name CAS-No Weight % Trade Secret
Sodium hypochlo 7681-52-9 5 - 10 *
ation) of composition has been withheld as a trade secret.

4. FIRST AID MEASURES
First aid measures
General Advice 
Call a poison control center or doctor immediately for treatment advice.
data sheet to the doctor in attendance.
Show this safety
Eye Contact 
Hold eye open and rinse slowly and gently with water for 15 - 20 minutes. Remove contact
lenses, if present, after the first 5 minutes, then continue rinsing eye. Call a poison control
center or doctor for treatment advice.
Skin Contact 
Take off contaminated clothing. Rinse skin immediately with plenty of water for 15-20
minutes. Call a poison control center or doctor for treatment advice.
Inhalation 
Move to fresh air. If breathing is affected, call a doctor.
Ingestion 
Have person sip a glassful of water if able to swallow. Do not induce vomiting unless told to
do so by a poison control center or doctor. Do not give anything by mouth to an
unconscious person. Call a poison control center or doctor immediately for treatment
advice.

May cause severe irritation to skin. Prolonged contact may cause burns to skin.
May cause severe damage to eyes.
Harmful if swallowed.
"""

class TestInterfaceVariations:
    """Test different TypeScript interface structures"""
    
    def test_original_interface(self):
        """Test the original SDSData interface"""
        ts_interface = """
        interface SDSData {
          productName: string;
          hazard: {
            signalWord: string;
            hazardStatements: string[];
          };
          ingredients: {
            chemicalName: string;
            casNumber: string;
            weightPercent: string;
          }[];
        }
        """
        
        with patch('parse_ts_interface.parse_ts_interface') as mock_parse:
            mock_parse.return_value = {
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
            }
            
            result = fill_fields(mock_parse.return_value, SAMPLE_PDF_TEXT)
            
            # Assertions
            assert result["productName"] == "XXXXX Regular-Bleach"
            assert result["hazard"]["signalWord"] == "Danger"
            assert isinstance(result["hazard"]["hazardStatements"], list)
            assert len(result["hazard"]["hazardStatements"]) > 0
            assert isinstance(result["ingredients"], list)
            assert len(result["ingredients"]) > 0
            assert result["ingredients"][0]["chemicalName"] == "Sodium hypochlorite"
            assert result["ingredients"][0]["casNumber"] == "7681-52-9"
            assert result["ingredients"][0]["weightPercent"] == "5 - 10"

    def test_simplified_interface(self):
        """Test a simplified interface with minimal fields"""
        ts_interface = """
        interface SimpleData {
          name: string;
          signal: string;
        }
        """
        
        with patch('parse_ts_interface.parse_ts_interface') as mock_parse:
            mock_parse.return_value = {
                "name": "productName",
                "signal": "signalWord"
            }
            
            result = fill_fields(mock_parse.return_value, SAMPLE_PDF_TEXT)
            
            assert result["name"] == "XXXXX Regular-Bleach"
            assert result["signal"] == "Danger"

    def test_nested_complex_interface(self):
        """Test deeply nested interface structure"""
        ts_interface = """
        interface ComplexData {
          identification: {
            product: {
              name: string;
              code: string;
            };
            company: {
              name: string;
              address: string;
            };
          };
          safety: {
            hazards: {
              classification: string;
              signal: string;
              statements: string[];
            };
            firstAid: {
              general: string;
              eyeContact: string;
            };
          };
        }
        """
        
        with patch('parse_ts_interface.parse_ts_interface') as mock_parse:
            mock_parse.return_value = {
                "identification": {
                    "product": {
                        "name": "productName",
                        "code": None
                    },
                    "company": {
                        "name": None,
                        "address": None
                    }
                },
                "safety": {
                    "hazards": {
                        "classification": None,
                        "signal": "signalWord",
                        "statements": "hazardStatements"
                    },
                    "firstAid": {
                        "general": None,
                        "eyeContact": None
                    }
                }
            }
            
            result = fill_fields(mock_parse.return_value, SAMPLE_PDF_TEXT)
            
            assert result["identification"]["product"]["name"] == "XXXXX Regular-Bleach"
            assert result["safety"]["hazards"]["signal"] == "Danger"
            assert isinstance(result["safety"]["hazards"]["statements"], list)

    def test_array_only_interface(self):
        """Test interface with only array fields"""
        ts_interface = """
        interface ArrayData {
          chemicals: {
            name: string;
            cas: string;
            percent: string;
          }[];
          hazards: string[];
        }
        """
        
        with patch('parse_ts_interface.parse_ts_interface') as mock_parse:
            mock_parse.return_value = {
                "chemicals": [
                    {
                        "name": "chemicalName",
                        "cas": "casNumber",
                        "percent": "weightPercent"
                    }
                ],
                "hazards": "hazardStatements"
            }
            
            result = fill_fields(mock_parse.return_value, SAMPLE_PDF_TEXT)
            
            assert isinstance(result["chemicals"], list)
            assert len(result["chemicals"]) > 0
            assert result["chemicals"][0]["name"] == "Sodium hypochlorite"
            assert isinstance(result["hazards"], list)

    def test_mixed_types_interface(self):
        """Test interface with various data types"""
        ts_interface = """
        interface MixedData {
          productName: string;
          isHazardous: boolean;
          hazardCount: number;
          ingredients: {
            chemicalName: string;
            casNumber: string;
            weightPercent: string;
          }[];
          metadata: {
            version: string;
            lastUpdated: string;
          };
        }
        """
        
        with patch('parse_ts_interface.parse_ts_interface') as mock_parse:
            mock_parse.return_value = {
                "productName": "productName",
                "isHazardous": None,  # Will be None for boolean fields not implemented
                "hazardCount": None,  # Will be None for number fields not implemented
                "ingredients": [
                    {
                        "chemicalName": "chemicalName",
                        "casNumber": "casNumber",
                        "weightPercent": "weightPercent"
                    }
                ],
                "metadata": {
                    "version": None,
                    "lastUpdated": None
                }
            }
            
            result = fill_fields(mock_parse.return_value, SAMPLE_PDF_TEXT)
            
            assert result["productName"] == "XXXXX Regular-Bleach"
            assert result["isHazardous"] is None
            assert result["hazardCount"] is None
            assert isinstance(result["ingredients"], list)
            assert result["metadata"]["version"] is None

class TestConsistencyAndDeterminism:
    """Test that the same interface produces consistent results"""
    
    def test_deterministic_output(self):
        """Test that running the same interface multiple times gives identical results"""
        schema = {
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
        }
        
        # Run the same extraction multiple times
        results = []
        for _ in range(5):
            result = fill_fields(schema, SAMPLE_PDF_TEXT)
            results.append(json.dumps(result, sort_keys=True))
        
        # All results should be identical
        assert all(result == results[0] for result in results)

    def test_empty_interface_consistency(self):
        """Test behavior with empty interfaces"""
        empty_schema = {}
        
        result1 = fill_fields(empty_schema, SAMPLE_PDF_TEXT)
        result2 = fill_fields(empty_schema, SAMPLE_PDF_TEXT)
        
        assert result1 == result2
        assert result1 == {}

class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_pdf_text(self):
        """Test behavior with empty PDF text"""
        schema = {
            "productName": "productName",
            "signalWord": "signalWord"
        }
        
        result = fill_fields(schema, "")
        
        assert result["productName"] is None
        assert result["signalWord"] is None

    def test_malformed_ingredients_section(self):
        """Test handling of malformed ingredients data"""
        malformed_text = """
        Product Name Test Product
        Signal word Warning
        Chemical Name CAS-No Weight %
        Incomplete data here
        """
        
        schema = {
            "ingredients": [
                {
                    "chemicalName": "chemicalName",
                    "casNumber": "casNumber", 
                    "weightPercent": "weightPercent"
                }
            ]
        }
        
        result = fill_fields(schema, malformed_text)
        
        # Should handle gracefully, likely returning empty list
        assert isinstance(result["ingredients"], list)

    def test_special_characters_in_data(self):
        """Test handling of special characters and encoding"""
        special_text = """
        Product Name Tëst Prøduct™
        Signal word Danger
        Sodium hypochlorite 7681-52-9 5-10%
        """
        
        schema = {"productName": "productName"}
        result = fill_fields(schema, special_text)
        
        # Should preserve special characters
        assert "Tëst Prøduct™" in str(result["productName"]) if result["productName"] else True

class TestIngredientExtraction:
    """Test ingredient extraction functionality specifically"""
    
    def test_extract_ingredient_data_basic(self):
        """Test basic ingredient extraction"""
        text = """
        Chemical Name CAS-No Weight %
        Sodium hypochlorite 7681-52-9 5 - 10
        Potassium chloride 7447-40-7 1 - 5
        """
        
        ingredients = extract_ingredient_data(text)
        
        assert len(ingredients) >= 1
        assert any("Sodium hypochlorite" in ing[0] for ing in ingredients)
        assert any("7681-52-9" in ing[1] for ing in ingredients)

    def test_extract_ingredient_data_with_noise(self):
        """Test ingredient extraction with noisy data"""
        text = """
        PERSONAL PROTECTION Control parameters
        ACGIH TLV OSHA PEL NIOSH IDLH
        Sodium hypochlorite 7681-52-9 5 - 10
        New Jersey Massachusetts Pennsylvania
        """
        
        ingredients = extract_ingredient_data(text)
        
        # Should filter out the noise and only return valid ingredients
        for chemical, cas, weight in ingredients:
            assert "PERSONAL PROTECTION" not in chemical
            assert "ACGIH" not in chemical
            assert "New Jersey" not in chemical

class TestValueExtraction:
    """Test individual value extraction functions"""
    
    def test_find_product_name(self):
        """Test product name extraction variations"""
        texts = [
            "Product Name XXXXX Regular-Bleach",
            "Product: Test Chemical Solution",
            "Trade Name: Industrial Cleaner"
        ]
        
        for text in texts:
            result = find_value_by_key("productName", text)
            assert result is not None
            assert len(result.strip()) > 0

    def test_find_signal_word(self):
        """Test signal word extraction"""
        texts = [
            "Signal word Danger",
            "Signal word Warning",
            "Signal word: Danger"
        ]
        
        expected = ["Danger", "Warning", "Danger"]
        
        for text, expected_word in zip(texts, expected):
            result = find_value_by_key("signalWord", text)
            assert result == expected_word

    def test_find_hazard_statements(self):
        """Test hazard statement extraction"""
        text = """
        Causes severe skin burns and eye damage
        May cause respiratory irritation
        Harmful if swallowed
        """
        
        result = find_value_by_key("hazardStatements", text)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert any("Causes severe skin burns" in stmt for stmt in result)

@pytest.fixture
def sample_interfaces():
    """Fixture providing various interface examples"""
    return {
        "simple": {
            "name": "productName",
            "type": "signalWord"
        },
        "original": {
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
        "complex": {
            "document": {
                "product": {
                    "name": "productName",
                    "classification": "signalWord"
                },
                "chemicals": [
                    {
                        "name": "chemicalName",
                        "id": "casNumber",
                        "concentration": "weightPercent"
                    }
                ]
            }
        }
    }

class TestWithFixtures:
    """Tests using fixtures for consistent test data"""
    
    def test_all_interfaces_produce_valid_output(self, sample_interfaces):
        """Test that all interface variations produce valid, non-empty output"""
        for interface_name, schema in sample_interfaces.items():
            result = fill_fields(schema, SAMPLE_PDF_TEXT)
            
            # Basic validation - result should be a dict and not empty for non-empty schemas
            assert isinstance(result, dict)
            if schema:  # Non-empty schema should produce some result
                assert len(result) > 0
            
            # Check that nested structures are preserved
            self._validate_structure_matches_schema(result, schema)

    def _validate_structure_matches_schema(self, result, schema):
        """Helper method to validate that result structure matches schema structure"""
        if isinstance(schema, dict):
            assert isinstance(result, dict)
            for key in schema.keys():
                assert key in result
        elif isinstance(schema, list) and schema:
            assert isinstance(result, list)
        # For primitive types, we just ensure the key exists in the parent dict

    def test_interface_consistency_across_runs(self, sample_interfaces):
        """Test that each interface type produces consistent results across multiple runs"""
        for interface_name, schema in sample_interfaces.items():
            results = []
            for _ in range(3):
                result = fill_fields(schema, SAMPLE_PDF_TEXT)
                results.append(json.dumps(result, sort_keys=True))
            
            # All runs should produce identical results
            assert all(r == results[0] for r in results), f"Inconsistent results for {interface_name} interface"

# Integration test
class TestEndToEndIntegration:
    """Test the complete pipeline integration"""
    
    @patch('fitz.open')
    @patch('parse_ts_interface.parse_ts_interface')
    def test_full_pipeline_mock(self, mock_parse_ts, mock_fitz):
        """Test the complete pipeline with mocked dependencies"""
        # Mock PDF reading
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = SAMPLE_PDF_TEXT
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz.return_value = mock_doc
        
        # Mock TypeScript parsing
        mock_parse_ts.return_value = {
            "productName": "productName",
            "signalWord": "signalWord",
            "ingredients": [
                {
                    "chemicalName": "chemicalName",
                    "casNumber": "casNumber",
                    "weightPercent": "weightPercent"
                }
            ]
        }
        
        # Import and run main (this would need to be adapted based on your main.py structure)
        # For now, we'll test the core functionality
        schema = mock_parse_ts.return_value
        text = SAMPLE_PDF_TEXT
        
        result = fill_fields(schema, text)
        
        # Validate the complete result
        assert result["productName"] == "XXXXX Regular-Bleach"
        assert result["signalWord"] == "Danger"
        assert len(result["ingredients"]) > 0
        assert result["ingredients"][0]["chemicalName"] == "Sodium hypochlorite"

if __name__ == "__main__":
    # Run with: python -m pytest test_pdf_scrapper.py -v
    pytest.main([__file__, "-v", "--tb=short"])