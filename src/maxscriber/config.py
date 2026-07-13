"""
MaXScriber v1.0
Test definitions, reference ranges, and clinical thresholds.
These dictionaries are PRESERVED EXACTLY as-is from the original script.
"""

# =============================================================================
# TEST DEFINITIONS (Merged from v2 for comprehensiveness)
# =============================================================================

TEST_ALIASES = {
    "Haemoglobin": ["haemoglobin", "hemoglobin", "hb", "hgb", "hemo", "haemo"],
    "Packed Cell,Volume": [
        "packed cell volume",
        "packed cell, volume",
        "pcv",
        "hematocrit",
        "hct",
        "haematocrit",
        "packed cell vol",
    ],
    "Total Leukocyte Count(TLC)": [
        "total leukocyte count",
        "total leucocyte count",
        "tlc",
        "wbc",
        "wbc count",
        "white blood cell",
        "leukocyte",
        "leucocyte",
        "total wbc",
    ],
    "RBC": ["rbc", "rbc count", "red blood cell", "red cell count", "erythrocyte"],
    "MCV": ["mcv", "mean corpuscular volume", "mean cell volume"],
    "MCH": ["mch", "mean corpuscular hemoglobin", "mean cell hemoglobin"],
    "MCHC": ["mchc", "mean corpuscular hemoglobin concentration", "mean cell hb conc"],
    "Platelet": ["platelet", "platelet count", "plt", "thrombocyte", "platelets"],
    "MPV": ["mpv", "mean platelet volume"],
    "RDW": ["rdw", "red cell distribution width", "red cell dist width"],
    "Neutrophils": ["neutrophils", "neutrophil", "neut", "polymorphs", "polys", "pmn"],
    "Lymphocytes": ["lymphocytes", "lymphocyte", "lymph", "lym"],
    "Monocytes": ["monocytes", "monocyte", "mono"],
    "Eosinophils": ["eosinophils", "eosinophil", "eos", "eosino"],
    "Basophils": ["basophils", "basophil", "baso", "bas"],
    "Absolute Neutrophil Count": [
        "absolute neutrophil count",
        "anc",
        "abs neutrophil",
        "neutrophil absolute",
    ],
    "Absolute Lymphocyte Count": [
        "absolute lymphocyte count",
        "alc",
        "abs lymphocyte",
        "lymphocyte absolute",
    ],
    "Absolute Monocyte Count": [
        "absolute monocyte count",
        "amc",
        "abs monocyte",
        "monocyte absolute",
    ],
    "Absolute Eosinophil Count": [
        "absolute eosinophil count",
        "aec",
        "abs eosinophil",
        "eosinophil absolute",
    ],
    "Absolute Basophil Count": [
        "absolute basophil count",
        "abc",
        "abs basophil",
        "basophil absolute",
    ],
    "Total Protein": ["total protein", "protein total", "serum protein", "total prot"],
    "Albumin": ["albumin", "alb", "serum albumin"],
    "Globulin": ["globulin", "glob", "serum globulin"],
    "A.G.": ["a/g ratio", "ag ratio", "a g ratio", "albumin globulin ratio", "a.g."],
    "Bilirubin (Total)": ["bilirubin total", "total bilirubin", "bilirubin t", "tbil", "t bili"],
    "Bilirubin (Direct)": [
        "bilirubin direct",
        "direct bilirubin",
        "bilirubin d",
        "dbil",
        "d bili",
        "conjugated bilirubin",
    ],
    "Bilirubin (Indirect)": [
        "bilirubin indirect",
        "indirect bilirubin",
        "bilirubin i",
        "ibil",
        "i bili",
        "unconjugated bilirubin",
    ],
    "Transaminase (AST)": [
        "ast",
        "sgot",
        "aspartate transaminase",
        "aspartate aminotransferase",
        "transaminase ast",
    ],
    "Transaminase (ALT)": [
        "alt",
        "sgpt",
        "alanine transaminase",
        "alanine aminotransferase",
        "transaminase alt",
    ],
    "Alkaline Phosphatase": [
        "alkaline phosphatase",
        "alk phos",
        "alp",
        "alkphos",
        "alk phosphatase",
    ],
    "GGTP (Gamma GT), Serum": [
        "ggtp",
        "ggt",
        "gamma gt",
        "gamma glutamyl transferase",
        "gamma glutamyl transpeptidase",
    ],
    "Dengue NS1 Antigen": [
        "dengue ns1 antigen",
        "dengue ns 1 antigen",
        "ns1 antigen",
        "dengue ns1",
        "ns1",
        "dengue ns 1",
        "ns 1 antigen",
        "dengue ns1 ag",
        "dengue antigen",
        "dengue ns1 antigen test",
    ],
    "Dengue IgG": [
        "dengue igg",
        "dengue igg antibody",
        "igg antibody serum",
        "dengue igg antibody serum",
        "igg",
        "dengue immunoglobulin g",
        "igg antibody, serum",
    ],
    "Dengue IgM": [
        "dengue igm",
        "dengue igm antibody",
        "igm antibody serum",
        "dengue igm antibody serum",
        "igm",
        "dengue immunoglobulin m",
        "igm antibody, serum",
    ],
    # =========================================================================
    # KFT PARAMETERS (Added: Structural Audit 2023)
    # =========================================================================
    "Urea": [
        "urea",
        "blood urea",
        "serum urea",
        "urea serum",
        "urea nitrogen",
        "urea urease gldh",
        "urea urease uv",
        "urea enzymatic rate",
        "urea urease",
        "urea urase uv",
        "urea urease with indicator dye",
    ],
    "BUN": [
        "bun",
        "blood urea nitrogen",
        "b.u.n",
        "b.u.n.",
        "bun blood urea nitrogen",
        "blood urea nitrogen urease gldh",
        "blood urea nitrogen urease uv",
        "blood urea nitrogen enzymatic rate",
        "blood urea nitrogen calculated",
        "blood urea nitrogen urease with indicator dye",
    ],
    "Creatinine": [
        "creatinine",
        "s. creatinine",
        "serum creatinine",
        "creatinine serum",
        "creatinine, serum",
        "creatinine, serum*",
        "creatinine jaffe kinetic",
        "creatinine rate-jaffe",
        "creatinine rate jaffe",
        "creatinine alkaline picrate kinetic",
        "creatinine alkaline picrate",
        "creatinine enzymatic",
        "creatinine enzymatic creatinine amidohydrolase",
        "creatinine uricase",
        "creatinine modified jaffe",
    ],
    "BUN_Creatinine_Ratio": [
        "bun/creatinine ratio",
        "bun creatinine ratio",
        "bun/creatinine",
        "blood urea nitrogen/creatinine ratio",
    ],
    "Uric_Acid": [
        "uric acid",
        "s. uric acid",
        "serum uric acid",
        "uric acid serum",
        "uric acid, serum",
        "uric acid, serum*",
        "uric acid uricase colorimetric",
        "uric acid uricase peroxidase",
        "uric acid uricase",
        "uric acid enzymatic",
    ],
    "eGFR": [
        "egfr",
        "e-gfr",
        "egfr by mdrd",
        "egfr mdrd",
        "egfr by ckd epi",
        "egfr by ckd epi 2021",
        "egfr ckd epi",
        "egfr ckd-epi",
        "glomerular filtration rate",
        "estimated glomerular filtration rate",
        "gfr mdrd",
        "gfr ckd epi",
    ],
}

