# Roadmap

This roadmap outlines targeted features and development goals for future releases.

## v0.2.0 (Target: Next Cut)
- **Clinical Schema Scanner Wizard**: Replace the manual schema entry modal in the TUI with an interactive scanning interface. Users will load a sample PDF and visually map detected layout fields to a schema.
- **Dynamic Stratification Rule Engine**: Replace hardcoded Dengue rules in `stratification.py` with a generic YAML evaluation engine.
- **Real-time Log Streamer**: Integrate a live terminal log terminal (`RichLog`) inside the TUI pipeline view to monitor `extraction.log` messages during active runs.

## v0.3.0 (Target: Deployment)
- **Bioconda Integration**: Publish the project on Bioconda. Package development including official `meta.yaml` recipes, automated build checks, and cross-platform installation validation (WSL/Linux).
- **Expanded Test Coverage**: Add unit and integration tests covering extraction rules against sample clinical documents.
