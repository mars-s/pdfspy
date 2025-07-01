"""
Streamlined dynamic field extraction using NLP and semantic matching.
Efficiently extracts values for TypeScript interface fields from PDF text.
"""
import re
from typing import Dict, Any, List, Optional, Union
from difflib import SequenceMatcher

# Load spaCy model for NLP processing
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    print("SpaCy loaded successfully for NLP processing")
except (OSError, ImportError, ValueError) as e:
    print(f"Warning: spaCy not available ({e}). Install with: python -m spacy download en_core_web_sm")
    nlp = None

# Cache for processed documents to improve performance
_doc_cache = {}
_max_cache_size = 10


def extract_field_value(field_name: str, text: str, field_type: str = "string") -> Any:
    """
    Extract a field value from text using intelligent semantic matching and NLP.
    
    Args:
        field_name: The field name from TypeScript interface
        text: The PDF text to search in  
        field_type: The expected type of the field
        
    Returns:
        Extracted value or None if not found
    """
    # Generate field variants for better matching
    field_variants = _generate_field_variants(field_name)
    
    # Step 1: Quick pattern-based extraction (most efficient)
    value = _extract_with_optimized_patterns(field_variants, text)
    if value:
        return _convert_to_type(value, field_type)
    
    # Step 2: NLP-enhanced extraction for semantic understanding
    if nlp:
        nlp_value = _extract_with_enhanced_nlp(field_variants, text, field_type)
        if nlp_value:
            return _convert_to_type(nlp_value, field_type)
    
    # Step 3: Fuzzy matching as fallback
    fuzzy_value = _extract_with_fuzzy_matching(field_variants, text)
    if fuzzy_value:
        return _convert_to_type(fuzzy_value, field_type)
    
    return None


