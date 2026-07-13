import os
import sys
from pathlib import Path

# Add project source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

project = "MaxScriber"
copyright = "2026, vaishnavpvarma"
author = "vaishnavpvarma"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx_click",
    "myst_parser"
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = []

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
