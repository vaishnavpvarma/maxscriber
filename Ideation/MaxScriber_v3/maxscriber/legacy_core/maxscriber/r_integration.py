"""
r_integration.py
Export stratified clinical data to Excel and generate standalone R scripts
that perform Kruskal-Wallis analysis and produce publication-ready plots.
"""

import pandas as pd
from pathlib import Path
import logging
import subprocess
import textwrap


# ── Excel Export ────────────────────────────────────────────────────────────

def export_stratified_excel(stratified_data: dict, excel_path: Path) -> Path:
    """Write stratified biomarker data to an Excel workbook.

    Layout: one sheet per severity group (Mild, Moderate, Clinically Severe).
    Each sheet has columns = biomarker names, rows = individual patient values.
    This "wide" layout makes the R import straightforward.

    Parameters
    ----------
    stratified_data : dict
        ``{biomarker: {group: [values]}}`` as returned by
        ``perform_stratification``.
    excel_path : Path
        Destination ``.xlsx`` file.

    Returns
    -------
    Path  – the written file path.
    """
    group_names = ['Mild', 'Moderate', 'Clinically Severe']

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        for group in group_names:
            # Collect every biomarker's values for this group
            col_data = {}
            for var, groups in stratified_data.items():
                col_data[var] = pd.Series(groups.get(group, []))

            df = pd.DataFrame(col_data)
            sheet = group if len(group) <= 31 else group[:31]  # Excel 31-char limit
            df.to_excel(writer, index=False, sheet_name=sheet)

    return excel_path


# ── R Script Generation ────────────────────────────────────────────────────