LFT_TESTS = {
    "Total Protein",
    "Albumin",
    "Globulin",
    "A.G.",
    "Bilirubin (Total)",
    "Bilirubin (Direct)",
    "Bilirubin (Indirect)",
    "Transaminase (AST)",
    "Transaminase (ALT)",
    "Alkaline Phosphatase",
    "GGTP (Gamma GT), Serum",
}

CBC_TESTS = {
    "Haemoglobin",
    "Packed Cell,Volume",
    "Total Leukocyte Count(TLC)",
    "RBC",
    "MCV",
    "MCH",
    "MCHC",
    "Platelet",
    "MPV",
    "RDW",
    "Neutrophils",
    "Lymphocytes",
    "Monocytes",
    "Eosinophils",
    "Basophils",
    "Absolute Neutrophil Count",
    "Absolute Lymphocyte Count",
    "Absolute Monocyte Count",
    "Absolute Eosinophil Count",
    "Absolute Basophil Count",
}

DENGUE_TESTS = {"Dengue NS1 Antigen", "Dengue IgG", "Dengue IgM"}

KFT_TESTS = {"Urea", "BUN", "Creatinine", "BUN_Creatinine_Ratio", "Uric_Acid", "eGFR"}

# KFT implicit default units (used when unit column is absent/empty)
KFT_DEFAULT_UNITS = {
    "Urea": "mg/dL",
    "BUN": "mg/dL",
    "Creatinine": "mg/dL",
    "BUN_Creatinine_Ratio": "Ratio",
    "Uric_Acid": "mg/dL",
    "eGFR": "ml/min/1.73 m\u00b2",
}

