import re
from typing import Dict


def identify_longitudinal_tests(patient_data: Dict) -> Dict:
    """
    Identify tests with MULTIPLE dates (>= 2 distinct dates).
    """
    longitudinal = {}

    for max_id, tests in patient_data.items():
        multi_date = []
        for test_name, date_values in tests.items():
            # Get valid distinct dates
            raw_dates = set([d for d in date_values.keys() if d != "nil"])

            # Simple check: Are there 2 or more distinct dates?
            if len(raw_dates) >= 2:
                multi_date.append(test_name)

        if multi_date:
            longitudinal[max_id] = multi_date

    return longitudinal


def normalize_centre_name(centre: str) -> str:
    if not centre:
        return ""
    s = centre.lower().strip()
    # Strip numeric prefix
    s = re.sub(r"^\d+\s*-\s*", "", s)
    # Remove parenthesized details
    s = re.sub(r"\(.*?\)", "", s)
    # Remove noise suffixes
    s = re.sub(r"\b(company|owned?|own|cent(?:er|re)|lab|labs)\b", "", s)
    # Strip non-alphanumeric chars
    s = re.sub(r"[^a-z0-9]", "", s)
    return s.strip()
