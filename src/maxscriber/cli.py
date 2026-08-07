"""
MaXScriber v0.1.0
CLI entry point using Click and Textual.
"""

import logging
import sys
import time
from pathlib import Path

import click

from maxscriber import __version__
from maxscriber.core import (
    run_all_phase1,
    run_all_phase2,
)
from maxscriber.utils.banner import print_banner, print_exit_message

RED = "\033[91m"
RESET = "\033[0m"


def _verification_gate(output_dir: Path) -> bool:
    """Conditional Verification Gate."""
    log_path = (output_dir / "extraction.log").resolve()
    while True:
        try:
            choice = input("\nHave you referred to the extraction.log file? Yes or No: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)

        if choice.lower() in ("y", "yes"):
            return True
        elif choice.lower() in ("n", "no"):
            print(f"\n   Extraction log: {log_path}")
            print("   Proceed after verification.\n")
            while True:
                try:
                    sub = input("   Press 1 to Continue  |  Press 0 to Abort: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted.")
                    sys.exit(1)
                if sub == "1":
                    return True
                elif sub == "0":
                    print(
                        f"\n{RED}WARNING: This will generate only Master_Data.xlsx and extraction.log."
                    )
                    print(f"This will NOT proceed to QC, Stats, and Plots. Are you sure?{RESET}\n")
                    try:
                        confirm = input(
                            "   Type 'yes' to confirm abort, or 'no' to go back: "
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nAborted.")
                        sys.exit(1)
                    if confirm.lower() in ("y", "yes"):
                        return False
                    else:
                        continue
                else:
                    print("   Please press 1 or 0.")
        else:
            print("Please type 'Yes' or 'No'.")


from maxscriber.tui.app import run_tui


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="MaxScriber")
@click.pass_context
def main(ctx):
    """MaXScriber v0.1.0 | Universal Medical PDF Extractor"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if ctx.invoked_subcommand is None:
        from rich.console import Console
        from rich.table import Table

        print_banner()
        console = Console()
        console.print(f"Welcome to [bold]MaxScriber[/] [bold #00ffff]v{__version__}[/]!")
        console.print("[bold #ffffff]Creator:[/] [bold #d49040]@vaishnavpvarma[/]")
        console.print("Please choose an operating mode:\n")

        table = Table.grid(padding=(0, 0))
        table.add_column(style="bold #00ffff")
        table.add_column(style="bold #c0d0d0")
        table.add_row("  1. Visual Mode (TUI) ", ": maxscriber tui")
        table.add_row("  2. CLI Mode          ", ": maxscriber run [OPTIONS]")

        console.print(table)
        console.print()
        console.print("[bold #c0d0d0]Run 'maxscriber --help' for all available commands.[/]\n")
        console.print("[bold #d49040]SIMPLY LOVELY 😉- Max Verstappen[/]")


@main.command("tui")
def tui_mode():
    """Launch the interactive Visual Dashboard (TUI)"""
    run_tui()


@main.command()
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Directory containing input PDF lab reports",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False),
    help="Directory to write output files",
)
@click.option(
    "--schema", type=str, default="MaxHospitals_Dengue", help="Schema to use for extraction"
)
@click.option(
    "--pattern",
    type=click.Choice(["2024_2025", "2023"]),
    default="2024_2025",
    help="Pattern logic for extraction (legacy)",
)
@click.option(
    "--threads", "-t", type=int, default=None, help="Number of concurrent worker processes"
)
@click.option("--verbose", "-v", is_flag=True, help="Run sequentially and stream logs to stdout")
@click.option(
    "--job-name", type=str, default=None, help="Namespace prefix for all generated outputs"
)
def run(input_dir, output_dir, schema, pattern, threads, verbose, job_name):
    """Full pipeline: Transcribe -> QC -> Stats -> Plot"""
    print_banner()
    if not job_name:
        try:
            job_name = input(
                "Enter a <job_name> for this run (or press Enter for 'default'): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)
        if not job_name:
            job_name = "default"

    out = Path(output_dir)
    inp = Path(input_dir)
    pdf_count = len([f for f in inp.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])

    start_time = time.time()

    # Stub for Phase 1
    selected_cats = ["CBC", "LFT", "KFT", "DENGUE"]  # Defaulted for now, will be driven by schema

    run_all_phase1(
        inp,
        out,
        pattern=pattern,
        threads=threads,
        verbose=verbose,
        job_name=job_name,
        selected_categories=selected_cats,
    )

    should_continue = _verification_gate(out)
    if should_continue:
        run_all_phase2(out, job_name=job_name)
    else:
        logger = logging.getLogger(job_name)
        logger.info("Pipeline aborted by user at verification gate.")
        print(f"\nMaster_Data.xlsx and extraction.log saved to {out}")

    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    print(f"\nTotal time taken to transcribe: {minutes} Minutes and {seconds} Seconds.")
    print_exit_message()


@main.group()
def schema():
    """Manage MaxScriber schemas"""
    pass


@schema.command(name="list")
def list_schemas():
    """List all registered schemas"""
    from rich.console import Console
    from rich.table import Table
    from maxscriber.core.schema import SchemaManager
    console = Console()
    sm = SchemaManager()
    schemas = sm.get_all_schemas()

    if not schemas:
        click.echo("No schemas found.")
        return

    table = Table(title="Available MaxScriber Schemas", border_style="cyan")
    table.add_column("Name", style="bold white")
    table.add_column("Tests Count", style="yellow")
    table.add_column("Description", style="dim white")

    for s in schemas:
        table.add_row(s.get("name", "Unknown"), str(s.get("tests_count", 0)), s.get("description", ""))

    console.print(table)


@schema.command(name="import")
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
def import_schema(filepath):
    """Import a YAML schema file into MaxScriber"""
    from maxscriber.core.schema import SchemaManager
    sm = SchemaManager()
    try:
        name = sm.import_schema_file(Path(filepath))
        console.print(f"[bold green]✓ Successfully imported schema '{name}'![/bold green]")
        console.print(f"You can now run extraction with: [cyan]maxscriber run --schema {name} ...[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Failed to import schema: {e}[/bold red]")


@schema.command(name="open")
def open_schema_folder():
    """Open the schema folder in system file explorer"""
    from maxscriber.core.schema import SchemaManager
    import subprocess
    import platform

    sm = SchemaManager()
    folder = sm.base_dir
    folder.mkdir(parents=True, exist_ok=True)

    console.print(f"Opening schema directory: [cyan]{folder}[/cyan]")
    system_name = platform.system().lower()
    try:
        if "windows" in system_name or os.name == "nt":
            os.startfile(str(folder))
        elif "darwin" in system_name:
            subprocess.run(["open", str(folder)])
        else:
            # Linux / WSL
            subprocess.run(["xdg-open", str(folder)])
    except Exception as e:
        console.print(f"[yellow]Could not automatically open GUI folder ({e}). Directory path is: {folder}[/yellow]")


if __name__ == "__main__":
    main()
