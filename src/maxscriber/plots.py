"""
MaXScriber v1.0 - Eau Rouge Edition
Clinical distribution graph generation.
"""

import logging
from pathlib import Path
from typing import Dict

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def generate_clinical_plots(
    latest_data: Dict,
    metadata_map: Dict,
    output_dir: Path,
    logger: logging.Logger,
    job_name: str = 'default',
):
    """Generate clinical distribution plots (age, Hb, platelet)."""
    if not HAS_MATPLOTLIB:
        logger.warning("Matplotlib not installed. Skipping plots.")
        return

    graphs_dir = output_dir / f'{job_name}_graphs'
    graphs_dir.mkdir(exist_ok=True)

    # Prepare Data
    ages = []
    hb_vals = {'M': [], 'F': []}
    tlc_vals = []
    plt_vals = []

    for mid, d in latest_data.items():
        meta = metadata_map.get(mid, {})
        age = meta.get('Age')
        gender = meta.get('Gender', 'U')

        if age and str(age).isdigit():
            ages.append(int(age))

        hb = d.get('Haemoglobin')
        if hb and str(hb).replace('.', '').isdigit():
            v = float(hb)
            if gender in ['M', 'F']:
                hb_vals[gender].append(v)

        tlc = d.get('Total Leukocyte Count(TLC)')
        if tlc and str(tlc).replace('.', '').isdigit():
            tlc_vals.append(float(tlc))

        pl = d.get('Platelet')
        if pl and str(pl).replace('.', '').isdigit():
            plt_vals.append(float(pl))

    # 1. Age Distribution
    if ages:
        plt.figure(figsize=(10, 6))
        plt.hist(ages, bins=20, color='skyblue', edgecolor='black')
        plt.title('Patient Age Distribution')
        plt.xlabel('Age (Years)')
        plt.ylabel('Count')
        plt.savefig(graphs_dir / f'{job_name}_Age_Distribution.png')
        plt.close()

    # 2. Haemoglobin by Gender
    if hb_vals['M'] or hb_vals['F']:
        plt.figure(figsize=(10, 6))
        if hb_vals['M']:
            plt.hist(hb_vals['M'], bins=15, alpha=0.5, label='Male', color='blue')
        if hb_vals['F']:
            plt.hist(hb_vals['F'], bins=15, alpha=0.5, label='Female', color='pink')
        plt.title('Haemoglobin Distribution by Gender')
        plt.xlabel('Haemoglobin (g/dL)')
        plt.legend()
        plt.savefig(graphs_dir / f'{job_name}_Hb_Distribution.png')
        plt.close()

    # 3. Platelet Counts
    if plt_vals:
        plt.figure(figsize=(10, 6))
        plt.hist(
            [p for p in plt_vals if p < 1000000],
            bins=30, color='green', edgecolor='black'
        )
        plt.title('Platelet Count Distribution')
        plt.xlabel('Platelets (/cmm)')
        plt.savefig(graphs_dir / f'{job_name}_Platelet_Distribution.png')
        plt.close()

    logger.info(f"Generated plots in {graphs_dir}")
