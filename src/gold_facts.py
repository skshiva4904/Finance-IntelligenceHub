import pandas as pd

from src.config import (
    SILVER_DIR,
    FACTS_DIR,
    DIMENSIONS_DIR
)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def normalize_code(value):
    """
    Standardizes business keys before joins.
    Example:
    500000.0 -> 500000
    cc1001   -> CC1001
    """

    if pd.isna(value):
        return pd.NA

    value = str(value).strip().upper()

    if value in ["", "NAN", "NONE", "NULL"]:
        return pd.NA

    if value.endswith(".0"):
        value = value[:-2]

    return value


def create_date_key_from_date(series):
    """
    Converts date column to DateKey format: YYYYMMDD.
    """

    dates = pd.to_datetime(series, errors="coerce")
    return dates.dt.strftime("%Y%m%d").astype("Int64")


def create_date_from_fiscal_period(gjahr, period):
    """
    Converts fiscal year + period into month-start date.
    Indian FY assumption:
    Period 1 = April
    Period 12 = March
    """

    period = pd.to_numeric(period, errors="coerce")
    gjahr = pd.to_numeric(gjahr, errors="coerce")

    month = period.apply(
        lambda p: p + 3 if pd.notna(p) and p <= 9 else p - 9 if pd.notna(p) else pd.NA
    )

    year = [
        y - 1 if pd.notna(p) and p <= 9 else y
        for y, p in zip(gjahr, period)
    ]

    return pd.to_datetime(
        {
            "year": year,
            "month": month,
            "day": 1
        },
        errors="coerce"
    )


def create_asset_reporting_date(gjahr):
    """
    Asset fact grain is Asset + Fiscal Year.
    So DateKey should use fiscal-year start date, not AKTIV.
    Example:
    GJAHR 2025 -> 20240401
    """

    gjahr = pd.to_numeric(gjahr, errors="coerce")

    return pd.to_datetime(
        {
            "year": gjahr - 1,
            "month": 4,
            "day": 1
        },
        errors="coerce"
    )


def safe_merge(fact_df, dim_df, fact_col, dim_col, key_col):
    """
    Safely joins dimension key into fact table after normalizing codes.
    """

    if fact_col in fact_df.columns and dim_col in dim_df.columns:

        fact_df[fact_col] = fact_df[fact_col].apply(normalize_code)
        dim_df[dim_col] = dim_df[dim_col].apply(normalize_code)

        fact_df = fact_df.merge(
            dim_df[[key_col, dim_col]],
            how="left",
            left_on=fact_col,
            right_on=dim_col
        )

        if dim_col != fact_col and dim_col in fact_df.columns:
            fact_df.drop(columns=[dim_col], inplace=True)

    else:
        fact_df[key_col] = pd.NA

    return fact_df


def fill_unknown_keys(df, key_columns):
    """
    Replaces missing surrogate keys with 0.
    This must match UNKNOWN rows in dimension tables.
    """

    for col in key_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def print_unknown_key_summary(table_name, df):
    """
    Prints count of unknown keys for validation.
    """

    key_cols = [col for col in df.columns if col.endswith("Key")]

    summary = {
        col: int((df[col] == 0).sum())
        for col in key_cols
        if col in df.columns
    }

    print(f"{table_name} Unknown Key Summary: {summary}")


# =====================================================
# FACT_GL_POSTINGS
# =====================================================

def create_fact_gl_postings(fi_df, dims):
    """
    Grain:
    One row = one GL posting line.

    Main measure:
    DMBTR / ReportingAmount_INR
    """

    fact = fi_df.copy()

    if "BUDAT" in fact.columns:
        fact["DateKey"] = create_date_key_from_date(fact["BUDAT"])
    else:
        fact["DateKey"] = pd.NA

    fact = safe_merge(fact, dims["Dim_Company"], "BUKRS", "BUKRS", "CompanyKey")
    fact = safe_merge(fact, dims["Dim_GL_Account"], "HKONT", "GLAccount", "GLKey")
    fact = safe_merge(fact, dims["Dim_CostCenter"], "KOSTL", "KOSTL", "CostCenterKey")
    fact = safe_merge(fact, dims["Dim_ProfitCenter"], "PRCTR", "PRCTR", "ProfitCenterKey")
    fact = safe_merge(fact, dims["Dim_Plant"], "WERKS", "WERKS", "PlantKey")
    fact = safe_merge(fact, dims["Dim_DocumentType"], "BLART", "BLART", "DocumentTypeKey")

    fact = fill_unknown_keys(
        fact,
        [
            "CompanyKey",
            "GLKey",
            "CostCenterKey",
            "ProfitCenterKey",
            "PlantKey",
            "DocumentTypeKey"
        ]
    )

    selected_cols = [
        "DateKey",
        "CompanyKey",
        "GLKey",
        "CostCenterKey",
        "ProfitCenterKey",
        "PlantKey",
        "DocumentTypeKey",
        "Source_GJAHR",
        "Source_MONAT",
        "FiscalYearNo",
        "FiscalPeriod",
        "IsFiscalDateMismatch",

        "BUKRS",
        "BELNR",
        "GJAHR",
        "MONAT",
        "BUDAT",
        "BLART",
        "HKONT",
        "KOSTL",
        "PRCTR",
        "WERKS",
        "WAERS",
        "WRBTR",
        "DMBTR",
        "ReportingAmount_INR",
        "XBLNR",
        "SGTXT",
        "USNAM",
        "IsAmountNull"
    ]

    selected_cols = [col for col in selected_cols if col in fact.columns]

    fact = fact[selected_cols]

    print_unknown_key_summary("Fact_GL_Postings", fact)

    return fact


