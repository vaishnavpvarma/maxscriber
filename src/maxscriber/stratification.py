import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import subprocess

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

def load_stratification_config(config_path: Path, logger: logging.Logger) -> dict:
    if config_path.exists():
        if not HAS_YAML:
            logger.warning("PyYAML not installed. Cannot parse custom_stratification.yaml. Falling back to legacy Dengue mode.")
            return None
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded custom stratification config from {config_path}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load custom stratification config: {e}. Falling back to legacy Dengue mode.")
    return None

def apply_legacy_dengue_stratification(latest_data: dict, metadata_map: dict) -> dict:
    """
    Applies the legacy Dengue stratification rules:
    - Child (Age <= 12, normal TLC >= 5.0)
    - Adult (Age > 12, normal TLC >= 4.0)
    
    Mild: TLC >= normal bound
    Moderate: TLC < normal bound AND Platelet > 50,000
    Severe: Platelet <= 50,000
    """
    stratified = {'Mild': [], 'Moderate': [], 'Severe': [], 'Unclassified': []}

    for mid, d in latest_data.items():
        meta = metadata_map.get(mid, {})
        age_str = str(meta.get('Age', '')).replace('.', '', 1)
        
        # If age is unknown, assume Adult
        age = int(float(age_str)) if age_str.isdigit() else 30
        
        tlc_str = d.get('Total Leukocyte Count(TLC)')
        plt_str = d.get('Platelet')

        try:
            tlc = float(str(tlc_str).replace(',', '').replace('>', '').replace('<', '').strip())
        except (ValueError, TypeError):
            tlc = None

        try:
            plt_val = float(str(plt_str).replace(',', '').replace('>', '').replace('<', '').strip())
        except (ValueError, TypeError):
            plt_val = None
            
        if plt_val is None and tlc is None:
            stratified['Unclassified'].append(mid)
            continue
            
        # Determine normal TLC bound
        normal_tlc = 5.0 if age <= 12 else 4.0
        
        # Determine severity
        if plt_val is not None and plt_val <= 50000:
            stratified['Severe'].append(mid)
        elif tlc is not None and tlc < normal_tlc and (plt_val is None or plt_val > 50000):
            stratified['Moderate'].append(mid)
        elif tlc is not None and tlc >= normal_tlc:
            stratified['Mild'].append(mid)
        else:
            # Fallback if logic misses
            stratified['Unclassified'].append(mid)

    return stratified

def export_stratified_data(stratified_data: dict, latest_data: dict, metadata_map: dict, output_dir: Path, job_name: str, logger: logging.Logger):
    """
    Exports the stratified patient data into separate sheets in an Excel file.
    """
    xlsx_path = output_dir / f"{job_name}_mild_mod_severe.xlsx"
    
    from maxscriber.constants import OUTPUT_COLUMNS
    from maxscriber.pipeline import determine_tests_done
    
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        for bucket, mids in stratified_data.items():
            rows = []
            for mid in mids:
                row = {
                    'MAX_id': mid,
                    'Tests Done': determine_tests_done(latest_data.get(mid, {})),
                    'Gender': metadata_map.get(mid, {}).get('Gender', 'nil'),
                    'Age': metadata_map.get(mid, {}).get('Age', 'nil'),
                    'Collection_date': latest_data.get(mid, {}).get('collection_date', 'nil')
                }
                # Add all outputs
                for col in [c for c in OUTPUT_COLUMNS if not c.endswith('_Unit')]:
                    if col not in row:
                        row[col] = latest_data.get(mid, {}).get(col, 'nil')
                rows.append(row)
            
            if rows:
                df = pd.DataFrame(rows)
                df.to_excel(writer, index=False, sheet_name=bucket)
                
    logger.info(f"Exported stratified data to {xlsx_path}")
    return xlsx_path

