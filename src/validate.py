import pandas as pd

from src.config import (
    BRONZE_DIR,
    SILVER_DIR,
    DQ_DIR
)


def add_dq_record(records, table, issue_type, issue_description, record_count):
    """
    Helper function to add one data quality issue record.
    """

    records.append({
        "TableName": table,
        "IssueType": issue_type,
        "IssueDescription": issue_description,
        "RecordCount": int(record_count)
    })


def run_data_quality_layer():
    """
    Data Quality Layer:
    - Reads Bronze and Silver files
    - Calculates issue counts
    - Exports DataQuality_Report.csv
    """

    print("\n========== DATA QUALITY LAYER STARTED ==========")

    dq_records = []

    # =====================================================
    # READ BRONZE FILES
    # =====================================================

    fi_raw = pd.read_parquet(BRONZE_DIR / "FI_GL_LineItems.parquet")
    co_raw = pd.read_parquet(BRONZE_DIR / "CO_CostCenter_Actuals.parquet")
    pl_raw = pd.read_parquet(BRONZE_DIR / "PC_ProfitCenter_PL.parquet")
    asset_raw = pd.read_parquet(BRONZE_DIR / "AA_AssetRegister.parquet")

    # =====================================================
    # READ SILVER FILES
    # =====================================================

    fi_silver = pd.read_parquet(SILVER_DIR / "FI_GL.parquet")
    co_silver = pd.read_parquet(SILVER_DIR / "CO_Actuals.parquet")
    pl_silver = pd.read_parquet(SILVER_DIR / "ProfitCenter_PL.parquet")
    asset_silver = pd.read_parquet(SILVER_DIR / "Asset.parquet")

    # =====================================================
    # FI_GL DATA QUALITY CHECKS
    # =====================================================

    reversed_count = (
        fi_raw["STBLG"].notna()
        & (fi_raw["STBLG"].astype(str).str.strip() != "")
    ).sum()

    dummy_count = (
        fi_raw["SGTXT"]
        .astype(str)
        .str.upper()
        .str.contains("DUMMY", na=False)
    ).sum()

    amount_null_count = (
        fi_raw[["WRBTR", "DMBTR"]]
        .isna()
        .any(axis=1)
        .sum()
    )

    budat_null_count = (
        fi_raw["BUDAT"]
        .astype(str)
        .eq("00.00.0000")
        .sum()
    )

    bukrs_null_count = fi_raw["BUKRS"].isna().sum()
    kostl_null_count = fi_raw["KOSTL"].isna().sum()
    hkont_null_count = fi_raw["HKONT"].isna().sum()

    add_dq_record(
        dq_records,
        "FI_GL_LineItems",
        "Reversed Entries",
        "Rows where STBLG is not blank. These were excluded from Silver.",
        reversed_count
    )

    add_dq_record(
        dq_records,
        "FI_GL_LineItems",
        "Dummy Postings",
        "Rows where SGTXT contains DUMMY. These were excluded from Silver.",
        dummy_count
    )

    add_dq_record(
        dq_records,
        "FI_GL_LineItems",
        "Null Amounts",
        "Rows where WRBTR or DMBTR is null.",
        amount_null_count
    )

    add_dq_record(
        dq_records,
        "FI_GL_LineItems",
        "Invalid Posting Date",
        "Rows where BUDAT contains SAP null date 00.00.0000.",
        budat_null_count
    )

    add_dq_record(
        dq_records,
        "FI_GL_LineItems",
        "Missing Company Code",
        "Rows where BUKRS is null.",
        bukrs_null_count
    )

    add_dq_record(
        dq_records,
        "FI_GL_LineItems",
        "Missing Cost Center",
        "Rows where KOSTL is null.",
        kostl_null_count
    )

    add_dq_record(
        dq_records,
        "FI_GL_LineItems",
        "Missing GL Account",
        "Rows where HKONT is null.",
        hkont_null_count
    )

    # =====================================================
    # CO DATA QUALITY CHECKS
    # =====================================================

    co_kostl_null_count = co_raw["KOSTL"].isna().sum()

    wkg_cols = [
        col for col in co_raw.columns
        if str(col).startswith("WKG")
    ]

    wkg_null_count = (
        co_raw[wkg_cols]
        .isna()
        .any(axis=1)
        .sum()
    )

    add_dq_record(
        dq_records,
        "CO_CostCenter_Actuals",
        "Missing Cost Center",
        "Rows where KOSTL is null.",
        co_kostl_null_count
    )

    add_dq_record(
        dq_records,
        "CO_CostCenter_Actuals",
        "Null WKG Amounts",
        "Rows where one or more WKG period values are null.",
        wkg_null_count
    )

    add_dq_record(
        dq_records,
        "CO_CostCenter_Actuals",
        "Unpivoted Rows",
        "Rows created after unpivoting WKG001-WKG012.",
        len(co_silver)
    )

    # =====================================================
    # PROFIT CENTER PL DATA QUALITY CHECKS
    # =====================================================

    unknown_pc_count = (
        pl_raw["PRCTR"]
        .astype(str)
        .str.upper()
        .eq("PRCTR_UNKNOWN")
        .sum()
    )

    revenue_null_count = pl_raw["REVENUE"].isna().sum()

    add_dq_record(
        dq_records,
        "PC_ProfitCenter_PL",
        "Unknown Profit Center",
        "Rows where PRCTR is PRCTR_UNKNOWN.",
        unknown_pc_count
    )

    add_dq_record(
        dq_records,
        "PC_ProfitCenter_PL",
        "Null Revenue",
        "Rows where REVENUE is null.",
        revenue_null_count
    )

    # =====================================================
    # ASSET REGISTER DATA QUALITY CHECKS
    # =====================================================

    acq_missing_count = asset_raw["ACQUISITION_COST"].isna().sum()

    negative_nbv_count = (
        asset_silver["Original_NBV"] < 0
    ).sum()

    fully_depreciated_count = (
        asset_silver["IsFullyDepreciated"]
    ).sum()

    add_dq_record(
        dq_records,
        "AA_AssetRegister",
        "Missing Acquisition Cost",
        "Rows where ACQUISITION_COST is null.",
        acq_missing_count
    )

    add_dq_record(
        dq_records,
        "AA_AssetRegister",
        "Negative NBV Fixed",
        "Rows where calculated NBV was negative and floored to 0.",
        negative_nbv_count
    )

    add_dq_record(
        dq_records,
        "AA_AssetRegister",
        "Fully Depreciated Assets",
        "Rows where asset NBV is zero or below.",
        fully_depreciated_count
    )

    # =====================================================
    # PIPELINE SUMMARY CHECKS
    # =====================================================

    add_dq_record(
        dq_records,
        "Pipeline",
        "Bronze FI Rows",
        "Total FI rows received in Bronze.",
        len(fi_raw)
    )

    add_dq_record(
        dq_records,
        "Pipeline",
        "Silver FI Rows",
        "Total FI rows after Silver cleaning.",
        len(fi_silver)
    )

    add_dq_record(
        dq_records,
        "Pipeline",
        "Bronze CO Rows",
        "Total CO rows received in Bronze.",
        len(co_raw)
    )

    add_dq_record(
        dq_records,
        "Pipeline",
        "Silver CO Rows",
        "Total CO rows after WKG unpivot.",
        len(co_silver)
    )

    # =====================================================
    # EXPORT DQ REPORT
    # =====================================================

    # Convert all collected DQ records into a DataFrame first
    dq_df = pd.DataFrame(dq_records)

    # Current pipeline run information
    run_time = pd.Timestamp.now()

    dq_df["SnapshotDate"] = run_time.strftime("%Y-%m-%d")
    dq_df["RunTimestamp"] = run_time.isoformat()

    # Ensure DQ directory exists
    DQ_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DQ_DIR / "DataQuality_Report.csv"

    # Append current run to existing DQ history
    if output_path.exists():

        try:
            existing_df = pd.read_csv(output_path)
        except pd.errors.EmptyDataError:
            existing_df = pd.DataFrame()

        if not existing_df.empty:

            # Support the older CreatedDate column
            if "SnapshotDate" not in existing_df.columns:
                if "CreatedDate" in existing_df.columns:
                    existing_df["SnapshotDate"] = (
                        pd.to_datetime(
                            existing_df["CreatedDate"],
                            errors="coerce"
                        )
                        .dt.strftime("%Y-%m-%d")
                    )
                else:
                    existing_df["SnapshotDate"] = pd.NA

            if "RunTimestamp" not in existing_df.columns:
                if "CreatedDate" in existing_df.columns:
                    existing_df["RunTimestamp"] = existing_df["CreatedDate"]
                else:
                    existing_df["RunTimestamp"] = pd.NA

            history_df = pd.concat(
                [existing_df, dq_df],
                ignore_index=True
            )

        else:
            history_df = dq_df.copy()

    else:
        history_df = dq_df.copy()

    # During development, rerunning on the same day should not
    # create duplicate DQ records. Keep the latest run for that day.
    history_df = history_df.drop_duplicates(
        subset=[
            "SnapshotDate",
            "TableName",
            "IssueType"
        ],
        keep="last"
    )

    history_df.to_csv(
        output_path,
        index=False
    )

    print(f"Data Quality Report saved: {output_path}")
    print(
        f"Current run DQ records: {len(dq_df)} | "
        f"Historical DQ records: {len(history_df)}"
    )

    print("========== DATA QUALITY LAYER COMPLETED ==========\n")

    return history_df