"""
MaXScriber v1.0
PDF content extraction, helpers, and multi-pass strategies.
"""

import hashlib
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import pdfplumber
from fuzzywuzzy import fuzz, process

from maxscriber.config import (
    ALIAS_TO_CANONICAL,
    CBC_TESTS,
    KFT_DEFAULT_UNITS,
    KFT_NOISE_PREFIXES,
    KFT_TESTS,
    LFT_TESTS,
    REFERENCE_RANGES,
    UNIT_NORMALISATION,
)

# =============================================================================
# PDF CONTENT STRUCTURE (With QC Hashing)
# =============================================================================


class PDFContent:
    """Rich PDF content structure."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.full_text = ""
        self.content_hash = ""  # QC Check
        self.pages_text = []
        self.tables = []
        self.lines = []


def extract_pdf_content(file_path: str, logger: logging.Logger) -> Optional[PDFContent]:
    """Extract comprehensive content from PDF."""
    try:
        content = PDFContent(file_path)
        all_text = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    content.pages_text.append((page_num, text))
                    all_text.append(text)
                    for line in text.split("\n"):
                        line = line.strip()
                        if line:
                            content.lines.append((page_num, line))
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        if table:
                            cleaned = [
                                [str(c).strip() if c else "" for c in row]
                                for row in table
                                if row and any(row)
                            ]
                            if cleaned:
                                content.tables.append((page_num, cleaned))

        content.full_text = "\n".join(all_text)

        # Calculate Hash for QC
        content.content_hash = hashlib.md5(content.full_text.encode("utf-8")).hexdigest()

        # Verbose logging from V2
        logger.info(
            f"Extracted: {len(content.pages_text)} pages, "
            f"{len(content.tables)} tables, {len(content.lines)} lines"
        )
        return content
    except Exception as e:
        logger.error(f"Extraction failed for {file_path}: {e}")
        return None


# =============================================================================
# EXTRACTION HELPERS (Same as v2 logic)
# =============================================================================


def fuzzy_match_test_name(raw_name: str, threshold: int = 80) -> Optional[str]:
    if not raw_name:
        return None
    clean_name = raw_name.lower().strip()
    clean_name = re.sub(
        r"\b(calculated|estimated|electrical impedance|vcs|light microscopy)\b",
        "",
        clean_name,
        flags=re.IGNORECASE,
    )
    clean_name = re.sub(r"\s+", " ", clean_name).strip()
    if clean_name in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[clean_name]
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        if alias in clean_name or clean_name in alias:
            return canonical
    match = process.extractOne(
        clean_name, list(ALIAS_TO_CANONICAL.keys()), scorer=fuzz.token_sort_ratio
    )
    if match and match[1] >= threshold:
        return ALIAS_TO_CANONICAL[match[0]]
    return None


def normalize_date(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    formats = [
        "%d/%b/%Y",
        "%d/%B/%Y",
        "%d/%b/%y",
        "%d/%B/%y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d-%b-%y",
        "%d-%B-%y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return None


def extract_all_dates(text: str) -> List[str]:
    dates = []
    patterns = [
        (
            r"\b(\d{1,2})/([A-Za-z]{3})/(\d{4})\b",
            lambda m: f"{m.group(1)}/{m.group(2)}/{m.group(3)}",
        ),
        (
            r"\b(\d{1,2})/([A-Za-z]{3})/(\d{2})\b",
            lambda m: f"{m.group(1)}/{m.group(2)}/20{m.group(3)}",
        ),
        (
            r"\b(\d{1,2})-([A-Za-z]{3})-(\d{4})\b",
            lambda m: f"{m.group(1)}/{m.group(2)}/{m.group(3)}",
        ),
        (r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", lambda m: f"{m.group(1)}/{m.group(2)}/{m.group(3)}"),
        (r"\b(\d{1,2})-(\d{1,2})-(\d{4})\b", lambda m: f"{m.group(1)}/{m.group(2)}/{m.group(3)}"),
    ]
    for pattern, formatter in patterns:
        for match in re.finditer(pattern, text):
            try:
                dates.append(formatter(match))
            except Exception:
                continue
    return dates


def extract_dates_from_content(content: PDFContent, logger: logging.Logger) -> List[str]:
    raw = extract_all_dates(content.full_text)
    norm = []
    seen = set()
    for d in raw:
        n = normalize_date(d)
        if n and n not in seen:
            norm.append(n)
            seen.add(n)

    # Verbose logging from V2
    logger.info(f"Found {len(norm)} unique dates: {norm}")
    return norm


def is_value_plausible(test_name: str, value: str) -> bool:
    if str(value).lower() in [
        "positive",
        "negative",
        "detected",
        "not detected",
        "reactive",
        "non-reactive",
    ]:
        return True
    try:
        n = float(value)
        if test_name in REFERENCE_RANGES:
            return REFERENCE_RANGES[test_name][0] <= n <= REFERENCE_RANGES[test_name][1]
        return n >= 0
    except Exception:
        return False


def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    """Normalise unit strings to canonical form (e.g. mg/dl -> mg/dL)."""
    if not raw_unit:
        return None
    cleaned = raw_unit.strip()
    return UNIT_NORMALISATION.get(cleaned, cleaned) or cleaned


def _is_noise_line(text: str) -> bool:
    """Return True if a line is part of a Ref-Range / Comment / Note block."""
    t = text.lower().strip()
    return any(t.startswith(pfx) for pfx in KFT_NOISE_PREFIXES)


def find_closest_date(pos: int, text: str, dates: List[str]) -> Optional[str]:
    if not dates:
        return None
    start, end = max(0, pos - 500), min(len(text), pos + 500)
    ctx_dates = extract_all_dates(text[start:end])
    if ctx_dates:
        n = normalize_date(ctx_dates[0])
        if n:
            return n
    return dates[0]


# =============================================================================
# STRATEGIES
# =============================================================================


def func_table_smart(content, dates, logger):
    res = defaultdict(dict)

    for p, table in content.tables:
        date_cols = {}

        for row in table:
            if not row:
                continue

            # Reset date_cols if new header
            row_has_keywords = False
            for idx, cell in enumerate(row):
                if not cell:
                    continue
                s = str(cell).strip()
                if any(k in s for k in ["Date", "Result", "Unit", "Bio Ref"]):
                    row_has_keywords = True
                    break

            if row_has_keywords:
                date_cols = {}

            is_header = False
            for idx, cell in enumerate(row):
                if not cell:
                    continue
                s = str(cell).strip()
                if any(k in s for k in ["Date", "Result", "Unit"]):
                    is_header = True
                ds = extract_all_dates(s)
                for d in ds:
                    nd = normalize_date(d)
                    if nd:
                        if len(s) < 50:
                            date_cols[idx] = nd
                            is_header = True
                            break

            if is_header:
                if not date_cols and dates:
                    for idx in range(1, min(len(row), len(dates) + 1)):
                        if idx - 1 < len(dates):
                            date_cols[idx] = dates[idx - 1]
                continue

            if not row[0]:
                continue

            nm = fuzzy_match_test_name(str(row[0]).split("\n")[0])
            if not nm:
                continue

            for idx, d_col in date_cols.items():
                if idx < len(row) and row[idx]:
                    val = re.sub(r"[^0-9.\-]", "", str(row[idx]).strip())
                    if nm in ["Dengue NS1 Antigen", "Dengue IgG", "Dengue IgM"]:
                        if val and val not in [".", "-"]:
                            if d_col not in res[nm]:
                                res[nm][d_col] = val
                                logger.debug(f"  Extracted: {nm}[{d_col}] = {val}")
                            continue
                    if val and val not in [".", "-"] and is_value_plausible(nm, val):
                        if d_col not in res[nm]:
                            res[nm][d_col] = val
                            logger.debug(f"  Extracted: {nm}[{d_col}] = {val}")

    return dict(res)


def func_line_pattern(content, dates, logger):
    res = defaultdict(dict)
    pat = r"^(.+?)\s*[:]\s*(.+)$"
    for p, line in content.lines:
        m = re.match(pat, line)
        if not m:
            continue
        nm = fuzzy_match_test_name(m.group(1))
        val = m.group(2).strip()
        if nm:
            cl = None
            if nm in ["Dengue NS1 Antigen", "Dengue IgG", "Dengue IgM"]:
                vm = re.search(r"(\d+\.?\d*)", val)
                if vm:
                    cl = vm.group(1)
            else:
                cl = re.sub(r"[^0-9.\-]", "", val)

            if cl and dates and is_value_plausible(nm, cl):
                if dates[0] not in res[nm]:
                    res[nm][dates[0]] = cl
                    logger.debug(f"Line match: {nm}[{dates[0]}] = {cl}")
    return dict(res)


def func_dengue_dedicated(content, dates, logger):
    res = defaultdict(dict)
    pat_val = (
        r"(\d+\.?\d*|Positive|Negative|Reactive|Non-?Reactive|Equivocal|Detected|Not\s+Detected)"
    )
    pats = {
        "Dengue NS1 Antigen": r"Dengue\s+NS\s*1\s+Antigen\s+(?:[:\-]\s*)?" + pat_val,
        "Dengue IgG": r"Dengue\s+IgG\s+(?:[:\-]\s*)?" + pat_val,
        "Dengue IgM": r"Dengue\s+IgM\s+(?:[:\-]\s*)?" + pat_val,
    }
    for nm, p in pats.items():
        for m in re.finditer(p, content.full_text, re.IGNORECASE):
            val = m.group(1)
            date = find_closest_date(m.start(), content.full_text, dates)
            if date and val:
                # Validation logic
                is_valid = False
                if re.match(r"^[a-zA-Z\s\-]+$", val):
                    is_valid = True
                else:
                    try:
                        fv = float(val)
                        if 1900 < fv < 2100 and fv.is_integer():
                            ctx = content.full_text[m.end() : m.end() + 20].lower()
                            if any(x in ctx for x in ["index", "s/co", "ratio"]):
                                is_valid = True
                        else:
                            is_valid = True
                    except Exception:
                        pass
                if is_valid and date not in res[nm]:
                    res[nm][date] = val
                    logger.info(f"{nm} extract: [{date}] = {val}")
    return dict(res)


def extract_metadata(content, logger, pattern="2024_2025"):
    txt = content.full_text
    meta = {
        "MAX_id": None,
        "SIN_No": None,
        "Age": None,
        "Gender": None,
        "Centre": None,
        "Location_ID": "-",
        "Location": "-",
    }

    # MAX ID
    mps = [
        r"(?:MaxID|Max\s+ID|Lab\s+ID)\s*[:/]\s*([A-Z]{3,5}\.\d+)",
        r"\b([A-Z]{4}\.\d{6})\b",
        r"(?:MaxID|Max\s+ID|Lab\s+ID)\s*[:/]\s*([A-Z]{2}\d+)",
    ]
    for p in mps:
        m = re.search(p, txt, re.IGNORECASE)
        if m:
            meta["MAX_id"] = m.group(1).upper()
            logger.info(f"Found MAX_id: {meta['MAX_id']}")
            break
    if not meta["MAX_id"]:
        flm = re.search(r"([A-Z]{2,5}\.?\d{6,})", content.file_name, re.IGNORECASE)
        if flm:
            meta["MAX_id"] = flm.group(1).upper()
            logger.info(f"Found MAX_id in filename: {meta['MAX_id']}")

    # SIN
    sps = [r"SIN\s+No\s*[:/]\s*([A-Z0-9]+)", r"SIN\s*[:/]\s*([A-Z0-9]+)"]
    for p in sps:
        m = re.search(p, txt, re.IGNORECASE)
        if m:
            meta["SIN_No"] = m.group(1).upper()
            logger.info(f"Found SIN_No: {meta['SIN_No']}")
            break

    if pattern == "2023":
        # 2023 Pattern: Distinctly capture Location ID and Location Name
        cp_2023 = r"Centre\s*[:/]\s*(?:(\d+)\s*-\s*)?(.+?)(?:OP/IP|Collection|Ref\s*Doctor|\n|$)"
        cm = re.search(cp_2023, txt, re.IGNORECASE)
        if cm:
            loc_id = cm.group(1)
            loc_name = cm.group(2)

            if loc_name:
                loc_name = loc_name.strip()
                loc_name = re.split(r"\s{2,}|\t", loc_name)[0].strip()
                if len(loc_name) > 2:
                    meta["Location"] = loc_name
                    meta["Location_ID"] = loc_id.strip() if loc_id else "-"
                    meta["Centre"] = meta["Location"]  # Fallback
                    logger.info(
                        f"Found Location ID: {meta['Location_ID']}, Location: {meta['Location']}"
                    )
    else:
        # 2024_2025 (Legacy) Pattern: Capture only Centre name
        centre_patterns = [
            r"Centre\s*[:/]\s*(?:\d+\s*-\s*)?(.+?)(?:OP/IP|Collection|Ref\s*Doctor|$)",
            r"Centre\s*[:/]\s*(.+?)\n",
        ]
        for cp in centre_patterns:
            cm = re.search(cp, txt, re.IGNORECASE)
            if cm:
                centre_raw = cm.group(1).strip()
                # Remove trailing noise tokens
                centre_raw = re.split(r"\s{2,}|\t", centre_raw)[0].strip()
                if centre_raw and len(centre_raw) > 2:
                    meta["Centre"] = centre_raw
                    logger.info(f"Found Centre: {meta['Centre']}")
                    break

    # Age/Gender
    agps = [
        r"Age\s*/\s*Gender\s*[:/]\s*(\d+)\s*Y.*?/\s*([MF])",
        r"Age\s*[:/]\s*(\d+).*?Gender\s*[:/]\s*([MF])",
        r"(\d{1,3})\s*Y.*?([MF])",
    ]
    for p in agps:
        m = re.search(p, txt, re.IGNORECASE)
        if m:
            meta["Age"] = m.group(1)
            meta["Gender"] = m.group(2).upper()
            logger.info(f"Found Age: {meta['Age']}, Gender: {meta['Gender']}")
            break
    return meta


# =============================================================================
# KFT DEDICATED EXTRACTION STRATEGY
# =============================================================================


def func_kft_table(content, dates, logger):
    """
    Dedicated multi-pass table extractor for KFT parameters.

    Strategy:
      1. Scan every table for rows whose first cell matches a KFT alias.
      2. Skip rows that are noise (Ref. Range / Comment / Note blocks).
      3. Detect the Unit column dynamically (header row containing 'Unit').
      4. If a unit is found, normalise it; otherwise apply KFT_DEFAULT_UNITS.
      5. Store result as (value, unit) keyed by canonical name and date.
    """
    res = defaultdict(dict)  # canonical_name -> {date: (value, unit)}
    unit_store = defaultdict(dict)  # canonical_name -> {date: unit}  — for the pipeline

    for _page, table in content.tables:
        unit_col = -1
        date_cols = {}
        fallback_date = dates[0] if dates else None

        for row in table:
            if not row:
                continue

            # Check if this row is a header
            row_has_keywords = False
            for idx, cell in enumerate(row):
                if not cell:
                    continue
                s = str(cell).strip()
                if any(k in s for k in ["Date", "Result", "Unit", "Bio Ref"]):
                    row_has_keywords = True
                    break

            if row_has_keywords:
                date_cols = {}
                unit_col = -1

            is_header = False
            for idx, cell in enumerate(row):
                if not cell:
                    continue
                s = str(cell).strip()
                if any(k in s for k in ["Date", "Result", "Unit"]):
                    is_header = True
                    if "Unit" in s:
                        unit_col = idx
                ds = extract_all_dates(s)
                for d in ds:
                    nd = normalize_date(d)
                    if nd:
                        # Prevent long demographics blocks from being treated as date columns
                        if len(s) < 50:
                            date_cols[idx] = nd
                            is_header = True
                            break

            if is_header:
                if not date_cols and dates:
                    for idx in range(1, min(len(row), len(dates) + 1)):
                        if idx - 1 < len(dates):
                            date_cols[idx] = dates[idx - 1]
                continue

            if not row[0]:
                continue

            cell0 = str(row[0]).replace("\n", " ").strip()

            # Noise filter — skip reference / comment blocks
            if _is_noise_line(cell0):
                continue

            # Match canonical test name
            nm = fuzzy_match_test_name(cell0.split("\n")[0])
            if not nm or nm not in KFT_TESTS:
                continue

            # --- Determine unit ---
            raw_unit = None
            if unit_col != -1 and unit_col < len(row):
                raw_unit = str(row[unit_col]).strip() if row[unit_col] else None
            unit = normalize_unit(raw_unit) or KFT_DEFAULT_UNITS.get(nm)

            # --- Extract value per date column ---
            if date_cols:
                for col_idx, col_date in date_cols.items():
                    if col_idx < len(row) and row[col_idx]:
                        val = re.sub(r"[^0-9.\-]", "", str(row[col_idx]).strip())
                        if val and val not in [".", "-"] and is_value_plausible(nm, val):
                            if col_date not in res[nm]:
                                res[nm][col_date] = val
                                unit_store[nm][col_date] = unit
                                logger.debug(f"KFT: {nm}[{col_date}] = {val} {unit}")
            elif fallback_date:
                # Single-date table — use value at index 1
                val_raw = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                val = re.sub(r"[^0-9.\-]", "", val_raw)
                if val and val not in [".", "-"] and is_value_plausible(nm, val):
                    if fallback_date not in res[nm]:
                        res[nm][fallback_date] = val
                        unit_store[nm][fallback_date] = unit
                        logger.debug(f"KFT: {nm}[{fallback_date}] = {val} {unit}")

    # Attach unit_store onto the result dict so the pipeline can retrieve units
    # We encode as a special sentinel key to keep interface compatible.
    result = dict(res)
    result["__kft_units__"] = dict(unit_store)
    return result


def determine_tests_done(row_data: Dict) -> str:
    has_lft = any(
        row_data.get(t) and str(row_data.get(t)).lower() not in ["nil", "nan", "none", "", "null"]
        for t in LFT_TESTS
    )
    has_cbc = any(
        row_data.get(t) and str(row_data.get(t)).lower() not in ["nil", "nan", "none", "", "null"]
        for t in CBC_TESTS
    )
    has_kft = any(
        row_data.get(t) and str(row_data.get(t)).lower() not in ["nil", "nan", "none", "", "null"]
        for t in KFT_TESTS
    )

    dn = row_data.get("Dengue NS1 Antigen")
    dg = row_data.get("Dengue IgG")
    dm = row_data.get("Dengue IgM")

    hn = dn and str(dn).lower() not in ["nil", "nan", "none", "", "null"]
    hg = dg and str(dg).lower() not in ["nil", "nan", "none", "", "null"]
    hm = dm and str(dm).lower() not in ["nil", "nan", "none", "", "null"]
    has_any = hn or hg or hm

    parts = []
    if has_cbc:
        parts.append("CBC")
    if has_lft:
        parts.append("LFT")
    if has_kft:
        parts.append("KFT")
    if has_any:
        if hn and hg and hm:
            dl = "Dengue NS1, IgG & IgM"
        else:
            dp = []
            if hn:
                dp.append("NS1")
            if hg:
                dp.append("IgG")
            if hm:
                dp.append("IgM")
            if len(dp) == 1:
                dl = f"Dengue {dp[0]}"
            elif len(dp) == 2:
                dl = f"Dengue {dp[0]} & {dp[1]}"
            else:
                dl = f"Dengue {', '.join(dp[:-1])} & {dp[-1]}"
        parts.append(dl)

    if not parts:
        return "No Data"
    if len(parts) == 1:
        return f"{parts[0]} only" if "Dengue" in parts[0] else f"{parts[0]} Only"
    last = parts.pop()
    return (
        f"{', '.join(parts)} & {last} Tests"
        if "Dengue" in last
        else f"{', '.join(parts)} & {last} only"
    )


# =============================================================================
# ADAPTIVE SCHEMA-BASED EXTRACTOR
# =============================================================================

from rapidfuzz import fuzz, process


class AdaptiveExtractor:
    """Advanced Schema-driven PDF data extractor with fuzzy matching and heuristics."""

    def __init__(self, schema: dict):
        self.schema = schema
        self.test_names = schema.get("tests", [])
        self.metadata_patterns = schema.get("metadata", {})
        # Pre-process canonical names for fuzzy matching
        self.canonical_names_lower = {t.lower(): t for t in self.test_names}

    def _clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return text.strip().replace("\n", " ")

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
            candidate_lower, self.canonical_names_lower.keys(), scorer=fuzz.WRatio
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
            if value == "nil" and re.search(r"\d+\.?\d*", cell):
                # Clean up value (remove any trailing characters that aren't numbers)
                num_match = re.search(r"([<>]?\s*\d+\.?\d*)", cell)
                if num_match:
                    value = num_match.group(1).strip()
                # If the cell itself also contains a unit (e.g. "15.5 mg/dL")
                unit_match = re.search(r"[a-zA-Z/]+", cell.replace(value, ""))
                if unit_match:
                    unit = unit_match.group().strip()
            elif value != "nil" and unit == "nil" and re.search(r"[a-zA-Z/]+", cell):
                # If we found the value in a previous cell, the next text-heavy cell might be the unit
                if len(cell) < 15:  # basic safety check to avoid grabbing reference ranges
                    unit = cell.strip()
                    break

        return canonical_name, value, self._normalize_unit(unit)

    def extract_from_tables(self, tables: List[List[List[str]]]) -> Dict[str, str]:
        """Extract test results using structural table parsing."""
        results = {}
        for table in tables:
            for row in table:
                if not row:
                    continue
                name, val, unit = self._intelligent_row_parse(row)
                if name and val and val != "nil":
                    # For now, we return just values to match the legacy pipeline shape
                    results[name] = val
        return results

    def extract_from_lines(self, text: str) -> Dict[str, str]:
        """Fallback: Extract test results by scanning raw text lines via regex."""
        results = {}
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Very greedy approach: if the line contains a test name, try to extract a number
            for canonical_name in self.test_names:
                if canonical_name.lower() in line.lower():
                    # Look for the first number sequence following the test name
                    # (Simplified logic, would need refinement for complex lines)
                    idx = line.lower().find(canonical_name.lower())
                    remainder = line[idx + len(canonical_name) :]
                    num_match = re.search(r"([<>]?\s*\d+\.?\d*)", remainder)
                    if num_match:
                        results[canonical_name] = num_match.group(1).strip()
                        break  # move to next line once a match is found
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