def extract_array_values(field_name: str, text: str, array_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract array values using intelligent field recognition.
    
    Args:
        field_name: The array field name
        text: The text to search in
        array_schema: Schema of array items
        
    Returns:
        List of extracted objects
    """
    if array_schema.get("_type") == "array_of_objects":
        return _extract_structured_array(text, array_schema)
    else:
        # For simple arrays
        items = _extract_simple_array(field_name, text)
        return items


def _generate_field_variants(field_name: str) -> List[str]:
    """Generate semantic variants of a field name for better matching."""
    variants = [field_name]
    
    # Convert camelCase to readable format
    readable = re.sub(r'([a-z])([A-Z])', r'\1 \2', field_name)
    if readable != field_name:
        variants.append(readable)
        variants.append(readable.lower())
        variants.append(readable.upper())
        variants.append(readable.title())
    
    # Add common formatting variants
    variants.extend([
        field_name.lower(),
        field_name.upper(),
        field_name.replace('_', ' '),
        field_name.replace('-', ' '),
        re.sub(r'([a-z])([A-Z])', r'\1-\2', field_name).lower(),  # kebab-case
        re.sub(r'([a-z])([A-Z])', r'\1_\2', field_name).lower(),  # snake_case
    ])
    
    return list(set(filter(None, variants)))


def _extract_with_optimized_patterns(field_variants: List[str], text: str) -> Optional[str]:
    """Extract value using optimized regex patterns with field variants."""
    
    for variant in field_variants:
        # Multiple pattern strategies with priority order
        patterns = [
            # High confidence patterns
            rf"\b{re.escape(variant)}\s*[:=]\s*([^\n\r]+)",
            rf"^{re.escape(variant)}\s*[:=]\s*([^\n\r]+)",
            
            # Medium confidence patterns
            rf"\b{re.escape(variant)}\s+([^\n\r]+?)(?=\n|$|\t)",
            rf"{re.escape(variant)}\s*[|\t]\s*([^\n\r|]+)",
            
            # Lower confidence patterns
            rf"^{re.escape(variant)}\s*$\n\s*([^\n]+)",
            rf"{re.escape(variant)}[:\-\s]*([^\n\r.;,]+)",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                value = _clean_extracted_value(match.group(1))
                if value and len(value.strip()) > 1:
                    # Score the match based on context
                    score = _score_extraction_context(match, text, variant)
                    if score > 0.5:  # Threshold for acceptance
                        return value
    
    return None


def _extract_with_enhanced_nlp(field_variants: List[str], text: str, field_type: str) -> Optional[str]:
    """Use enhanced NLP for semantic field matching with better performance."""
    if not nlp:
        return None
    
    # Use caching for better performance
    text_hash = hash(text[:1000])  # Hash first 1000 chars for cache key
    if text_hash in _doc_cache:
        doc = _doc_cache[text_hash]
    else:
        # Limit text size for performance
        max_chars = 30000 if field_type == "number" else 20000
        text_to_process = _find_relevant_text_sections(field_variants[0], text, max_chars)
        
        doc = nlp(text_to_process)
        
        # Manage cache size
        if len(_doc_cache) >= _max_cache_size:
            _doc_cache.clear()
        _doc_cache[text_hash] = doc
    
    # Extract named entities that might be relevant
    relevant_entities = []
    for ent in doc.ents:
        if field_type == "number" and ent.label_ in ["QUANTITY", "PERCENT", "MONEY", "CARDINAL"]:
            relevant_entities.append(ent.text)
        elif field_type == "string" and ent.label_ in ["ORG", "PRODUCT", "PERSON", "GPE"]:
            relevant_entities.append(ent.text)
    
    # Find sentences most likely to contain our field
    best_candidates = []
    for sent in doc.sents:
        sent_text = sent.text
        max_similarity = 0
        
        for variant in field_variants:
            # Calculate semantic similarity using token vectors
            similarity = _calculate_semantic_similarity(variant, sent_text, doc)
            max_similarity = max(max_similarity, similarity)
        
        if max_similarity > 0.4:  # Threshold for relevance
            best_candidates.append((sent_text, max_similarity))
    
    # Sort by similarity and extract from best candidates
    best_candidates.sort(key=lambda x: x[1], reverse=True)
    
    for sentence, similarity in best_candidates[:3]:  # Check top 3 candidates
        for variant in field_variants:
            value = _extract_value_from_sentence(sentence, variant)
            if value:
                return value
    
    # Try extracting from relevant entities if sentence-based extraction fails
    if relevant_entities and field_type == "number":
        for entity in relevant_entities:
            if re.search(r'\d', entity):  # Contains numbers
                return entity
    elif relevant_entities and field_type == "string":
        # Return the most relevant entity
        return relevant_entities[0]
    
    return None


def _extract_with_fuzzy_matching(field_variants: List[str], text: str) -> Optional[str]:
    """Extract using fuzzy string matching as a fallback method."""
    lines = text.split('\n')
    best_match = None
    best_score = 0
    
    for line in lines:
        line_cleaned = line.strip()
        if len(line_cleaned) < 3:
            continue
            
        for variant in field_variants:
            # Calculate fuzzy similarity
            similarity = SequenceMatcher(None, variant.lower(), line_cleaned.lower()).ratio()
            
            if similarity > best_score and similarity > 0.6:  # Minimum threshold
                # Try to extract value from this line
                value = _extract_value_from_fuzzy_line(line_cleaned, variant)
                if value:
                    best_match = value
                    best_score = similarity
    
    return best_match


def _calculate_semantic_similarity(field_name: str, sentence: str, doc) -> float:
    """Calculate semantic similarity using spaCy's word vectors."""
    try:
        # Create a small doc for the field name
        field_doc = nlp(field_name)
        sentence_doc = nlp(sentence)
        
        # Check if vectors are available
        if field_doc.has_vector and sentence_doc.has_vector and field_doc.vector_norm > 0 and sentence_doc.vector_norm > 0:
            return field_doc.similarity(sentence_doc)
        else:
            # Fallback to token-based similarity when vectors not available
            return _token_based_similarity(field_name, sentence)
    except:
        return _token_based_similarity(field_name, sentence)


def _token_based_similarity(field_name: str, sentence: str) -> float:
    """Calculate similarity based on token overlap."""
    field_tokens = set(field_name.lower().split())
    sentence_tokens = set(sentence.lower().split())
    
    if not field_tokens:
        return 0
    
    overlap = len(field_tokens.intersection(sentence_tokens))
    return overlap / len(field_tokens)


def _score_extraction_context(match, text: str, field_name: str) -> float:
    """Score an extraction based on its context."""
    score = 0.5  # Base score
    
    # Get context around the match
    start = max(0, match.start() - 100)
    end = min(len(text), match.end() + 100)
    context = text[start:end]
    
    # Positive indicators
    if ':' in context[:match.start()-start+10]:  # Colon before field
        score += 0.2
    if re.search(r'\b(value|amount|quantity|weight|percentage)\b', context, re.IGNORECASE):
        score += 0.2
    if len(match.group(1).strip()) > 3:  # Reasonable value length
        score += 0.1
    
    # Negative indicators
    if re.search(r'\b(title|header|caption|label)\b', context, re.IGNORECASE):
        score -= 0.3
    if match.group(1).strip().endswith(':'):  # Value ends with colon (likely a label)
        score -= 0.4
    
    return max(0, min(1, score))


def _extract_value_from_fuzzy_line(line: str, field_name: str) -> Optional[str]:
    """Extract value from a line using fuzzy matching."""
    # Try to find a pattern that separates the field from its value
    separators = [':', '=', '-', '|', '\t']
    
    for sep in separators:
        if sep in line:
            parts = line.split(sep, 1)
            if len(parts) == 2:
                label_part = parts[0].strip()
                value_part = parts[1].strip()
                
                # Check if the label part is similar to our field
                similarity = SequenceMatcher(None, field_name.lower(), label_part.lower()).ratio()
                if similarity > 0.6 and value_part:
                    return _clean_extracted_value(value_part)
    
    return None





def _find_relevant_text_sections(field_name: str, text: str, max_chars: int) -> str:
    """Find text sections most likely to contain the field."""
    variants = _generate_field_variants(field_name)
    lines = text.split('\n')
    relevant_lines = []
    line_scores = []
    
    # Score each line based on field relevance
    for i, line in enumerate(lines):
        line_lower = line.lower()
        max_score = 0
        
        for variant in variants:
            variant_lower = variant.lower()
            if variant_lower in line_lower:
                # Direct match gets high score
                score = 1.0
                # Bonus for being at start of line
                if line_lower.strip().startswith(variant_lower):
                    score += 0.2
                # Bonus for having separator after field name
                if re.search(rf"{re.escape(variant_lower)}\s*[:=\-]", line_lower):
                    score += 0.3
                max_score = max(max_score, score)
            else:
                # Fuzzy matching for partial matches
                similarity = SequenceMatcher(None, variant_lower, line_lower).ratio()
                if similarity > 0.7:
                    max_score = max(max_score, similarity * 0.8)
        
        if max_score > 0.5:
            line_scores.append((i, max_score, line))
    
    # Sort by score and include context around high-scoring lines
    line_scores.sort(key=lambda x: x[1], reverse=True)
    included_indices = set()
    
    for i, score, line in line_scores[:10]:  # Top 10 scoring lines
        # Include context around the matching line
        start = max(0, i - 3)
        end = min(len(lines), i + 4)
        for idx in range(start, end):
            included_indices.add(idx)
    
    # Build relevant text from included lines
    if included_indices:
        sorted_indices = sorted(included_indices)
        relevant_lines = [lines[i] for i in sorted_indices]
        relevant_text = '\n'.join(relevant_lines)
    else:
        relevant_text = text[:max_chars]
    
    return relevant_text[:max_chars]


def _semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity between two texts."""
    return SequenceMatcher(None, text1, text2).ratio()


def _extract_value_from_sentence(sentence: str, field_name: str) -> Optional[str]:
    """Extract value from a sentence containing the field."""
    variants = _generate_field_variants(field_name)
    
    for variant in variants:
        # Look for patterns within the sentence with priority order
        patterns = [
            # High confidence patterns
            rf"{re.escape(variant)}\s*[:=]\s*([^,\n\r.;]+)",
            rf"{re.escape(variant)}\s+is\s+([^,\n\r.;]+)",
            rf"{re.escape(variant)}\s*[:\-]\s*([^,\n\r.;]+)",
            
            # Medium confidence patterns
            rf"{re.escape(variant)}\s+([^,\n\r.;:]+?)(?=\s|$)",
            rf"(?:^|\s){re.escape(variant)}\s*[,]?\s*([^,\n\r.;]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                value = _clean_extracted_value(match.group(1))
                if value and len(value.strip()) > 1:
                    return value
    
    return None


def _clean_extracted_value(value: str) -> str:
    """Clean and normalize extracted values."""
    if not value:
        return ""
    
    # Remove common noise patterns
    value = re.sub(r'^[:\-\s=]+', '', value)  # Leading separators
    value = re.sub(r'[:\-\s=]+$', '', value)  # Trailing separators
    value = re.sub(r'^\w+\s*:\s*', '', value)  # "Label: " prefixes
    value = re.sub(r'\s+', ' ', value)  # Multiple spaces
    
    # Remove common unwanted prefixes/suffixes
    noise_patterns = [
        r'^(of|the|a|an)\s+',
        r'\s+(sheet|data|information|document)s?$',
        r'^(number|no\.?|code)\s+',
    ]
    
    for pattern in noise_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    return value.strip()


def _convert_to_type(value: str, field_type: str) -> Any:
    """Convert string value to appropriate type with better parsing."""
    if not value or not value.strip():
        return None
    
    value = value.strip()
    
    if field_type == "number":
        # Extract numbers with various formats (1,234.56, 1.234,56, etc.)
        number_match = re.search(r'[\d,.\s]+', value)
        if number_match:
            number_str = number_match.group().replace(' ', '').replace(',', '.')
            try:
                # Handle different decimal separators
                if number_str.count('.') > 1:
                    # Format like 1.234.567 (European)
                    parts = number_str.split('.')
                    number_str = ''.join(parts[:-1]) + '.' + parts[-1]
                return float(number_str)
            except ValueError:
                pass
        return 0
    
    elif field_type == "boolean":
        return value.lower() in ["true", "yes", "1", "on", "enabled", "active"]
    
    else:  # string
        return value


def _extract_structured_array(text: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract structured array data using field-aware parsing with improved accuracy."""
    results = []
    field_names = [k for k in schema.keys() if not k.startswith('_')]
    
    # First, try to identify table-like structures
    table_data = _extract_table_data(text, field_names)
    if table_data:
        return table_data
    
    # Fallback to section-based extraction
    sections = _identify_data_sections(text, field_names)
    
    for section in sections:
        row_data = {}
        field_confidence = {}
        
        for field_name in field_names:
            field_schema = schema.get(field_name, {})
            field_type = field_schema.get('_type', 'string')
            
            # Extract with confidence scoring
            value = extract_field_value(field_name, section, field_type)
            if value is not None and value != "" and value != 0:
                # Calculate confidence based on value quality
                confidence = _calculate_value_confidence(value, field_type, section, field_name)
                if confidence > 0.3:  # Minimum confidence threshold
                    row_data[field_name] = value
                    field_confidence[field_name] = confidence
        
        # Only include rows with reasonable field population and confidence
        if len(row_data) >= max(2, len(field_names) // 3):  # At least 2 fields or 1/3 of total
            avg_confidence = sum(field_confidence.values()) / len(field_confidence) if field_confidence else 0
            if avg_confidence > 0.4:  # Minimum average confidence
                # Fill missing fields with smart defaults
                for field_name in field_names:
                    if field_name not in row_data:
                        field_schema = schema.get(field_name, {})
                        field_type = field_schema.get('_type', 'string')
                        row_data[field_name] = _get_default_value(field_type)
                results.append(row_data)
    
    # Limit results to prevent noise
    return results[:20]  # Maximum 20 items


def _extract_table_data(text: str, field_names: List[str]) -> List[Dict[str, Any]]:
    """Extract data from table-like structures in text."""
    lines = text.split('\n')
    table_rows = []
    
    # Look for table headers
    header_indices = {}
    for i, line in enumerate(lines):
        line_lower = line.lower()
        field_matches = 0
        
        for field in field_names:
            field_variants = _generate_field_variants(field)
            for variant in field_variants:
                if variant.lower() in line_lower:
                    field_matches += 1
                    # Try to find column position
                    col_pos = line_lower.find(variant.lower())
                    header_indices[field] = col_pos
                    break
        
        # If we found most fields in this line, it's likely a header
        if field_matches >= len(field_names) * 0.6:  # 60% of fields found
            # Extract data rows following this header
            for j in range(i + 1, min(i + 20, len(lines))):  # Check next 20 lines
                data_line = lines[j].strip()
                if data_line and not data_line.lower().startswith(tuple(field_names)):
                    row_data = _parse_table_row(data_line, header_indices, field_names)
                    if row_data and len(row_data) >= 2:
                        table_rows.append(row_data)
            
            if table_rows:
                return table_rows[:15]  # Return first 15 valid rows
    
    return []


def _parse_table_row(line: str, header_indices: Dict[str, int], field_names: List[str]) -> Dict[str, Any]:
    """Parse a single table row based on header positions."""
    row_data = {}
    
    # Try different separators
    separators = ['\t', '|', ';', ',']
    
    for sep in separators:
        if sep in line:
            parts = [p.strip() for p in line.split(sep)]
            if len(parts) >= len(field_names):
                # Map parts to field names
                for i, field in enumerate(field_names):
                    if i < len(parts) and parts[i]:
                        row_data[field] = _clean_extracted_value(parts[i])
                return row_data
    
    # If no clear separator, try position-based extraction
    if header_indices:
        sorted_fields = sorted(header_indices.items(), key=lambda x: x[1])
        for i, (field, pos) in enumerate(sorted_fields):
            next_pos = sorted_fields[i + 1][1] if i + 1 < len(sorted_fields) else len(line)
            value = line[pos:next_pos].strip()
            if value:
                row_data[field] = _clean_extracted_value(value)
    
    return row_data


def _calculate_value_confidence(value: Any, field_type: str, context: str, field_name: str) -> float:
    """Calculate confidence score for an extracted value."""
    confidence = 0.5  # Base confidence
    
    if field_type == "number":
        if isinstance(value, (int, float)) and value > 0:
            confidence += 0.3
        if re.search(r'\d+\.?\d*\s*%', str(value)):  # Percentage
            confidence += 0.2
    
    elif field_type == "string":
        value_str = str(value)
        if len(value_str) > 2:
            confidence += 0.2
        if not re.search(r'\d{4,}', value_str):  # Avoid long numbers as strings
            confidence += 0.1
        # Avoid common noise patterns
        if not any(noise in value_str.lower() for noise in ['section', 'page', 'see', 'refer']):
            confidence += 0.1
    
    # Context-based confidence
    field_variants = _generate_field_variants(field_name)
    for variant in field_variants:
        if variant.lower() in context.lower():
            confidence += 0.2
            break
    
    return min(1.0, confidence)


def _identify_data_sections(text: str, field_names: List[str]) -> List[str]:
    """Identify sections of text that likely contain structured data."""
    lines = text.split('\n')
    sections = []
    current_section = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            if current_section and len(current_section) >= 2:
                sections.append('\n'.join(current_section))
            current_section = []
            continue
        
        # Check if line contains any field names
        has_field = any(field.lower() in line_stripped.lower() for field in field_names)
        
        if has_field or current_section:
            current_section.append(line)
        elif len(current_section) >= 3:  # Complete section
            sections.append('\n'.join(current_section))
            current_section = []
    
    # Don't forget the last section
    if current_section and len(current_section) >= 2:
        sections.append('\n'.join(current_section))
    
    return sections


def _extract_simple_array(field_name: str, text: str) -> List[str]:
    """Extract simple array values with smart pattern recognition."""
    items = []
    
    # Find text sections relevant to this field
    relevant_text = _find_relevant_text_sections(field_name, text, 10000)
    
    # Look for list patterns
    list_patterns = [
        r'[•\-\*]\s*([^\n\r]+)',  # Bullet points
        r'\d+\.\s*([^\n\r]+)',    # Numbered lists
        r'[a-zA-Z]\)\s*([^\n\r]+)',  # Lettered lists
        r'\|\s*([^\n\r|]+)',      # Pipe-separated
        r',\s*([^,\n\r]+)',       # Comma-separated
    ]
    
    for pattern in list_patterns:
        matches = re.findall(pattern, relevant_text, re.IGNORECASE)
        if matches:
            cleaned_items = [_clean_extracted_value(item) for item in matches]
            items.extend([item for item in cleaned_items if item and len(item.strip()) > 2])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    
    return unique_items[:10]  # Limit to reasonable number


def _get_default_value(field_type: str) -> Any:
    """Get default value for a field type."""
    defaults = {
        'number': 0,
        'boolean': False,
        'array': [],
        'array_of_objects': [],
        'object': {},
        'string': ""
    }
    return defaults.get(field_type, "")



