import concurrent.futures
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple

from alive_progress import alive_bar

from maxscriber.core.extraction import (
    AdaptiveExtractor,
    extract_pdf_content,
)
from maxscriber.core.parsing import (
    aggregate_data,
    load_extraction_data,
    save_extraction_data,
)
from maxscriber.core.qc import run_qc
from maxscriber.core.schema import SchemaManager
from maxscriber.core.tracking import identify_longitudinal_tests
from maxscriber.io.excel_writer import (
    generate_excel_report,
    generate_help_parameters,
    generate_lab_variance_report,
    generate_longitudinal_excel,
    save_to_sqlite,
)
from maxscriber.io.stats_writer import generate_condensed_stats
from maxscriber.plotting.distributions import generate_clinical_plots
from maxscriber.plotting.stratification import (
    apply_legacy_dengue_stratification,
    export_stratified_data,
    generate_r_script,
    load_stratification_config,
)


def setup_logging(
    output_dir: Path,
    append: bool = False,
    verbose: bool = True,
    log_filename: str = "extraction.log",
    job_name: str = "default",
) -> logging.Logger:
    """Setup comprehensive logging."""
    if log_filename == "extraction.log":
        log_file = output_dir / f"{job_name}_{log_filename}"
    else:
        log_file = output_dir / log_filename

    root = logging.getLogger(job_name)
    for h in root.handlers[:]:
        root.removeHandler(h)

    file_mode = "a" if append else "w"
    handlers = [logging.FileHandler(log_file, mode=file_mode, encoding="utf-8")]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    logger = logging.getLogger(job_name)

    if append:
        if log_filename == "extraction.log":
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"Resuming pipeline — Phase 2 (QC / Stats / Plot) for {job_name}")
            logger.info("=" * 80)
    else:
        logger.info("=" * 80)
        logger.info(f"Intelligent Multi-Pass Medical PDF Extractor [Job: {job_name}]")
        logger.info("No AI/ML - Pure Rule-Based with Cross-Validation")
        logger.info("=" * 80)
    return logger


def _process_pdf_worker(
    pdf: Path,
    output_dir: Path,
    job_name: str,
    verbose: bool,
    pattern: str = "2024_2025",
    selected_categories: list = None,
    schema_name: str = "MaxHospitals_Dengue",
) -> Tuple:
    """Process a single PDF file using the AdaptiveExtractor."""
    logger = setup_logging(
        output_dir, append=True, verbose=verbose, log_filename="extraction.log", job_name=job_name
    )
    try:
        import pdfplumber

        sm = SchemaManager()
        schema = sm.get_schema(schema_name)
        if not schema:
            logger.error(f"Schema {schema_name} not found.")
            return pdf.name, None, {}, {}, {}, 0.0

        extractor = AdaptiveExtractor(schema)

        text_content = ""
        tables = []
        with pdfplumber.open(pdf) as p:
            for page in p.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

        meta = extractor.extract_metadata(text_content)
        final_test_data = extractor.extract_tests(tables, text_content)

        content = extract_pdf_content(str(pdf), logger)
        content_hash = content.content_hash if content else None

        collection_date = meta.get("Collection Date", "nil")
        if collection_date == "nil":
            collection_date = datetime.now().strftime("%d-%m-%Y")

        test_data_by_date = {
            t: {collection_date: v} for t, v in final_test_data.items() if v != "nil"
        }
        kft_units = {}

        total_tests = len(final_test_data)
        populated = sum(1 for v in final_test_data.values() if v != "nil")
        confidence = (populated / total_tests * 100) if total_tests > 0 else 0.0

        return pdf.name, content_hash, meta, dict(test_data_by_date), kft_units, confidence
    except Exception as e:
        logger.error(f"Error processing {pdf.name}: {e}", exc_info=True)
        return pdf.name, None, {}, {}, {}, 0.0


