import warnings
warnings.filterwarnings("ignore", message="builtin type.*has no __module__ attribute")

import pymupdf
import re
import json
from parse_ts_interface import parse_ts_interface

def extract_ingredient_data(text):
    # More precise pattern for chemical ingredients
    pattern = re.compile(r"([A-Za-z][A-Za-z\s\-,\(\)]+?)\s+(\d{4,5}-\d{2}-\d{1})\s+([\d\.\-–\s%]+)", re.MULTILINE)
    matches = pattern.findall(text)
    
    # Filter out matches that contain unwanted text
    filtered_matches = []
    unwanted_keywords = [
        'PERSONAL PROTECTION', 'Control parameters', 'Exposure Guidelines',
        'ACGIH TLV', 'OSHA PEL', 'NIOSH IDLH', 'Inhalation',
        'IARC', 'NTP', 'CWA', 'Reportable', 'Quantities', 'Toxic Pollutants',
        'Priority Pollutants', 'Hazardous Substances', 'Right-to-Know',
        'New Jersey', 'Massachusetts', 'Pennsylvania', 'Rhode Island', 'Illinois',
        'Extremely Hazardous'
    ]
    
    for chemical, cas, weight in matches:
        chemical = chemical.strip()
        # Clean up chemical names by removing excessive newlines and whitespace
        chemical = re.sub(r'\s+', ' ', chemical)
        weight = weight.strip()
        
        # Skip if chemical name contains unwanted keywords
        if any(keyword.lower() in chemical.lower() for keyword in unwanted_keywords):
            continue
            
        # Skip entries that are clearly table headers or formatting
        if (chemical.startswith('X ') or 
            len(chemical) < 3 or 
            len(chemical) > 100 or
            chemical.lower().startswith('chemical name')):
            continue
        
        # Extract the actual chemical name (often the last part after various prefixes)
        chemical_parts = chemical.split('\n')
        if len(chemical_parts) > 1:
            # Take the last meaningful part as the chemical name
            for part in reversed(chemical_parts):
                part = part.strip()
                if part and len(part) > 3 and not part.startswith('Trade Secret'):
                    chemical = part
                    break
        
        # Remove common prefixes
        if chemical.startswith('Trade Secret '):
            chemical = chemical.replace('Trade Secret ', '').strip()
        
        # Handle incomplete chemical names (like "Sodium hypochlo" -> "Sodium hypochlorite")
        if chemical.endswith('hypochlo'):
            chemical = chemical + 'rite'
        
        if weight and weight not in ['-', '']:
            filtered_matches.append((chemical, cas, weight))
    
    return filtered_matches