# =====================================================
# FACT_COSTCENTER_ACTUALS
# =====================================================

def create_fact_costcenter_actuals(co_df, dims):
    """
    Grain:
    Cost Center + Cost Element + Fiscal Year + Period.

    Note:
    CO source contains actual cost only.
    No real plan amount column exists in source.
    """

    fact = co_df.copy()

    if "GJAHR" in fact.columns and "Period_Num" in fact.columns:
        fact["PeriodStartDate"] = create_date_from_fiscal_period(
            fact["GJAHR"],
            fact["Period_Num"]
        )
        fact["DateKey"] = create_date_key_from_date(fact["PeriodStartDate"])
    else:
        fact["DateKey"] = pd.NA

    # CO source does not contain BUKRS
    fact["CompanyKey"] = 0

    fact = safe_merge(fact, dims["Dim_GL_Account"], "KSTAR", "GLAccount", "GLKey")
    fact = safe_merge(fact, dims["Dim_CostCenter"], "KOSTL", "KOSTL", "CostCenterKey")
    fact = safe_merge(fact, dims["Dim_ProfitCenter"], "PRCTR", "PRCTR", "ProfitCenterKey")
    fact = safe_merge(fact, dims["Dim_Plant"], "WERKS", "WERKS", "PlantKey")

    fact = fill_unknown_keys(
        fact,
        [
            "CompanyKey",
            "GLKey",
            "CostCenterKey",
            "ProfitCenterKey",
            "PlantKey"
        ]
    )

    # No genuine Cost Centre plan is available in the source dataset.
    # Do not generate artificial plan or variance values.

    fact["Plan_Amount"] = pd.NA
    fact["Variance_Percent"] = pd.NA
    fact["Variance_Amount"] = pd.NA

    selected_cols = [
        "DateKey",
        "CompanyKey",
        "GLKey",
        "CostCenterKey",
        "ProfitCenterKey",
        "PlantKey",
        

        "KOKRS",
        "KOSTL",
        "KSTAR",
        "LSTAR",
        "BEKNZ",
        "GJAHR",
        "PERIO",
        "Period_Num",
        "Period_Column",
        "PeriodStartDate",
        "WAERS",
        "PRCTR",
        "WERKS",

        "Actual_Amount",
        "Signed_Actual_Amount",
        "ReportingActual_INR",
        "IsNonINRCurrency",
        "Plan_Amount",
        "Variance_Amount",
        "Variance_Percent",
        "IsKostlNull"
    ]

    selected_cols = [col for col in selected_cols if col in fact.columns]

    fact = fact[selected_cols]

    print_unknown_key_summary("Fact_CostCenter_Actuals", fact)

    return fact


# =====================================================
# FACT_PROFITCENTER_PL
# =====================================================

def create_fact_profitcenter_pl(pl_df, dims):
    """
    Grain:
    Profit Center + Fiscal Year + Period.
    """

    fact = pl_df.copy()

    if "GJAHR" in fact.columns and "PERIO" in fact.columns:
        fact["PeriodStartDate"] = create_date_from_fiscal_period(
            fact["GJAHR"],
            fact["PERIO"]
        )
        fact["DateKey"] = create_date_key_from_date(fact["PeriodStartDate"])
    else:
        fact["DateKey"] = pd.NA

    # PL source does not contain BUKRS
    fact["CompanyKey"] = 0

    fact = safe_merge(
        fact,
        dims["Dim_GL_Account"],
        "HKONT",
        "GLAccount",
        "GLKey"
    )
    
    fact = safe_merge(fact, dims["Dim_ProfitCenter"], "PRCTR", "PRCTR", "ProfitCenterKey")
    fact = safe_merge(fact, dims["Dim_Plant"], "WERKS", "WERKS", "PlantKey")

    fact = fill_unknown_keys(
        fact,
        [
            "CompanyKey",
            "GLKey",
            "ProfitCenterKey",
            "PlantKey"
        ]
    )

    selected_cols = [
        "DateKey",
        "CompanyKey",
        "GLKey",
        "ProfitCenterKey",
        "PlantKey",

        "PRCTR",
        "HKONT",
        "ProfitCenter_Bucket",
        "WERKS",
        "SEGMENT",
        "GJAHR",
        "PERIO",
        "PeriodStartDate",

        "REVENUE",
        "COGS",
        "GROSS_PROFIT",
        "OVERHEADS",
        "EBITDA",
        "DEPRECIATION",
        "EBIT",
        "INTEREST",
        "EBT",
        "TAX",
        "PAT",

        "PLAN_REV",
        "PLAN_COGS",
        "VAR_REV",
        "VAR_COGS",

        "IsUnknownProfitCenter",
        "IsRevenueNull"
    ]

    selected_cols = [col for col in selected_cols if col in fact.columns]

    fact = fact[selected_cols]

    print_unknown_key_summary("Fact_ProfitCenter_PL", fact)

    return fact


