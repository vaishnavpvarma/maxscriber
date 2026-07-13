import re
from typing import List, Dict, Any
from rapidfuzz import process, fuzz

# Canonical Unit Normalisation mapping
UNIT_NORMALISATION = {
    'mg/dl':  'mg/dL',
    'mg/DL':  'mg/dL',
    'MG/DL':  'mg/dL',
    'mmol/l': 'mmol/L',
    'mmol/L': 'mmol/L',
    'MMOL/L': 'mmol/L',
    'g/dl':   'g/dL',
    'G/DL':   'g/dL',
    'u/l':    'U/L',
    'U/l':    'U/L',
}

class AdaptiveExtractor:
    """Advanced Schema-driven PDF data extractor with fuzzy matching and heuristics."""
    
    def __init__(self, schema: dict):
        self.schema = schema
        self.test_names = schema.get('tests', [])
        self.metadata_patterns = schema.get('metadata', {})
        # Pre-process canonical names for fuzzy matching
        self.canonical_names_lower = {t.lower(): t for t in self.test_names}
        
    def _clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return text.strip().replace('\n', ' ')

    def _normalize_unit(self, unit: str) -> str:
        """Standardize units to canonical form."""
        unit = self._clean_text(unit)
        if not unit:
            return "nil"
        return UNIT_NORMALISATION.get(unit, unit)

    def extract_metadata(self, text: str) -> Dict[str, str]:
        """Apply schema-defined regex patterns to extract demographics."""
        results = {}
        for key, pattern in self.metadata_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            results[key] = match.group(1).strip() if match else "nil"
        return results

    def _fuzzy_match_test(self, candidate: str, threshold: float = 85.0) -> str:
        """Match a candidate string to the closest canonical test name using rapidfuzz."""
        if not candidate or len(candidate) < 3:
            return None
            
        candidate_lower = candidate.lower()
        # Fast exact match
        if candidate_lower in self.canonical_names_lower:
            return self.canonical_names_lower[candidate_lower]
            
        # Fuzzy match
        match = process.extractOne(
            candidate_lower, 
            self.canonical_names_lower.keys(), 
            scorer=fuzz.WRatio
        )
        
        if match and match[1] >= threshold:
            best_match_lower = match[0]
            return self.canonical_names_lower[best_match_lower]
        return None

    def _intelligent_row_parse(self, row: List[str]) -> tuple:
        """
        Heuristically finds the test name, value, and unit in a row.
        Returns: (canonical_name, value, unit)
        """
        clean_row = [self._clean_text(cell) for cell in row if cell]
        if not clean_row:
            return None, None, None

        # Assume test name is usually the first non-empty cell
        candidate_name = clean_row[0]
        canonical_name = self._fuzzy_match_test(candidate_name)
        
        if not canonical_name:
            return None, None, None

        value = "nil"
        unit = "nil"
        
        # Heuristic: Value is the first cell after the name that contains a number
        # Unit is often the cell right after the value
        for i in range(1, len(clean_row)):
            cell = clean_row[i]
            # Simple float regex check
            if value == "nil" and re.search(r'\d+\.?\d*', cell):
                # Clean up value (remove any trailing characters that aren't numbers)
                num_match = re.search(r'([<>]?\s*\d+\.?\d*)', cell)
                if num_match:
                    value = num_match.group(1).strip()
                # If the cell itself also contains a unit (e.g. "15.5 mg/dL")
                unit_match = re.search(r'[a-zA-Z/]+', cell.replace(value, ''))
                if unit_match:
                    unit = unit_match.group().strip()
            elif value != "nil" and unit == "nil" and re.search(r'[a-zA-Z/]+', cell):
                # If we found the value in a previous cell, the next text-heavy cell might be the unit
                if len(cell) < 15: # basic safety check to avoid grabbing reference ranges
                    unit = cell.strip()
                    break

        return canonical_name, value, self._normalize_unit(unit)

    def extract_from_tables(self, tables: List[List[List[str]]]) -> Dict[str, str]:
        """Extract test results using structural table parsing."""
        results = {}
        for table in tables:
            for row in table:
                if not row: continue
                name, val, unit = self._intelligent_row_parse(row)
                if name and val and val != "nil":
                    # For now, we return just values to match the legacy pipeline shape
                    results[name] = val
        return results

    def extract_from_lines(self, text: str) -> Dict[str, str]:
        """Fallback: Extract test results by scanning raw text lines via regex."""
        results = {}
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Very greedy approach: if the line contains a test name, try to extract a number
            for canonical_name in self.test_names:
                if canonical_name.lower() in line.lower():
                    # Look for the first number sequence following the test name
                    # (Simplified logic, would need refinement for complex lines)
                    idx = line.lower().find(canonical_name.lower())
                    remainder = line[idx + len(canonical_name):]
                    num_match = re.search(r'([<>]?\s*\d+\.?\d*)', remainder)
                    if num_match:
                        results[canonical_name] = num_match.group(1).strip()
                        break # move to next line once a match is found
        return results

    def extract_tests(self, tables: List[List[List[str]]], text: str) -> Dict[str, str]:
        """Master extraction function prioritizing tables, falling back to lines."""
        results = {test: "nil" for test in self.test_names}
        
        # Strategy 1: Tables
        table_results = self.extract_from_tables(tables)
        
        # Strategy 2: Line fallback for tests that were missed
        line_results = {}
        if len(table_results) < len(self.test_names):
            line_results = self.extract_from_lines(text)
            
        # Merge: Table wins over Line
        for t in self.test_names:
            if t in table_results and table_results[t] != "nil":
                results[t] = table_results[t]
            elif t in line_results and line_results[t] != "nil":
                results[t] = line_results[t]
                
        return results
