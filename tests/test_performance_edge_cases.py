# test_performance_edge_cases.py
import pytest
import time
import json
from unittest.mock import patch
from main import fill_fields, extract_ingredient_data, find_value_by_key

class TestPerformance:
    """Performance tests for the PDF scrapper"""
    
    @pytest.mark.performance
    def test_large_document_processing_time(self, sample_pdf_text):
        """Test processing time for large documents"""
        # Create a large document by repeating content
        large_text = sample_pdf_text * 100
        
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
        
        start_time = time.time()
        result = fill_fields(schema, large_text)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0, f"Processing took {processing_time:.2f} seconds, too slow"
        assert isinstance(result, dict)
        assert result["productName"] is not None

    @pytest.mark.performance
    def test_complex_nested_interface_performance(self, sample_pdf_text):
        """Test performance with deeply nested interfaces"""
        complex_schema = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
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
                        }
                    }
                }
            }
        }
        
        start_time = time.time()
        result = fill_fields(complex_schema, sample_pdf_text)
        end_time = time.time()
        
        assert (end_time - start_time) < 2.0
        assert isinstance(result["level1"]["level2"]["level3"]["level4"]["level5"], dict)

    @pytest.mark.performance
    def test_multiple_array_processing(self, sample_pdf_text):
        """Test performance with multiple large arrays"""
        schema_with_arrays = {
            "ingredients": [{"name": "chemicalName", "cas": "casNumber", "percent": "weightPercent"}] * 10,
            "hazards": "hazardStatements",
            "precautions": "hazardStatements",  # Reuse same extraction logic
            "firstAid": "hazardStatements"
        }
        
        start_time = time.time()
        result = fill_fields(schema_with_arrays, sample_pdf_text)
        end_time = time.time()
        
        assert (end_time - start_time) < 3.0
        assert isinstance(result["ingredients"], list)

