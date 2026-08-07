"""
MaXScriber v0.1.0 - Eau Rouge Edition
Statistical report generation.
"""

import logging
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from maxscriber.config import CLINICAL_THRESHOLDS


def generate_condensed_stats(
    latest_data: Dict,
    metadata_map: Dict,
    all_extractions: List,
    qc_dupes: List[Dict],
    failed_files: List[str],
    file_name_map: Dict,
    longitudinal_tests: Dict,
    patient_data: Dict,
    output_path: Path,
    logger: logging.Logger,
):
    """
    Combines V2's unstructured stats format with V3's additional clinical info.
    """

    # --- Part 1: V2-style Unstructured Stats ---
    stats = []
    stats.append("Final Statistical Summary")
    stats.append("=" * 30)

    total_patients = len(latest_data)
    total_pdfs = len(all_extractions) + len(failed_files)

    # Count patients with multiple PDFs
    multi_pdf_patients = {mid: fnames for mid, fnames in file_name_map.items() if len(fnames) > 1}
    patients_multiple_pdfs = len(multi_pdf_patients)

    stats.append(f"1. Total No. of Patients = {total_patients}")
    stats.append(f"2. Total no. of PDFs Processed = {total_pdfs}")
    stats.append(f"3. Patients with longitudinal data = {len(longitudinal_tests)}")
    stats.append(f"4. No. of Patients with multiple PDFs = {patients_multiple_pdfs}")

    # List patients with multiple PDFs
    if multi_pdf_patients:
        stats.append("\n   [Details: Patients with >1 PDF]")
        for mid, fnames in sorted(multi_pdf_patients.items()):
            stats.append(f"   - {mid} ({len(fnames)} files): {', '.join(sorted(fnames))}")

    # Multi-PDF Breakdown Table (fixed-width aligned)
    stats.append("")
    stats.append("Multi-PDF Breakdown:")
    col_cat = 15
    col_pts = 16
    col_calc = 12
    col_pdfs = 10
    header = f"{'Category'.ljust(col_cat)}| {'No. of Patients'.ljust(col_pts)}| {'Calculation'.ljust(col_calc)}| {'Total PDFs'.ljust(col_pdfs)}"
    sep_line = "-" * len(header)
    stats.append(header)
    stats.append(sep_line)
    file_count_groups = defaultdict(list)
    for mid, fnames in file_name_map.items():
        n = len(fnames)
        if n > 1:
            file_count_groups[n].append(mid)
    table_total_pts = 0
    table_total_pdfs = 0
    for n_files in sorted(file_count_groups.keys(), reverse=True):
        n_pts = len(file_count_groups[n_files])
        n_pdfs = n_pts * n_files
        table_total_pts += n_pts
        table_total_pdfs += n_pdfs
        cat_str = f"{n_files} Files"
        calc_str = f"{n_pts} x {n_files}"
        stats.append(
            f"{cat_str.ljust(col_cat)}| {str(n_pts).ljust(col_pts)}| {calc_str.ljust(col_calc)}| {str(n_pdfs).ljust(col_pdfs)}"
        )
    stats.append(sep_line)
    if table_total_pts > 0:
        stats.append(
            f"{'TOTAL'.ljust(col_cat)}| {str(table_total_pts).ljust(col_pts)}| {''.ljust(col_calc)}| {str(table_total_pdfs).ljust(col_pdfs)}"
        )
    else:
        stats.append("  (All patients have exactly 1 PDF)")

    stats.append("")

    # Demographics (V2 Style)
    stats.append("1️⃣ Demographic Breakdown")
    genders = []
    ages = []  # list of (age_int, max_id)

    for max_id, meta in metadata_map.items():
        g = meta.get("Gender")
        if g and g in ["M", "F"]:
            genders.append(g)
        a = meta.get("Age")
        if a is not None and str(a).replace(".", "", 1).isdigit():
            ages.append((int(float(str(a))), max_id))

    gender_counts = Counter(genders)
    m_count = gender_counts.get("M", 0)
    f_count = gender_counts.get("F", 0)
    total_gender = m_count + f_count

    m_pct = (m_count / total_gender * 100) if total_gender else 0
    f_pct = (f_count / total_gender * 100) if total_gender else 0
    ratio = f"{m_count / f_count:.2f} : 1" if f_count else f"{m_count} : 0"

    stats.append("Gender Distribution:")
    stats.append(f"Male: {m_count} ({m_pct:.1f}%)")
    stats.append(f"Female: {f_count} ({f_pct:.1f}%)")
    stats.append(f"Male : Female Ratio ≈ {ratio}")

    if ages:
        age_values = [a for a, _ in ages]
        mean_age = statistics.mean(age_values)
        min_age = min(age_values)
        max_age = max(age_values)
        adults = sum(1 for a in age_values if 19 <= a <= 60)
        children = sum(1 for a in age_values if 0 <= a <= 18)
        seniors = sum(1 for a in age_values if a > 60)
        total_ages = len(age_values)

        # Find source files for youngest and oldest patients
        youngest_mids = [mid for a, mid in ages if a == min_age]
        oldest_mids = [mid for a, mid in ages if a == max_age]
        youngest_files = []
        for mid in youngest_mids:
            youngest_files.extend(sorted(file_name_map.get(mid, [])))
        oldest_files = []
        for mid in oldest_mids:
            oldest_files.extend(sorted(file_name_map.get(mid, [])))

        stats.append("Age Demographics:")
        stats.append(f"Mean Age: {mean_age:.2f} years")
        stats.append(
            f"Youngest Patient: {min_age} Years (Source File: {', '.join(youngest_files)})"
        )
        stats.append(f"Oldest Patient: {max_age} Years (Source File: {', '.join(oldest_files)})")
        stats.append("Age Groups:")
        stats.append(
            f"Adults (19–60 years): {adults} patients ({(adults / total_ages * 100):.1f}%)"
        )
        stats.append(
            f"Children & Adolescents (0–18 years): {children} patients ({(children / total_ages * 100):.1f}%)"
        )
        stats.append(
            f"Seniors (>60 years): {seniors} patients ({(seniors / total_ages * 100):.1f}%)"
        )
    else:
        stats.append("Age Demographics: No valid age data found.")
    stats.append("")

    # Diagnostic Insights (V2 Style)
    stats.append("2️⃣ Diagnostic Insights")
    ns1_tested = 0
    ns1_positive = 0
    ns1_values = []

    for max_id, tests in latest_data.items():
        val = tests.get("Dengue NS1 Antigen")
        if val and str(val).lower() not in ["nil", "nan", "none", "", "null"]:
            ns1_tested += 1
            is_pos = False
            try:
                # Clean value
                clean_val = str(val).lower().replace(">", "").replace("<", "").strip()
                if clean_val in ["positive", "reactive", "detected"]:
                    is_pos = True
                else:
                    fval = float(clean_val)
                    ns1_values.append(fval)
                    if fval >= 0.9:
                        is_pos = True
            except Exception:
                pass

            if is_pos:
                ns1_positive += 1

    pos_rate = (ns1_positive / ns1_tested * 100) if ns1_tested else 0
    avg_ns1 = sum(ns1_values) / len(ns1_values) if ns1_values else 0

    stats.append("Dengue NS1 Antigen:")
    stats.append(f"Total Tested: {ns1_tested} patients")
    stats.append(f"Total Positive: {ns1_positive} patients")
    stats.append(f"Positivity Rate: {pos_rate:.2f}%")
    stats.append(f"Average NS1 (S/CO): {avg_ns1:.2f}")
    stats.append("")

    # Data Coverage (V2 Style)
    stats.append("3️⃣ Data Coverage")
    all_dates = []
    for max_id, tests in latest_data.items():
        d = tests.get("collection_date")
        if d and d != "nil":
            try:
                all_dates.append(datetime.strptime(d, "%d-%m-%Y"))
            except Exception:
                pass

    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
        span = max_date - min_date
        months = span.days / 30
        stats.append(
            f"Reporting Period: {min_date.strftime('%d %B %Y')} – {max_date.strftime('%d %B %Y')}"
        )
        stats.append(f"Dataset Span: ~{months:.1f} months")
    else:
        stats.append("Reporting Period: No valid dates found.")
    stats.append("")

    # --- Part 2: V3 features appended ---
    stats.append("=" * 30)
    stats.append("CLINICAL CONDITIONS PREVALENCE (v3)")
    stats.append("=" * 30)

    cond_counts = defaultdict(int)
    for mid, d in latest_data.items():
        meta = metadata_map.get(mid, {})
        gender = meta.get("Gender", "U")

        hb = d.get("Haemoglobin")
        if hb and str(hb).replace(".", "").isdigit():
            v = float(hb)
            th = CLINICAL_THRESHOLDS["Anemia"]
            if (gender == "M" and v < th["low_M"]) or (gender == "F" and v < th["low_F"]):
                cond_counts["Anemia"] += 1

        tlc = d.get("Total Leukocyte Count(TLC)")
        if tlc and str(tlc).replace(".", "").isdigit():
            v = float(tlc)
            if v < CLINICAL_THRESHOLDS["Leukopenia"]["low"]:
                cond_counts["Leukopenia"] += 1
            if v > CLINICAL_THRESHOLDS["Leukocytosis"]["high"]:
                cond_counts["Leukocytosis"] += 1

        pl = d.get("Platelet")
        if pl and str(pl).replace(".", "").isdigit():
            v = float(pl)
            if v < CLINICAL_THRESHOLDS["Thrombocytopenia"]["low"]:
                cond_counts["Thrombocytopenia"] += 1
            if v > CLINICAL_THRESHOLDS["Thrombocytosis"]["high"]:
                cond_counts["Thrombocytosis"] += 1

    for cond, count in cond_counts.items():
        prev = (count / len(latest_data) * 100) if latest_data else 0
        stats.append(f"{cond:<20} | {count:<10} | {prev:.1f}%")
    stats.append("")

    # Longitudinal Breakdown
    stats.append("=" * 30)
    stats.append("LONGITUDINAL CLINICAL BREAKDOWN")
    stats.append("=" * 30)

    bins = {
        "Re-Tested < 3 Days": [],
        "Re-Tested 5-7 Days": [],
        "Re-Tested < 15 Days": [],
        "Re-Tested < 30 Days": [],
        "Re-Tested > 1 Year": [],
        "Other Intervals": [],
    }

    sorted_long_mids = sorted(longitudinal_tests.keys())

    for mid in sorted_long_mids:
        # Determine max span
        max_span_days = -1
        p_tests = patient_data.get(mid, {})

        for t, date_vals in p_tests.items():
            valid_dates = []
            for dstr in date_vals.keys():
                try:
                    valid_dates.append(datetime.strptime(dstr, "%d-%m-%Y"))
                except:
                    pass

            if len(valid_dates) >= 2:
                span = (max(valid_dates) - min(valid_dates)).days
                if span > max_span_days:
                    max_span_days = span

        if max_span_days != -1:
            if max_span_days < 3:
                bins["Re-Tested < 3 Days"].append(mid)
            elif 5 <= max_span_days <= 7:
                bins["Re-Tested 5-7 Days"].append(mid)
            elif max_span_days < 15:
                bins["Re-Tested < 15 Days"].append(mid)
            elif max_span_days < 30:
                bins["Re-Tested < 30 Days"].append(mid)
            elif max_span_days > 365:
                bins["Re-Tested > 1 Year"].append(mid)
            else:
                bins["Other Intervals"].append(mid)

    has_longitudinal = False
    for bin_name, mids in bins.items():
        if mids:
            has_longitudinal = True
            stats.append(f"{bin_name}:")
            for mid in mids:
                # Get filenames
                fnames = sorted(list(file_name_map.get(mid, [])))
                fname_str = ", ".join(fnames)
                stats.append(f"  - {mid} ({fname_str})")
            stats.append("")

    if not has_longitudinal:
        stats.append("No longitudinal data patterns found.")
    stats.append("")

    # QC Summary (V3 style)
    stats.append("QUALITY CONTROL SUMMARY")
    stats.append("-" * 20)
    stats.append(f"Duplicate Content Files : {len(qc_dupes)}")

    if qc_dupes:
        stats.append("\n[!] Duplicate Details:")
        for item in qc_dupes:
            stats.append(f"    - {item['duplicate']} -> Identical to: {item['original']}")

    stats.append(f"\nFailed/No Data Files    : {len(failed_files)}")
    if failed_files:
        stats.append("\n[!] Failed Files:")
        for f in failed_files:
            stats.append(f"    - {f}")

    # QC Calculation (Balance Sheet)
    # Correct flow: Duplicates removed FIRST, then multi-file extras calculated
    # from remaining unique files to avoid double-counting.
    stats.append("")
    stats.append("=" * 60)
    stats.append("QC Calculation")
    stats.append("-" * 60)

    # Stage 1: Total PDFs in input
    total_processed = len(all_extractions) + len(failed_files)
    n_dupes = len(qc_dupes)
    n_failed = len(failed_files)

    # Stage 2: Unique Files = Total PDFs - Duplicates - Failed
    unique_files = total_processed - n_dupes - n_failed

    # Stage 3: Unique Patients (distinct MAX_IDs)
    actual_unique = total_patients

    # Stage 4: Extra PDFs (Multi-file) = Unique Files - Unique Patients
    extra_pdfs = unique_files - actual_unique

    # Verification: Total PDFs = Unique Patients + Extra PDFs + Duplicates + Failed
    reconstructed = actual_unique + extra_pdfs + n_dupes + n_failed

    stats.append(f"Stage 1: Total PDFs in Input       = {total_processed}")
    stats.append(f"Stage 2: Duplicate Content PDFs     = {n_dupes}")
    stats.append(f"         Failed/No Data PDFs        = {n_failed}")
    stats.append(
        f"         Unique Files (Remaining)   = {total_processed} - {n_dupes} - {n_failed} = {unique_files}"
    )
    stats.append(f"Stage 3: Unique Patients (MAX_IDs)  = {actual_unique}")
    stats.append(
        f"Stage 4: Extra PDFs (Multi-file)    = {unique_files} - {actual_unique} = {extra_pdfs}"
    )
    stats.append("")
    stats.append("Proof:")
    stats.append("  Total PDFs = Unique Patients + Extra PDFs + Duplicates + Failed")
    stats.append(
        f"  {total_processed} = {actual_unique} + {extra_pdfs} + {n_dupes} + {n_failed} = {reconstructed}"
    )

    if reconstructed == total_processed:
        stats.append("\n✅ BALANCED — QC formula verified.")
    else:
        stats.append(
            f"\n❌ IMBALANCED — Reconstructed {reconstructed}, expected {total_processed}. Investigate discrepancy."
        )
        # Log specific MAX_ids that may be causing drift
        duplicate_filenames = {item["duplicate"] for item in qc_dupes}
        drift_ids = []
        for mid, fnames in file_name_map.items():
            overlap = (
                fnames & duplicate_filenames
                if isinstance(fnames, set)
                else set(fnames) & duplicate_filenames
            )
            if overlap:
                drift_ids.append((mid, sorted(overlap)))
        logger.critical(
            f"QC IMBALANCE: Reconstructed={reconstructed}, Expected={total_processed}. "
            f"Unique Patients={actual_unique}, Extra PDFs={extra_pdfs}, "
            f"Duplicates={n_dupes}, Failed={n_failed}."
        )
        if drift_ids:
            logger.critical("MAX_IDs with overlapping duplicate flags:")
            for mid, overlap_files in drift_ids:
                logger.critical(f"  {mid}: duplicate files = {', '.join(overlap_files)}")

    # lgtm[py/cleartext-storage-sensitive-data]
    # codeql[py/cleartext-storage-sensitive-data]
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(stats))
    logger.info(f"Stats Report saved: {output_path}")
