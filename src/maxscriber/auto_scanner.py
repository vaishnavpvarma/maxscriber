import pdfplumber
import re
from pathlib import Path
from typing import List, Set, Dict, Tuple
from maxscriber.utils.logger import get_logger

logger = get_logger("auto_scanner")

class AutoScanner:
    """
    Scans PDF files to discover test names and metadata patterns.
    """
    def __init__(self):
        self.noise_patterns = [
            re.compile(r'^\s*$'),               # empty or whitespace
            re.compile(r'^\d+$'),               # purely numeric
            re.compile(r'^\d{1,2}[/-]\d{1,2}'), # dates
            re.compile(r'(?i)result|value|unit|reference|method|normal'), # headers
            re.compile(r'^[-_]+$')              # dashes/separators
        ]

    def _is_noise(self, text: str) -> bool:
        if not text or len(text.strip()) < 2:
            return True
        for pattern in self.noise_patterns:
            if pattern.search(text.strip()):
                return True
        return False

    def scan_directory(self, input_dir: Path, max_files: int = 50) -> Tuple[List[str], Dict[str, bool]]:
        """
        Scans up to max_files PDFs in the directory and extracts candidate test names and detects metadata.
        """
        test_names: Set[str] = set()
        metadata_found = {
            "Patient Name": False,
            "Age/Gender": False,
            "Lab ID": False,
            "Collection Date": False
        }

        pdf_files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
        pdf_files = pdf_files[:max_files]

        if not pdf_files:
            logger.warning(f"No PDFs found in {input_dir}")
            return [], metadata_found

        logger.info(f"Scanning {len(pdf_files)} PDFs for structure discovery...")

        for pdf_path in pdf_files:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        # Extract metadata cues from text
                        text = page.extract_text()
                        if text:
                            if re.search(r'(?i)name|patient', text): metadata_found["Patient Name"] = True
                            if re.search(r'(?i)age|years|gender|sex', text): metadata_found["Age/Gender"] = True
                            if re.search(r'(?i)id|ref\s*no|sid', text): metadata_found["Lab ID"] = True
                            if re.search(r'(?i)date|collected|reported', text): metadata_found["Collection Date"] = True

                        # Extract test names from tables (assuming first column)
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if not row:
                                    continue
                                first_col = row[0]
                                if first_col and isinstance(first_col, str):
                                    clean_text = first_col.strip().replace('\n', ' ')
                                    if not self._is_noise(clean_text):
                                        test_names.add(clean_text)
            except Exception as e:
                logger.error(f"Error reading {pdf_path.name}: {e}")

        sorted_tests = sorted(list(test_names))
        return sorted_tests, metadata_found