def generate_r_script(
    stratified_data: dict,
    excel_path: Path,
    r_script_path: Path,
    plot_type: str = "1",
) -> Path:
    """Generate a self-contained R script for Kruskal-Wallis analysis + plots.

    The script:
      1. Reads the stratified Excel workbook.
      2. Reshapes data to long format.
      3. Runs a Kruskal-Wallis test per biomarker and prints results.
      4. Creates a box-and-whisker (default) or violin plot per biomarker.
      5. Saves each plot as both PNG (300 dpi) and SVG.

    Parameters
    ----------
    stratified_data : dict
        Only used to extract the list of biomarker names for the script.
    excel_path : Path
        Path to the Excel workbook written by ``export_stratified_excel``.
    r_script_path : Path
        Where to write the ``.R`` file.
    plot_type : str
        ``"1"`` → box-and-whisker, ``"2"`` → violin.

    Returns
    -------
    Path  – the written script path.
    """
    geom = "geom_violin(trim = FALSE, alpha = 0.7) + geom_boxplot(width = 0.15, fill = 'white')" \
        if plot_type == "2" else "geom_boxplot(alpha = 0.7, outlier.colour = 'red', outlier.shape = 16)"

    plot_subtitle = "Violin Plot" if plot_type == "2" else "Box-and-Whisker Plot"

    # Use forward slashes for R path compatibility
    excel_posix = excel_path.as_posix()
    out_dir_posix = r_script_path.parent.as_posix()

    variables = list(stratified_data.keys())
    var_vector = ', '.join(f'"{v}"' for v in variables)

    r_code = textwrap.dedent(f"""\
    #!/usr/bin/env Rscript
    # ─────────────────────────────────────────────────────────────────────────
    # MaxScriber – Kruskal-Wallis Analysis & Stratification Plots
    # Auto-generated R script – do not edit above the "USER PARAMETERS" line
    # ─────────────────────────────────────────────────────────────────────────

    # ── Dependencies ────────────────────────────────────────────────────────
    if (!requireNamespace("readxl",  quietly = TRUE)) install.packages("readxl",  repos = "https://cran.r-project.org")
    if (!requireNamespace("ggplot2", quietly = TRUE)) install.packages("ggplot2", repos = "https://cran.r-project.org")
    if (!requireNamespace("dplyr",   quietly = TRUE)) install.packages("dplyr",   repos = "https://cran.r-project.org")
    if (!requireNamespace("tidyr",   quietly = TRUE)) install.packages("tidyr",   repos = "https://cran.r-project.org")
    if (!requireNamespace("svglite", quietly = TRUE)) install.packages("svglite", repos = "https://cran.r-project.org")

    library(readxl)
    library(ggplot2)
    library(dplyr)
    library(tidyr)

    # ── USER PARAMETERS ─────────────────────────────────────────────────────
    excel_file <- "{excel_posix}"
    output_dir <- "{out_dir_posix}"
    variables  <- c({var_vector})

    # ── Read & Combine ───────────────────────────────────────────────────────
    sheets <- c("Mild", "Moderate", "Clinically Severe")
    all_data <- data.frame()

    for (sh in sheets) {{
      tryCatch({{
        df <- read_excel(excel_file, sheet = sh)
        if (nrow(df) > 0) {{
          df$Group <- sh
          all_data <- bind_rows(all_data, df)
        }}
      }}, error = function(e) {{
        message(paste("Skipping sheet:", sh, "-", e$message))
      }})
    }}

    all_data$Group <- factor(all_data$Group, levels = sheets)

    # ── Custom colour palette ────────────────────────────────────────────────
    severity_colours <- c(
      "Mild"              = "#4CAF50",
      "Moderate"          = "#FF9800",
      "Clinically Severe" = "#F44336"
    )

    # ── Analysis & Plots ─────────────────────────────────────────────────────
    cat("\\n══════════════════════════════════════════════════════════\\n")
    cat("  MaxScriber – Kruskal-Wallis H-test Results\\n")
    cat("══════════════════════════════════════════════════════════\\n\\n")

    for (var in variables) {{
      if (!(var %in% colnames(all_data))) {{
        message(paste("Variable not found in data:", var))
        next
      }}

      sub_df <- all_data[, c(var, "Group")]
      colnames(sub_df) <- c("Value", "Group")
      sub_df$Value <- as.numeric(sub_df$Value)
      sub_df <- sub_df[!is.na(sub_df$Value), ]

      if (nrow(sub_df) < 3) {{
        message(paste("Not enough data for:", var))
        next
      }}

      # ── Kruskal-Wallis test ──────────────────────────────────────────────
      kw <- kruskal.test(Value ~ Group, data = sub_df)
      cat(sprintf("%-30s  H = %8.3f   p = %.6f  %s\\n",
                  var, kw$statistic, kw$p.value,
                  ifelse(kw$p.value < 0.05, "*", "")))

      # ── Plot ─────────────────────────────────────────────────────────────
      p <- ggplot(sub_df, aes(x = Group, y = Value, fill = Group)) +
        {geom} +
        scale_fill_manual(values = severity_colours) +
        labs(
          title    = var,
          subtitle = paste0("{plot_subtitle}  |  Kruskal-Wallis p = ",
                            formatC(kw$p.value, format = "g", digits = 4)),
          x = "Severity Group",
          y = var
        ) +
        theme_minimal(base_size = 14) +
        theme(
          legend.position  = "none",
          plot.title       = element_text(face = "bold", size = 16),
          plot.subtitle    = element_text(size = 11, colour = "grey40"),
          panel.grid.major.x = element_blank()
        )

      # Sanitise variable name for filenames
      safe_var <- gsub("[^A-Za-z0-9_]", "_", var)

      # PNG
      png_path <- file.path(output_dir, paste0(safe_var, ".png"))
      ggsave(png_path, plot = p, width = 8, height = 6, dpi = 300)

      # SVG
      svg_path <- file.path(output_dir, paste0(safe_var, ".svg"))
      ggsave(svg_path, plot = p, device = "svg", width = 8, height = 6)
    }}

    cat("\\n══════════════════════════════════════════════════════════\\n")
    cat(paste("Plots saved to:", output_dir, "\\n"))
    cat("══════════════════════════════════════════════════════════\\n")
    """)

    r_script_path.write_text(r_code, encoding='utf-8')
    return r_script_path


# ── R Execution ─────────────────────────────────────────────────────────────

def run_r_script(r_script_path: Path, logger: logging.Logger) -> bool:
    """Execute the generated R script via ``Rscript``.

    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ["Rscript", "--vanilla", str(r_script_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        if result.stdout:
            logger.info(f"R output:\n{result.stdout}")
        if result.returncode != 0:
            logger.warning(f"R script exited with code {result.returncode}")
            if result.stderr:
                logger.warning(f"R stderr:\n{result.stderr}")
            return False
        return True
    except FileNotFoundError:
        logger.error(
            "Rscript executable not found. "
            "Ensure R is installed and Rscript is in your PATH. "
            "You can still run the generated .R file manually."
        )
        return False
    except subprocess.TimeoutExpired:
        logger.error("R script timed out after 300 seconds.")
        return False
