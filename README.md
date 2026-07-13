# MaxScriber

**MaxScriber** is a universal, adaptive pipeline for extracting, tabulating, and analyzing structured data from medical laboratory report PDFs. 

Built with clinical research in mind, MaxScriber replaces manual data entry with an intelligent, multi-pass extraction engine. Whether you're working with CBC, LFT, KFT, or Serology reports, MaxScriber can adapt to different hospital PDF formats and automatically export your data to Excel, alongside statistical summaries and distribution plots.

## Key Features

- 🏥 **Universal Adaptability:** Define new PDF extraction schemas using simple YAML files—no code changes required.
- ⚡ **High Performance:** Parallel processing allows for rapid batch extraction of hundreds of PDFs.
- 🔬 **Clinical Analytics:** Automatically generate descriptive statistics, data plots, and R scripts for your datasets.
- 🖥️ **Beautiful CLI & TUI:** Features a modern, intuitive command-line interface powered by `Click` and `Textual`.

---

## Installation

MaxScriber is packaged as a universal Python library, supporting all major package managers. Requires **Python 3.9+**.

### Using `uv` (Recommended - Fastest)
```bash
uv pip install -e .
```

### Using `pip`
```bash
pip install -e .
```

### Using `Conda` / `Mamba`
```bash
conda env create -f environment.yml
conda activate maxscriber-dev
```

---

## Usage

MaxScriber comes with an intuitive CLI. 

### Interactive TUI Wizard
Run the tool without arguments to launch the interactive, full-screen terminal UI:
```bash
maxscriber
```

### Headless CLI Execution
You can bypass the TUI and run jobs directly from the command line:

```bash
# Run the complete pipeline using a saved schema
maxscriber run --schema MaxHospitals_Dengue --input-dir ./my_pdfs --output-dir ./results

# Run using a custom test list file
maxscriber run --tests-file my_tests.txt --input-dir ./my_pdfs --output-dir ./results

# Create a new schema from a batch of sample PDFs
maxscriber schema create
```

### Get Help
```bash
maxscriber --help
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
