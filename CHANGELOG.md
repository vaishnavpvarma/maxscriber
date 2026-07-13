# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-07-13

### Added
- Core pipeline runner (`maxscriber run`) to parse, aggregate, and report patient demographics and clinical assay results from heterogeneous medical PDF reports.
- Intelligent multi-pass extraction with layout detection and rule-based validation gating.
- Global Schema Registry allowing CLI-driven metadata matching via custom schema configurations.
- SQLite backend indexing and structured spreadsheet exporter (`Master_Data_Refined.xlsx`, `longitudinal_data.xlsx`).
- Matplotlib distribution plot outputs and auto-generated R script templates for downstream analysis.
- Textual terminal user interface (`maxscriber tui`) supporting workspace loading, live telemetry graphing, and schema inspection.