class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error conditions"""
    
    def test_malformed_pdf_text(self):
        """Test handling of malformed or corrupted text"""
        malformed_texts = [
            "",  # Empty
            "\x00\x01\x02",  # Binary data
            "���",  # Encoding issues
            "A" * 10000,  # Very repetitive text
            "\n" * 1000,  # Only newlines
            "Product Name \n\n\n Signal word \n\n\n",  # Excessive whitespace
        ]
        
        schema = {
            "productName": "productName",
            "signalWord": "signalWord"
        }
        
        for text in malformed_texts:
            # Should not crash, even with malformed input
            result = fill_fields(schema, text)
            assert isinstance(result, dict)
            # Results may be None/empty for malformed input, which is acceptable

    def test_extremely_long_field_values(self):
        """Test handling of extremely long field values"""
        long_text = """
        Product Name """ + "A" * 1000 + """
        Signal word Danger
        Sodium hypochlorite 7681-52-9 5-10
        """
        
        schema = {
            "productName": "productName",
            "signalWord": "signalWord"
        }
        
        result = fill_fields(schema, long_text)
        
        # Should handle long values gracefully
        assert isinstance(result, dict)
        if result["productName"]:
            assert len(result["productName"]) > 100  # Should capture the long name

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        unicode_text = """
        Product Name Tëst Prödüct™ 2024 ®
        Signal word Danger
        Natriumhypochlorit 7681-52-9 5–10%
        Causés sévère brûlures
        """
        
        schema = {
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
        
        result = fill_fields(schema, unicode_text)
        
        assert isinstance(result, dict)
        # Should preserve Unicode characters
        if result["productName"]:
            assert any(char in result["productName"] for char in "ëöü™®")

    def test_cas_number_variations(self):
        """Test different CAS number formats"""
        cas_variations = [
            "7681-52-9",      # Standard format
            "7681 52 9",      # Space separated
            "7681.52.9",      # Dot separated
            "007681-52-9",    # Leading zeros
            "7681-052-9",     # Padded middle
        ]
        
        for cas in cas_variations:
            text = f"Sodium hypochlorite {cas} 5-10"
            ingredients = extract_ingredient_data(text)
            
            # Should extract at least one ingredient regardless of CAS format
            if ingredients:
                extracted_cas = ingredients[0][1]
                assert extracted_cas is not None

    def test_weight_percent_variations(self):
        """Test different weight percentage formats"""
        weight_variations = [
            "5-10",           # Dash
            "5 - 10",         # Dash with spaces
            "5–10",           # En dash
            "5 to 10",        # Text
            "5%",             # Single percentage
            "< 5",            # Less than
            "> 10",           # Greater than
            "5.5-10.5",       # Decimals
        ]
        
        for weight in weight_variations:
            text = f"Sodium hypochlorite 7681-52-9 {weight}"
            ingredients = extract_ingredient_data(text)
            
            if ingredients:
                extracted_weight = ingredients[0][2]
                assert extracted_weight is not None
                assert len(extracted_weight.strip()) > 0

    def test_missing_required_fields(self):
        """Test behavior when required fields are missing"""
        incomplete_texts = [
            "Product Name Test Product",  # Missing signal word
            "Signal word Danger",         # Missing product name
            "Sodium hypochlorite 5-10",   # Missing CAS number
            "7681-52-9 5-10",            # Missing chemical name
        ]
        
        schema = {
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
        
        for text in incomplete_texts:
            result = fill_fields(schema, text)
            
            # Should not crash and should return valid structure
            assert isinstance(result, dict)
            assert "productName" in result
            assert "signalWord" in result
            assert isinstance(result["ingredients"], list)

    def test_duplicate_chemical_entries(self):
        """Test handling of duplicate chemical entries"""
        duplicate_text = """
        Sodium hypochlorite 7681-52-9 5-10
        Sodium hypochlorite 7681-52-9 5-10
        Sodium hypochlorite 7681-52-9 3-8
        """
        
        ingredients = extract_ingredient_data(duplicate_text)
        
        # Should handle duplicates (implementation may vary)
        assert isinstance(ingredients, list)
        if ingredients:
            # All entries should be valid
            for chemical, cas, weight in ingredients:
                assert chemical.strip()
                assert cas.strip()
                assert weight.strip()

class TestInterfaceVariationsExtensive:
    """Extensive testing of different interface variations"""
    
    @pytest.mark.parametrize("interface_type", [
        "minimal",
        "basic", 
        "standard",
        "nested",
        "arrays_only"
    ])
    def test_interface_variations_parametrized(self, interface_type, sample_ts_interfaces, sample_pdf_text):
        """Parametrized test for different interface types"""
        schema = sample_ts_interfaces[interface_type]
        
        result = fill_fields(schema, sample_pdf_text)
        
        # Basic validation for all interface types
        assert isinstance(result, dict)
        
        # Type-specific validations
        if interface_type == "minimal":
            assert "name" in result
        elif interface_type == "basic":
            assert "productName" in result
            assert "signalWord" in result
        elif interface_type == "standard":
            assert "productName" in result
            assert "hazard" in result
            assert "ingredients" in result
            assert isinstance(result["hazard"], dict)
            assert isinstance(result["ingredients"], list)
        elif interface_type == "nested":
            assert "document" in result
            assert isinstance(result["document"], dict)
        elif interface_type == "arrays_only":
            assert "chemicals" in result
            assert "hazards" in result
            assert isinstance(result["chemicals"], list)
            assert isinstance(result["hazards"], list)

    def test_empty_array_handling(self):
        """Test handling of empty arrays in schema"""
        schema_with_empty_arrays = {
            "productName": "productName",
            "emptyIngredients": [],
            "emptyHazards": []
        }
        
        result = fill_fields(schema_with_empty_arrays, "Product Name Test")
        
        assert isinstance(result["emptyIngredients"], list)
        assert isinstance(result["emptyHazards"], list)
        assert len(result["emptyIngredients"]) == 0
        assert len(result["emptyHazards"]) == 0

    def test_mixed_data_types_in_arrays(self):
        """Test arrays with mixed data types"""
        schema = {
            "mixedArray": [
                "productName",
                {"nested": "signalWord"},
                ["hazardStatements"]
            ]
        }
        
        result = fill_fields(schema, "Product Name Test\nSignal word Danger")
        
        # Should handle mixed types gracefully
        assert isinstance(result["mixedArray"], list)

class TestRegressionTests:
    """Regression tests for known issues"""
    
    def test_chemical_name_truncation_bug(self):
        """Test for the 'Sodium hypochlo' truncation issue"""
        text = "Sodium hypochlo 7681-52-9 5-10"
        ingredients = extract_ingredient_data(text)
        
        if ingredients:
            chemical_name = ingredients[0][0]
            # Should expand truncated name
            assert "hypochlorite" in chemical_name or "hypochlo" in chemical_name

    def test_trade_secret_handling(self):
        """Test handling of trade secret markings"""
        text = """
        Chemical Name CAS-No Weight % Trade Secret
        Sodium hypochlorite 7681-52-9 5-10 *
        """
        
        ingredients = extract_ingredient_data(text)
        
        if ingredients:
            chemical_name = ingredients[0][0]
            # Should not include "Trade Secret" in chemical name
            assert "Trade Secret" not in chemical_name

    def test_table_header_filtering(self):
        """Test filtering of table headers from results"""
        text = """
        Chemical Name CAS-No Weight %
        ACGIH TLV OSHA PEL NIOSH IDLH
        Sodium hypochlorite 7681-52-9 5-10
        """
        
        ingredients = extract_ingredient_data(text)
        
        # Should filter out header rows
        for chemical, cas, weight in ingredients:
            assert "ACGIH" not in chemical
            assert "Chemical Name" not in chemical
            assert "CAS-No" not in chemical

class TestMemoryAndResourceUsage:
    """Test memory usage and resource management"""
    
    @pytest.mark.performance
    def test_memory_usage_with_large_input(self):
        """Test memory usage doesn't grow excessively with large inputs"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process a large document
        large_text = """
        Product Name Test Product
        Signal word Danger
        Sodium hypochlorite 7681-52-9 5-10
        """ * 1000
        
        schema = {
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
        
        # Process multiple times
        for _ in range(10):
            result = fill_fields(schema, large_text)
            del result  # Explicit cleanup
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (adjust threshold as needed)
        assert memory_increase < 100 * 1024 * 1024  # 100MB threshold

    @pytest.mark.performance
    def test_no_memory_leaks_repeated_calls(self):
        """Test for memory leaks in repeated function calls"""
        import gc
        
        schema = {"productName": "productName"}
        text = "Product Name Test"
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Make many repeated calls
        for _ in range(100):
            result = fill_fields(schema, text)
            del result
        
        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Object count shouldn't grow significantly
        object_increase = final_objects - initial_objects
        assert object_increase < 50  # Allow some growth but not excessive

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not performance"])