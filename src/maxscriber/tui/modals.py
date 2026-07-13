import json
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Input, Button, Static, ProgressBar
from rich.syntax import Syntax

from maxscriber.schema_manager import SchemaManager

class WorkspaceLoaderModal(ModalScreen):
    """Command palette to load a workspace."""
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("LOAD WORKSPACE DIRECTORY", id="dialog-title")
            yield Input(placeholder="e.g. ./output_2026", id="ws-input", classes="dialog-input")
            with Horizontal():
                yield Button("Load", id="btn-load", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-load":
            self.dismiss(self.query_one("#ws-input", Input).value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

class RecordInspectorModal(ModalScreen):
    """Displays raw JSON/YAML content."""
    def __init__(self, title: str, data: dict, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.data = data

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", style="width: 80; height: 80%;"):
            yield Label(f"INSPECT: {self.title_text}", id="dialog-title")
            
            json_str = json.dumps(self.data, indent=2)
            syntax = Syntax(json_str, "json", theme="monokai", word_wrap=True, background_color="default")
            
            yield Static(syntax, style="height: 1fr; overflow-y: auto; background: #1c2a35; padding: 1;")
            yield Button("Close", id="btn-close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

class ExecutePipelineModal(ModalScreen):
    """Prompts for input/output dirs to run the extraction pipeline."""
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("EXECUTE EXTRACTION PIPELINE", id="dialog-title")
            yield Input(placeholder="Input Directory (e.g. ./raw_pdfs)", id="in-dir", classes="dialog-input")
            yield Input(placeholder="Output Directory (e.g. ./output_run)", id="out-dir", classes="dialog-input")
            
            self.progress = ProgressBar(total=100, show_eta=False, id="pipeline-progress")
            self.progress.display = False
            yield self.progress
            
            self.status_lbl = Label("", style="color: #40e0d0; margin-bottom: 1;")
            yield self.status_lbl

            with Horizontal():
                yield Button("Start Execution", id="btn-start", variant="primary")
                yield Button("Close", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-start":
            in_dir = self.query_one("#in-dir", Input).value
            out_dir = self.query_one("#out-dir", Input).value
            if in_dir and out_dir:
                # Disable inputs
                self.query_one("#in-dir").disabled = True
                self.query_one("#out-dir").disabled = True
                event.button.disabled = True
                
                self.progress.display = True
                self.status_lbl.update("Initializing extraction workers...")
                
                # We return the paths to the main screen to start the worker
                self.dismiss({'in': in_dir, 'out': out_dir})

class SchemaWizardModal(ModalScreen):
    """Creates a new schema."""
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("NEW EHR TEMPLATE", id="dialog-title")
            yield Input(placeholder="Schema Name (e.g. MY_LAB_V1)", id="sch-name", classes="dialog-input")
            yield Input(placeholder="Assays (comma separated e.g. Hb, WBC, Platelets)", id="sch-assays", classes="dialog-input")
            yield Input(placeholder="Description", id="sch-desc", classes="dialog-input")
            
            with Horizontal():
                yield Button("Save Schema", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(False)
        elif event.button.id == "btn-save":
            name = self.query_one("#sch-name", Input).value
            assays_raw = self.query_one("#sch-assays", Input).value
            desc = self.query_one("#sch-desc", Input).value
            
            if name and assays_raw:
                assays = [a.strip() for a in assays_raw.split(",") if a.strip()]
                sm = SchemaManager()
                sm.save_schema(name, assays, {"custom": True}, is_legacy=False, description=desc)
                self.dismiss(True)

class ConfigModal(ModalScreen):
    """Adjusts parser configurations."""
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("PARSER CONFIGURATION", id="dialog-title")
            yield Label("Max Worker Threads:")
            yield Input(placeholder="4", value="4", id="cfg-threads", classes="dialog-input")
            yield Label("OCR Confidence Threshold (%):")
            yield Input(placeholder="85.0", value="85.0", id="cfg-ocr", classes="dialog-input")
            
            with Horizontal():
                yield Button("Save & Apply", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            try:
                th = int(self.query_one("#cfg-threads", Input).value)
                ocr = float(self.query_one("#cfg-ocr", Input).value)
                self.dismiss({'threads': th, 'ocr': ocr})
            except ValueError:
                pass
