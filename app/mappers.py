"""
Streamlined schema mapping for TypeScript interface structures.
Maps interface fields to extracted PDF data using intelligent field recognition.
"""
from typing import Dict, Any, List, Union
from .dynamic_extractor import extract_fields_from_interface


def map_schema_to_data(schema: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Efficiently map TypeScript interface schema to extracted PDF data.
    
    Args:
        schema: The parsed TypeScript interface schema
        content: The PDF content dictionary containing 'text' key
    
    Returns:
        JSON structure matching the TypeScript interface
    """
    # Extract text from content
    text = content.get('text', '') if isinstance(content, dict) else str(content)
    
    # Use the new dynamic extractor
    return extract_fields_from_interface(text, schema)


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
