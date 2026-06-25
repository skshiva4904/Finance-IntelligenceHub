import pandas as pd

from src.config import (
    DATA_FILE,
    BRONZE_DIR,
    FI_SHEET,
    CO_SHEET,
    PL_SHEET,
    ASSET_SHEET
)


def run_bronze_layer():
    """
    Bronze Layer:
    - Reads raw Excel file
    - Extracts the 4 main SAP finance sheets
    - Saves them exactly as received
    - No cleaning is applied here
    """

    print("\n========== BRONZE LAYER STARTED ==========")

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {DATA_FILE}")

    sheets = {
        "FI_GL_LineItems": FI_SHEET,
        "CO_CostCenter_Actuals": CO_SHEET,
        "PC_ProfitCenter_PL": PL_SHEET,
        "AA_AssetRegister": ASSET_SHEET
    }

    for output_name, sheet_name in sheets.items():
        print(f"Reading sheet: {sheet_name}")

        df = pd.read_excel(
            DATA_FILE,
            sheet_name=sheet_name,
            engine="openpyxl"
        )

        output_path = BRONZE_DIR / f"{output_name}.parquet"

        df.to_parquet(
            output_path,
            index=False
        )

        print(f"Saved: {output_path}")
        print(f"Rows: {len(df):,} | Columns: {len(df.columns)}")

    print("========== BRONZE LAYER COMPLETED ==========\n")