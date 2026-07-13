from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.reactive import reactive
from rich.text import Text

ASCII_BANNER = r"""
 [bold #e0e0e0]  __  __             [/][bold #e0e0e0] _____           _ _               [/]
 [bold #e0e0e0] |  \/  |            [/][bold #e0e0e0]/ ____|         (_) |              [/]
 [bold #e0e0e0] | \  / | __ ___  __ [/][bold #e0e0e0]| (___   ___ _ __ _| |__   ___ _ __  [/]
 [bold #e0e0e0] | |\/| |/ _` \ \/ / [/][bold #e0e0e0] \___ \ / __| '__| | '_ \ / _ \ '__| [/]
 [bold #e0e0e0] | |  | | (_| |>  <  [/][bold #e0e0e0] ____) | (__| |  | | |_) |  __/ |    [/]
 [bold #e0e0e0] |_|  |_|\__,_/_/\_\ [/][bold #e0e0e0]|_____/ \___|_|  |_|_.__/ \___|_|    [/]
 [bold #d49040]              ELECTRONIC HEALTH RECORD TRANSCRIBER         [/]
"""

class Banner(Static):
    def render(self) -> str:
        return ASCII_BANNER

class WavyChart(Static):
    """Simulates a smooth wavy spline area chart using Braille characters."""
    shift_offset = reactive(0)
    
    def __init__(self, color_style: str, **kwargs):
        self.color_style = color_style
        # Base pattern to scroll
        self.p1 = "  ⡠⠤⢄⡀    ⢀⡠⠤⢄⡀     ⢀⡠⠤⢄⡀    ⢀⡠⠤⢄⡀ " * 3
        self.p2 = "⡠⠊⠉⠉⠉⠑⢄⡠⠊⠉⠉⠉⠑⢄⡠⠊⠉⠉⠉⠑⢄⡠⠊⠉⠉⠉⠑⢄" * 3
        self.p3 = "⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿" * 3
        super().__init__(**kwargs)

    def render(self) -> Text:
        w = self.size.width if self.size.width > 0 else 40
        offset = self.shift_offset % 20
        
        l1 = self.p1[offset:offset+w]
        l2 = self.p2[offset:offset+w]
        l3 = self.p3[offset:offset+w]
        
        text = Text()
        text.append(l1 + "\n", style=f"bold {self.color_style}")
        text.append(l2 + "\n", style=f"{self.color_style}")
        text.append(l3, style=f"dim {self.color_style}")
        return text

class StatsPanel(Vertical):
    current_throughput = reactive(0.0)
    current_confidence = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield Label("Extraction Throughput (Pages/sec)", classes="stats-title")
        yield Label("125.0", classes="stats-max")
        self.chart_throughput = WavyChart(color_style="#00ccff", classes="wavy-chart")
        yield self.chart_throughput
        with Horizontal(classes="stats-bounds"):
            yield Label("0.0", classes="stats-min")
            self.lbl_throughput = Label("0.0", classes="stats-current")
            yield self.lbl_throughput
            
        yield Label("Data Confidence Probability", classes="stats-title")
        yield Label("100%", classes="stats-max")
        self.chart_confidence = WavyChart(color_style="#33ff33", classes="wavy-chart")
        yield self.chart_confidence
        with Horizontal(classes="stats-bounds"):
            yield Label("0.0%", classes="stats-min")
            self.lbl_confidence = Label("0.0%", classes="stats-current")
            yield self.lbl_confidence

    def watch_current_throughput(self, val: float) -> None:
        self.lbl_throughput.update(f"{val:.1f}")
        # Animate chart horizontally based on throughput
        if val > 0:
            self.chart_throughput.shift_offset += int(val)

    def watch_current_confidence(self, val: float) -> None:
        self.lbl_confidence.update(f"{val:.1f}%")
        if val > 0:
            self.chart_confidence.shift_offset += 1

class ActionMenu(Vertical):
    def compose(self) -> ComposeResult:
        yield Button("📁 Schema Registry", id="btn_nav_schemas", classes="menu-btn default-btn")
        yield Button("⚙️ Parser Configuration", id="btn_nav_settings", classes="menu-btn default-btn")
        yield Button("➕ New EHR Template", id="btn_new_schema", classes="menu-btn default-btn")
        yield Button("▶ Execute Extraction Pipeline", id="btn_run", classes="menu-btn primary-btn")
