import os
import sqlite3
import random
import time
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Footer, DataTable, Label, Button
from textual.binding import Binding
from rich.text import Text

from maxscriber.tui.widgets import Banner, StatsPanel, ActionMenu
from maxscriber.tui.modals import (
    WorkspaceLoaderModal, RecordInspectorModal, ExecutePipelineModal, 
    SchemaWizardModal, ConfigModal
)
from maxscriber.schema_manager import SchemaManager

class MainScreen(Screen):
    """The main Sci-Fi dashboard."""
    
    BINDINGS = [
        ("f1", "quit", "Exit Console"),
        ("f2", "new_schema", "New Template"),
        ("f3", "palette", "Load Workspace"),
        ("ctrl+question_mark", "help", "Help")
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_workspace = None
        self.worker_threads = 4

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-row"):
            with Container(id="banner-panel", classes="panel") as banner_pane:
                banner_pane.border_title = " EHR PARSER ENGINE "
                yield Banner()
            with Container(id="stats-panel", classes="panel") as stats_pane:
                stats_pane.border_title = " PIPELINE ANALYTICS "
                self.stats = StatsPanel()
                yield self.stats
                
        with Horizontal(id="bottom-row"):
            with Container(id="menu-panel", classes="panel") as menu_pane:
                menu_pane.border_title = " WORKSPACE MENU "
                yield ActionMenu()
            with Container(id="schema-panel", classes="panel") as schema_pane:
                self.schema_pane = schema_pane
                schema_pane.border_title = " SCHEMA REGISTRY "
                yield DataTable(id="schema-table", cursor_type="row")
                yield Label("✦", id="sparkle-icon")
        
        yield Footer()

    def on_mount(self) -> None:
        self.app.title = "MaxScriber v2.0 | Sci-Fi Terminal Workspace"
        self._load_schema_registry()

    def _load_schema_registry(self):
        self.current_workspace = None
        self.schema_pane.border_title = " SCHEMA REGISTRY "
        
        table = self.query_one("#schema-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            Text("TAG", style="bold #40a0b0"),
            Text("NAME", style="bold #40a0b0"),
            Text("VERSION", style="bold #40a0b0"),
            Text("STATUS", style="bold #40a0b0"),
            Text("LAST UPDATED", style="bold #40a0b0"),
        )
        
        sm = SchemaManager()
        schemas = sm.get_all_schemas()
        
        for s in schemas:
            is_legacy = s.get("is_legacy", False)
            tag = "SYS_01" if is_legacy else "USR_01"
            status_txt = Text("✅ [Active]", style="bold #33ff33") if is_legacy else Text("⚠️ [Review]", style="bold #ffcc00")
            
            table.add_row(
                Text(tag, style="#c0d0d0"),
                Text(s.get("name"), style="#c0d0d0"),
                Text("1.0.0", style="#c0d0d0"),
                status_txt,
                Text(s.get("date_added", ""), style="#c0d0d0"),
                key=s.get("name")
            )

    def _load_job_workspace(self, path: Path):
        self.current_workspace = path
        self.schema_pane.border_title = f" PATIENT RECORDS : {path.name} "
        
        table = self.query_one("#schema-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            Text("🏥 MAX_ID", style="bold #40a0b0"),
            Text("👤 AGE/SEX", style="bold #40a0b0"),
            Text("📍 LOCATION", style="bold #40a0b0"),
            Text("📄 ASSAYS", style="bold #40a0b0"),
        )
        
        db_path = None
        for file in path.glob("*_extractions.db"):
            db_path = file
            break
            
        if not db_path:
            self.app.notify("No extractions DB found in this workspace.", severity="error")
            self._load_schema_registry()
            return

        # Fetch longitudinal keys
        longitudinal_ids = set()
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if longitudinal_data table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='longitudinal_data'")
            if cursor.fetchone():
                cursor.execute("SELECT DISTINCT max_id FROM longitudinal_data")
                longitudinal_ids = {r['max_id'] for r in cursor.fetchall()}
                
            cursor.execute("SELECT * FROM patient_demographics")
            patients = cursor.fetchall()
            
            for p in patients:
                pid = p['max_id']
                cursor.execute("SELECT COUNT(*) as c FROM patient_tests WHERE max_id = ?", (pid,))
                c = cursor.fetchone()['c']
                
                # Highlight if longitudinal
                id_txt = Text(f"🧬 [LONG] {pid}", style="bold #b142f5") if pid in longitudinal_ids else Text(pid, style="bold #e2e8f0")
                
                table.add_row(
                    id_txt,
                    Text(f"{p['age']}/{p['gender']}", style="#c0d0d0"),
                    Text(str(p['location']), style="#c0d0d0"),
                    Text(f"{c} assays", style="#c0d0d0"),
                    key=f"patient_{pid}"
                )
            conn.close()
            self.app.notify(f"Loaded {len(patients)} records from {path.name}")
        except Exception as e:
            self.app.notify(f"Database error: {e}", severity="error")

    # =========================================================================
    # EVENT BINDINGS
    # =========================================================================
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_nav_schemas":
            self._load_schema_registry()
        elif event.button.id == "btn_nav_settings":
            def apply_config(cfg):
                if cfg:
                    self.worker_threads = cfg['threads']
                    self.app.notify(f"Threads updated to {self.worker_threads}")
            self.app.push_screen(ConfigModal(), apply_config)
        elif event.button.id == "btn_new_schema":
            self.action_new_schema()
        elif event.button.id == "btn_run":
            def start_pipeline(paths):
                if paths:
                    self.run_pipeline_worker(Path(paths['in']), Path(paths['out']))
            self.app.push_screen(ExecutePipelineModal(), start_pipeline)

    def action_new_schema(self) -> None:
        def on_schema_saved(saved: bool):
            if saved:
                self.app.notify("Schema saved successfully.")
                self._load_schema_registry()
        self.app.push_screen(SchemaWizardModal(), on_schema_saved)

    def action_palette(self) -> None:
        def check_workspace(path_str):
            if path_str:
                path = Path(path_str)
                if path.exists():
                    self._load_job_workspace(path)
        self.app.push_screen(WorkspaceLoaderModal(), check_workspace)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Inspect the raw data."""
        row_key = event.row_key.value
        
        if self.current_workspace is None:
            # Schema registry inspection
            sm = SchemaManager()
            schema_data = sm.get_schema(row_key)
            if schema_data:
                self.app.push_screen(RecordInspectorModal(row_key, schema_data))
        else:
            # Patient record inspection
            pid = row_key.replace("patient_", "")
            db_path = next(self.current_workspace.glob("*_extractions.db"), None)
            if db_path:
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM patient_tests WHERE max_id = ?", (pid,))
                    tests = [dict(r) for r in cursor.fetchall()]
                    conn.close()
                    self.app.push_screen(RecordInspectorModal(pid, {"tests": tests}))
                except Exception:
                    pass

    # =========================================================================
    # WORKERS
    # =========================================================================

    @work(exclusive=True, thread=True)
    def run_pipeline_worker(self, in_dir: Path, out_dir: Path):
        """Runs extraction pipeline and posts real-time telemetry."""
        from maxscriber.core import run_transcribe
        
        pdf_files = list(in_dir.glob("*.pdf"))
        total = len(pdf_files)
        
        self.app.call_from_thread(self.app.notify, f"Starting extraction on {total} files...")
        
        start_time = time.time()
        processed_count = [0]
        
        def progress_cb(pdf_name, confidence):
            processed_count[0] += 1
            elapsed = time.time() - start_time
            throughput = processed_count[0] / elapsed if elapsed > 0 else 0.0
            
            self.app.call_from_thread(
                setattr, self.stats, 'current_throughput', throughput
            )
            self.app.call_from_thread(
                setattr, self.stats, 'current_confidence', confidence
            )
        
        # Run actual pipeline
        try:
            run_transcribe(in_dir, out_dir, threads=self.worker_threads, progress_callback=progress_cb)
            self.app.call_from_thread(self.app.notify, "Extraction complete!")
            self.app.call_from_thread(self._load_job_workspace, out_dir)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")
        finally:
            self.app.call_from_thread(setattr, self.stats, 'current_throughput', 0.0)
