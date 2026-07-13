import logging
from typing import Dict, Any, List

# Setup logging
logger = logging.getLogger(__name__)

# Try to import ML libraries safely to allow core execution without them
try:
    # pyrefly: ignore [missing-import]
    import torch
    # pyrefly: ignore [missing-import]
    from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
    # pyrefly: ignore [missing-import]
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    # pyrefly: ignore [missing-import]
    from transformers import pipeline
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries (torch, transformers) not found. AIExtractor will be disabled.")


class AIExtractor:
    """
    AI Extractor module utilizing LayoutLMv3 for spatial document understanding
    and BioBERT for biomedical entity extraction.
    """
    
    def __init__(self, use_cuda: bool = True):
        self.ml_available = ML_AVAILABLE
        if not self.ml_available:
            logger.error("Attempted to initialize AIExtractor without ML dependencies.")
            return

        self.device = self._get_device(use_cuda)
        self.layoutlm_processor = None
        self.layoutlm_model = None
        self.biobert_pipeline = None

    def _get_device(self, preferred_use_cuda: bool) -> str:
        """Determines the appropriate device (CUDA or CPU) with graceful fallback."""
        if preferred_use_cuda and torch.cuda.is_available():
            logger.info("CUDA is available. Using GPU for AIExtractor.")
            return f"cuda:{torch.cuda.current_device()}"
        else:
            logger.info("CUDA not requested or not available. Falling back to CPU.")
            return "cpu"

    def load_models(self, layoutlm_path: str = "microsoft/layoutlmv3-base", biobert_path: str = "dmis-lab/biobert-v1.1"):
        """
        Loads the HuggingFace models into memory.
        
        Args:
            layoutlm_path (str): HuggingFace hub path or local path to LayoutLMv3 model.
            biobert_path (str): HuggingFace hub path or local path to BioBERT model.
        """
        if not self.ml_available:
            return

        logger.info(f"Loading LayoutLMv3 from {layoutlm_path} onto {self.device}...")
        self.layoutlm_processor = LayoutLMv3Processor.from_pretrained(layoutlm_path)
        self.layoutlm_model = LayoutLMv3ForTokenClassification.from_pretrained(layoutlm_path).to(self.device)

        logger.info(f"Loading BioBERT from {biobert_path} onto {self.device}...")
        tokenizer = AutoTokenizer.from_pretrained(biobert_path)
        model = AutoModelForTokenClassification.from_pretrained(biobert_path).to(self.device)
        self.biobert_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, device=self.device)
        
        logger.info("AI Models loaded successfully.")

    def extract_entities(self, text: str, image: Any = None) -> Dict[str, Any]:
        """
        Extracts entities from a document using both spatial (if image provided) and text data.
        
        Args:
            text (str): The raw text of the document.
            image: The image of the document page (PIL Image) for LayoutLMv3.
            
        Returns:
            dict: Structured data containing extracted clinical entities.
        """
        if not self.ml_available:
            raise RuntimeError("ML libraries not installed. Cannot run AIExtractor.")

        results = {
            "layout_entities": [],
            "clinical_entities": []
        }

        # 1. Spatial/Layout extraction
        if image and self.layoutlm_model and self.layoutlm_processor:
            # Placeholder for LayoutLMv3 encoding/forward pass
            # encoding = self.layoutlm_processor(image, text, return_tensors="pt").to(self.device)
            # outputs = self.layoutlm_model(**encoding)
            pass 

        # 2. Text-only Biomedical extraction
        if text and self.biobert_pipeline:
            # Note: We might chunk the text to handle model max-length limits
            ner_results = self.biobert_pipeline(text)
            results["clinical_entities"] = ner_results

        return results
