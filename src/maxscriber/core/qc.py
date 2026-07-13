from pathlib import Path

from maxscriber.core.parsing import load_extraction_data


def run_qc(output_dir: Path, job_name: str = "default"):
    """
    Phase 2: Report content hashing and duplicate detection results.
    """
    data = load_extraction_data(output_dir, job_name=job_name)
    qc_duplicates = data.get("qc_duplicates", [])
    failed_files = data.get("failed_files", [])

    print("\n" + "=" * 50)
    print("QUALITY CONTROL REPORT")
    print("=" * 50)
    print(f"Duplicate Content Files : {len(qc_duplicates)}")
    if qc_duplicates:
        for item in qc_duplicates:
            print(f"    -> {item['duplicate']} (identical to {item['original']})")
    print(f"Failed/No Data Files    : {len(failed_files)}")
    if flagged := failed_files:
        for f in flagged:
            print(f"    -> {f}")
    print("=" * 50)
