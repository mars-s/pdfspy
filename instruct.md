# PDFSpy Performance Upgrade Plan

## Phase 1: Core Infrastructure Replacement (Priority 1)

### 1.1 Replace PyMuPDF with pdfplumber

**Files to modify:** `app/utils.py`, `main.py`

**Changes:**

```python
# Replace PyMuPDF extraction with pdfplumber
import pdfplumber
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

def extract_pdf_content(pdf_path):
    """Fast PDF extraction with layout awareness"""
    with pdfplumber.open(pdf_path) as pdf:
        # Extract text with position info
        full_text = ""
        tables = []

        for page in pdf.pages:
            # Get text with bounding boxes
            full_text += page.extract_text(layout=True)

            # Extract tables separately
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)

        return {
            'text': full_text,
            'tables': tables,
            'metadata': pdf.metadata
        }
```

### 1.2 Remove spaCy Dependencies

**Files to modify:** `app/dynamic_extractor.py`

**Replace with:**

- `rapidfuzz` for fuzzy string matching
- `re` with pre-compiled patterns
- Custom tokenization for chemical terms

```python
import rapidfuzz
import re
from functools import lru_cache

# Pre-compile common chemical patterns
CHEMICAL_PATTERNS = {
    'cas_number': re.compile(r'\b\d{2,7}-\d{2}-\d\b'),
    'ec_number': re.compile(r'\b\d{3}-\d{3}-\d\b'),
    'reach_number': re.compile(r'\b\d{2}-\d{10}-\d{2}-[a-zA-Z0-9]\b'),
    'hazard_code': re.compile(r'\bH\d{3}\b'),
    'precautionary_code': re.compile(r'\bP\d{3}\b')
}

@lru_cache(maxsize=1000)
def fuzzy_match_field(field_name, text_chunk, threshold=80):
    """Fast fuzzy matching with caching"""
    return rapidfuzz.fuzz.partial_ratio(field_name.lower(), text_chunk.lower()) > threshold
```

## Phase 2: Add Donut for Document Understanding (Priority 2)

### 2.1 Donut Integration Setup

**New file:** `app/donut_processor.py`

```python
from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image
import pdf2image
import time

class FastDonutProcessor:
    def __init__(self, model_name="naver-clova-ix/donut-base-finetuned-docvqa"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = DonutProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        self.model.to(self.device)

        # Enable optimizations
        if self.device == "cuda":
            self.model.half()  # Use FP16 for speed

    def process_pdf_page(self, pdf_path, page_num=0, timeout=5):
        """Process single PDF page with timeout"""
        start_time = time.time()

        try:
            # Convert PDF page to image
            images = pdf2image.convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
            if not images:
                return None

            image = images[0]

            # Check timeout
            if time.time() - start_time > timeout:
                return None

            # Process with Donut
            pixel_values = self.processor(image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)

            # Generate with timeout
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=512,
                    num_beams=1,  # Faster than beam search
                    do_sample=False
                )

            # Decode results
            sequence = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

            return {
                'structured_text': sequence,
                'processing_time': time.time() - start_time,
                'success': True
            }

        except Exception as e:
            return {
                'error': str(e),
                'processing_time': time.time() - start_time,
                'success': False
            }

# Usage with timeout fallback
def try_donut_extraction(pdf_path, fallback_extractor):
    donut = FastDonutProcessor()
    result = donut.process_pdf_page(pdf_path, timeout=5)

    if result and result['success'] and result['processing_time'] < 5:
        return result['structured_text']
    else:
        # Fallback to pdfplumber
        return fallback_extractor(pdf_path)
```

### 2.2 Conditional Donut Usage

**File to modify:** `app/dynamic_extractor.py`

```python
def extract_with_fallback(pdf_path, interface_schema):
    """Try Donut first, fallback to pdfplumber"""

    # Try Donut with 5-second timeout
    donut_result = try_donut_extraction(pdf_path)

    if donut_result:
        # Process Donut structured output
        return process_structured_text(donut_result, interface_schema)
    else:
        # Fallback to fast pdfplumber extraction
        return process_with_pdfplumber(pdf_path, interface_schema)
```

## Phase 3: Chemical Domain-Specific Extraction (Priority 1)

### 3.1 Chemical NER System

**New file:** `app/chemical_ner.py`

