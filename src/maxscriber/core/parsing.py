import pickle
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def save_extraction_data(output_dir: Path, payload: dict, job_name: str = "default"):
    """Save intermediate extraction data for subcommand independence."""
    pkl_name = f"{job_name}_extraction_data.pkl"
    with open(output_dir / pkl_name, "wb") as f:  # codeql[py/clear-text-storage-sensitive-data]
        pickle.dump(payload, f)  # codeql[py/clear-text-storage-sensitive-data]  # lgtm[py/clear-text-storage-sensitive-data]


def load_extraction_data(output_dir: Path, job_name: str = "default") -> dict:
    """Load previously saved extraction data."""
    pkl_name = f"{job_name}_extraction_data.pkl"
    pkl_path = output_dir / pkl_name
    if not pkl_path.exists():
        import sys

        print(f"ERROR: No extraction data found at {pkl_path}")
        print(
            f"Run 'maxscriber transcribe --job-name {job_name}' first to generate extraction data."
        )
        sys.exit(1)
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def aggregate_data(all_extractions: List) -> dict:
    """Aggregate per-PDF extractions into per-patient data."""
    p_data = defaultdict(lambda: defaultdict(dict))
    f_map = defaultdict(set)
    m_map = {}
    # centre_map: MAX_id -> {date -> {centre, fname}} for variance detection
    centre_map: Dict[str, List[dict]] = defaultdict(list)
    # kft_unit_map: MAX_id -> test -> {date -> unit}
    kft_unit_map: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(lambda: defaultdict(dict))

    for record in all_extractions:
        # Support both old 3-tuple (backward compat) and new 4-tuple
        if len(record) == 4:
            fname, meta, tdata, kft_units = record
        else:
            fname, meta, tdata = record
            kft_units = {}

        mid = meta.get("MAX_id") or f"UNKNOWN_{fname}"
        f_map[mid].add(fname)
        if mid not in m_map or (not m_map[mid].get("Age") and meta.get("Age")):
            m_map[mid] = meta

        # Track centre per date for variance reporting
        centre = meta.get("Centre")
        for t, dv in tdata.items():
            for d, v in dv.items():
                p_data[mid][t][d] = v
                if centre:
                    centre_map[mid].append(
                        {
                            "date": d,
                            "centre": centre,
                            "fname": fname,
                        }
                    )

        # Merge KFT units
        for test_nm, date_unit in kft_units.items():
            for d, u in date_unit.items():
                kft_unit_map[mid][test_nm][d] = u

    latest_data = {}
    for mid, tests in p_data.items():
        latest_data[mid] = {}
        last_dt = None
        for t, dv in tests.items():
            valid = []
            for dstr, val in dv.items():
                try:
                    dt = datetime.strptime(dstr, "%d-%m-%Y")
                    valid.append((dt, dstr, val))
                except Exception:
                    pass
            if valid:
                valid.sort(reverse=True)
                latest_data[mid][t] = valid[0][2]
                if not last_dt or valid[0][0] > last_dt:
                    last_dt = valid[0][0]
                    latest_data[mid]["collection_date"] = valid[0][1]
            else:
                latest_data[mid][t] = "nil"

    return {
        "patient_data": dict(p_data),
        "latest_data": latest_data,
        "f_map": dict(f_map),
        "m_map": m_map,
        "centre_map": dict(centre_map),
        "kft_unit_map": dict(kft_unit_map),
    }