def generate_r_script(xlsx_path: Path, output_dir: Path, job_name: str, logger: logging.Logger):
    """
    Generates and optionally runs a standalone R script for statistical analysis (Kruskal-Wallis).
    """
    r_script_path = output_dir / f"{job_name}_analysis.R"
    graphs_dir = output_dir / f"{job_name}_graphs"
    
    # We want to use readxl to read the sheets and perform analysis
    r_code = f"""# Auto-generated R script for {job_name}
library(readxl)
library(dplyr)
library(ggplot2)

file_path <- "{xlsx_path.as_posix()}"
sheets <- excel_sheets(file_path)

data_list <- list()
for (s in sheets) {{
    if (s != "Unclassified") {{
        df <- read_excel(file_path, sheet = s)
        if (nrow(df) > 0) {{
            df$Severity <- s
            data_list[[s]] <- df
        }}
    }}
}}

if (length(data_list) > 0) {{
    full_data <- bind_rows(data_list)
    full_data$Severity <- factor(full_data$Severity, levels = c("Mild", "Moderate", "Severe"))

    # Convert numeric columns safely
    full_data$`Platelet` <- as.numeric(as.character(full_data$`Platelet`))
    full_data$`Total Leukocyte Count(TLC)` <- as.numeric(as.character(full_data$`Total Leukocyte Count(TLC)`))
    
    # Create graphs dir
    dir.create("{graphs_dir.as_posix()}", showWarnings = FALSE)

    # 1. Platelet boxplot
    p1 <- ggplot(full_data[!is.na(full_data$Platelet), ], aes(x = Severity, y = Platelet, fill = Severity)) +
        geom_boxplot() +
        theme_minimal() +
        labs(title = "Platelet Count by Severity", x = "Severity", y = "Platelet Count")
    ggsave("{graphs_dir.as_posix()}/Platelet_by_Severity.png", plot = p1, width = 8, height = 6)
    ggsave("{graphs_dir.as_posix()}/Platelet_by_Severity.svg", plot = p1, width = 8, height = 6)

    # Kruskal-Wallis test for Platelet
    if (length(unique(full_data$Severity[!is.na(full_data$Platelet)])) > 1) {{
        kw_plt <- kruskal.test(Platelet ~ Severity, data = full_data)
        print("Kruskal-Wallis Test for Platelet across Severity:")
        print(kw_plt)
    }}

    # 2. TLC boxplot
    p2 <- ggplot(full_data[!is.na(full_data$`Total Leukocyte Count(TLC)`), ], aes(x = Severity, y = `Total Leukocyte Count(TLC)`, fill = Severity)) +
        geom_boxplot() +
        theme_minimal() +
        labs(title = "TLC by Severity", x = "Severity", y = "Total Leukocyte Count (TLC)")
    ggsave("{graphs_dir.as_posix()}/TLC_by_Severity.png", plot = p2, width = 8, height = 6)
    ggsave("{graphs_dir.as_posix()}/TLC_by_Severity.svg", plot = p2, width = 8, height = 6)

    # Kruskal-Wallis test for TLC
    if (length(unique(full_data$Severity[!is.na(full_data$`Total Leukocyte Count(TLC)`)])) > 1) {{
        kw_tlc <- kruskal.test(`Total Leukocyte Count(TLC)` ~ Severity, data = full_data)
        print("Kruskal-Wallis Test for TLC across Severity:")
        print(kw_tlc)
    }}
}} else {{
    print("No valid classified data found for analysis.")
}}
"""
    with open(r_script_path, 'w', encoding='utf-8') as f:
        f.write(r_code)
    logger.info(f"Generated R analysis script at {r_script_path}")
    
    # Try to execute the R script using Rscript if available
    try:
        logger.info(f"Executing R script: Rscript {r_script_path.name}")
        # Note: We run it with output_dir as cwd
        result = subprocess.run(["Rscript", r_script_path.name], cwd=output_dir, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("R script executed successfully.")
            logger.info(f"R output:\n{result.stdout}")
        else:
            logger.error(f"R script execution failed with code {result.returncode}")
            logger.error(f"R error:\n{result.stderr}")
    except FileNotFoundError:
        logger.warning("Rscript executable not found in PATH. Skipping R script execution.")
        logger.info("You can run the R script manually using R or RStudio.")