def find_value_by_key(key: str, text: str):
    if key is None:
        return None
    key = key.lower()
    if "productname" in key:
        # Look for product name patterns
        patterns = [
            r"Product Name[:\s]+([^\n]+)",
            r"Product[:\s]+([^\n]+)",
            r"Trade Name[:\s]+([^\n]+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    elif "signalword" in key:
        match = re.search(r"Signal word[:\s]+(Danger|Warning)", text, re.IGNORECASE)
        return match.group(1).capitalize() if match else None
    elif "hazardstatement" in key:
        # Look for actual hazard statements, not ingredient data
        patterns = [
            r"(Causes\s+[^\n]+)",
            r"(May cause\s+[^\n]+)",
            r"(Fatal if\s+[^\n]+)",
            r"(Harmful if\s+[^\n]+)",
            r"(Toxic if\s+[^\n]+)"
        ]
        statements = []
        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            for statement in found:
                statement = statement.strip()
                # Clean up incomplete statements and trailing punctuation
                if len(statement) > 10 and not statement.endswith(', '):
                    statements.append(statement)
        return statements if statements else []
    return None

def _is_ingredient_related(key):
    """Check if a key is related to ingredients/chemicals"""
    if not key:
        return False
    key_lower = key.lower()
    return any(term in key_lower for term in [
        'ingredient', 'chemical', 'component', 'substance', 'compound'
    ])

def _is_hazard_related(key):
    """Check if a key is related to hazards"""
    if not key:
        return False
    key_lower = key.lower()
    return any(term in key_lower for term in [
        'hazard', 'danger', 'warning', 'statement', 'risk'
    ])

def _map_ingredient_data(ingredients, schema_item, text=""):
    """Map ingredient data to the expected schema structure"""
    if not ingredients:
        return []
    
    result = []
    for chemical, cas, weight in ingredients:
        item = {}
        
        if isinstance(schema_item, dict):
            for key, value in schema_item.items():
                key_lower = key.lower()
                if any(term in key_lower for term in ['chemical', 'name', 'substance']):
                    item[key] = chemical.strip()
                elif any(term in key_lower for term in ['cas', 'number', 'registry']):
                    item[key] = cas
                elif any(term in key_lower for term in ['weight', 'percent', 'concentration', 'amount']):
                    item[key] = weight.strip()
                else:
                    # For unmapped fields, try to find the value using the mapped key
                    item[key] = find_value_by_key(value, text) if isinstance(value, str) else None
        else:
            # Default structure if schema_item is not a dict
            item = {"chemicalName": chemical.strip(), "casNumber": cas, "weightPercent": weight.strip()}
        
        result.append(item)
    
    return result

def _get_array_data(schema, text, current_key):
    """Get appropriate data for array fields based on context"""
    # Determine array type based on key name and schema structure
    if _is_ingredient_related(current_key):
        ingredients = extract_ingredient_data(text)
        return _map_ingredient_data(ingredients, schema[0] if schema else None, text)
    
    elif _is_hazard_related(current_key):
        hazard_data = find_value_by_key(current_key, text)
        # Ensure we always return a list for hazard arrays
        if hazard_data is None:
            return []
        elif isinstance(hazard_data, list):
            return hazard_data
        else:
            return [hazard_data] if hazard_data else []
    
    else:
        # For other array types, try to infer based on schema structure
        if schema and isinstance(schema[0], dict):
            # If it's an array of objects, check if any keys suggest ingredient data
            schema_keys = list(schema[0].keys())
            has_ingredient_keys = any(_is_ingredient_related(key) for key in schema_keys)
            has_hazard_keys = any(_is_hazard_related(key) for key in schema_keys)
            
            if has_ingredient_keys:
                ingredients = extract_ingredient_data(text)
                return _map_ingredient_data(ingredients, schema[0], text)
            elif has_hazard_keys:
                hazard_data = find_value_by_key('hazardStatements', text)
                if isinstance(hazard_data, list):
                    return [schema[0] for _ in hazard_data] if hazard_data else []
                return []
        
        # Default: return empty array
        return []

def fill_fields(schema, text, current_key=None):
    """
    Dynamically fill schema fields with extracted text data.
    
    Args:
        schema: The schema structure (dict, list, or string)
        text: The text to extract data from
        current_key: The current key being processed (for context)
    
    Returns:
        Filled data structure matching the schema
    """
    if isinstance(schema, dict):
        # Recursively process dictionary fields
        result = {}
        for key, value in schema.items():
            result[key] = fill_fields(value, text, key)
        return result
    
    elif isinstance(schema, list):
        # Handle array fields
        return _get_array_data(schema, text, current_key)
    
    else:
        # Handle primitive fields (strings)
        return find_value_by_key(schema, text)

def main():
    # 1. Read the interface
    with open("interface.ts") as f:
        ts_code = f.read()

    schema = parse_ts_interface(ts_code)

    # 2. Extract text from PDF
    doc = pymupdf.open("samples/sample.pdf")
    text = "\n".join(page.get_text() for page in doc)

    # 3. Fill schema
    data = fill_fields(schema, text)

    # 4. Output
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
