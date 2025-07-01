"""
Modern Dynamic Field Extraction System with Donut-First Architecture
Prioritizes Donut for structured document understanding, falls back to intelligent NLP extraction.
All field searching is completely dynamic based on TypeScript interface structure.
"""
import re
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from functools import lru_cache
import rapidfuzz
from dataclasses import dataclass

# Import modules
from .parse_ts_interface import parse_ts_interface, get_all_field_names, get_field_search_terms
from .donut_processor import FastDonutProcessor, DONUT_AVAILABLE

# Optional NLP imports with graceful fallback
try:
    import spacy
    from spacy.matcher import Matcher
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


@dataclass
class ExtractionConfig:
    """Configuration for extraction behavior."""
    donut_timeout: int = 15
    donut_max_length: int = 2048
    use_nlp_fallback: bool = True
    confidence_threshold: float = 0.7
    max_extraction_attempts: int = 3


@dataclass
class ExtractionResult:
    """Result of field extraction with metadata."""
    data: Dict[str, Any]
    confidence: float
    method_used: str
    processing_time: float
    field_count: int
    errors: List[str]


class DynamicExtractor:
    """
    Modern dynamic extractor that adapts to any interface structure.
    Uses Donut for visual document understanding, NLP for intelligent text processing.
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """Initialize the dynamic extractor."""
        self.config = config or ExtractionConfig()
        self.donut_processor = None
        self.nlp_model = None
        self.field_matchers = {}
        self._extraction_cache = {}
        
        # Initialize components
        self._init_donut()
        self._init_nlp()
    
    def _init_donut(self) -> None:
        """Initialize Donut processor if available."""
        if DONUT_AVAILABLE:
            try:
                self.donut_processor = FastDonutProcessor()
                print("✅ Donut processor initialized successfully")
            except Exception as e:
                print(f"⚠️ Donut initialization failed: {e}")
                self.donut_processor = None
        else:
            print("❌ Donut not available - install transformers, torch, and dependencies")
    
    def _init_nlp(self) -> None:
        """Initialize NLP model if available."""
        if NLP_AVAILABLE and self.config.use_nlp_fallback:
            try:
                # Try to load transformer model first (best accuracy), then fallback
                model_names = ["en_core_web_trf", "en_core_web_sm", "en_core_web_md", "en"]
                for model_name in model_names:
                    try:
                        self.nlp_model = spacy.load(model_name)
                        print(f"✅ NLP model '{model_name}' loaded successfully")
                        break
                    except OSError:
                        continue
                        
                if not self.nlp_model:
                    print("⚠️ No spaCy model found - install with: python -m spacy download en_core_web_trf")
                    
            except Exception as e:
                print(f"⚠️ NLP initialization failed: {e}")
                self.nlp_model = None
        else:
            print("❌ NLP not available or disabled")
    
    def extract_from_pdf(self, pdf_path: str, interface_schema: Dict[str, Any], 
                        page_num: int = 0) -> ExtractionResult:
        """
        Extract fields from PDF using Donut-first approach.
        
        Args:
            pdf_path: Path to PDF file
            interface_schema: Parsed TypeScript interface schema
            page_num: Page number to process (0-indexed)
            
        Returns:
            ExtractionResult with extracted data and metadata
        """
        import time
        start_time = time.time()
        errors = []
        
        print(f"🚀 Starting extraction from PDF: {pdf_path} (page {page_num})")
        
        # Attempt 1: Donut extraction (primary method)
        donut_result = self._extract_with_donut(pdf_path, interface_schema, page_num)
        
        if donut_result and self._is_high_quality_result(donut_result, interface_schema):
            processing_time = time.time() - start_time
            print(f"✅ High-quality Donut extraction completed in {processing_time:.2f}s")
            return ExtractionResult(
                data=donut_result,
                confidence=0.9,
                method_used="donut",
                processing_time=processing_time,
                field_count=self._count_fields(donut_result),
                errors=errors
            )
        
        # Attempt 2: Enhanced Donut + NLP hybrid
        print("🔄 Attempting enhanced Donut + NLP hybrid extraction...")
        hybrid_result = self._extract_hybrid(pdf_path, interface_schema, page_num, donut_result)
        
        if hybrid_result and self._is_adequate_result(hybrid_result, interface_schema):
            processing_time = time.time() - start_time
            print(f"✅ Hybrid extraction completed in {processing_time:.2f}s")
            return ExtractionResult(
                data=hybrid_result,
                confidence=0.8,
                method_used="hybrid_donut_nlp",
                processing_time=processing_time,
                field_count=self._count_fields(hybrid_result),
                errors=errors
            )
        
        # Attempt 3: Pure NLP extraction (fallback)
        print("🔄 Falling back to pure NLP extraction...")
        nlp_result = self._extract_with_nlp(pdf_path, interface_schema, page_num)
        
        processing_time = time.time() - start_time
        print(f"✅ NLP extraction completed in {processing_time:.2f}s")
        
        return ExtractionResult(
            data=nlp_result or self._create_empty_result(interface_schema),
            confidence=0.6 if nlp_result else 0.3,
            method_used="nlp_fallback" if nlp_result else "minimal",
            processing_time=processing_time,
            field_count=self._count_fields(nlp_result) if nlp_result else 0,
            errors=errors
        )
    
    def _extract_with_donut(self, pdf_path: str, interface_schema: Dict[str, Any], 
                           page_num: int) -> Optional[Dict[str, Any]]:
        """Extract using Donut visual document understanding."""
        if not self.donut_processor:
            return None
        
        try:
            print("🤖 Processing with Donut...")
            donut_result = self.donut_processor.process_pdf_page(
                pdf_path, 
                page_num=page_num, 
                timeout=self.config.donut_timeout
            )
            
            if not donut_result or not donut_result.get('success'):
                print(f"❌ Donut failed: {donut_result.get('error', 'Unknown error')}")
                return None
            
            donut_text = donut_result.get('structured_text', '')
            print(f"📄 Donut extracted {len(donut_text)} characters")
            
            if len(donut_text) < 10:
                print("⚠️ Donut extraction too short, likely incomplete")
                return None
            
            # Process Donut output through dynamic field extraction
            return self._process_donut_output(donut_text, interface_schema)
            
        except Exception as e:
            print(f"❌ Donut extraction error: {e}")
            return None
    
    def _process_donut_output(self, donut_text: str, interface_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Donut's structured text output using dynamic field mapping.
        """
        # Try to parse as JSON first (Donut sometimes outputs structured JSON)
        json_result = self._try_parse_json(donut_text)
        if json_result:
            return self._map_json_to_schema(json_result, interface_schema)
        
        # Process as structured text with dynamic field extraction
        return self._extract_from_structured_text(donut_text, interface_schema)
    
    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to parse text as JSON."""
        try:
            # Clean up common Donut output issues
            cleaned = text.strip()
            if cleaned.startswith('<s>'):
                cleaned = cleaned[3:]
            if cleaned.endswith('</s>'):
                cleaned = cleaned[:-4]
            
            # Try direct JSON parsing
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            # Try to extract JSON from text
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, cleaned)
            
            for match in matches:
                try:
                    return json.loads(match)
                except (json.JSONDecodeError, ValueError):
                    continue
            
            return None
    
    def _map_json_to_schema(self, json_data: Dict[str, Any], 
                           interface_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically map JSON data to interface schema using intelligent field matching.
        """
        result = {}
        
        for field_name, field_info in interface_schema.items():
            if field_name.startswith('_'):
                continue
            
            # Get search terms for this field
            search_terms = self._get_field_search_terms(field_name, field_info)
            field_type = self._get_field_type(field_info)
            
            # Find best matching value in JSON
            best_value = self._find_best_json_match(json_data, search_terms, field_type)
            
            if field_type == 'object' and isinstance(field_info, dict):
                # Recursively process nested objects
                nested_result = self._map_json_to_schema(best_value or {}, field_info)
                result[field_name] = nested_result
            elif field_type == 'array_of_objects' and isinstance(field_info, dict):
                # Process array of objects
                result[field_name] = self._extract_array_from_json(best_value, field_info)
            else:
                result[field_name] = best_value
        
        return result
    
    def _extract_from_structured_text(self, text: str, interface_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract fields from structured text using dynamic pattern matching.
        """
        result = {}
        
        # Pre-process text for better extraction
        processed_text = self._preprocess_text(text)
        
        for field_name, field_info in interface_schema.items():
            if field_name.startswith('_'):
                continue
            
            search_terms = self._get_field_search_terms(field_name, field_info)
            field_type = self._get_field_type(field_info)
            
            if field_type == 'object' and isinstance(field_info, dict):
                # Extract nested object
                result[field_name] = self._extract_from_structured_text(processed_text, field_info)
            elif field_type == 'array_of_objects':
                # Extract array of objects
                result[field_name] = self._extract_array_of_objects(processed_text, field_info)
            elif field_type == 'array':
                # Extract array of strings
                result[field_name] = self._extract_array_field(processed_text, search_terms)
            else:
                # Extract simple field
                result[field_name] = self._extract_simple_field(processed_text, search_terms, field_type)
        
        return result
    
    def _extract_hybrid(self, pdf_path: str, interface_schema: Dict[str, Any], 
                       page_num: int, donut_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Perform hybrid extraction combining Donut and NLP approaches.
        """
        # Extract raw text for NLP processing
        raw_text = self._extract_pdf_text(pdf_path, page_num)
        if not raw_text:
            return donut_result
        
        # Perform NLP extraction
        nlp_result = self._extract_with_nlp_text(raw_text, interface_schema)
        
        # Intelligently merge results
        return self._merge_results(donut_result, nlp_result, interface_schema)
    
    def _extract_with_nlp(self, pdf_path: str, interface_schema: Dict[str, Any], 
                         page_num: int) -> Optional[Dict[str, Any]]:
        """Extract using NLP-based text processing."""
        raw_text = self._extract_pdf_text(pdf_path, page_num)
        if not raw_text:
            return None
        
        return self._extract_with_nlp_text(raw_text, interface_schema)
    
    def _extract_with_nlp_text(self, text: str, interface_schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract fields from text using NLP processing."""
        if not self.nlp_model:
            # Fallback to regex-based extraction
            return self._extract_with_regex(text, interface_schema)
        
        print("🧠 Processing with NLP...")
        try:
            doc = self.nlp_model(text)
            return self._extract_with_spacy(doc, interface_schema)
        except Exception as e:
            print(f"❌ NLP processing error: {e}")
            return self._extract_with_regex(text, interface_schema)
    
    def _extract_with_spacy(self, doc, interface_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields using spaCy NLP processing."""
        result = {}
        
        for field_name, field_info in interface_schema.items():
            if field_name.startswith('_'):
                continue
            
            search_terms = self._get_field_search_terms(field_name, field_info)
            field_type = self._get_field_type(field_info)
            
            if field_type == 'object' and isinstance(field_info, dict):
                result[field_name] = self._extract_with_spacy(doc, field_info)
            elif field_type == 'array_of_objects':
                result[field_name] = self._extract_array_with_nlp(doc, field_info)
            elif field_type == 'array':
                result[field_name] = self._extract_array_with_nlp_simple(doc, search_terms)
            else:
                result[field_name] = self._extract_field_with_nlp(doc, search_terms, field_type)
        
        return result
    
    def _extract_with_regex(self, text: str, interface_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback regex-based extraction."""
        result = {}
        
        for field_name, field_info in interface_schema.items():
            if field_name.startswith('_'):
                continue
            
            search_terms = self._get_field_search_terms(field_name, field_info)
            field_type = self._get_field_type(field_info)
            
            if field_type == 'object' and isinstance(field_info, dict):
                result[field_name] = self._extract_with_regex(text, field_info)
            elif field_type == 'array_of_objects':
                result[field_name] = self._extract_array_with_regex(text, field_info)
            elif field_type == 'array':
                result[field_name] = self._extract_array_with_regex_simple(text, search_terms)
            else:
                result[field_name] = self._extract_field_with_regex(text, search_terms, field_type)
        
        return result
    
    # Helper methods for dynamic field processing
    
    def _get_field_search_terms(self, field_name: str, field_info: Any) -> List[str]:
        """Get search terms for a field based on interface structure."""
        if isinstance(field_info, dict) and '_search_terms' in field_info:
            return field_info['_search_terms']
        
        # Generate dynamic search terms based on field name
        return self._generate_search_terms(field_name)
    
    def _get_field_type(self, field_info: Any) -> str:
        """Get field type from interface info."""
        if isinstance(field_info, dict):
            return field_info.get('_type', 'string')
        return 'string'
    
    @lru_cache(maxsize=128)
    def _generate_search_terms(self, field_name: str) -> List[str]:
        """Generate dynamic search terms for a field name."""
        terms = [field_name]
        
        # Add variations
        terms.extend([
            field_name.lower(),
            field_name.upper(),
            field_name.replace('_', ' '),
            field_name.replace('_', '-'),
            re.sub(r'([A-Z])', r' \1', field_name).strip(),  # camelCase to words
        ])
        
        # Add semantic variations based on common field patterns
        semantic_map = {
            'product': ['name', 'title', 'identifier', 'designation'],
            'hazard': ['danger', 'warning', 'safety', 'risk'],
            'signal': ['warning', 'danger'],
            'cas': ['cas number', 'cas no', 'cas-no', 'registry number'],
            'ingredient': ['component', 'substance', 'chemical'],
            'percent': ['percentage', '%', 'concentration', 'amount'],
        }
        
        for key, variations in semantic_map.items():
            if key in field_name.lower():
                terms.extend(variations)
        
        return list(set(terms))  # Remove duplicates
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better extraction."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR/extraction issues
        text = text.replace('|', ' ')  # Table separators
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Split joined words
        
        return text.strip()
    
    def _extract_pdf_text(self, pdf_path: str, page_num: int) -> Optional[str]:
        """Extract raw text from PDF using pdfplumber."""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > page_num:
                    page = pdf.pages[page_num]
                    return page.extract_text() or ""
                return ""
        except Exception as e:
            print(f"❌ PDF text extraction error: {e}")
            return None
    
    # Specific field extraction methods
    
    def _extract_simple_field(self, text: str, search_terms: List[str], field_type: str) -> Any:
        """Extract a simple field value using dynamic search terms."""
        # Try pattern-based extraction for specific field types
        if 'cas' in str(search_terms).lower():
            cas_match = self._extract_cas_number(text)
            if cas_match:
                return cas_match
        
        # Try fuzzy matching
        best_value = self._extract_with_fuzzy_matching(text, search_terms)
        
        # Clean and format based on field type
        if best_value:
            return self._format_field_value(best_value, field_type)
        
        return None
    
    def _extract_array_field(self, text: str, search_terms: List[str]) -> List[str]:
        """Extract array field values."""
        results = []
        
        # Look for list patterns
        list_patterns = [
            r'^\s*[-*•]\s*(.+)$',  # Bullet points
            r'^\s*\d+\.\s*(.+)$',  # Numbered lists
            r'^\s*[a-z]\)\s*(.+)$',  # Letter lists
        ]
        
        lines = text.split('\n')
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Check if line matches search terms
            if self._line_matches_terms(line_clean, search_terms):
                # Extract content from list items
                content = line_clean
                for pattern in list_patterns:
                    match = re.match(pattern, line_clean)
                    if match:
                        content = match.group(1).strip()
                        break
                
                if content and len(content) > 2:
                    results.append(content)
        
        return results[:10]  # Limit results
    
    def _extract_array_of_objects(self, text: str, array_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract array of objects dynamically."""
        # Find sections that likely contain array data
        sections = self._find_table_sections(text, array_schema)
        
        results = []
        for section in sections:
            obj = {}
            for field_name, field_info in array_schema.items():
                if field_name.startswith('_'):
                    continue
                
                search_terms = self._get_field_search_terms(field_name, field_info)
                field_type = self._get_field_type(field_info)
                
                value = self._extract_simple_field(section, search_terms, field_type)
                if value:
                    obj[field_name] = value
            
            if obj:
                results.append(obj)
        
        return results
    
    def _find_table_sections(self, text: str, array_schema: Dict[str, Any]) -> List[str]:
        """Find sections that contain tabular/array data."""
        all_terms = []
        for field_name, field_info in array_schema.items():
            if not field_name.startswith('_'):
                terms = self._get_field_search_terms(field_name, field_info)
                all_terms.extend(terms)
        
        sections = []
        lines = text.split('\n')
        current_section = []
        section_score = 0
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                if current_section and section_score > 1:
                    sections.append('\n'.join(current_section))
                current_section = []
                section_score = 0
                continue
            
            # Score line based on relevant terms
            line_score = sum(1 for term in all_terms 
                           if self._fuzzy_match_score(term, line_clean) > 60)
            
            current_section.append(line_clean)
            section_score += line_score
            
            # Individual high-scoring lines are also sections
            if line_score >= 2:
                sections.append(line_clean)
        
        if current_section and section_score > 1:
            sections.append('\n'.join(current_section))
        
        return sections
    
    def _extract_cas_number(self, text: str) -> Optional[str]:
        """Extract CAS numbers using pattern matching."""
        patterns = [
            r'\bCAS[:\s]*(\d{2,7}-\d{2}-\d)\b',
            r'\b(\d{2,7}-\d{2}-\d)\b',
            r'CAS\s*No\.?\s*:?\s*(\d{2,7}-\d{2}-\d)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for cas in matches:
                if self._validate_cas_number(cas):
                    return cas
        
        return None
    
    def _validate_cas_number(self, cas: str) -> bool:
        """Validate CAS number using check digit."""
        if not re.match(r'^\d{2,7}-\d{2}-\d$', cas):
            return False
        
        digits = cas.replace('-', '')
        check_digit = int(digits[-1])
        calculated = sum(int(d) * (i + 1) for i, d in enumerate(digits[-2::-1])) % 10
        
        return check_digit == calculated
    
    def _extract_with_fuzzy_matching(self, text: str, search_terms: List[str]) -> Optional[str]:
        """Extract using fuzzy string matching."""
        best_score = 0
        best_value = None
        
        lines = text.split('\n')
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            for term in search_terms:
                score = self._fuzzy_match_score(term, line_clean)
                if score > 70 and score > best_score:
                    extracted = self._extract_value_from_line(line_clean, term)
                    if extracted:
                        best_score = score
                        best_value = extracted
        
        return best_value
    
    def _fuzzy_match_score(self, term: str, text: str) -> float:
        """Calculate fuzzy match score between term and text."""
        return rapidfuzz.fuzz.partial_ratio(term.lower(), text.lower())
    
    def _extract_value_from_line(self, line: str, search_term: str) -> Optional[str]:
        """Extract value from line containing search term."""
        patterns = [
            rf'{re.escape(search_term)}\s*[:\-]\s*(.+?)(?:\n|$)',
            rf'{re.escape(search_term)}\s+(.+?)(?:\n|$)',
            rf'(.+?)\s*[:\-]\s*{re.escape(search_term)}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                return self._clean_extracted_value(value)
        
        return line.strip()
    
    def _clean_extracted_value(self, value: str) -> str:
        """Clean extracted value."""
        if not value:
            return ""
        
        # Remove common prefixes/suffixes
        value = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', value)
        value = re.sub(r'\s+', ' ', value)
        
        return value.strip()
    
    def _format_field_value(self, value: str, field_type: str) -> Any:
        """Format value according to field type."""
        if field_type == 'number':
            number_match = re.search(r'(\d+(?:\.\d+)?)', value)
            return float(number_match.group(1)) if number_match else value
        elif field_type == 'boolean':
            return value.lower() in ['true', 'yes', '1', 'on']
        
        return value
    
    def _line_matches_terms(self, line: str, search_terms: List[str]) -> bool:
        """Check if line matches any search terms."""
        return any(self._fuzzy_match_score(term, line) > 60 for term in search_terms)
    
    def _find_best_json_match(self, json_data: Dict[str, Any], 
                             search_terms: List[str], field_type: str) -> Any:
        """Find best matching value in JSON data."""
        best_score = 0
        best_value = None
        
        def search_recursive(obj, path=""):
            nonlocal best_score, best_value
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    for term in search_terms:
                        score = self._fuzzy_match_score(term, key)
                        if score > 70 and score > best_score:
                            best_score = score
                            best_value = value
                    
                    search_recursive(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_recursive(item, f"{path}[{i}]")
        
        search_recursive(json_data)
        return best_value
    
    def _extract_array_from_json(self, json_value: Any, array_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract array of objects from JSON value."""
        if not isinstance(json_value, list):
            return []
        
        results = []
        for item in json_value:
            if isinstance(item, dict):
                mapped_item = self._map_json_to_schema(item, array_schema)
                if mapped_item:
                    results.append(mapped_item)
        
        return results
    
    # NLP-specific extraction methods
    
    def _extract_field_with_nlp(self, doc, search_terms: List[str], field_type: str) -> Any:
        """Extract field using spaCy NLP."""
        # Use named entity recognition and pattern matching
        for ent in doc.ents:
            for term in search_terms:
                if self._fuzzy_match_score(term, ent.text) > 70:
                    return self._format_field_value(ent.text, field_type)
        
        # Fallback to sentence-level matching
        for sent in doc.sents:
            for term in search_terms:
                if self._fuzzy_match_score(term, sent.text) > 60:
                    extracted = self._extract_value_from_line(sent.text, term)
                    if extracted:
                        return self._format_field_value(extracted, field_type)
        
        return None
    
    def _extract_array_with_nlp(self, doc, array_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract array of objects using NLP."""
        # Find relevant sentences/sections
        all_terms = []
        for field_name, field_info in array_schema.items():
            if not field_name.startswith('_'):
                terms = self._get_field_search_terms(field_name, field_info)
                all_terms.extend(terms)
        
        relevant_sents = []
        for sent in doc.sents:
            score = sum(1 for term in all_terms 
                       if self._fuzzy_match_score(term, sent.text) > 60)
            if score >= 2:
                relevant_sents.append(sent.text)
        
        # Extract objects from relevant sentences
        results = []
        for sent_text in relevant_sents:
            obj = {}
            for field_name, field_info in array_schema.items():
                if field_name.startswith('_'):
                    continue
                
                search_terms = self._get_field_search_terms(field_name, field_info)
                field_type = self._get_field_type(field_info)
                
                value = self._extract_simple_field(sent_text, search_terms, field_type)
                if value:
                    obj[field_name] = value
            
            if obj:
                results.append(obj)
        
        return results
    
    def _extract_array_with_nlp_simple(self, doc, search_terms: List[str]) -> List[str]:
        """Extract simple array using NLP."""
        results = []
        
        for sent in doc.sents:
            for term in search_terms:
                if self._fuzzy_match_score(term, sent.text) > 60:
                    results.append(sent.text.strip())
                    break
        
        return results[:10]
    
    # Result processing and merging
    
    def _merge_results(self, donut_result: Optional[Dict[str, Any]], 
                      nlp_result: Optional[Dict[str, Any]], 
                      interface_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Intelligently merge results from different extraction methods."""
        if not donut_result and not nlp_result:
            return self._create_empty_result(interface_schema)
        
        if not donut_result:
            return nlp_result
        
        if not nlp_result:
            return donut_result
        
        # Merge intelligently
        merged = {}
        for field_name, field_info in interface_schema.items():
            if field_name.startswith('_'):
                continue
            
            donut_value = donut_result.get(field_name)
            nlp_value = nlp_result.get(field_name)
            
            # Choose better value based on completeness and quality
            if self._is_better_value(donut_value, nlp_value):
                merged[field_name] = donut_value
            else:
                merged[field_name] = nlp_value
        
        return merged
    
    def _is_better_value(self, value1: Any, value2: Any) -> bool:
        """Determine if value1 is better than value2."""
        if not value2:
            return bool(value1)
        if not value1:
            return False
        
        # Convert to comparable format
        str1 = str(value1).strip() if value1 else ""
        str2 = str(value2).strip() if value2 else ""
        
        # Longer, more detailed values are generally better
        if len(str1) > len(str2) * 1.5:
            return True
        
        # Structured content is better
        structure_score1 = str1.count(':') + str1.count('=') + str1.count('-')
        structure_score2 = str2.count(':') + str2.count('=') + str2.count('-')
        
        return structure_score1 > structure_score2
    
    def _is_high_quality_result(self, result: Dict[str, Any], 
                               interface_schema: Dict[str, Any]) -> bool:
        """Check if result is high quality."""
        field_count = self._count_fields(result)
        total_fields = len([k for k in interface_schema.keys() if not k.startswith('_')])
        
        # High quality if we filled > 70% of fields
        return field_count / max(total_fields, 1) > 0.7
    
    def _is_adequate_result(self, result: Dict[str, Any], 
                           interface_schema: Dict[str, Any]) -> bool:
        """Check if result is adequate."""
        field_count = self._count_fields(result)
        
        # Adequate if we have at least 2 meaningful fields
        return field_count >= 2
    
    def _count_fields(self, result: Dict[str, Any]) -> int:
        """Count non-empty fields in result."""
        count = 0
        
        def count_recursive(obj):
            nonlocal count
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if not key.startswith('_'):
                        if value and str(value).strip():
                            count += 1
                        count_recursive(value)
            elif isinstance(obj, list):
                if obj:
                    count += 1
                    for item in obj[:3]:  # Count first few items
                        count_recursive(item)
        
        count_recursive(result)
        return count
    
    def _create_empty_result(self, interface_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create empty result matching interface schema."""
        result = {}
        
        for field_name, field_info in interface_schema.items():
            if field_name.startswith('_'):
                continue
            
            field_type = self._get_field_type(field_info)
            
            if field_type == 'object':
                result[field_name] = self._create_empty_result(field_info)
            elif field_type in ['array', 'array_of_objects']:
                result[field_name] = []
            else:
                result[field_name] = None
        
        return result


# Convenience functions for backward compatibility

def extract_fields_from_pdf_with_donut(pdf_path: str, interface_schema: Dict[str, Any], 
                                      page_num: int = 0, timeout: int = 15) -> Dict[str, Any]:
    """
    Extract fields from PDF using modern Donut-first approach.
    
    Args:
        pdf_path: Path to PDF file
        interface_schema: Parsed TypeScript interface schema
        page_num: Page number to process
        timeout: Timeout for Donut processing
        
    Returns:
        Extracted data dictionary
    """
    config = ExtractionConfig(donut_timeout=timeout)
    extractor = DynamicExtractor(config)
    result = extractor.extract_from_pdf(pdf_path, interface_schema, page_num)
    return result.data


def extract_fields_from_interface(text: str, interface_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract fields from text using interface schema (backward compatibility).
    
    Args:
        text: Text to extract from
        interface_schema: Interface schema
        
    Returns:
        Extracted data dictionary
    """
    extractor = DynamicExtractor()
    return extractor._extract_with_nlp_text(text, interface_schema) or {}


def get_extraction_stats() -> Dict[str, Any]:
    """Get extraction statistics."""
    return {
        "note": "Statistics integrated into ExtractionResult objects",
        "donut_available": DONUT_AVAILABLE,
        "nlp_available": NLP_AVAILABLE
    }