def run_transcribe(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "2024_2025",
    threads: int = None,
    verbose: bool = False,
    job_name: str = "default",
    selected_categories: list = None,
    progress_callback=None,
):
    """Phase 1: PDF text extraction, test mapping, and QC hashing."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    output_dir.mkdir(parents=True, exist_ok=True)
    generate_help_parameters(output_dir)
    logger = setup_logging(
        output_dir, append=False, verbose=verbose, log_filename="extraction.log", job_name=job_name
    )
    logger.info(f"Input: {input_dir}")
    logger.info(f"Output: {output_dir}")

    pdf_files = sorted(
        [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"],
        key=lambda x: x.name,
    )
    if not pdf_files:
        logger.error("No PDFs found.")
        print("No PDFs found in input directory.")
        return

    all_extractions = []
    failed_files = []
    seen_hashes = {}
    qc_duplicates = []

    logger.info(f"Found {len(pdf_files)} PDFs. Starting extraction...")
    if not verbose:
        print(
            f"Starting extraction for {len(pdf_files)} files (Parallel mode, worker processes)..."
        )
    else:
        print(f"Starting extraction for {len(pdf_files)} files (Sequential verbose mode)...")

    start_time = time.time()

    if not verbose:
        num_workers = threads if threads is not None else os.cpu_count()
        logger.info(f"Running in parallel mode with {num_workers} processes.")

        with alive_bar(len(pdf_files), title="Transcribing PDFs", force_tty=True) as bar:
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {
                    executor.submit(
                        _process_pdf_worker,
                        pdf,
                        output_dir,
                        "extraction.log",
                        False,
                        pattern,
                        selected_categories,
                    ): pdf
                    for pdf in pdf_files
                }

                for future in concurrent.futures.as_completed(futures):
                    pdf = futures[future]
                    try:
                        pdf_name, content_hash, meta, final_test_data, kft_units, confidence = (
                            future.result()
                        )
                        if progress_callback:
                            progress_callback(pdf_name, confidence)

                        if content_hash is None:
                            failed_files.append(pdf_name)
                            logger.warning(f"No data extracted from {pdf_name}")
                        else:
                            if content_hash in seen_hashes:
                                orig = seen_hashes[content_hash]
                                logger.warning(
                                    f"DUPLICATE DETECTED: {pdf_name} is identical to {orig}"
                                )
                                qc_duplicates.append({"duplicate": pdf_name, "original": orig})
                            else:
                                seen_hashes[content_hash] = pdf_name

                            if final_test_data:
                                all_extractions.append((pdf_name, meta, final_test_data, kft_units))
                            else:
                                failed_files.append(pdf_name)
                                logger.warning(f"No data extracted from {pdf_name}")
                    except Exception as exc:
                        logger.error(
                            f"Process generated an exception for {pdf.name}: {exc}", exc_info=True
                        )
                        failed_files.append(pdf.name)

                    bar()
    else:
        logger.info("Running in sequential verbose mode.")
        for idx, pdf in enumerate(pdf_files, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"PDF {idx}/{len(pdf_files)}: {pdf.name}")
            logger.info(f"{'=' * 80}")

            pdf_name, content_hash, meta, final_test_data, kft_units, confidence = (
                _process_pdf_worker(
                    pdf, output_dir, "extraction.log", True, pattern, selected_categories
                )
            )
            if progress_callback:
                progress_callback(pdf_name, confidence)

            if content_hash is None:
                failed_files.append(pdf_name)
            else:
                if content_hash in seen_hashes:
                    orig = seen_hashes[content_hash]
                    logger.warning(f"DUPLICATE DETECTED: {pdf_name} is identical to {orig}")
                    qc_duplicates.append({"duplicate": pdf_name, "original": orig})
                else:
                    seen_hashes[content_hash] = pdf_name

                if final_test_data:
                    all_extractions.append((pdf_name, meta, final_test_data, kft_units))
                else:
                    failed_files.append(pdf_name)

    aggregated = aggregate_data(all_extractions)

    patient_data = aggregated["patient_data"]
    longitudinal_tests = identify_longitudinal_tests(patient_data)

    payload = {
        "all_extractions": all_extractions,
        "failed_files": failed_files,
        "qc_duplicates": qc_duplicates,
        "longitudinal_tests": longitudinal_tests,
        **aggregated,
    }
    save_extraction_data(output_dir, payload, job_name=job_name)
    save_to_sqlite(output_dir, payload, job_name=job_name)

    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)

    manual_time_minutes = len(pdf_files) * 5

    print(f"\nTotal time taken to transcribe: {minutes} Minutes and {seconds} Seconds.")
    print(
        f"Doing this manually would have taken you approximately {manual_time_minutes} minutes. You're welcome! ;)"
    )

    print(
        f"\nExtraction complete. {len(all_extractions)} files processed, {len(failed_files)} failed."
    )
    print("Check extraction.log for details.")
    logger.info("Extraction phase complete.")


def run_stats(output_dir: Path, job_name: str = "default"):
    """Generate the Stats_Refined.txt statistical report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(
        output_dir, append=True, log_filename="extraction.log", job_name=job_name
    )
    data = load_extraction_data(output_dir, job_name=job_name)

    generate_condensed_stats(
        latest_data=data["latest_data"],
        metadata_map=data["m_map"],
        all_extractions=data["all_extractions"],
        qc_dupes=data["qc_duplicates"],
        failed_files=data["failed_files"],
        file_name_map=data["f_map"],
        longitudinal_tests=data.get("longitudinal_tests", {}),
        patient_data=data.get("patient_data", {}),
        output_path=output_dir / f"{job_name}_Stats_Refined.txt",
        logger=logger,
    )
    print(f"Stats report saved to {output_dir / f'{job_name}_Stats_Refined.txt'}")