```python
import re
from typing import Dict, List, Tuple
import json
from pathlib import Path

class ChemicalNER:
    def __init__(self):
        self.patterns = self._load_chemical_patterns()
        self.dictionaries = self._load_chemical_dictionaries()

    def _load_chemical_patterns(self):
        """Pre-compiled regex patterns for chemical entities"""
        return {
            'cas_number': re.compile(r'\b(\d{2,7}-\d{2}-\d)\b'),
            'ec_number': re.compile(r'\b(\d{3}-\d{3}-\d)\b'),
            'reach_registration': re.compile(r'\b(\d{2}-\d{10}-\d{2}-[a-zA-Z0-9])\b'),
            'hazard_statement': re.compile(r'\b(H\d{3}[A-Za-z]*)\b'),
            'precautionary_statement': re.compile(r'\b(P\d{3}[A-Za-z]*)\b'),
            'signal_word': re.compile(r'\b(DANGER|WARNING|CAUTION)\b', re.IGNORECASE),
            'pictogram': re.compile(r'GHS\d{2}', re.IGNORECASE),
            'concentration_range': re.compile(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%'),
            'concentration_exact': re.compile(r'(\d+(?:\.\d+)?)\s*%'),
            'boiling_point': re.compile(r'(\d+(?:\.\d+)?)\s*°?C', re.IGNORECASE),
            'molecular_weight': re.compile(r'(\d+(?:\.\d+)?)\s*g/mol', re.IGNORECASE)
        }

    def _load_chemical_dictionaries(self):
        """Load chemical substance dictionaries"""
        return {
            'hazard_statements': self._load_hazard_statements(),
            'pictogram_meanings': self._load_pictogram_meanings(),
            'chemical_synonyms': self._load_chemical_synonyms()
        }

    def extract_entities(self, text: str) -> Dict[str, List[Tuple[str, int, int]]]:
        """Extract all chemical entities from text"""
        entities = {}

        for entity_type, pattern in self.patterns.items():
            matches = []
            for match in pattern.finditer(text):
                matches.append((
                    match.group(1) if match.groups() else match.group(0),
                    match.start(),
                    match.end()
                ))
            entities[entity_type] = matches

        return entities

    def validate_cas_number(self, cas: str) -> bool:
        """Validate CAS number using check digit"""
        if not re.match(r'^\d{2,7}-\d{2}-\d$', cas):
            return False

        # CAS check digit validation
        digits = cas.replace('-', '')
        check_digit = int(digits[-1])
        calculated = sum(int(d) * (i + 1) for i, d in enumerate(digits[-2::-1])) % 10

        return check_digit == calculated

    def _load_hazard_statements(self):
        """Load H-statements dictionary"""
        return {
            'H200': 'Unstable explosive',
            'H201': 'Explosive; mass explosion hazard',
            'H301': 'Toxic if swallowed',
            'H302': 'Harmful if swallowed',
            'H315': 'Causes skin irritation',
            'H319': 'Causes serious eye irritation',
            'H335': 'May cause respiratory irritation',
            # Add more as needed
        }

    def _load_pictogram_meanings(self):
        """Load GHS pictogram meanings"""
        return {
            'GHS01': 'Explosive',
            'GHS02': 'Flammable',
            'GHS03': 'Oxidizing',
            'GHS04': 'Compressed Gas',
            'GHS05': 'Corrosive',
            'GHS06': 'Toxic',
            'GHS07': 'Harmful',
            'GHS08': 'Health Hazard',
            'GHS09': 'Environmental Hazard'
        }

    def _load_chemical_synonyms(self):
        """Load common chemical name variations"""
        return {
            'sodium_bicarbonate': ['sodium hydrogen carbonate', 'baking soda', 'nahco3'],
            'hydrochloric_acid': ['muriatic acid', 'hcl'],
            # Add more synonyms
        }
```

### 3.2 Hazard Code Recognition

**New file:** `app/hazard_classifier.py`

```python
class HazardClassifier:
    def __init__(self):
        self.hazard_classes = self._build_hazard_classification()

    def classify_hazard_statements(self, h_codes: List[str]) -> Dict[str, List[str]]:
        """Classify H-codes into hazard categories"""
        classification = {
            'physical_hazards': [],
            'health_hazards': [],
            'environmental_hazards': []
        }

        for code in h_codes:
            code_num = int(code[1:])  # Remove 'H' prefix

            if 200 <= code_num <= 290:
                classification['physical_hazards'].append(code)
            elif 300 <= code_num <= 390:
                classification['health_hazards'].append(code)
            elif 400 <= code_num <= 490:
                classification['environmental_hazards'].append(code)

        return classification

    def determine_signal_word(self, h_codes: List[str]) -> str:
        """Determine signal word based on H-codes"""
        danger_codes = ['H200', 'H201', 'H300', 'H301', 'H310', 'H330', 'H340', 'H350', 'H360', 'H370']

        for code in h_codes:
            if code in danger_codes:
                return 'DANGER'

        return 'WARNING' if h_codes else 'None'
```

## Phase 4: Performance Optimizations (Priority 2)

### 4.1 Parallel Processing Setup

**File to modify:** `main.py`

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import asyncio
from pathlib import Path

