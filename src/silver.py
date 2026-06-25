import pandas as pd

from src.config import BRONZE_DIR, SILVER_DIR


# =====================================================
# COMMON HELPER FUNCTIONS
# =====================================================

def clean_text_column(df, column_name):
    """
    Trim spaces, convert to uppercase, and replace invalid 'NAN' text with blank.
    """
    if column_name in df.columns:
        df[column_name] = (
            df[column_name]
            .astype(str)
            .str.strip()
            .str.upper()
            .replace("NAN", pd.NA)
        )
    return df


def parse_sap_date(df, column_name):
    """
    Converts SAP-style date columns.
    Handles:
    - 00.00.0000
    - blank values
    - DD.MM.YYYY format
    """
    if column_name in df.columns:
        df[column_name] = (
            df[column_name]
            .replace("00.00.0000", pd.NA)
        )

        df[column_name] = pd.to_datetime(
            df[column_name],
            format="%d.%m.%Y",
            errors="coerce"
        )

    return df


# =====================================================
# FI_GL_LineItems CLEANING
# =====================================================

def clean_fi_gl():
    """
    Silver transformation for FI_GL_LineItems.

    Rules Applied:
    1. Remove reversed entries where STBLG is not blank
    2. Remove dummy postings where SGTXT contains DUMMY
    3. Fix SAP null dates
    4. Standardize key fields
    5. Replace null amounts with 0
    6. Keep DMBTR as reporting amount
    """

    df = pd.read_parquet(BRONZE_DIR / "FI_GL_LineItems.parquet")

    original_rows = len(df)

    # Audit flags before filtering
    df["IsReversed"] = df["STBLG"].notna() & (df["STBLG"].astype(str).str.strip() != "")
    df["IsDummyPosting"] = df["SGTXT"].astype(str).str.upper().str.contains("DUMMY", na=False)

    reversed_count = df["IsReversed"].sum()
    dummy_count = df["IsDummyPosting"].sum()

    # Remove reversed and dummy entries
    df = df[~df["IsReversed"]]
    df = df[~df["IsDummyPosting"]]

    # Fix SAP dates
    for date_col in ["BLDAT", "BUDAT", "CPUDT"]:
        df = parse_sap_date(df, date_col)

    # Preserve original SAP fiscal fields for audit
    df["Source_GJAHR"] = pd.to_numeric(
        df["GJAHR"],
        errors="coerce"
    ).astype("Int64")

    df["Source_MONAT"] = pd.to_numeric(
        df["MONAT"],
        errors="coerce"
    ).astype("Int64")

    # Derive correct fiscal period from posting date
    posting_month = df["BUDAT"].dt.month

    df["FiscalPeriod"] = (
        ((posting_month - 4) % 12) + 1
    ).astype("Int64")

    # FY2026 represents Apr-2025 to Mar-2026
    df["FiscalYearNo"] = (
        df["BUDAT"].dt.year
        + (df["BUDAT"].dt.month >= 4).astype("Int64")
    ).astype("Int64")

    # Flag disagreement between source values and posting date
    df["IsFiscalDateMismatch"] = (
        df["BUDAT"].notna()
        & (
            df["Source_GJAHR"].ne(df["FiscalYearNo"])
            | df["Source_MONAT"].ne(df["FiscalPeriod"])
        )
    ).fillna(False)

    # Use BUDAT-derived fiscal values for reporting
    df["GJAHR"] = df["FiscalYearNo"]
    df["MONAT"] = df["FiscalPeriod"]

        # Standardize key text columns
    for col in [
        "MANDT", "BUKRS", "BELNR", "BLART", "BSCHL",
        "HKONT", "KOSTL", "PRCTR", "GSBER", "WERKS",
        "SEGMENT", "WAERS", "MWSKZ", "XBLNR", "USNAM", "ZUONR"
    ]:
        df = clean_text_column(df, col)

    # Amount null flag
    df["IsAmountNull"] = False

    for amount_col in ["WRBTR", "DMBTR", "MWSTS"]:
        if amount_col in df.columns:
            df["IsAmountNull"] = df["IsAmountNull"] | df[amount_col].isna()
            df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

    # Reporting amount should always use local currency
    if "DMBTR" in df.columns:
        df["ReportingAmount_INR"] = df["DMBTR"]

    df.to_parquet(SILVER_DIR / "FI_GL.parquet", index=False)

    return {
        "Table": "FI_GL_LineItems",
        "OriginalRows": original_rows,
        "FinalRows": len(df),
        "ReversedRowsRemoved": int(reversed_count),
        "DummyRowsRemoved": int(dummy_count),
        "Output": "silver/FI_GL.parquet"
    }


