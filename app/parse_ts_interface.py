"""
Enhanced TypeScript interface parser for dynamic field extraction.
Parses TS interfaces and provides rich metadata for intelligent field matching.
"""
import re
from typing import Dict, Any, List, Union


def parse_ts_interface(ts_code: str) -> Dict[str, Any]:
    """
    Parse TypeScript interface into a structured schema with rich metadata.
    
    Args:
        ts_code: TypeScript interface code as string
        
    Returns:
        Dictionary representing the interface structure with metadata for extraction
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

        # Handle nested objects with arrays (e.g., "substances: {")
        if re.match(r"\w+:\s*{\s*$", line):
            key = line.split(":")[0].strip()
            new_obj = {
                "_field_name": key,
                "_type": "object",
                "_search_terms": _generate_search_terms(key)
            }
            current[key] = new_obj
            schema_stack.append(current)
            key_stack.append(key)
            current = new_obj

        # Handle closing nested object that's an array
        elif line == "}[]":
            last_key = key_stack.pop() if key_stack else "unknown"
            parent = schema_stack.pop()
            current["_type"] = "array_of_objects"
            current = parent

        # Handle closing nested object
        elif line == "}":
            if schema_stack:
                current = schema_stack.pop()
                if key_stack:
                    key_stack.pop()

        # Handle simple field with type
        elif ":" in line:
            key, val_type = map(str.strip, line.split(":", 1))
            
            # Create rich field metadata
            field_info = {
                "_field_name": key,
                "_type": _normalize_type(val_type),
                "_original_type": val_type,
                "_search_terms": _generate_search_terms(key),
                "_priority": _get_field_priority(key)
            }
            
            current[key] = field_info

    return root


def _normalize_type(type_str: str) -> str:
    """Normalize TypeScript types to extraction-friendly types."""
    type_str = type_str.strip()
    
    if type_str.endswith("[]"):
        return "array"
    elif type_str in ["string", "String"]:
        return "string"
    elif type_str in ["number", "Number"]:
        return "number"
    elif type_str in ["boolean", "Boolean"]:
        return "boolean"
    else:
        return "string"  # Default to string for custom types


def _generate_search_terms(field_name: str) -> List[str]:
    """
    Generate intelligent search terms for a field name.
    These help the NLP extractor find relevant text sections.
    """
    terms = [field_name]
    
    # Convert camelCase to readable variations
    readable = re.sub(r'([a-z])([A-Z])', r'\1 \2', field_name)
    if readable != field_name:
        terms.extend([readable, readable.lower(), readable.upper(), readable.title()])
    
    # Add common formatting variations
    terms.extend([
        field_name.lower(),
        field_name.upper(),
        field_name.replace('_', ' '),
        field_name.replace('-', ' '),
        re.sub(r'([a-z])([A-Z])', r'\1-\2', field_name).lower(),  # kebab-case
        re.sub(r'([a-z])([A-Z])', r'\1_\2', field_name).lower(),  # snake_case
    ])
    
    # Add semantic alternatives based on field name
    semantic_map = {
        # Product information
        'productname': ['product name', 'product', 'name', 'title', 'product title'],
        'name': ['product name', 'product', 'title', 'identifier', 'designation'],
        'manufacturer': ['supplier', 'company', 'producer', 'vendor', 'distributor'],
        'version': ['revision', 'ver', 'version number', 'rev'],
        
        # Chemical information
        'cas': ['cas number', 'cas no', 'cas-no', 'cas registry number'],
        'component': ['substance', 'ingredient', 'chemical', 'material', 'compound'],
        'substance': ['component', 'ingredient', 'chemical', 'material'],
        'reach_registration_number': ['reach no', 'reach number', 'reach reg', 'ec number'],
        
        # Safety information
        'hazard': ['danger', 'warning', 'safety', 'risk'],
        'signalword': ['signal word', 'signal', 'warning word'],
        'hazardstatements': ['hazard statements', 'h-statements', 'h statements', 'dangers'],
        
        # Quantities and measurements
        'percentage': ['percent', '%', 'concentration', 'weight', 'content'],
        'weight': ['mass', 'amount', 'quantity', 'percentage', '%'],
        'concentration': ['content', 'percentage', 'amount', '%'],
    }
    
    field_lower = field_name.lower()
    # Check for exact matches and partial matches
    for key, alternatives in semantic_map.items():
        if key in field_lower or field_lower in key:
            terms.extend(alternatives)
    
    # Remove duplicates and empty terms
    unique_terms = []
    seen = set()
    for term in terms:
        term_clean = term.strip()
        if term_clean and term_clean not in seen:
            seen.add(term_clean)
            unique_terms.append(term_clean)
    
    return unique_terms


def _get_field_priority(field_name: str) -> int:
    """
    Assign priority to fields for extraction ordering.
    Higher priority fields are extracted first.
    """
    field_lower = field_name.lower()
    
    # High priority - core identification fields
    if any(term in field_lower for term in ['name', 'product', 'manufacturer', 'supplier']):
        return 3
    
    # Medium priority - important data fields  
    if any(term in field_lower for term in ['cas', 'component', 'substance', 'hazard', 'version']):
        return 2
    
    # Low priority - supplementary fields
    return 1


def get_all_field_names(schema: Dict[str, Any]) -> List[str]:
    """
    Extract all field names from the parsed schema for comprehensive search.
    
    Args:
        schema: Parsed TypeScript interface schema
        
    Returns:
        List of all field names with their search terms
    """
    all_terms = []
    
    def _extract_terms(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not key.startswith("_"):  # Skip metadata
                    all_terms.append(key)
                    if isinstance(value, dict):
                        # Add search terms if available
                        search_terms = value.get("_search_terms", [])
                        all_terms.extend(search_terms)
                        _extract_terms(value)
    
    _extract_terms(schema)
    return list(set(all_terms))  # Remove duplicates


def get_field_search_terms(schema: Dict[str, Any], field_name: str) -> List[str]:
    """
    Get search terms for a specific field from the schema.
    
    Args:
        schema: Parsed TypeScript interface schema
        field_name: Name of the field to get search terms for
        
    Returns:
        List of search terms for the field
    """
    def _find_field_terms(obj, target_field):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == target_field and isinstance(value, dict):
                    return value.get("_search_terms", [])
                elif isinstance(value, dict):
                    result = _find_field_terms(value, target_field)
                    if result:
                        return result
        return []
    
    return _find_field_terms(schema, field_name)