def run_plot(output_dir: Path, job_name: str = "default"):
    """Generate clinical distribution graphs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(
        output_dir, append=True, log_filename="extraction.log", job_name=job_name
    )
    data = load_extraction_data(output_dir, job_name=job_name)

    generate_clinical_plots(
        latest_data=data["latest_data"],
        metadata_map=data["m_map"],
        output_dir=output_dir,
        job_name=job_name,
        logger=logger,
    )
    print(f"Clinical plots saved to {output_dir / f'{job_name}_graphs'}")


def run_stratification(output_dir: Path, job_name: str = "default"):
    """Run clinical stratification and generate R analysis."""
    data = load_extraction_data(output_dir, job_name=job_name)
    logger = setup_logging(
        output_dir, append=True, log_filename="extraction.log", job_name=job_name
    )

    config_path = Path.cwd() / "custom_stratification.yaml"
    config = load_stratification_config(config_path, logger)

    if config:
        logger.info(
            "Custom stratification from YAML is not fully implemented for dynamic parsing yet. Falling back to Legacy."
        )
        stratified = apply_legacy_dengue_stratification(data["latest_data"], data["m_map"])
    else:
        stratified = apply_legacy_dengue_stratification(data["latest_data"], data["m_map"])

    xlsx_path = export_stratified_data(
        stratified, data["latest_data"], data["m_map"], output_dir, job_name, logger
    )
    generate_r_script(xlsx_path, output_dir, job_name, logger)

    print(f"Stratification data saved to {xlsx_path.name}")
    print(f"R script generated at {job_name}_analysis.R")


def run_all_phase1(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "2024_2025",
    threads: int = None,
    verbose: bool = False,
    job_name: str = "default",
    selected_categories: list = None,
):
    """Executes the entire Phase 1 pipeline."""
    run_transcribe(
        input_dir,
        output_dir,
        pattern=pattern,
        threads=threads,
        verbose=verbose,
        job_name=job_name,
        selected_categories=selected_categories,
    )

    data = load_extraction_data(output_dir, job_name=job_name)
    logger = setup_logging(
        output_dir, append=True, log_filename="extraction.log", job_name=job_name
    )

    generate_excel_report(data, output_dir, logger, pattern=pattern, job_name=job_name)

    longitudinal_tests = data.get("longitudinal_tests", {})
    if longitudinal_tests:
        generate_longitudinal_excel(
            data["patient_data"],
            longitudinal_tests,
            output_dir / f"{job_name}_longitudinal_data.xlsx",
            logger,
        )

    generate_lab_variance_report(
        centre_map=data.get("centre_map", {}),
        patient_data=data.get("patient_data", {}),
        f_map=data.get("f_map", {}),
        kft_unit_map=data.get("kft_unit_map", {}),
        output_path=output_dir / f"{job_name}_lab_variance_report.txt",
        logger=logger,
    )

    logger.info("Phase 1 complete: Transcription and Excel reports generated.")


def run_all_phase2(output_dir: Path, job_name: str = "default"):
    """Phase 2 of the full pipeline: QC + Stats + Plot."""
    data = load_extraction_data(output_dir, job_name=job_name)
    logger = setup_logging(
        output_dir, append=True, log_filename="extraction.log", job_name=job_name
    )

    run_qc(output_dir, job_name=job_name)

    generate_condensed_stats(
        latest_data=data["latest_data"],
        metadata_map=data["m_map"],
        all_extractions=data["all_extractions"],
        qc_dupes=data["qc_duplicates"],
        failed_files=data["failed_files"],
        file_name_map=data["f_map"],
        longitudinal_tests=data.get("longitudinal_tests", {}),
        patient_data=data.get("patient_data", {}),
        output_path=output_dir / f"{job_name}_Stats_Refined.txt",
        logger=logger,
    )

    generate_clinical_plots(
        latest_data=data["latest_data"],
        metadata_map=data["m_map"],
        output_dir=output_dir,
        job_name=job_name,
        logger=logger,
    )

    run_stratification(output_dir, job_name=job_name)

    logger.info("DONE.")
    print(f"\nAll reports saved to {output_dir}")
