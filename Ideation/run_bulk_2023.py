import re
import sys
from pathlib import Path


# Helper to automatically translate Windows paths to WSL paths if running on Linux/WSL
def get_platform_path(win_path_str: str) -> Path:
    if sys.platform != "win32":
        # Convert D:\... or d:\... to /mnt/d/... and flip slashes
        wsl_path = win_path_str.replace("\\", "/")
        wsl_path = re.sub(r"^([a-zA-Z]):", lambda m: f"/mnt/{m.group(1).lower()}", wsl_path)
        return Path(wsl_path)
    return Path(win_path_str)


# Map paths dynamically
workspace_root = get_platform_path(
    r"d:\DENV_Genome_WGS\MaxScriber_Py\Lab_Report_Samples\Max_Scriber_Tool_2_Repo_KFT_Location"
)
sys.path.insert(0, str(workspace_root))

from maxscriber.pipeline import run_all_phase1, run_all_phase2

input_dir = get_platform_path(
    r"D:\DENV_Genome_WGS\Meta_Data\Dengue_2023_data\Dengue_clinical_reports_2023_corrected\All_PDFs_2023"
)
output_dir = get_platform_path(r"D:\DENV_Genome_WGS\Meta_Data\Dengue_2023_data\2023_op_test_2")

print("--- Platform Detection ---")
print(f"OS/Platform detected: {sys.platform}")
print(f"Workspace Root:       {workspace_root}")
print(f"Input Directory:      {input_dir}")
print(f"Output Directory:     {output_dir}")
print("--------------------------\n")

print("--- Executing Bulk Phase 1 (Transcription & Extraction) ---")
run_all_phase1(input_dir, output_dir, pattern="2023")

print("\n--- Executing Bulk Phase 2 (QC & Analytics & Plots) ---")
run_all_phase2(output_dir)

print("\n--- Completed Bulk Execution Successfully! ---")
