# MaXScriber v1.0 🏎️

**Intelligent Multi-Pass Medical PDF Extractor**
No AI/ML — Pure Rule-Based with Cross-Validation

> *coded with ❤️ by vaishnavpvarma*

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vaishnavpvarma/Max_Scriber_Tool_2_Repo.git
   cd Max_Scriber_Tool_2_Repo
   ```

2. **Install in development mode:**
   ```bash
   pip install -e .
   ```

   This installs the `maxscriber` command globally.

---

## Usage

### Show Banner & Help

```bash
maxscriber
maxscriber -h
```

### Full Pipeline (Transcribe → QC → Stats → Plot)

```bash
maxscriber run --input_dir <path_to_pdfs> --output_dir <path_to_output>
```

> Before executing, you'll be asked: *"Have you referred to the extraction.log file?"*
> Answer **Yes** to proceed, or **No** to review logs first.

### Individual Commands

| Command | Description |
|---------|-------------|
| `maxscriber transcribe --input_dir <IN> --output_dir <OUT>` | PDF text extraction & test mapping |
| `maxscriber qc --output_dir <OUT>` | Content hashing & duplicate detection |
| `maxscriber stats --output_dir <OUT>` | Generate `Stats_Refined.txt` |
| `maxscriber plot --output_dir <OUT>` | Generate clinical distribution graphs |

> **Note:** `qc`, `stats`, and `plot` require a prior `transcribe` run (they load saved extraction data).

### Per-Command Help

```bash
maxscriber run -h
maxscriber transcribe -h
maxscriber qc -h
maxscriber stats -h
maxscriber plot -h
```

---

## Output Files

| File | Description |
|------|-------------|
| `Master_Data_Refined.xlsx` | Aggregated patient data in Excel |
| `Stats_Refined.txt` | Statistical summary report |
| `extraction.log` | Detailed extraction log for debugging |
| `graphs/` | Clinical distribution histograms |
| `extraction_data.pkl` | Intermediate data (for subcommand independence) |

---

## Dependencies

- `pdfplumber`
- `openpyxl`
- `pandas`
- `fuzzywuzzy`
- `python-Levenshtein`
- `matplotlib`

---

*SIMPLY LOVELY 😉 — Max Verstappen*
