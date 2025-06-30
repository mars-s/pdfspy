import fitz
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

def fill_fields(schema, text, current_key=None):
    if isinstance(schema, dict):
        return {k: fill_fields(v, text, k) for k, v in schema.items()}
    elif isinstance(schema, list):
        # Handle different types of arrays based on context
        if current_key and "ingredient" in current_key.lower():
            # This is an ingredients array
            ingredients = extract_ingredient_data(text)
            return [{"chemicalName": c.strip(), "casNumber": cas, "weightPercent": w.strip()} 
                    for c, cas, w in ingredients]
        elif current_key and "hazardstatement" in current_key.lower():
            # This is a hazard statements array - should be strings
            return find_value_by_key(current_key, text)
        else:
            # Default case for unknown arrays
            return []
    else:
        return find_value_by_key(schema, text)

def main():
    # 1. Read the interface
    with open("interface.ts") as f:
        ts_code = f.read()

    schema = parse_ts_interface(ts_code)

    # 2. Extract text from PDF
    doc = fitz.open("sample.pdf")
    text = "\n".join(page.get_text() for page in doc)

    # 3. Fill schema
    data = fill_fields(schema, text)

    # 4. Output
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
