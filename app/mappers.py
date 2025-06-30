"""
Schema mapping utilities for dynamic field mapping.
Handles mapping between extracted data and TypeScript interface structures.
"""
from .extractors import extract_ingredient_data, extract_product_name, extract_signal_word, extract_hazard_statements


def map_schema_to_data(schema, text, current_key=None):
    """
    Dynamically map schema structure to extracted data.
    
    Args:
        schema: The schema structure (dict, list, or string)
        text: The text to extract data from
        current_key: The current key being processed (for context)
    
    Returns:
        Filled data structure matching the schema
    """
    if isinstance(schema, dict):
        return _map_object_schema(schema, text)
    elif isinstance(schema, list):
        return _map_array_schema(schema, text, current_key)
    else:
        return _map_primitive_schema(schema, text)


def _map_object_schema(schema, text):
    """Map object schema to data"""
    result = {}
    for key, value in schema.items():
        result[key] = map_schema_to_data(value, text, key)
    return result


def _map_array_schema(schema, text, current_key):
    """Map array schema to data"""
    if not schema:
        return []
    
    # Determine what type of array this is based on the schema structure
    array_item_schema = schema[0]
    
    if isinstance(array_item_schema, dict):
        field_names = list(array_item_schema.keys())
        extraction_strategy = _determine_extraction_strategy(field_names)
        
        if extraction_strategy == 'ingredients':
            ingredients = extract_ingredient_data(text)
            return _map_ingredients_to_schema(ingredients, array_item_schema, text)
        elif extraction_strategy == 'hazards':
            hazard_statements = extract_hazard_statements(text)
            return _map_hazards_to_schema(hazard_statements, array_item_schema)
    
    return []


def _map_primitive_schema(schema_value, text):
    """Map primitive schema values to extracted data"""
    if isinstance(schema_value, str):
        key_lower = schema_value.lower()
        
        if "productname" in key_lower:
            return extract_product_name(text)
        elif "signalword" in key_lower:
            return extract_signal_word(text)
        elif "hazardstatement" in key_lower:
            return extract_hazard_statements(text)
    
    return None


def _determine_extraction_strategy(field_names):
    """
    Dynamically determine extraction strategy based on actual field names
    in the TypeScript interface.
    """
    field_names_lower = [name.lower() for name in field_names]
    
    # Check for chemical/ingredient indicators
    chemical_indicators = {'component', 'chemical', 'substance', 'cas', 'reach', 'ec'}
    has_chemical_fields = any(
        any(indicator in field for indicator in chemical_indicators)
        for field in field_names_lower
    )
    
    # Check for hazard indicators
    hazard_indicators = {'hazard', 'statement', 'warning', 'danger'}
    has_hazard_fields = any(
        any(indicator in field for indicator in hazard_indicators)
        for field in field_names_lower
    )
    
    if has_chemical_fields:
        return 'ingredients'
    elif has_hazard_fields:
        return 'hazards'
    else:
        return 'unknown'


def _map_ingredients_to_schema(ingredients, schema_item, text=""):
    """Map ingredient data to schema structure"""
    if not ingredients:
        return []
    
    result = []
    for ingredient_data in ingredients:
        item = {}
        
        for field_name, field_schema in schema_item.items():
            mapped_value = _map_ingredient_field(field_name, ingredient_data, text)
            item[field_name] = mapped_value
        
        result.append(item)
    
    return result


def _map_ingredient_field(field_name, ingredient_data, text=""):
    """Map a single ingredient field based on field name"""
    field_lower = field_name.lower()
    
    # Direct mapping based on field name patterns
    if any(term in field_lower for term in ['component', 'name', 'substance', 'chemical']):
        return ingredient_data.get('component', '')
    elif 'cas' in field_lower:
        return ingredient_data.get('cas_number', '')
    elif 'reach' in field_lower:
        return ingredient_data.get('reach_number', '')
    elif any(term in field_lower for term in ['weight', 'percent', 'concentration']):
        return ingredient_data.get('weight_percent', '')
    elif 'ec' in field_lower:
        return ingredient_data.get('ec_number', '')
    elif any(term in field_lower for term in ['classification', 'class']):
        return ingredient_data.get('classification', '')
    else:
        # Try to extract from text as fallback
        return _extract_field_from_text(field_name, text)


def _map_hazards_to_schema(hazard_statements, schema_item):
    """Map hazard statements to schema structure"""
    # For hazard arrays, typically we just return the statements
    # The schema structure determines how they're organized
    return hazard_statements


def _extract_field_from_text(field_name, text):
    """Extract field value from text using field name as hint"""
    # This is a fallback for unmapped fields
    # Could be extended with more sophisticated extraction logic
    return None
