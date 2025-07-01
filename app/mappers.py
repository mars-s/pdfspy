"""
Streamlined schema mapping for TypeScript interface structures.
Maps interface fields to extracted PDF data using intelligent field recognition.
"""
from typing import Dict, Any, List, Union
from .dynamic_extractor import extract_field_value, extract_array_from_interface, extract_fields_from_interface


def map_schema_to_data(schema: Dict[str, Any], text: str) -> Dict[str, Any]:
    """
    Efficiently map TypeScript interface schema to extracted PDF data.
    
    Args:
        schema: The parsed TypeScript interface schema
        text: The PDF text to extract data from
    
    Returns:
        JSON structure matching the TypeScript interface
    """
    result = {}
    
    for field_name, field_schema in schema.items():
        if field_name.startswith('_'):  # Skip metadata fields
            continue
        
        field_type = field_schema.get('_type', 'string')
        
        if field_type == 'object':
            # Recursively process nested objects
            nested_result = map_schema_to_data(field_schema, text)
            result[field_name] = nested_result
        
        elif field_type == 'array_of_objects':
            # Extract structured array data
            array_data = extract_array_from_interface(text, field_schema, field_name)
            result[field_name] = array_data
        
        elif field_type == 'array':
            # Extract simple array data
            array_items = extract_array_from_interface(text, field_schema, field_name)
            result[field_name] = array_items
        
        else:
            # Extract primitive values (string, number, boolean)
            value = extract_field_value(field_name, text, schema, field_name)
            result[field_name] = value if value is not None else _get_default_value(field_type)
    
    return result


def _get_default_value(field_type: str) -> Any:
    """Get appropriate default value for a field type."""
    defaults = {
        'number': 0,
        'boolean': False,
        'array': [],
        'array_of_objects': [],
        'object': {},
        'string': ""
    }
    return defaults.get(field_type, "")