# =====================================================
# FACT_ASSET_BALANCES
# =====================================================

def create_fact_asset_balances(asset_df, dims):
    """
    Grain:
    One row = one asset + fiscal year.

    Important:
    DateKey uses fiscal-year reporting date from GJAHR.
    AKTIV is kept only as capitalisation date.
    """

    fact = asset_df.copy()

    if "GJAHR" in fact.columns:
        fact["ReportingDate"] = create_asset_reporting_date(fact["GJAHR"])
        fact["DateKey"] = create_date_key_from_date(fact["ReportingDate"])
    else:
        fact["DateKey"] = pd.NA

    fact = safe_merge(fact, dims["Dim_Company"], "BUKRS", "BUKRS", "CompanyKey")
    fact = safe_merge(fact, dims["Dim_ProfitCenter"], "PRCTR", "PRCTR", "ProfitCenterKey")
    fact = safe_merge(fact, dims["Dim_Plant"], "WERKS", "WERKS", "PlantKey")
    fact = safe_merge(fact, dims["Dim_AssetClass"], "ANLKL", "ANLKL", "AssetClassKey")

    fact = fill_unknown_keys(
        fact,
        [
            "CompanyKey",
            "ProfitCenterKey",
            "PlantKey",
            "AssetClassKey"
        ]
    )

    selected_cols = [
        "DateKey",
        "CompanyKey",
        "ProfitCenterKey",
        "PlantKey",
        "AssetClassKey",

        "BUKRS",
        "ANLN1",
        "ANLKL",
        "TXT50",
        "AKTIV",
        "DEACT",
        "GJAHR",
        "ReportingDate",
        "DEP_KEY",
        "USEFUL_LIFE",
        "PRCTR",
        "WERKS",

        "ACQUISITION_COST",
        "ACC_DEPRECIATION",
        "NET_BOOK_VALUE",
        "CURR_YR_DEP",

        "ACQUISITION_COST_CLEAN",
        "ACC_DEPRECIATION_CLEAN",
        "Original_NBV",
        "NET_BOOK_VALUE_CLEAN",

        "IsAcqCostMissing",
        "IsFullyDepreciated"
    ]

    selected_cols = [col for col in selected_cols if col in fact.columns]

    fact = fact[selected_cols]

    print_unknown_key_summary("Fact_Asset_Balances", fact)

    return fact


# =====================================================
# RUN GOLD FACTS
# =====================================================

def run_gold_facts_layer():
    """
    Reads Silver files + Dimension CSV files.
    Creates all 4 Fact tables for Power BI.
    """

    print("\n========== GOLD FACTS STARTED ==========")

    fi_df = pd.read_parquet(SILVER_DIR / "FI_GL.parquet")
    co_df = pd.read_parquet(SILVER_DIR / "CO_Actuals.parquet")
    pl_df = pd.read_parquet(SILVER_DIR / "ProfitCenter_PL.parquet")
    asset_df = pd.read_parquet(SILVER_DIR / "Asset.parquet")

    dims = {
        "Dim_Date": pd.read_csv(DIMENSIONS_DIR / "Dim_Date.csv"),
        "Dim_Company": pd.read_csv(DIMENSIONS_DIR / "Dim_Company.csv", dtype=str),
        "Dim_GL_Account": pd.read_csv(DIMENSIONS_DIR / "Dim_GL_Account.csv", dtype=str),
        "Dim_CostCenter": pd.read_csv(DIMENSIONS_DIR / "Dim_CostCenter.csv", dtype=str),
        "Dim_ProfitCenter": pd.read_csv(DIMENSIONS_DIR / "Dim_ProfitCenter.csv", dtype=str),
        "Dim_Plant": pd.read_csv(DIMENSIONS_DIR / "Dim_Plant.csv", dtype=str),
        "Dim_DocumentType": pd.read_csv(DIMENSIONS_DIR / "Dim_DocumentType.csv", dtype=str),
        "Dim_AssetClass": pd.read_csv(DIMENSIONS_DIR / "Dim_AssetClass.csv", dtype=str)
    }

    facts = {
        "Fact_GL_Postings": create_fact_gl_postings(fi_df, dims),
        "Fact_CostCenter_Actuals": create_fact_costcenter_actuals(co_df, dims),
        "Fact_ProfitCenter_PL": create_fact_profitcenter_pl(pl_df, dims),
        "Fact_Asset_Balances": create_fact_asset_balances(asset_df, dims)
    }

    for name, df in facts.items():
        output_path = FACTS_DIR / f"{name}.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved {name}: {len(df):,} rows")

    print("========== GOLD FACTS COMPLETED ==========\n")

    return facts