# Normalise unit strings to canonical form (case-insensitive key match)
UNIT_NORMALISATION = {
    "mg/dl": "mg/dL",
    "mg/DL": "mg/dL",
    "MG/DL": "mg/dL",
    "MG/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "mmol/L": "mmol/L",
    "MMOL/L": "mmol/L",
    "g/dl": "g/dL",
    "G/DL": "g/dL",
    "u/l": "U/L",
    "U/l": "U/L",
}

# Noise-block prefixes — lines starting with these are excluded from KFT extraction
KFT_NOISE_PREFIXES = (
    "ref. range",
    "ref range",
    "reference range",
    "comment",
    "comments",
    "note:",
    "notes:",
    "interpretation",
    "advice",
    "advise",
    "kindly correlate",
    "*** end",
)

CLINICAL_THRESHOLDS = {
    "Anemia": {"test": "Haemoglobin", "low_M": 13.0, "low_F": 12.0},
    "Leukopenia": {"test": "Total Leukocyte Count(TLC)", "low": 4000.0},
    "Leukocytosis": {"test": "Total Leukocyte Count(TLC)", "high": 11000.0},
    "Thrombocytopenia": {"test": "Platelet", "low": 150000.0},
    "Thrombocytosis": {"test": "Platelet", "high": 450000.0},
    "Polycythemia": {"test": "Haemoglobin", "high_M": 16.5, "high_F": 16.0},
}

# Derived lookup table
ALIAS_TO_CANONICAL = {}
for canonical, aliases in TEST_ALIASES.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical

OUTPUT_COLUMNS = [
    "MAX_id",
    "Centre",
    "Tests Done",
    "File Name",
    "SIN No.",
    "Gender",
    "Age",
    "Collection_date",
]
for k in list(TEST_ALIASES.keys()):
    OUTPUT_COLUMNS.append(k)
    OUTPUT_COLUMNS.append(f"{k}_Unit")

REFERENCE_RANGES = {
    "Haemoglobin": (3.0, 25.0),
    "Packed Cell,Volume": (15.0, 65.0),
    "Total Leukocyte Count(TLC)": (0.5, 100.0),
    "RBC": (1.5, 8.0),
    "Platelet": (10.0, 1500.0),
    "Dengue NS1 Antigen": (0.0, 100.0),
    "Dengue IgG": (0.0, 100.0),
    "Dengue IgM": (0.0, 100.0),
    # KFT plausibility ranges
    "Urea": (1.0, 500.0),
    "BUN": (1.0, 250.0),
    "Creatinine": (0.1, 30.0),
    "BUN_Creatinine_Ratio": (1.0, 100.0),
    "Uric_Acid": (0.5, 30.0),
    "eGFR": (1.0, 200.0),
}
