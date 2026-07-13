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

from maxscriber.constants import (
    ALIAS_TO_CANONICAL,
    CBC_TESTS,
    LFT_TESTS,
    REFERENCE_RANGES,
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
        if len(table) < 2:
            continue
        header = table[0]
        date_cols = {}
        for idx, cell in enumerate(header):
            if cell:
                ds = extract_all_dates(cell)
                for d in ds:
                    nd = normalize_date(d)
                    if nd:
                        date_cols[idx] = nd
                        break
        if not date_cols and dates:
            for idx in range(1, min(len(header), len(dates) + 1)):
                if idx - 1 < len(dates):
                    date_cols[idx] = dates[idx - 1]

        for r in table[1:]:
            if not r or not r[0]:
                continue
            nm = fuzzy_match_test_name(r[0].split("\n")[0])
            if not nm:
                continue
            for idx, d in date_cols.items():
                if idx < len(r) and r[idx]:
                    val = re.sub(r"[^0-9.\-]", "", r[idx].strip())
                    if nm in ["Dengue NS1 Antigen", "Dengue IgG", "Dengue IgM"]:
                        if val and val not in [".", "-"]:
                            if d not in res[nm]:
                                res[nm][d] = val
                                logger.debug(f"  Extracted: {nm}[{d}] = {val}")
                            continue
                    if val and val not in [".", "-"] and is_value_plausible(nm, val):
                        if d not in res[nm]:
                            res[nm][d] = val
                            logger.debug(f"  Extracted: {nm}[{d}] = {val}")
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


def extract_metadata(content, logger):
    txt = content.full_text
    meta = {"MAX_id": None, "SIN_No": None, "Age": None, "Gender": None}

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

    # Age/Gender
    agps = [
        r"Age\s*/\s*Gender\s*[:/]\s*(\d+)\s*Y(?:.*?(\d+)\s*M)?.*?/\s*([MF])",
        r"Age\s*[:/]\s*(\d+)(?:\s*Y.*?(\d+)\s*M)?.*?Gender\s*[:/]\s*([MF])",
        r"(\d{1,3})\s*Y(?:.*?(\d+)\s*M)?.*?([MF])",
        # Handle cases where only months are listed (e.g. "9 Months / M")
        r"Age\s*/\s*Gender\s*[:/]\s*(?:0\s*Y\s*)?(\d+)\s*Months?.*?/\s*([MF])",
        r"Age\s*[:/]\s*(?:0\s*Y\s*)?(\d+)\s*Months?.*?Gender\s*[:/]\s*([MF])",
        r"(?:0\s*Y\s*)?(\d{1,3})\s*Months?.*?([MF])",
    ]
    for p in agps:
        m = re.search(p, txt, re.IGNORECASE)
        if m:
            if len(m.groups()) == 3:
                years = int(m.group(1))
                months = int(m.group(2)) if m.group(2) else 0
                gender = m.group(3).upper()
            else:
                years = 0
                months = int(m.group(1))
                gender = m.group(2).upper()

            if years == 0 and months > 0:
                meta["Age"] = f"{months} Months"
            else:
                meta["Age"] = str(years)

            meta["Gender"] = gender
            logger.info(f"Found Age: {meta['Age']}, Gender: {meta['Gender']}")
            break
    return meta


def determine_tests_done(row_data: Dict) -> str:
    has_lft = any(
        row_data.get(t) and str(row_data.get(t)).lower() not in ["nil", "nan", "none", "", "null"]
        for t in LFT_TESTS
    )
    has_cbc = any(
        row_data.get(t) and str(row_data.get(t)).lower() not in ["nil", "nan", "none", "", "null"]
        for t in CBC_TESTS
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
