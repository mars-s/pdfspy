"""
Dynamic field extraction based on TypeScript interface field names.
Searches PDF text for field names and extracts corresponding values.
"""
import re
from typing import Dict, Any, List, Optional, Union


def extract_field_value(field_name: str, text: str, field_type: str = "string") -> Any:
    """
    Extract a field value from text by searching for the field name.
    Uses smart analysis to adapt to different PDF formats.
    
    Args:
        field_name: The field name to search for
        text: The text to search in
        field_type: The expected type of the field
        
    Returns:
        Extracted value or None if not found
    """
    # First, try smart field search using PDF structure analysis
    smart_result = smart_field_search(field_name, text)
    if smart_result and smart_result.strip():
        return _convert_to_type(smart_result.strip(), field_type)
    
    # Fallback to pattern-based search
    patterns = _create_search_patterns(field_name)
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            # Extract the value based on the match
            value = _extract_value_from_match(match, field_type)
            if value and value.strip():
                return _convert_to_type(value, field_type)
    
    return None


def extract_array_values(field_name: str, text: str, array_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract array values from text based on the field name and schema.
    
    Args:
        field_name: The array field name
        text: The text to search in
        array_schema: Schema of array items
        
    Returns:
        List of extracted objects
    """
    # Find the section related to this field
    section_text = _find_field_section(field_name, text)
    if not section_text:
        return []
    
    # For arrays of objects, try to extract tabular data
    if array_schema.get("_type") == "array_of_objects":
        return _extract_tabular_data(section_text, array_schema)
    
    # For simple arrays, extract list items
    return _extract_list_items(section_text, field_name)


def _create_search_patterns(field_name: str) -> List[str]:
    """Create various search patterns for a field name"""
    patterns = []
    
    # Convert camelCase to different formats
    field_variations = _get_field_variations(field_name)
    
    for variation in field_variations:
        if not variation or len(variation) < 2:
            continue
            
        escaped_variation = re.escape(variation)
        
        # Pattern 1: Exact match followed by newline and value
        patterns.append(rf"{escaped_variation}\s*\n\s*([^\n]+?)(?=\n|$)")
        
        # Pattern 2: Field with colon/separator and value on same line
        patterns.append(rf"{escaped_variation}\s*[:=\-]\s*([^\n\r]+?)(?=\s{2,}|\n|$)")
        
        # Pattern 3: Field followed by any whitespace and value
        patterns.append(rf"{escaped_variation}\s+([A-Z0-9][^\n\r]*?)(?=\s{2,}|\n|$)")
        
        # Pattern 4: Flexible word boundary matching
        patterns.append(rf"\b{escaped_variation}\b\s*[:=\-]?\s*([^\n\r]+?)(?=\n|$)")
        
        # Pattern 5: Case insensitive partial matching for compound terms
        if len(variation.split()) > 1:
            words = variation.split()
            flexible_pattern = r'\s+'.join([re.escape(word) for word in words])
            patterns.append(rf"{flexible_pattern}\s*[:=\-]?\s*([^\n\r]+?)(?=\n|$)")
    
    return patterns


def _get_field_variations(field_name: str) -> List[str]:
    """Generate different variations of a field name for searching"""
    variations = [field_name]
    
    # Convert camelCase to space-separated
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', field_name)
    variations.append(spaced)
    
    # Convert to uppercase
    variations.append(field_name.upper())
    variations.append(spaced.upper())
    
    # Convert to lowercase
    variations.append(field_name.lower())
    variations.append(spaced.lower())
    
    # Title case
    variations.append(spaced.title())
    
    # Add punctuation variations
    variations.extend([
        field_name.replace('_', ' '),
        field_name.replace('_', '-'),
        spaced.replace(' ', '_'),
        spaced.replace(' ', '-'),
        spaced.replace(' ', '')
    ])
    
    # Generate semantic variations dynamically
    semantic_variations = _generate_semantic_variations(field_name)
    variations.extend(semantic_variations)
    
    return list(set(filter(None, variations)))


def _extract_value_from_match(match: re.Match, field_type: str) -> Optional[str]:
    """Extract value from regex match"""
    if not match.groups():
        return None
    
    value = match.group(1).strip()
    
    # Clean up common unwanted characters
    value = re.sub(r'^[:\-\s]+', '', value)
    value = re.sub(r'[:\-\s]+$', '', value)
    
    # Remove common prefixes/suffixes
    value = re.sub(r'^(is|are|the)\s+', '', value, flags=re.IGNORECASE)
    
    # Remove trailing dots/periods and extra whitespace
    value = re.sub(r'\.+$', '', value)
    value = re.sub(r'\s+', ' ', value)
    
    # Filter out very short or non-meaningful values
    if len(value) < 2:
        return None
    
    # Filter out common non-data text
    non_data_words = {
        'not', 'none', 'n/a', 'na', 'unknown', 'see', 'section', 
        'refer', 'to', 'as', 'per', 'according', 'described'
    }
    
    if value.lower() in non_data_words:
        # Special case: "None" is valid for signal word
        if value.lower() == 'none':
            return value
        return None
    
    return value if value else None


def _convert_to_type(value: str, field_type: str) -> Any:
    """Convert string value to the appropriate type"""
    if not value:
        return None
    
    if field_type == "number":
        # Extract numeric value
        numeric_match = re.search(r'[\d.,]+', value)
        if numeric_match:
            try:
                return float(numeric_match.group().replace(',', ''))
            except ValueError:
                pass
        return 0
    
    elif field_type == "boolean":
        return value.lower() in ["true", "yes", "1", "on", "enabled"]
    
    else:  # string or unknown
        return value.strip()


def _find_field_section(field_name: str, text: str) -> str:
    """Find the section of text related to a specific field"""
    variations = _get_field_variations(field_name)
    
    for variation in variations:
        # Look for section headers
        pattern = rf"(\d+\.?\s*)?{re.escape(variation)}.*?\n(.*?)(?=\n\d+\.|\n[A-Z][A-Z\s]+:|\Z)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(2)
    
    return text  # Return full text as fallback


def _extract_tabular_data(text: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tabular data from text"""
    results = []
    lines = text.split('\n')
    
    # Get schema field names (excluding metadata)
    schema_fields = [k for k in schema.keys() if not k.startswith('_')]
    
    # Look for table-like structures
    current_row_data = {}
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 2:
            # If we have accumulated data, save it
            if len(current_row_data) >= 2:  # At least 2 fields filled
                results.append(current_row_data.copy())
                current_row_data = {}
            continue
        
        # Skip header lines
        if any(header in line.lower() for header in ['component', 'ec-no', 'cas-no', 'weight', 'classification', 'reach']):
            continue
        
        # Try to match this line to schema fields
        for field_name in schema_fields:
            field_schema = schema[field_name]
            field_variations = _get_field_variations(field_name)
            
            # Check if this line matches any field variation
            line_lower = line.lower()
            for variation in field_variations:
                if variation.lower() in line_lower:
                    # Extract the value for this field
                    value = _clean_extracted_value(line)
                    if value and len(value) > 1:
                        current_row_data[field_name] = value
                    break
        
        # Special handling for common patterns
        # CAS numbers (format: XXX-XX-X)
        cas_match = re.search(r'\b\d{2,7}-\d{2}-\d\b', line)
        if cas_match and 'CAS' in schema_fields:
            current_row_data['CAS'] = cas_match.group()
        
        # REACH registration numbers
        reach_match = re.search(r'\b\d{2}-\d{10}-\d{2}-x{1,3}\b', line, re.IGNORECASE)
        if reach_match:
            for field in schema_fields:
                if 'reach' in field.lower():
                    current_row_data[field] = reach_match.group()
        
        # Component names (look for chemical-sounding names)
        if re.match(r'^[A-Z][a-z]+(\s+[a-z]+)*$', line) and 'component' in [f.lower() for f in schema_fields]:
            component_field = next((f for f in schema_fields if 'component' in f.lower()), None)
            if component_field:
                current_row_data[component_field] = line
    
    # Don't forget the last row
    if len(current_row_data) >= 2:
        results.append(current_row_data)
    
    return results


def _clean_extracted_value(value: str) -> str:
    """Clean extracted value"""
    # Remove extra whitespace
    value = re.sub(r'\s+', ' ', value.strip())
    
    # Remove trailing dots and dashes
    value = re.sub(r'[-\.]+$', '', value)
    
    return value


def _extract_list_items(text: str, field_name: str) -> List[str]:
    """Extract list items from text"""
    items = []
    
    # Special handling for hazard statements
    if 'hazard' in field_name.lower():
        # Look for H-codes (e.g., H315, H319)
        h_codes = re.findall(r'H\d{3}[^\n\r]*', text, re.IGNORECASE)
        items.extend(h_codes)
        
        # Look for "Not classified" type statements
        not_classified = re.findall(r'Not\s+classified[^\n\r]*', text, re.IGNORECASE)
        items.extend(not_classified)
        
        # Look for other hazard-related statements
        hazard_patterns = [
            r'May\s+cause[^\n\r]*',
            r'Causes[^\n\r]*',
            r'Harmful[^\n\r]*',
            r'Toxic[^\n\r]*',
            r'Dangerous[^\n\r]*'
        ]
        
        for pattern in hazard_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            items.extend(matches)
    
    # General list extraction patterns
    patterns = [
        r'•\s*([^\n\r]+)',  # Bullet points
        r'-\s*([^\n\r]+)',  # Dashes
        r'\d+\.\s*([^\n\r]+)',  # Numbered lists
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        items.extend([match.strip() for match in matches if match.strip()])
    
    # If no specific patterns found, return a default message for hazards
    if not items and 'hazard' in field_name.lower():
        if re.search(r'not\s+classified', text, re.IGNORECASE):
            items.append("Not classified")
    
    return list(set(items))  # Remove duplicates


def _generate_semantic_variations(field_name: str) -> List[str]:
    """Generate semantic variations based on common domain synonyms"""
    variations = []
    field_lower = field_name.lower()
    
    # Create a comprehensive synonym map
    synonym_map = {
        # Identity/naming synonyms
        'name': ['identifier', 'title', 'label', 'designation', 'product name', 'trade name', 'commercial name'],
        'productname': ['product identifier', 'product', 'substance name', 'chemical name', 'material name'],
        'title': ['name', 'heading', 'label'],
        
        # Chemical/substance synonyms
        'component': ['substance', 'ingredient', 'chemical', 'material', 'compound', 'constituent'],
        'substance': ['component', 'ingredient', 'chemical', 'material', 'compound'],
        'ingredient': ['component', 'substance', 'chemical', 'constituent'],
        'chemical': ['substance', 'component', 'ingredient', 'compound'],
        
        # Registration/identification synonyms
        'cas': ['cas number', 'cas no', 'cas-no', 'cas reg', 'cas registry', 'chemical abstracts'],
        'reach': ['reach registration', 'reach number', 'reach reg', 'registration number', 'reg no'],
        'ec': ['ec number', 'ec no', 'einecs', 'elincs', 'european community'],
        
        # Safety/hazard synonyms
        'hazard': ['danger', 'risk', 'warning', 'caution', 'safety'],
        'hazardstatements': ['hazard statements', 'h statements', 'h codes', 'danger statements'],
        'signalword': ['signal word', 'warning word', 'danger word'],
        
        # Company/business synonyms
        'manufacturer': ['producer', 'supplier', 'company', 'vendor', 'distributor'],
        'supplier': ['manufacturer', 'producer', 'vendor', 'company'],
        
        # Version/revision synonyms
        'version': ['revision', 'ver', 'v', 'release', 'edition'],
        'revision': ['version', 'ver', 'update', 'amendment'],
        
        # Code/number synonyms
        'code': ['number', 'id', 'identifier', 'reference', 'ref'],
        'number': ['no', 'num', '#', 'code'],
        
        # Percentage/concentration synonyms
        'percentage': ['percent', '%', 'concentration', 'weight', 'w/w', 'mass'],
        'concentration': ['percentage', 'percent', 'content', 'amount'],
        
        # Classification synonyms
        'classification': ['class', 'category', 'type', 'group'],
        'category': ['classification', 'class', 'type', 'group']
    }
    
    # Find matches and add synonyms
    for key, synonyms in synonym_map.items():
        if key in field_lower or any(part in field_lower for part in key.split()):
            variations.extend(synonyms)
            # Also add uppercase and title case versions
            variations.extend([s.upper() for s in synonyms])
            variations.extend([s.title() for s in synonyms])
    
    # Handle compound words by checking individual parts
    words = re.findall(r'[a-z]+', field_lower)
    for word in words:
        if word in synonym_map:
            variations.extend(synonym_map[word])
    
    return variations


def analyze_pdf_structure(text: str) -> Dict[str, List[str]]:
    """
    Analyze PDF text to identify common field patterns and labels.
    This helps adapt to different PDF formats dynamically.
    """
    field_patterns = {}
    lines = text.split('\n')
    
    # Look for label-value patterns
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Pattern: "Label:" or "Label  Value"
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                label = parts[0].strip()
                value = parts[1].strip()
                if label and value and len(label) > 2 and len(value) > 1:
                    if 'colon_separated' not in field_patterns:
                        field_patterns['colon_separated'] = []
                    field_patterns['colon_separated'].append((label, value))
        
        # Pattern: "Label" followed by value on next line (detected by context)
        elif re.match(r'^[A-Za-z\s]+$', line) and len(line) > 3:
            if 'potential_labels' not in field_patterns:
                field_patterns['potential_labels'] = []
            field_patterns['potential_labels'].append(line)
    
    return field_patterns


def smart_field_search(field_name: str, text: str, pdf_structure: Dict[str, List[str]] = None) -> Optional[str]:
    """
    Use PDF structure analysis to find field values more intelligently.
    """
    if pdf_structure is None:
        pdf_structure = analyze_pdf_structure(text)
    
    field_variations = _get_field_variations(field_name)
    
    # First, try exact matches in colon-separated data
    if 'colon_separated' in pdf_structure:
        for label, value in pdf_structure['colon_separated']:
            for variation in field_variations:
                if _fuzzy_match(variation.lower(), label.lower()):
                    return value
    
    # Fallback to pattern-based search
    return None


def _fuzzy_match(term1: str, term2: str, threshold: float = 0.8) -> bool:
    """Simple fuzzy matching for field names"""
    # Simple approach: check if terms share significant overlap
    words1 = set(term1.split())
    words2 = set(term2.split())
    
    if not words1 or not words2:
        return False
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    # Jaccard similarity
    similarity = len(intersection) / len(union) if union else 0
    return similarity >= threshold
