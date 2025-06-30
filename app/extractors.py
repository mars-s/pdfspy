"""
Text extraction utilities for PDF parsing.
Handles extraction of ingredients, hazards, and other SDS data.
"""
import re


def extract_ingredient_data(text):
    """Extract ingredient data from the composition/ingredients section"""
    # Extract the table section specifically
    composition_match = re.search(
        r'3\.\s*Composition.*?3\.1\s*Substances(.*?)(?:3\.2|4\.)', 
        text, 
        re.DOTALL | re.IGNORECASE
    )
    
    table_section = composition_match.group(1) if composition_match else text
    
    # Try structured table data extraction
    ingredients = _extract_structured_ingredients(table_section)
    
    # Fallback to pattern matching if no structured data found
    if not ingredients:
        ingredients = _extract_pattern_ingredients(text)
    
    return ingredients


def _extract_structured_ingredients(table_section):
    """Extract ingredients from structured table format"""
    ingredients = []
    lines = table_section.split('\n')
    
    # Clean and filter lines
    clean_lines = [
        line.strip() for line in lines 
        if line.strip() and line.strip().lower() not in {
            'component', 'ec-no.', 'cas-no', 'weight', 'range', 
            'classification', 'reach', 'registration', 'number', '-', '%'
        }
    ]
    
    # Process lines to find component entries
    i = 0
    while i < len(clean_lines):
        line = clean_lines[i]
        
        # Look for chemical names
        if _is_chemical_name(line):
            component_name = line
            
            # Check for multi-line component names
            if i + 1 < len(clean_lines):
                next_line = clean_lines[i + 1]
                if _is_continuation_line(next_line, clean_lines, i):
                    component_name = f"{component_name} {next_line}"
                    i += 1
            
            # Extract associated data
            ingredient_data = _extract_ingredient_identifiers(clean_lines, i, component_name)
            if ingredient_data:
                ingredients.append(ingredient_data)
        
        i += 1
    
    return ingredients


def _extract_pattern_ingredients(text):
    """Fallback pattern-based ingredient extraction"""
    pattern = re.compile(
        r"([A-Za-z][A-Za-z\s\-,\(\)]+?)\s+(\d{3,5}-\d{2}-\d{1})\s+([\d\.\-–\s%]+)", 
        re.MULTILINE
    )
    matches = pattern.findall(text)
    
    ingredients = []
    unwanted_keywords = {
        'PERSONAL PROTECTION', 'Control parameters', 'Exposure Guidelines',
        'ACGIH TLV', 'OSHA PEL', 'NIOSH IDLH', 'Inhalation',
        'IARC', 'NTP', 'CWA', 'Reportable', 'Quantities', 'Toxic Pollutants'
    }
    
    for chemical, cas, weight in matches:
        chemical = re.sub(r'\s+', ' ', chemical.strip())
        weight = weight.strip()
        
        if any(keyword.lower() in chemical.lower() for keyword in unwanted_keywords):
            continue
        
        if weight and weight not in ['-', '']:
            ingredients.append({
                'component': chemical,
                'cas_number': cas,
                'weight_percent': weight
            })
    
    return ingredients


def _is_chemical_name(line):
    """Check if line looks like a chemical name"""
    return (
        re.match(r'^[A-Za-z][A-Za-z\s\-,\(\)]*$', line) and 
        len(line) > 3
    )


def _is_continuation_line(next_line, clean_lines, current_index):
    """Check if next line continues the component name"""
    if not _is_chemical_name(next_line) or re.match(r'^\d', next_line):
        return False
    
    # Check if line after that is a number pattern (EC or CAS)
    if current_index + 2 < len(clean_lines):
        return re.match(r'^\d{3}-\d{3}-\d{1}$', clean_lines[current_index + 2])
    
    return False


def _extract_ingredient_identifiers(clean_lines, start_index, component_name):
    """Extract EC, CAS, weight, and REACH data for a component"""
    ec_number = None
    cas_number = None
    weight_percent = None
    reach_number = None
    
    # Look ahead for identifiers
    for j in range(start_index + 1, min(start_index + 15, len(clean_lines))):
        check_line = clean_lines[j]
        
        # EC number pattern (like 205-633-8)
        if re.match(r'^\d{3}-\d{3}-\d{1}$', check_line):
            ec_number = check_line
        
        # CAS number pattern (like 144-55-8)
        elif re.match(r'^\d{2,4}-\d{2}-\d{1}$', check_line):
            cas_number = check_line
        
        # Weight percentage
        elif re.match(r'^[\d\-\.%\s]+$', check_line) and any(char.isdigit() for char in check_line):
            if not weight_percent and len(check_line) < 20:
                weight_percent = check_line
        
        # REACH registration number
        elif re.match(r'^\d{2}-\d{10}-\d{2}-\w*', check_line):
            reach_number = check_line
        
        # Stop if we hit another component name
        elif (_is_chemical_name(check_line) and 
              len(check_line) > 10 and 
              not any(term in check_line.lower() for term in ['classified', 'not', 'danger', 'warning'])):
            break
    
    # Return data if we found at least component name and CAS number
    if component_name and cas_number:
        return {
            'component': component_name,
            'ec_number': ec_number,
            'cas_number': cas_number,
            'weight_percent': weight_percent,
            'reach_number': reach_number
        }
    
    return None


def extract_product_name(text):
    """Extract product name from text"""
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


def extract_signal_word(text):
    """Extract signal word from text"""
    match = re.search(r"Signal word[:\s]+(Danger|Warning)", text, re.IGNORECASE)
    return match.group(1).capitalize() if match else None


def extract_hazard_statements(text):
    """Extract hazard statements from text"""
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
            # Clean up incomplete statements
            if len(statement) > 10 and not statement.endswith(', '):
                statements.append(statement)
    
    return statements if statements else []