# =====================================================
# CO_CostCenter_Actuals CLEANING
# =====================================================

def clean_co_actuals():
    """
    Silver transformation for CO_CostCenter_Actuals.

    Rules Applied:
    1. Standardize KOSTL
    2. Flag missing KOSTL
    3. Unpivot WKG001-WKG012 into Period_Num and Actual_Amount
    4. Apply BEKNZ debit/credit logic
    """

    df = pd.read_parquet(BRONZE_DIR / "CO_CostCenter_Actuals.parquet")

    original_rows = len(df)

    # Standardize text columns
    for col in ["KOKRS", "KOSTL", "KSTAR", "LSTAR", "BEKNZ", "WAERS", "PRCTR", "WERKS", "BUKRS"]:
        df = clean_text_column(df, col)

    # Normalize KOSTL underscore variants
    if "KOSTL" in df.columns:
        df["IsKostlNull"] = df["KOSTL"].isna()
        df["KOSTL"] = df["KOSTL"].str.replace("_", "-", regex=False)
    else:
        df["IsKostlNull"] = True

    # Identify WKG period columns
    wkg_cols = [col for col in df.columns if str(col).startswith("WKG")]

    # Replace null monthly values with 0
    for col in wkg_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Unpivot WKG001-WKG012
    id_cols = [col for col in df.columns if col not in wkg_cols]

    df = pd.melt(
        df,
        id_vars=id_cols,
        value_vars=wkg_cols,
        var_name="Period_Column",
        value_name="Actual_Amount"
    )

    # WKG001 -> 1, WKG012 -> 12
    df["Period_Num"] = (
        df["Period_Column"]
        .str.replace("WKG", "", regex=False)
        .astype(int)
    )

    # Debit/Credit logic:
    # S = cost incurred = positive
    # H = cost allocated out = negative
    if "BEKNZ" in df.columns:
        df["Signed_Actual_Amount"] = df.apply(
            lambda row: -row["Actual_Amount"] if row["BEKNZ"] == "H" else row["Actual_Amount"],
            axis=1
        )
    else:
        df["Signed_Actual_Amount"] = df["Actual_Amount"]

    # Currency validation for CO reporting
    df["IsNonINRCurrency"] = df["WAERS"].ne("INR")

    # Safe reporting amount until an exchange-rate table is available.
    # Non-INR values are kept for audit but excluded from INR totals.
    df["ReportingActual_INR"] = df["Signed_Actual_Amount"].where(
        df["WAERS"].eq("INR"),
        pd.NA
)
    
    df.to_parquet(SILVER_DIR / "CO_Actuals.parquet", index=False)

    return {
        "Table": "CO_CostCenter_Actuals",
        "OriginalRows": original_rows,
        "FinalRows": len(df),
        "WKGColumnsUnpivoted": len(wkg_cols),
        "Output": "silver/CO_Actuals.parquet"
    }


# =====================================================
# PC_ProfitCenter_PL CLEANING
# =====================================================

