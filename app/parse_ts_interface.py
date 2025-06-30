import re
from typing import Dict, Any, List, Union


def parse_ts_interface(ts_code: str) -> Dict[str, Any]:
    """
    Parse TypeScript interface into a structured schema that preserves
    field names and types for dynamic extraction.
    
    Args:
        ts_code: TypeScript interface code as string
        
    Returns:
        Dictionary representing the interface structure with metadata
    """
    lines = ts_code.splitlines()
    schema_stack = []
    root = {}
    current = root
    key_stack = []

    for line in lines:
        original_line = line
        line = line.strip().rstrip(";")

        if not line or line.startswith("interface "):
            continue

        # Case: nested object with array (e.g., "substances: {")
        if re.match(r"\w+:\s*{\s*$", line):
            key = line.split(":")[0].strip()
            new_obj = {"_field_name": key, "_type": "object"}
            current[key] = new_obj
            schema_stack.append(current)
            key_stack.append(key)
            current = new_obj

        # Case: closing a nested object that's an array
        elif line == "}[]":
            last_key = key_stack.pop() if key_stack else "unknown"
            parent = schema_stack.pop()
            # Mark this as an array of objects
            current["_type"] = "array_of_objects"
            current = parent

        # Case: closing a nested object
        elif line == "}":
            if schema_stack:
                current = schema_stack.pop()
                if key_stack:
                    key_stack.pop()

        # Case: simple field with type
        elif ":" in line:
            key, val_type = map(str.strip, line.split(":"))
            
            # Create field metadata
            field_info = {
                "_field_name": key,
                "_type": _normalize_type(val_type),
                "_original_type": val_type
            }
            
            current[key] = field_info

    return root


def _normalize_type(type_str: str) -> str:
    """Normalize TypeScript types to Python-friendly types"""
    type_str = type_str.strip()
    
    if type_str.endswith("[]"):
        return "array"
    elif type_str == "string":
        return "string"
    elif type_str == "number":
        return "number"
    elif type_str == "boolean":
        return "boolean"
    else:
        return "string"  # Default to string for unknown types


def get_all_field_names(schema: Dict[str, Any]) -> List[str]:
    """
    Extract all field names from the parsed schema for search purposes.
    
    Args:
        schema: Parsed TypeScript interface schema
        
    Returns:
        List of all field names in the interface
    """
    field_names = []
    
    def _extract_names(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not key.startswith("_"):  # Skip metadata fields
                    field_names.append(key)
                    if isinstance(value, dict) and "_field_name" in value:
                        field_names.append(value["_field_name"])
                    _extract_names(value)
    
    _extract_names(schema)
    return list(set(field_names))  # Remove duplicates