class PDFBatchProcessor:
    def __init__(self, max_workers=None):
        self.max_workers = max_workers or min(cpu_count(), 8)
        self.chemical_ner = ChemicalNER()

    def process_batch(self, pdf_paths: List[Path], interface_path: Path):
        """Process multiple PDFs in parallel"""
        interface_schema = self._load_interface_schema(interface_path)

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_pdf = {
                executor.submit(self._process_single_pdf, pdf_path, interface_schema): pdf_path
                for pdf_path in pdf_paths
            }

            results = {}
            for future in as_completed(future_to_pdf):
                pdf_path = future_to_pdf[future]
                try:
                    result = future.result(timeout=30)  # 30 second timeout per PDF
                    results[str(pdf_path)] = result
                except Exception as e:
                    results[str(pdf_path)] = {'error': str(e)}

        return results

    def _process_single_pdf(self, pdf_path: Path, interface_schema: dict):
        """Process single PDF with all optimizations"""
        try:
            # Try Donut first (with timeout)
            extracted_data = extract_with_fallback(pdf_path, interface_schema)

            # Apply chemical NER
            enhanced_data = self._enhance_with_chemical_ner(extracted_data)

            # Validate against TypeScript interface
            validated_data = self._validate_against_schema(enhanced_data, interface_schema)

            return validated_data

        except Exception as e:
            return {'error': f'Processing failed: {str(e)}'}

# Usage example
if __name__ == "__main__":
    processor = PDFBatchProcessor()
    pdf_files = list(Path("samples/").glob("*.pdf"))
    interface_file = Path("interfaces/sds_interface.ts")

    results = processor.process_batch(pdf_files, interface_file)

    # Save results
    with open("extraction_results.json", "w") as f:
        json.dump(results, f, indent=2)
```

### 4.2 Caching System

**New file:** `app/cache_manager.py`

```python
import joblib
import hashlib
from pathlib import Path
from functools import wraps

class ExtractionCache:
    def __init__(self, cache_dir="cache/"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, pdf_path, interface_schema):
        """Generate cache key from PDF hash and interface"""
        pdf_hash = hashlib.md5(Path(pdf_path).read_bytes()).hexdigest()
        schema_hash = hashlib.md5(str(interface_schema).encode()).hexdigest()
        return f"{pdf_hash}_{schema_hash}.pkl"

    def get(self, pdf_path, interface_schema):
        """Get cached result"""
        cache_file = self.cache_dir / self._get_cache_key(pdf_path, interface_schema)
        if cache_file.exists():
            return joblib.load(cache_file)
        return None

    def set(self, pdf_path, interface_schema, result):
        """Cache result"""
        cache_file = self.cache_dir / self._get_cache_key(pdf_path, interface_schema)
        joblib.dump(result, cache_file)

def cached_extraction(func):
    """Decorator for caching extraction results"""
    cache = ExtractionCache()

    @wraps(func)
    def wrapper(pdf_path, interface_schema, *args, **kwargs):
        # Try cache first
        cached_result = cache.get(pdf_path, interface_schema)
        if cached_result:
            return cached_result

        # Compute and cache result
        result = func(pdf_path, interface_schema, *args, **kwargs)
        cache.set(pdf_path, interface_schema, result)
        return result

    return wrapper
```

## Phase 5: Implementation Order

### Week 1: Core Replacement

1. Replace PyMuPDF with pdfplumber in `utils.py`
2. Remove spaCy dependencies, implement rapidfuzz matching
3. Add basic parallel processing to `main.py`
4. Test performance improvements

### Week 2: Chemical NER

1. Implement `chemical_ner.py` with pattern matching
2. Add hazard classification system
3. Integrate chemical entity extraction into pipeline
4. Validate chemical entity accuracy

### Week 3: Donut Integration

1. Set up Donut processor with timeout
2. Implement fallback system
3. Benchmark Donut vs pdfplumber performance
4. Optimize for 5-second constraint

### Week 4: Optimization & Testing

1. Add caching system
2. Performance profiling and bottleneck identification
3. Scale testing with large PDF batches
4. Documentation updates

## Expected Performance Improvements

- **Processing Speed**: 3-5x faster per PDF
- **Scalability**: Process 10-50 PDFs concurrently
- **Accuracy**: Better chemical entity recognition
- **Memory Usage**: 40-60% reduction
- **Cache Hit Rate**: 80%+ for repeated processing

## Dependencies to Add

```bash
pip install pdfplumber rapidfuzz transformers torch pdf2image
pip install joblib pillow datasets accelerate
```

## Success Metrics

- Single PDF processing: < 2 seconds (without Donut) or < 5 seconds (with Donut)
- Batch processing: 50+ PDFs in under 5 minutes
- Chemical entity accuracy: > 95% for CAS numbers, hazard codes
- Memory usage: < 100MB per PDF process
- Cache effectiveness: > 80% hit rate for repeated documents