def clean_profit_center_pl():
    """
    Silver transformation for PC_ProfitCenter_PL.

    Rules Applied:
    1. Standardize PRCTR
    2. Flag PRCTR_UNKNOWN
    3. Replace null REVENUE with 0
    4. Recalculate derived P&L fields where needed
    """

    df = pd.read_parquet(BRONZE_DIR / "PC_ProfitCenter_PL.parquet")

    original_rows = len(df)

    for col in ["PRCTR", "BUKRS", "WERKS", "SEGMENT", "GSBER"]:
        df = clean_text_column(df, col)

    if "PRCTR" in df.columns:
        df["IsUnknownProfitCenter"] = df["PRCTR"].eq("PRCTR_UNKNOWN")
        df["ProfitCenter_Bucket"] = df["PRCTR"].where(
            ~df["IsUnknownProfitCenter"],
            "UNATTRIBUTED"
        )
    else:
        df["IsUnknownProfitCenter"] = False
        df["ProfitCenter_Bucket"] = pd.NA

    if "REVENUE" in df.columns:
        df["IsRevenueNull"] = df["REVENUE"].isna()
        df["REVENUE"] = pd.to_numeric(df["REVENUE"], errors="coerce").fillna(0)
    else:
        df["IsRevenueNull"] = False

    numeric_cols = [
        "COGS", "GROSS_PROFIT", "OVERHEADS", "EBITDA",
        "DEPRECIATION", "EBIT", "INTEREST", "EBT", "TAX", "PAT",
        "PLAN_REV", "PLAN_COGS", "VAR_REV", "VAR_COGS"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Recalculate derived fields to keep formulas consistent
    if {"REVENUE", "COGS"}.issubset(df.columns):
        df["GROSS_PROFIT"] = df["REVENUE"] - df["COGS"]

    if {"GROSS_PROFIT", "OVERHEADS"}.issubset(df.columns):
        df["EBITDA"] = df["GROSS_PROFIT"] - df["OVERHEADS"]

    if {"EBITDA", "DEPRECIATION"}.issubset(df.columns):
        df["EBIT"] = df["EBITDA"] - df["DEPRECIATION"]

    if {"EBIT", "INTEREST"}.issubset(df.columns):
        df["EBT"] = df["EBIT"] - df["INTEREST"]

    if "EBT" in df.columns:
        df["TAX"] = df["EBT"] * 0.25
        df["PAT"] = df["EBT"] - df["TAX"]

    if {"REVENUE", "PLAN_REV"}.issubset(df.columns):
        df["VAR_REV"] = df["REVENUE"] - df["PLAN_REV"]

    if {"COGS", "PLAN_COGS"}.issubset(df.columns):
        df["VAR_COGS"] = df["COGS"] - df["PLAN_COGS"]

    df.to_parquet(SILVER_DIR / "ProfitCenter_PL.parquet", index=False)

    return {
        "Table": "PC_ProfitCenter_PL",
        "OriginalRows": original_rows,
        "FinalRows": len(df),
        "UnknownProfitCenters": int(df["IsUnknownProfitCenter"].sum()),
        "RevenueNulls": int(df["IsRevenueNull"].sum()),
        "Output": "silver/ProfitCenter_PL.parquet"
    }


# =====================================================
# AA_AssetRegister CLEANING
# =====================================================

def clean_asset_register():
    """
    Silver transformation for AA_AssetRegister.

    Rules Applied:
    1. Flag missing acquisition cost
    2. Calculate NBV
    3. Floor negative NBV at 0
    4. Flag fully depreciated assets
    5. Parse asset dates
    """

    df = pd.read_parquet(BRONZE_DIR / "AA_AssetRegister.parquet")

    original_rows = len(df)

    for col in ["ANLN1", "ANLKL", "TXT50", "DEP_KEY", "PRCTR", "WERKS", "BUKRS"]:
        df = clean_text_column(df, col)

    for date_col in ["AKTIV", "DEACT"]:
        df = parse_sap_date(df, date_col)

    numeric_cols = [
        "ACQUISITION_COST",
        "ACC_DEPRECIATION",
        "NET_BOOK_VALUE",
        "CURR_YR_DEP",
        "USEFUL_LIFE"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "ACQUISITION_COST" in df.columns:
        df["IsAcqCostMissing"] = df["ACQUISITION_COST"].isna()
    else:
        df["IsAcqCostMissing"] = True

        # Missing acquisition cost should be flagged and excluded from NBV calculation
    df["ACQUISITION_COST_CLEAN"] = df["ACQUISITION_COST"]
    df["ACC_DEPRECIATION_CLEAN"] = df["ACC_DEPRECIATION"].fillna(0)

    df["Original_NBV"] = df.apply(
        lambda row: pd.NA
        if row["IsAcqCostMissing"]
        else row["ACQUISITION_COST_CLEAN"] - row["ACC_DEPRECIATION_CLEAN"],
        axis=1
    )

    # Floor negative NBV to 0, but keep missing acquisition cost as blank
    df["NET_BOOK_VALUE_CLEAN"] = df["Original_NBV"].apply(
        lambda x: pd.NA if pd.isna(x) else max(x, 0)
    )

    df["IsFullyDepreciated"] = df["Original_NBV"].apply(
        lambda x: False if pd.isna(x) else x <= 0
    )

    df.to_parquet(SILVER_DIR / "Asset.parquet", index=False)

    return {
        "Table": "AA_AssetRegister",
        "OriginalRows": original_rows,
        "FinalRows": len(df),
        "MissingAcquisitionCost": int(df["IsAcqCostMissing"].sum()),
        "NegativeNBVFixed": int((df["Original_NBV"] < 0).sum()),
        "Output": "silver/Asset.parquet"
    }


# =====================================================
# RUN COMPLETE SILVER LAYER
# =====================================================

def run_silver_layer():
    """
    Runs all Silver transformations.
    """

    print("\n========== SILVER LAYER STARTED ==========")

    results = []

    results.append(clean_fi_gl())
    results.append(clean_co_actuals())
    results.append(clean_profit_center_pl())
    results.append(clean_asset_register())

    print("========== SILVER LAYER COMPLETED ==========\n")

    for result in results:
        print(result)

    return results