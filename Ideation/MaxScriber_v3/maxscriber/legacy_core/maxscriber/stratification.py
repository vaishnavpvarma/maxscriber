import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import scipy.stats as stats


def perform_stratification(latest_data: dict, m_map: dict):
    """
    Returns data grouped into: Mild, Moderate, Clinically Severe.
    Returns:
        stratified_data = {
            'Platelets': {'Mild': [], 'Moderate': [], 'Clinically Severe': []},
            'Haemoglobin': {'Mild': [], 'Moderate': [], 'Clinically Severe': []},
            ...
        }
    """
    groups = {"Mild": [], "Moderate": [], "Clinically Severe": []}

    for max_id, tests in latest_data.items():
        age_str = m_map.get(max_id, {}).get("Age", "0")
        try:
            age = float(age_str.replace("y", "").replace("Y", "").replace(" ", ""))
        except:
            age = 25  # default to adult

        tlc_val = tests.get("Total Leukocyte Count (TLC)", "nil")
        plt_val = tests.get("Platelet Count", "nil")

        try:
            tlc = float(str(tlc_val).strip())
            plt = float(str(plt_val).strip())
        except ValueError:
            continue

        is_child = age <= 12
        normal_tlc_min = 5.0 if is_child else 4.0

        if tlc >= normal_tlc_min:
            group = "Mild"
        else:
            if plt >= 150:
                group = "Moderate"
            else:
                group = "Clinically Severe"

        groups[group].append(max_id)

    stratified_data = {}

    # Stratify continuous variables
    variables_to_test = [
        "Platelet Count",
        "Total Leukocyte Count (TLC)",
        "Haemoglobin",
        "PCV",
        "AST (SGOT)",
        "ALT (SGPT)",
    ]

    for var in variables_to_test:
        stratified_data[var] = {"Mild": [], "Moderate": [], "Clinically Severe": []}
        for group_name, max_ids in groups.items():
            for mid in max_ids:
                val = latest_data[mid].get(var, "nil")
                try:
                    # Clean the string
                    clean_val = str(val).lower().replace(">", "").replace("<", "").strip()
                    stratified_data[var][group_name].append(float(clean_val))
                except ValueError:
                    pass

    return stratified_data, groups


def run_kruskal_wallis(stratified_data):
    stats_results = {}
    for var, groups in stratified_data.items():
        mild = groups["Mild"]
        mod = groups["Moderate"]
        sev = groups["Clinically Severe"]
        if len(mild) > 0 and len(mod) > 0 and len(sev) > 0:
            h_stat, p_val = stats.kruskal(mild, mod, sev)
            stats_results[var] = {"H-statistic": h_stat, "p-value": p_val}
    return stats_results


def generate_pzfx(stratified_data, output_path: Path, job_name: str, plot_type: str):
    """
    Generate a professional Prism XML (.pzfx) file structure that complies with Prism standards.
    """
    NS = "http://graphpad.com/prism/Prism.htm"
    ET.register_namespace("", NS)

    root = ET.Element(f"{{{NS}}}GraphPadPrismFile", {"PrismXMLVersion": "5.00"})

    # 1. Created Section
    created = ET.SubElement(root, f"{{{NS}}}Created")
    ET.SubElement(
        created,
        f"{{{NS}}}OriginalVersion",
        {
            "CreatedByProgram": "MaxScriber",
            "CreatedByVersion": "1.0",
            "DateTime": datetime.now().isoformat(),
        },
    )

    # 2. Info Section (Mandatory for some versions)
    info_seq = ET.SubElement(root, f"{{{NS}}}InfoSequence")
    ET.SubElement(info_seq, f"{{{NS}}}Ref", {"ID": "Info0", "Selected": "1"})

    info = ET.SubElement(root, f"{{{NS}}}Info", {"ID": "Info0"})
    title_info = ET.SubElement(info, f"{{{NS}}}Title")
    title_info.text = f"MaxScriber Analysis - {job_name}"
    ET.SubElement(info, f"{{{NS}}}Notes")

    # 3. Table Sequence
    table_seq = ET.SubElement(root, f"{{{NS}}}TableSequence")
    for i, var in enumerate(stratified_data.keys()):
        ET.SubElement(
            table_seq, f"{{{NS}}}Ref", {"ID": f"Table{i}", "Selected": "1" if i == 0 else "0"}
        )

    # 4. Tables
    for i, (var, groups) in enumerate(stratified_data.items()):
        table = ET.SubElement(
            root,
            f"{{{NS}}}Table",
            {
                "ID": f"Table{i}",
                "XFormat": "none",
                "TableType": "OneWay",
                "ExtTableType": "MultipleVariables",
                "EVFormat": "AsteriskAfterNumber",
            },
        )
        title = ET.SubElement(table, f"{{{NS}}}Title")
        title.text = var

        for group_name in ["Mild", "Moderate", "Clinically Severe"]:
            ycol = ET.SubElement(
                table, f"{{{NS}}}YColumn", {"Width": "114", "Decimals": "2", "Subcolumns": "1"}
            )
            ycol_title = ET.SubElement(ycol, f"{{{NS}}}Title")
            ycol_title.text = group_name

            subcol = ET.SubElement(ycol, f"{{{NS}}}Subcolumn")
            for val in groups[group_name]:
                d = ET.SubElement(subcol, f"{{{NS}}}d")
                d.text = str(val)

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)
