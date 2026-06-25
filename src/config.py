from pathlib import Path

# =====================================================
# ROOT PROJECT PATH
# =====================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

# =====================================================
# INPUT DATA FILE
# =====================================================

DATA_FILE = ROOT_DIR / "data" / "MFG_Finance_Dataset.xlsx"

# =====================================================
# LAYER FOLDERS
# =====================================================

BRONZE_DIR = ROOT_DIR / "bronze"
SILVER_DIR = ROOT_DIR / "silver"
GOLD_DIR = ROOT_DIR / "gold"

FACTS_DIR = GOLD_DIR / "facts"
DIMENSIONS_DIR = GOLD_DIR / "dimensions"

DQ_DIR = ROOT_DIR / "dq"
LOG_DIR = ROOT_DIR / "logs"

# =====================================================
# CREATE FOLDERS IF NOT EXISTS
# =====================================================

for folder in [
    BRONZE_DIR,
    SILVER_DIR,
    GOLD_DIR,
    FACTS_DIR,
    DIMENSIONS_DIR,
    DQ_DIR,
    LOG_DIR
]:
    folder.mkdir(parents=True, exist_ok=True)

# =====================================================
# EXCEL SHEET NAMES
# =====================================================

FI_SHEET = "FI_GL_LineItems"
CO_SHEET = "CO_CostCenter_Actuals"
PL_SHEET = "PC_ProfitCenter_PL"
ASSET_SHEET = "AA_AssetRegister"