"""
MaXScriber v1.0
CLI entry point with argparse subcommands.
"""

import sys
import logging
import argparse
import time
import os
import concurrent.futures
from pathlib import Path

from maxscriber.banner import print_banner, print_exit_message
from maxscriber.pipeline import (
    run_transcribe, run_qc, run_stats, run_plot,
    run_all_phase1, run_all_phase2,
)

# ANSI color from branding
RED = "\033[91m"
RESET = "\033[0m"


def _verification_gate(output_dir: Path, job_name: str) -> bool:
    """
    Conditional Verification Gate (circuit breaker).
    Called AFTER Phase 1 (Transcription) completes.
    Returns True if the pipeline should continue to Phase 2 (QC/Stats/Plot).
    Returns False if the user chose to abort.
    """
    log_path = (output_dir / f'{job_name}_extraction.log').resolve()

    while True:
        try:
            choice = input("\nHave you referred to the extraction.log file? Yes or No: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)

        if choice in ('Y', 'y', 'Yes', 'YES', 'yes'):
            return True  # proceed to Phase 2

        elif choice in ('N', 'n', 'No', 'NO', 'no'):
            print(f"\n   Extraction log: {log_path}")
            print("   Proceed after verification.\n")

            # Sub-option menu
            while True:
                try:
                    sub = input("   Press 1 to Continue  |  Press 0 to Abort: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted.")
                    sys.exit(1)

                if sub == '1':
                    return True  # continue to Phase 2

                elif sub == '0':
                    # RED warning + confirmation
                    print(f"\n{RED}WARNING: This will generate only Master_Data.xlsx and extraction.log.")
                    print(f"This will NOT proceed to QC, Stats, and Plots. Are you sure?{RESET}\n")

                    try:
                        confirm = input("   Type 'yes' to confirm abort, or 'no' to go back: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nAborted.")
                        sys.exit(1)

                    if confirm in ('Y', 'y', 'Yes', 'YES', 'yes'):
                        return False  # abort — only Master_Data + log
                    else:
                        continue  # back to sub-option menu

                else:
                    print("   Please press 1 or 0.")
        else:
            print("Please type 'Yes' or 'No'.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='maxscriber',
        description='MaXScriber v1.0 - Eau Rouge Edition | Intelligent Multi-Pass Medical PDF Extractor',
        epilog='coded with love by vaishnavpvarma  |  Inspiration: Max Verstappen / Red Bull Racing',
    )

    subparsers = parser.add_subparsers(
        dest='command',
        title='commands',
        description='Available pipeline stages. Use "maxscriber <command> -h" for command-specific help.',
    )

    # --- run ---
    run_parser = subparsers.add_parser(
        'run',
        help='Full pipeline: Transcribe -> QC -> Stats -> Plot',
        description='Execute the complete MaXScriber pipeline end-to-end.',
    )
    run_parser.add_argument('--input_dir', required=True, type=str,
                            help='Directory containing input PDF lab reports')
    run_parser.add_argument('--output_dir', required=True, type=str,
                            help='Directory to write output files (Excel, stats, plots)')
    run_parser.add_argument('--verbose', '-v', action='store_true',
                            help='Enable verbose logging and disable progress animation')
    # New flags
    run_parser.add_argument('--auto_continue', action='store_true',
                            help='Bypass the interactive verification gate and continue to Phase 2')
    run_parser.add_argument('--threads', '-t', type=int, default=os.cpu_count(),
                            help='Number of parallel threads for PDF extraction (default: CPU count)')

    # --- multirun ---
    multirun_parser = subparsers.add_parser(
        'multirun',
        help='Run multiple independent jobs concurrently',
        description='Execute several MaxScriber jobs in parallel. Each job requires a name, input directory, and output directory.',
    )
    multirun_parser.add_argument('--job', nargs=3, action='append', metavar=('NAME','INPUT','OUTPUT'), required=True,
                                 help='Specify a job: <NAME> <INPUT_DIR> <OUTPUT_DIR>. Can be repeated.')
    multirun_parser.add_argument('--threads', '-t', type=int, default=os.cpu_count(),
                                 help='Number of concurrent jobs to run (default: CPU count)')
    multirun_parser.add_argument('--auto_continue', action='store_true',
                                 help='Pass --auto_continue to each job')
    multirun_parser.add_argument('--verbose', '-v', action='store_true',
                                 help='Enable verbose logging for each job')
    # --- transcribe ---
    transcribe_parser = subparsers.add_parser(
        'transcribe',
        help='Extract text from PDFs and map to canonical test names',
        description='Run PDF text extraction, test name mapping, and QC hashing. '
                    'Saves intermediate data for downstream commands.',
    )
    transcribe_parser.add_argument('--input_dir', required=True, type=str,
                                   help='Directory containing input PDF lab reports')
    transcribe_parser.add_argument('--output_dir', required=True, type=str,
                                   help='Directory to write extraction results')
    transcribe_parser.add_argument('--verbose', '-v', action='store_true',
                                   help='Enable verbose logging and disable progress animation')

    # --- qc ---
    qc_parser = subparsers.add_parser(
        'qc',
        help='Report content hashing and duplicate detection results',
        description='Display QC results: duplicate content files and failed extractions. '
                    'Requires a prior "transcribe" run.',
    )
    qc_parser.add_argument('--output_dir', required=True, type=str,
                           help='Directory containing prior extraction data')

    # --- stats ---
    stats_parser = subparsers.add_parser(
        'stats',
        help='Generate the Stats_Refined.txt statistical report',
        description='Produce a comprehensive statistical summary including demographics, '
                    'diagnostic insights, and clinical condition prevalence. '
                    'Requires a prior "transcribe" run.',
    )
    stats_parser.add_argument('--output_dir', required=True, type=str,
                              help='Directory containing prior extraction data')

    # --- plot ---
    plot_parser = subparsers.add_parser(
        'plot',
        help='Generate clinical distribution graphs',
        description='Create age distribution, haemoglobin, and platelet count histograms. '
                    'Requires a prior "transcribe" run.',
    )
    plot_parser.add_argument('--output_dir', required=True, type=str,
                             help='Directory containing prior extraction data')

    # --- No args: show banner + help ---
    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        print_exit_message()
        sys.exit(0)

    args = parser.parse_args()

    # Always show banner
    print_banner()

    if args.command in ['run', 'multirun', 'transcribe', 'qc', 'stats', 'plot']:
        if args.command != 'multirun':
            while True:
                try:
                    job_name = input("\nEnter a project/job name (e.g. TestRun2025): ").strip()
                    if job_name:
                        break
                    print("Job name cannot be empty.")
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted.")
                    sys.exit(1)
        
        try:
            if args.command == 'run':
                out = Path(args.output_dir)
                inp = Path(args.input_dir)
                pdf_count = len(list(inp.glob('*.pdf')))
                verbose = args.verbose
                threads = args.threads
                auto_continue = args.auto_continue

                start_time = time.time()

                # Phase 1: Transcribe + generate Master_Data.xlsx
                run_all_phase1(inp, out, job_name, verbose=verbose, threads=threads)

                # Verification gate (skip if auto_continue)
                if auto_continue:
                    should_continue = True
                else:
                    should_continue = _verification_gate(out, job_name)

                if should_continue:
                    # Phase 2: QC + Stats + Plot
                    run_all_phase2(out, job_name)
                else:
                    # Graceful abort — log reason, flush, and close handlers
                    logger = logging.getLogger('MaxScriber')
                    logger.info("Pipeline aborted by user at verification gate.")
                    logger.info(f"extraction.log preserved at {out / f'{job_name}_extraction.log'}")
                    for handler in logger.handlers[:]:
                        handler.flush()
                        handler.close()
                        logger.removeHandler(handler)
                    # Also clean root logger handlers
                    for handler in logging.getLogger().handlers[:]:
                        handler.flush()
                        handler.close()
                        logging.getLogger().removeHandler(handler)
                    print(f"\n{job_name}_Master_Data.xlsx and {job_name}_extraction.log saved to {out}")

                elapsed_time = time.time() - start_time
                minutes, seconds = divmod(int(elapsed_time), 60)
                manual_time_minutes = pdf_count * 5
                print(f"\nTotal time taken to transcribe: {minutes} Minutes and {seconds} Seconds.")
                print(f"Doing this manually would have taken you approximately {manual_time_minutes} minutes. You're welcome! 😉")

            elif args.command == 'multirun':
                # args.job is a list of [NAME, INPUT, OUTPUT]
                max_jobs = args.threads
                auto_continue = args.auto_continue
                verbose = args.verbose
                job_list = args.job

                def _run_job(job_tuple):
                    name, inp_dir, out_dir = job_tuple
                    try:
                        out_path = Path(out_dir)
                        inp_path = Path(inp_dir)
                        # Phase 1: Set threads=1 per job since jobs are running concurrently
                        run_all_phase1(inp_path, out_path, name, verbose=verbose, threads=1)
                        # Verification
                        if auto_continue:
                            continue_flag = True
                        else:
                            continue_flag = _verification_gate(out_path, name)
                        
                        if continue_flag:
                            run_all_phase2(out_path, name)
                        return (name, None)
                    except Exception as e:
                        err_path = out_path / f"{name}_errors.txt"
                        with open(err_path, 'w') as ef:
                            ef.write(str(e))
                        return (name, err_path)

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_jobs) as executor:
                    future_to_job = {executor.submit(_run_job, jt): jt for jt in job_list}
                    for future in concurrent.futures.as_completed(future_to_job):
                        name, err = future.result()
                        if err:
                            print(f"Job {name} failed. See errors in {err}")
                        else:
                            print(f"Job {name} completed successfully.")

            elif args.command == 'transcribe':
                run_transcribe(Path(args.input_dir), Path(args.output_dir), job_name, args.verbose)

            elif args.command == 'qc':
                run_qc(Path(args.output_dir), job_name)

            elif args.command == 'stats':
                run_stats(Path(args.output_dir), job_name)

            elif args.command == 'plot':
                run_plot(Path(args.output_dir), job_name)

            else:
                parser.print_help()

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
        except Exception as e:
            print(f"\nERROR: {e}")
            sys.exit(1)

    # Always conclude with exit message
    print_exit_message()


if __name__ == '__main__':
    main()

