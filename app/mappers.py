"""
Dynamic schema mapping utilities.
Maps TypeScript interface structures to extracted PDF data using field names.
"""
from typing import Dict, Any, List, Union
from .dynamic_extractor import extract_field_value, extract_array_values


def map_schema_to_data(schema: Dict[str, Any], text: str) -> Dict[str, Any]:
    """
    Dynamically map schema structure to extracted data based on field names.
    
    Args:
        schema: The parsed TypeScript interface schema
        text: The text to extract data from
    
    Returns:
        Filled data structure matching the schema
    """
    result = {}
    
    for field_name, field_schema in schema.items():
        if field_name.startswith('_'):  # Skip metadata fields
            continue
        
        field_type = field_schema.get('_type', 'string')
        
        if field_type == 'object':
            # Recursively process nested objects
            result[field_name] = map_schema_to_data(field_schema, text)
        
        elif field_type == 'array_of_objects':
            # Extract array of objects
            result[field_name] = extract_array_values(field_name, text, field_schema)
        
        elif field_type == 'array':
            # Extract simple array
            array_items = extract_array_values(field_name, text, field_schema)
            # For simple arrays, extract just the values
            if array_items and isinstance(array_items[0], dict):
                # If we got objects but expected simple array, extract first value of each
                result[field_name] = [list(item.values())[0] if item else "" for item in array_items]
            else:
                result[field_name] = array_items or []
        
        else:
            # Extract primitive values
            value = extract_field_value(field_name, text, field_type)
            result[field_name] = value if value is not None else _get_default_value(field_type)
    
    return result


def _get_default_value(field_type: str) -> Any:
    """Get default value for a field type"""
    if field_type == 'number':
        return 0
    elif field_type == 'boolean':
        return False
    elif field_type == 'array':
        return []
    else:
        return ""
