# PRD: AIExtractor Module for MaxScriber v3

## Purpose
Enhance medical PDF data extraction by integrating AI models for layout understanding (LayoutLMv3) and biomedical entity recognition (BioBERT) to improve accuracy over rule-based methods.

## Target Users
Medical researchers, lab technicians, and healthcare professionals processing lab report PDFs who require structured data extraction for analysis.

## Key Features
1. **Layout-Aware Extraction**: Uses LayoutLMv3 to understand spatial relationships between text elements, enabling accurate association of test names with values/units.
2. **Biomedical Entity Recognition**: Employs BioBERT to identify clinical entities (diseases, chemicals, genes) within extracted text.
3. **Hybrid Operation**: Works alongside existing rule-based extractor; falls back gracefully if AI dependencies missing.
4. **Configurable Models**: Supports custom HuggingFace or local model paths for domain-specific fine-tuning.
5. **Hardware Acceleration**: Utilizes GPU when available, with CPU fallback.

## User Stories
- As a user, I want the AIExtractor to correctly map test names to values in complex layouts so I can reduce manual verification.
- As a user, I want biomedical entities extracted from reports to enable downstream analysis like phenotype-genotype correlation.
- As a user, I want the system to work without AI dependencies so I can still use rule-based extraction in restricted environments.
- As a user, I want to specify custom model paths so I can leverage institution-specific fine-tuned models.

## Acceptance Criteria
1. AIExtractor loads LayoutLMv3 and BioBERT models successfully when dependencies are present and paths are valid.
2. Given a medical PDF page, returns structured data containing test names, values, and units derived from layout understanding.
3. Given medical text, returns list of biomedical entities with confidence scores.
4. Initializes without error when AI dependencies missing, logging warning and disabling AI features.
5. Processes documents at acceptable speed (<5 sec/page on CPU, <1 sec/page on GPU).

# TRD: AIExtractor Module for MaxScriber v3

## Module Location
`MaxScriber_v3_App/maxscriber/ai_core/ai_extractor.py`

## Dependencies
- **Required** (for AI features): `torch>=1.9.0`, `transformers>=4.10.0`
- **Optional**: None (core functionality degrades gracefully)
- **Note**: AI dependencies are optional extras; rule-based extractor functions without them.

## Interface Specification

### Inputs
- `text` (str): Raw text extracted from PDF page (via pdfplumber)
- `image` (PIL.Image.Image): Rendered page image for layout analysis

### Outputs
Returns dictionary with:
- `layout_entities` (list): Entities from LayoutLMv3, each containing:
  - `entity` (str): Predicted label (e.g., "TEST_NAME", "VALUE", "UNIT")
  - `score` (float): Confidence [0-1]
  - `start` (int): Character start position in combined text+boxes input
  - `end` (int): Character end position
- `clinical_entities` (list): Entities from BioBERT NER, each containing:
  - `entity_group` (str): Entity type (e.g., "CHEMICAL", "DISEASE")
  - `score` (float): Confidence
  - `word` (str): Extracted entity text
  - `start` (int): Character start in input text
  - `end` (int): Character end in input text

## Data Flow
1. MaxScriber transcribe step extracts text/images from PDF pages
2. For each page: `AIExtractor.extract_entities(text, image)` called
3. Results aggregated across pages to build structured dataset
4. Output feeds into QC/stats/plotting stages

## Implementation Details

### Initialization
- `__init__(use_cuda=True)`: 
  - Checks `ML_AVAILABLE` flag (set during import)
  - Determines device (CUDA if available/requested, else CPU)
  - Initializes model placeholders to None

### Model Loading
- `load_models(layoutlm_path, biobert_path)`:
  - Loads LayoutLMv3Processor and LayoutLMv3ForTokenClassification
  - Loads BioBERT tokenizer/model and creates NER pipeline
  - Moves models to selected device
  - Logs loading progress

### Entity Extraction
- `extract_entities(text, image)`:
  - If `not ML_AVAILABLE`: raises RuntimeError
  - Layout processing (if image provided):
    - Processes image+text through LayoutLMv3
    - Extracts token/prediction alignments
    - Converts to entity list (TODO: implement alignment logic)
  - Text processing (if text provided):
    - Runs BioBERT NER pipeline on text
    - Returns entity list
  - Returns combined results dictionary

## Performance Requirements
- Model loading: One-time cost (<10 sec on modern hardware)
- Per-page processing: 
  - CPU: <5 seconds/page (Base models)
  - GPU: <1 second/page (Base models)
- Memory footprint: <2GB RAM for both models

## Error Handling
- Missing ML dependencies: Logs warning during import, sets `ML_AVAILABLE=False`
- Initialization without dependencies: Logs error, returns early
- Extraction without loaded models: Checks `self.ml_available` and raises RuntimeError
- Model loading failures: Propagates exceptions with context
- Invalid inputs: Validates text/image types, raises TypeError

## Scalability Considerations
- Stateless design allows parallel page processing
- Model loading optimized for single-session reuse
- Supports batch processing via external loop
- Memory usage constant per process (models loaded once)

## Security
- No direct network calls during execution (models pre-loaded)
- Model loading from trusted sources only (user-specified paths)
- No persistent state storage between executions

## Future Enhancements
1. Fine-tune LayoutLMv3 on medical document layout datasets
2. Implement confidence thresholding for entity filtering
3. Add support for multi-page context in layout analysis
4. Integrate with rule-based extractor for hybrid voting mechanism
5. Export attention maps for explainability