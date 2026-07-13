# Quickstart Guide

## Installation

To install MaxScriber from the local source directory in editable mode, run:

```bash
pip install -e .
```

## Example Usage

### 1. Transcribe reports using a specific schema
This will transcribe the clinical reports found in the input directory and export the structured Excel sheet and database outputs.

```bash
maxscriber run --schema MaxHospitals_Dengue --input-dir ./raw_pdfs --output-dir ./results
```

### 2. Launch the Interactive visual dashboard (TUI)
You can launch the full-screen terminal user interface to manage schemas, load extraction jobs, and inspect records.

```bash
maxscriber tui
```
