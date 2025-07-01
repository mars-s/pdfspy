"""
High-performance dynamic field extraction using rapidfuzz and chemical NER.
Efficiently extracts values for TypeScript interface fields from PDF text.
"""
import re
from typing import Dict, Any, List, Optional, Union
from functools import lru_cache

# Import optimized libraries
try:
    import rapidfuzz
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("Warning: rapidfuzz not available. Install with: pip install rapidfuzz")

# Import chemical NER and related modules
try:
    from .chemical_ner import ChemicalNER
    from .hazard_classifier import HazardClassifier
    CHEMICAL_NER_AVAILABLE = True
except ImportError:
    CHEMICAL_NER_AVAILABLE = False
    print("Warning: Chemical NER modules not available")

# Import interface parser
from .parse_ts_interface import parse_ts_interface, get_field_search_terms

# Pre-compile common chemical patterns for fast matching
CHEMICAL_PATTERNS = {
    'cas_number': re.compile(r'\b\d{2,7}-\d{2}-\d\b'),
    'ec_number': re.compile(r'\b\d{3}-\d{3}-\d\b'),
    'reach_number': re.compile(r'\b\d{2}-\d{10}-\d{2}-[a-zA-Z0-9]\b'),
    'hazard_code': re.compile(r'\bH\d{3}\b'),
    'precautionary_code': re.compile(r'\bP\d{3}\b'),
    'signal_word': re.compile(r'\b(DANGER|WARNING|CAUTION)\b', re.IGNORECASE),
    'pictogram': re.compile(r'GHS\d{2}', re.IGNORECASE),
    'concentration': re.compile(r'\d+(?:\.\d+)?\s*%'),
    'temperature': re.compile(r'\d+(?:\.\d+)?\s*°?C'),
    'molecular_formula': re.compile(r'\b[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*\b'),
    'phone_number': re.compile(r'[\+]?[\d\s\-\(\)]{10,}'),
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    'date': re.compile(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b'),
    'url': re.compile(r'https?://[^\s]+'),
}

# Cache for performance optimization
_extraction_cache = {}
_max_cache_size = 1000

# Initialize chemical processors if available
chemical_ner = ChemicalNER() if CHEMICAL_NER_AVAILABLE else None
hazard_classifier = HazardClassifier() if CHEMICAL_NER_AVAILABLE else None


@lru_cache(maxsize=1000)
def fuzzy_match_field(field_name: str, text_chunk: str, threshold: int = 80) -> bool:
    """Fast fuzzy matching with caching"""
    if not RAPIDFUZZ_AVAILABLE:
        return field_name.lower() in text_chunk.lower()
    
    return fuzz.partial_ratio(field_name.lower(), text_chunk.lower()) > threshold


def extract_field_value(field_name: str, text: str, interface_schema: Dict[str, Any], field_path: str = "") -> Any:
    """
    Extract a field value from text using TypeScript interface schema for intelligent matching.
    
    Args:
        field_name: The field name from TypeScript interface
        text: The PDF text to search in  
        interface_schema: Parsed TypeScript interface schema
        field_path: Path to the field in nested objects (e.g., "identification.productName")
        
    Returns:
        Extracted value or None if not found
    """
    # Check cache first
    cache_key = f"{field_path or field_name}:{hash(text[:1000])}"
    if cache_key in _extraction_cache:
        return _extraction_cache[cache_key]
    
    # Get field metadata from schema
    field_info = _get_field_info_from_schema(interface_schema, field_name, field_path)
    if not field_info:
        # Fallback to basic extraction without schema
        _cache_result(cache_key, None)
        return None
    
    field_type = field_info.get("_type", "string")
    search_terms = field_info.get("_search_terms", [field_name])
    priority = field_info.get("_priority", 1)
    
    # Step 1: Chemical-specific extraction (highest priority for chemical data)
    if chemical_ner and _is_chemical_field_from_schema(field_info, search_terms):
        chemical_value = _extract_chemical_field_from_schema(field_info, search_terms, text, field_type)
        if chemical_value is not None:
            _cache_result(cache_key, chemical_value)
            return chemical_value
    
    # Step 2: Pattern-based extraction using schema search terms
    pattern_value = _extract_with_schema_patterns(search_terms, text, field_type)
    if pattern_value is not None:
        _cache_result(cache_key, pattern_value)
        return pattern_value
    
    # Step 3: Fuzzy matching with schema terms
    if RAPIDFUZZ_AVAILABLE:
        fuzzy_value = _extract_with_schema_fuzzy_matching(search_terms, text, field_type)
        if fuzzy_value is not None:
            _cache_result(cache_key, fuzzy_value)
            return fuzzy_value
    
    # Step 4: Basic string matching fallback
    fallback_value = _extract_with_basic_schema_matching(search_terms, text, field_type)
    _cache_result(cache_key, fallback_value)
    return fallback_value


def _get_field_info_from_schema(schema: Dict[str, Any], field_name: str, field_path: str = "") -> Optional[Dict[str, Any]]:
    """Get field information from parsed TypeScript interface schema"""
    if field_path:
        # Navigate nested path (e.g., "identification.productName")
        parts = field_path.split('.')
        current = schema
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current if isinstance(current, dict) and current.get("_field_name") == field_name else None
    else:
        # Search for field in schema
        def _find_field_recursive(obj, target_field):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == target_field and isinstance(value, dict) and value.get("_field_name"):
                        return value
                    elif isinstance(value, dict) and not key.startswith("_"):
                        result = _find_field_recursive(value, target_field)
                        if result:
                            return result
            return None
        
        return _find_field_recursive(schema, field_name)


def _is_chemical_field_from_schema(field_info: Dict[str, Any], search_terms: List[str]) -> bool:
    """Check if field is chemical-related based on schema metadata"""
    field_name = field_info.get("_field_name", "").lower()
    all_terms = " ".join(search_terms).lower()
    
    chemical_indicators = [
        'cas', 'hazard', 'precautionary', 'signal', 'pictogram', 'concentration',
        'boiling', 'melting', 'flash', 'molecular', 'formula', 'density', 'ph',
        'toxicity', 'safety', 'ghs', 'reach', 'ec_number', 'physical_state',
        'component', 'substance', 'ingredient', 'chemical'
    ]
    
    return any(indicator in field_name or indicator in all_terms for indicator in chemical_indicators)


def _extract_chemical_field_from_schema(field_info: Dict[str, Any], search_terms: List[str], text: str, field_type: str) -> Any:
    """Extract chemical-specific field using NER and schema metadata"""
    if not chemical_ner:
        return None
    
    field_name = field_info.get("_field_name", "").lower()
    chemical_info = chemical_ner.extract_chemical_info(text)
    
    # Enhanced field mapping using schema search terms
    for term in search_terms:
        term_lower = term.lower()
        
        # Direct CAS number mapping
        if any(cas_term in term_lower for cas_term in ['cas', 'registry']):
            cas_numbers = chemical_info.get('cas_numbers', [])
            if cas_numbers:
                return cas_numbers if field_type == "array" else cas_numbers[0]
        
        # EC number mapping
        if any(ec_term in term_lower for ec_term in ['ec', 'einecs']):
            ec_numbers = chemical_info.get('ec_numbers', [])
            if ec_numbers:
                return ec_numbers if field_type == "array" else ec_numbers[0]
        
        # Hazard statements mapping
        if any(hazard_term in term_lower for hazard_term in ['hazard', 'h-statement', 'danger']):
            hazard_statements = chemical_info.get('hazard_statements', [])
            if hazard_statements:
                return hazard_statements if field_type == "array" else hazard_statements[0]
        
        # Signal word mapping
        if any(signal_term in term_lower for signal_term in ['signal', 'warning']):
            signal_word = chemical_info.get('signal_word', '')
            if signal_word:
                return signal_word
        
        # Concentration mapping
        if any(conc_term in term_lower for conc_term in ['concentration', 'percentage', 'content']):
            concentrations = chemical_info.get('concentrations', [])
            if concentrations:
                return concentrations if field_type == "array" else concentrations[0]
    
    return None


def _extract_with_schema_patterns(search_terms: List[str], text: str, field_type: str) -> Any:
    """Extract using pre-compiled regex patterns with schema search terms"""
    text_lower = text.lower()
    
    # Check each search term from schema
    for term in search_terms:
        term_lower = term.lower()
        
        # Try chemical patterns first if term suggests chemical data
        for pattern_name, pattern in CHEMICAL_PATTERNS.items():
            if any(keyword in term_lower for keyword in pattern_name.split('_')):
                matches = pattern.findall(text)
                if matches:
                    if field_type == "array":
                        return matches
                    return matches[0]
        
        # Context-based extraction using schema terms
        context_value = _extract_with_schema_context(term, text, field_type)
        if context_value is not None:
            return context_value
    
    return None


def _extract_with_schema_context(search_term: str, text: str, field_type: str) -> Any:
    """Extract value using contextual patterns with schema search term"""
    # Common patterns for finding values after field names from schema
    patterns = [
        rf"{re.escape(search_term)}\s*:?\s*([^\n\r,;]+)",
        rf"\b{re.escape(search_term)}\b\s*:?\s*([^\n\r,;]+)",
        rf"{re.escape(search_term)}\s*[-=:]\s*([^\n\r,;]+)",
        rf"^{re.escape(search_term)}\s*:?\s*([^\n\r]+)",
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            value = match.group(1).strip()
            if value and len(value) > 0:
                return _convert_to_type(value, field_type)
    
    return None


def _extract_with_schema_fuzzy_matching(search_terms: List[str], text: str, field_type: str) -> Any:
    """Extract using rapidfuzz for fuzzy matching with schema terms"""
    if not RAPIDFUZZ_AVAILABLE:
        return None
    
    # Split text into chunks for better matching
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    best_matches = []
    for term in search_terms:
        # Find the best matching lines using schema search terms
        matches = process.extract(term, lines, limit=3, scorer=fuzz.partial_ratio)
        for match, score in matches:
            if score > 70:  # Threshold for good matches
                best_matches.append((match, score, term))
    
    if not best_matches:
        return None
    
    # Sort by score and try to extract value from best matches
    best_matches.sort(key=lambda x: x[1], reverse=True)
    
    for match_line, score, term in best_matches:
        # Try to extract value from the matched line
        value = _extract_value_from_line(match_line, term, field_type)
        if value is not None:
            return value
    
    return None


def _extract_with_basic_schema_matching(search_terms: List[str], text: str, field_type: str) -> Any:
    """Basic string matching fallback using schema terms"""
    text_lower = text.lower()
    
    for term in search_terms:
        term_lower = term.lower()
        
        # Find term in text
        index = text_lower.find(term_lower)
        if index != -1:
            # Extract context around the match
            start = max(0, index - 50)
            end = min(len(text), index + len(term) + 100)
            context = text[start:end]
            
            # Try to extract value from context
            value = _extract_value_from_context(context, term, field_type)
            if value is not None:
                return value
    
    return None


def _extract_value_from_line(line: str, search_term: str, field_type: str) -> Any:
    """Extract value from a specific line using schema search term"""
    # Remove the search term from the line to get the value
    line_clean = line
    line_clean = re.sub(rf"\b{re.escape(search_term)}\b", "", line_clean, flags=re.IGNORECASE)
    
    # Clean up the remaining text
    line_clean = re.sub(r'^[:\-\s]*', '', line_clean)  # Remove leading separators
    line_clean = re.sub(r'[:\-\s]*$', '', line_clean)  # Remove trailing separators
    line_clean = line_clean.strip()
    
    if line_clean:
        return _convert_to_type(line_clean, field_type)
    
    return None


def _extract_value_from_context(context: str, search_term: str, field_type: str) -> Any:
    """Extract value from surrounding context using schema search term"""
    # Split context into parts and look for value after search term
    parts = re.split(r'[:\-\n\r]', context)
    
    term_found = False
    for part in parts:
        part = part.strip()
        if term_found and part:
            return _convert_to_type(part, field_type)
        if search_term.lower() in part.lower():
            term_found = True
            # Check if value is in the same part
            remaining = part.lower().replace(search_term.lower(), '', 1).strip()
            remaining = re.sub(r'^[:\-\s]*', '', remaining)
            if remaining:
                return _convert_to_type(remaining, field_type)
    
    return None


def _extract_with_optimized_patterns(field_variants: List[str], text: str, field_type: str) -> Any:
    """Extract using pre-compiled regex patterns"""
    text_lower = text.lower()
    
    # Check each field variant
    for variant in field_variants:
        variant_lower = variant.lower()
        
        # Try chemical patterns first
        for pattern_name, pattern in CHEMICAL_PATTERNS.items():
            if pattern_name in variant_lower:
                matches = pattern.findall(text)
                if matches:
                    if field_type == "array" or "[]" in field_type:
                        return matches
                    return matches[0]
        
        # Context-based extraction
        context_value = _extract_with_context(variant, text, field_type)
        if context_value is not None:
            return context_value
    
    return None


def _extract_with_context(field_name: str, text: str, field_type: str) -> Any:
    """Extract value using contextual patterns"""
    field_lower = field_name.lower()
    
    # Common patterns for finding values after field names
    patterns = [
        rf"{re.escape(field_name)}\s*:?\s*([^\n\r,;]+)",
        rf"{re.escape(field_lower)}\s*:?\s*([^\n\r,;]+)",
        rf"\b{re.escape(field_name)}\b\s*:?\s*([^\n\r,;]+)",
        rf"\b{re.escape(field_lower)}\b\s*:?\s*([^\n\r,;]+)",
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = match.group(1).strip()
            if value and len(value) > 0:
                return _convert_to_type(value, field_type)
    
    return None


def _extract_with_rapidfuzz(field_variants: List[str], text: str, field_type: str) -> Any:
    """Extract using rapidfuzz for fuzzy matching"""
    if not RAPIDFUZZ_AVAILABLE:
        return None
    
    # Split text into chunks for better matching
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    best_matches = []
    for variant in field_variants:
        # Find the best matching lines
        matches = process.extract(variant, lines, limit=3, scorer=fuzz.partial_ratio)
        for match, score in matches:
            if score > 70:  # Threshold for good matches
                best_matches.append((match, score, variant))
    
    if not best_matches:
        return None
    
    # Sort by score and try to extract value from best matches
    best_matches.sort(key=lambda x: x[1], reverse=True)
    
    for match_line, score, variant in best_matches:
        # Try to extract value from the matched line
        value = _extract_value_from_line(match_line, variant, field_type)
        if value is not None:
            return value
    
    return None


def _extract_value_from_line(line: str, field_name: str, field_type: str) -> Any:
    """Extract value from a specific line"""
    # Remove the field name from the line to get the value
    line_clean = line
    for pattern in [field_name, field_name.lower(), field_name.upper()]:
        line_clean = re.sub(rf"\b{re.escape(pattern)}\b", "", line_clean, flags=re.IGNORECASE)
    
    # Clean up the remaining text
    line_clean = re.sub(r'^[:\-\s]*', '', line_clean)  # Remove leading separators
    line_clean = re.sub(r'[:\-\s]*$', '', line_clean)  # Remove trailing separators
    line_clean = line_clean.strip()
    
    if line_clean:
        return _convert_to_type(line_clean, field_type)
    
    return None


def _extract_with_basic_matching(field_variants: List[str], text: str, field_type: str) -> Any:
    """Basic string matching fallback"""
    text_lower = text.lower()
    
    for variant in field_variants:
        variant_lower = variant.lower()
        
        # Find variant in text
        index = text_lower.find(variant_lower)
        if index != -1:
            # Extract context around the match
            start = max(0, index - 50)
            end = min(len(text), index + len(variant) + 100)
            context = text[start:end]
            
            # Try to extract value from context
            value = _extract_value_from_context(context, variant, field_type)
            if value is not None:
                return value
    
    return None


def _extract_value_from_context(context: str, field_name: str, field_type: str) -> Any:
    """Extract value from surrounding context"""
    # Split context into parts and look for value after field name
    parts = re.split(r'[:\-\n\r]', context)
    
    field_found = False
    for part in parts:
        part = part.strip()
        if field_found and part:
            return _convert_to_type(part, field_type)
        if field_name.lower() in part.lower():
            field_found = True
            # Check if value is in the same part
            remaining = part.lower().replace(field_name.lower(), '', 1).strip()
            remaining = re.sub(r'^[:\-\s]*', '', remaining)
            if remaining:
                return _convert_to_type(remaining, field_type)
    
    return None


def _generate_field_variants(field_name: str) -> List[str]:
    """Generate field name variants for better matching"""
    variants = [field_name]
    
    # Add common transformations
    base_name = field_name.replace('_', ' ').replace('-', ' ')
    variants.extend([
        base_name,
        base_name.title(),
        base_name.upper(),
        base_name.lower(),
        field_name.replace('_', ''),
        field_name.replace('_', '-'),
        field_name.replace('_', ' ').title(),
    ])
    
    # Add chemical-specific variants
    chemical_variants = {
        'cas_number': ['CAS No', 'CAS Number', 'CAS RN', 'CAS Registry Number'],
        'ec_number': ['EC No', 'EC Number', 'EINECS Number'],
        'signal_word': ['Signal Word', 'GHS Signal Word'],
        'hazard_statement': ['Hazard Statement', 'H-Statement', 'H Statement'],
        'precautionary_statement': ['Precautionary Statement', 'P-Statement', 'P Statement'],
        'molecular_weight': ['Molecular Weight', 'Mol. Wt.', 'MW'],
        'boiling_point': ['Boiling Point', 'BP', 'b.p.'],
        'melting_point': ['Melting Point', 'MP', 'm.p.'],
        'flash_point': ['Flash Point', 'FP'],
        'physical_state': ['Physical State', 'Appearance', 'Form'],
    }
    
    field_lower = field_name.lower()
    for key, additional_variants in chemical_variants.items():
        if key in field_lower:
            variants.extend(additional_variants)
    
    return list(set(variants))  # Remove duplicates


def extract_fields_from_interface(text: str, interface_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract all fields from text using TypeScript interface schema.
    
    Args:
        text: The PDF text to extract from
        interface_schema: Parsed TypeScript interface schema
        
    Returns:
        Dictionary with extracted field values matching interface structure
    """
    result = {}
    
    def _extract_recursive(schema_obj: Dict[str, Any], current_result: Dict[str, Any], path: str = ""):
        """Recursively extract fields based on schema structure"""
        for key, value in schema_obj.items():
            if key.startswith("_"):  # Skip metadata
                continue
                
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                if value.get("_type") == "array_of_objects":
                    # Handle array of objects
                    array_items = extract_array_from_interface(text, value, current_path)
                    current_result[key] = array_items
                elif value.get("_field_name"):
                    # This is a field definition
                    field_value = extract_field_value(key, text, interface_schema, current_path)
                    if field_value is not None:
                        current_result[key] = field_value
                else:
                    # This is a nested object
                    nested_result = {}
                    _extract_recursive(value, nested_result, current_path)
                    if nested_result:  # Only add if we found something
                        current_result[key] = nested_result
    
    _extract_recursive(interface_schema, result)
    return result


def extract_array_from_interface(text: str, array_schema: Dict[str, Any], field_path: str) -> List[Dict[str, Any]]:
    """
    Extract array values using TypeScript interface schema.
    
    Args:
        text: The text to search in
        array_schema: Schema of array items from interface
        field_path: Path to the array field
        
    Returns:
        List of extracted objects matching array schema
    """
    # For now, return empty list - this would need more sophisticated
    # table/structured data extraction logic
    return []


# Update the main conversion function to handle type conversion better
def _convert_to_type(value: str, field_type: str) -> Any:
    """Convert string value to appropriate type based on schema"""
    if not value or not isinstance(value, str):
        return value
    
    value = value.strip()
    
    # Handle array types
    if field_type == "array":
        # Split by common delimiters
        items = re.split(r'[,;|\n]', value)
        return [item.strip() for item in items if item.strip()]
    
    # Handle specific types
    if field_type in ["number", "float"]:
        try:
            # Extract first number found
            number_match = re.search(r'(\d+(?:\.\d+)?)', value)
            if number_match:
                return float(number_match.group(1))
        except (ValueError, AttributeError):
            pass
    
    elif field_type == "integer":
        try:
            # Extract first integer found
            int_match = re.search(r'(\d+)', value)
            if int_match:
                return int(int_match.group(1))
        except (ValueError, AttributeError):
            pass
    
    elif field_type == "boolean":
        value_lower = value.lower()
        if value_lower in ['true', 'yes', '1', 'on', 'enabled']:
            return True
        elif value_lower in ['false', 'no', '0', 'off', 'disabled']:
            return False
    
    # Return as string for everything else
    return value


def _cache_result(cache_key: str, result: Any) -> None:
    """Cache extraction result"""
    if len(_extraction_cache) >= _max_cache_size:
        # Remove oldest entries
        keys_to_remove = list(_extraction_cache.keys())[:100]
        for key in keys_to_remove:
            del _extraction_cache[key]
    
    _extraction_cache[cache_key] = result


def extract_all_chemical_entities(text: str) -> Dict[str, Any]:
    """Extract all chemical entities from text"""
    if not chemical_ner:
        return {}
    
    entities = chemical_ner.extract_chemical_info(text)
    
    # Add hazard classification if available
    if hazard_classifier and entities.get('hazard_statements'):
        hazard_analysis = hazard_classifier.get_hazard_category_summary(entities['hazard_statements'])
        entities['hazard_analysis'] = hazard_analysis
    
    return entities


def get_extraction_stats() -> Dict[str, Any]:
    """Get extraction performance statistics"""
    return {
        'cache_size': len(_extraction_cache),
        'max_cache_size': _max_cache_size,
        'rapidfuzz_available': RAPIDFUZZ_AVAILABLE,
        'chemical_ner_available': CHEMICAL_NER_AVAILABLE,
        'supported_patterns': list(CHEMICAL_PATTERNS.keys())
    }



