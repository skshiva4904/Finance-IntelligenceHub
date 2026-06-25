import pandas as pd

from src.config import SILVER_DIR, DIMENSIONS_DIR


# =====================================================
# COMMON CLEANING FUNCTIONS
# =====================================================

def normalize_code(value):
    """
    Standardizes business codes coming from Excel.

    Fixes:
    - 400000.0 -> 400000
    - extra spaces
    - lowercase text
    - nan text
    """

    if pd.isna(value):
        return pd.NA

    value = str(value).strip().upper()

    if value in ["", "NAN", "NONE", "NULL"]:
        return pd.NA

    if value.endswith(".0"):
        value = value[:-2]

    return value


def clean_unique_values(series):
    """
    Returns unique cleaned values from a column.
    """

    cleaned = series.apply(normalize_code)
    cleaned = cleaned.dropna()
    cleaned = cleaned.drop_duplicates()
    cleaned = cleaned.sort_values().reset_index(drop=True)

    return cleaned


def add_surrogate_key(df, key_name):
    """
    Adds surrogate key starting from 1.
    """

    df = df.reset_index(drop=True)
    df.insert(0, key_name, range(1, len(df) + 1))

    return df

def add_unknown_row(df, key_col, unknown_values):
    """
    Adds a standard UNKNOWN row with key = 0.
    This prevents fact rows with missing business keys from breaking relationships.
    """

    unknown_row = pd.DataFrame([unknown_values])

    df = pd.concat(
        [unknown_row, df],
        ignore_index=True
    )

    return df

# =====================================================
# BUSINESS MAPPING FUNCTIONS
# =====================================================

def map_gl_group(gl_account):
    """
    Derives GL Account Group based on GL account range.
    """

    try:
        acc = int(gl_account)
    except:
        return "Unclassified"

    if 400000 <= acc < 500000:
        return "Expense"
    elif 500000 <= acc < 600000:
        return "Revenue"
    elif 600000 <= acc < 700000:
        return "COGS"
    elif 700000 <= acc < 800000:
        return "Overheads"
    elif 800000 <= acc < 900000:
        return "Finance / Tax"
    else:
        return "Unclassified"


def map_gl_subcategory(gl_account):
    """
    Derives GL SubCategory.
    """

    try:
        acc = int(gl_account)
    except:
        return "Unclassified"

    if 400000 <= acc < 430000:
        return "Raw Material / Production Cost"
    elif 430000 <= acc < 460000:
        return "Labour / Factory Cost"
    elif 460000 <= acc < 500000:
        return "Other Operating Expense"
    elif 500000 <= acc < 600000:
        return "Sales Revenue"
    elif 600000 <= acc < 700000:
        return "Cost of Goods Sold"
    elif 700000 <= acc < 800000:
        return "Admin / Selling Overhead"
    elif 800000 <= acc < 900000:
        return "Interest / Tax"
    else:
        return "Unclassified"


def map_costcenter_department(kostl):
    """
    Derives department from cost center code.
    """

    try:
        num = int(str(kostl).replace("CC", "").replace("-", ""))
    except:
        return "Unclassified"

    if 1001 <= num <= 1010:
        return "Production"
    elif 1011 <= num <= 1020:
        return "Maintenance"
    elif 1021 <= num <= 1030:
        return "Quality"
    elif 1031 <= num <= 1040:
        return "HR & Admin"
    elif 1041 <= num <= 1050:
        return "Finance"
    else:
        return "Operations"


def map_profitcenter_division(prctr):
    """
    Maps profit center code to business division.
    """

    mapping = {
        "PC-AUTO": "Automotive Division",
        "PC-ELEC": "Electronics Division",
        "PC-CHEM": "Chemical Division",
        "PC-PACK": "Packaging Division",
        "PC-MACH": "Machinery Division",
        "PRCTR_UNKNOWN": "Unattributed"
    }

    return mapping.get(prctr, f"Division {prctr}")


def map_profitcenter_segment(prctr):
    """
    Maps profit center code to segment.
    """

    mapping = {
        "PC-AUTO": "Automotive",
        "PC-ELEC": "Electronics",
        "PC-CHEM": "Chemical",
        "PC-PACK": "Packaging",
        "PC-MACH": "Machinery",
        "PRCTR_UNKNOWN": "Unattributed"
    }

    return mapping.get(prctr, "Unclassified")


def map_plant_city(werks):
    """
    Maps plant code to city.
    """

    mapping = {
        "P001": "Chennai",
        "P002": "Pune",
        "P003": "Ahmedabad",
        "P004": "Bengaluru",
        "P005": "Nagpur"
    }

    return mapping.get(werks, "Unclassified")


def map_plant_region(werks):
    """
    Maps plant code to region.
    """

    mapping = {
        "P001": "South",
        "P002": "West",
        "P003": "West",
        "P004": "South",
        "P005": "Central"
    }

    return mapping.get(werks, "Unclassified")


def map_asset_class(anlkl):
    """
    Maps asset class code to description.
    """

    mapping = {
        "3000": "Machinery",
        "3001": "Heavy Machinery",
        "3100": "Vehicles",
        "3200": "Buildings",
        "3300": "Furniture",
        "3400": "Office Equipment",
        "4000": "IT Equipment",
        "4100": "Computers",
        "4200": "Software / Intangible"
    }

    return mapping.get(anlkl, f"Asset Class {anlkl}")


def map_standard_life(anlkl):
    """
    Maps asset class to useful life range.
    """

    mapping = {
        "3000": "8-15 Years",
        "3001": "10-15 Years",
        "3100": "5-8 Years",
        "3200": "25-40 Years",
        "3300": "5-10 Years",
        "3400": "3-7 Years",
        "4000": "3-5 Years",
        "4100": "3-5 Years",
        "4200": "3-5 Years"
    }

    return mapping.get(anlkl, "Unclassified")


def map_document_type(blart):
    """
    Maps SAP document type.
    """

    mapping = {
        "SA": "G/L Posting",
        "KR": "Vendor Invoice",
        "DR": "Customer Invoice",
        "WA": "Goods Issue",
        "WE": "Goods Receipt"
    }

    return mapping.get(blart, f"Document Type {blart}")


def map_document_category(blart):
    """
    Maps document type category.
    """

    mapping = {
        "SA": "Journal",
        "KR": "Payable",
        "DR": "Receivable",
        "WA": "Inventory",
        "WE": "Inventory"
    }

    return mapping.get(blart, "Original")


# =====================================================
# DIM_DATE
# =====================================================

def create_dim_date(fi_df, pl_df, co_df, asset_df):
    """
    Creates finance-ready fiscal date dimension.

    Indian Fiscal Year:
    Period 1  = Apr
    Period 2  = May
    Period 3  = Jun
    Period 4  = Jul
    Period 5  = Aug
    Period 6  = Sep
    Period 7  = Oct
    Period 8  = Nov
    Period 9  = Dec
    Period 10 = Jan
    Period 11 = Feb
    Period 12 = Mar
    """

    # Fixed calendar range as per requirement document
    start_date = pd.Timestamp("2020-01-01")
    end_date = pd.Timestamp("2026-12-31")

    dim_date = pd.DataFrame({
        "Date": pd.date_range(start=start_date, end=end_date, freq="D")
    })

    # Standard date fields
    dim_date["DateKey"] = dim_date["Date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["CalendarYear"] = dim_date["Date"].dt.year
    dim_date["CalendarMonthNo"] = dim_date["Date"].dt.month
    dim_date["CalendarMonthName"] = dim_date["Date"].dt.strftime("%B")
    dim_date["CalendarQuarter"] = "Q" + dim_date["Date"].dt.quarter.astype(str)

    # Fiscal year: Apr to Mar
    dim_date["FiscalYearNo"] = dim_date["Date"].apply(
        lambda x: x.year + 1 if x.month >= 4 else x.year
    )

    dim_date["FiscalYear"] = "FY" + dim_date["FiscalYearNo"].astype(str)

    # Fiscal period: Apr = 1, Mar = 12
    dim_date["FiscalPeriod"] = dim_date["Date"].apply(
        lambda x: x.month - 3 if x.month >= 4 else x.month + 9
    )

    # Fiscal month name
    fiscal_month_map = {
        1: "Apr",
        2: "May",
        3: "Jun",
        4: "Jul",
        5: "Aug",
        6: "Sep",
        7: "Oct",
        8: "Nov",
        9: "Dec",
        10: "Jan",
        11: "Feb",
        12: "Mar"
    }

    dim_date["FiscalMonthName"] = dim_date["FiscalPeriod"].map(fiscal_month_map)

    # Correct fiscal month-year label
    # Example: FY2026 = Apr-2025 to Mar-2026
    dim_date["FiscalMonthYear"] = (
        dim_date["FiscalMonthName"]
        + "-"
        + dim_date["Date"].dt.year.astype(str)
    )

    # Sort columns for Power BI
    dim_date["FiscalMonthSort"] = dim_date["FiscalPeriod"]

    dim_date["FiscalMonthYearSort"] = (
        dim_date["FiscalYearNo"] * 100
        + dim_date["FiscalPeriod"]
    )

    # Fiscal quarter
    dim_date["FiscalQuarter"] = dim_date["FiscalPeriod"].apply(
        lambda p:
        "Q1" if p in [1, 2, 3]
        else "Q2" if p in [4, 5, 6]
        else "Q3" if p in [7, 8, 9]
        else "Q4"
    )

    dim_date["IsWorkingDay"] = dim_date["Date"].dt.weekday < 5

    return dim_date[
        [
            "DateKey",
            "Date",
            "CalendarYear",
            "CalendarMonthNo",
            "CalendarMonthName",
            "CalendarQuarter",
            "FiscalYearNo",
            "FiscalYear",
            "FiscalQuarter",
            "FiscalPeriod",
            "FiscalMonthName",
            "FiscalMonthSort",
            "FiscalMonthYear",
            "FiscalMonthYearSort",
            "IsWorkingDay"
        ]
    ]


# =====================================================
# DIM_COMPANY
# =====================================================

def create_dim_company(fi_df, pl_df, asset_df):
    """
    Creates Dim_Company.
    Adds UNKNOWN row because CO and PL source tables do not contain BUKRS.
    """

    values = []

    for df in [fi_df, asset_df]:
        if "BUKRS" in df.columns:
            values.append(df["BUKRS"])

    company_codes = clean_unique_values(pd.concat(values, ignore_index=True))

    dim_company = pd.DataFrame({
        "BUKRS": company_codes
    })

    dim_company["CompanyName"] = dim_company["BUKRS"].apply(
        lambda x: f"Manufacturing Company {x}"
    )

    dim_company["Country"] = "India"
    dim_company["LocalCurrency"] = "INR"

    dim_company = add_surrogate_key(dim_company, "CompanyKey")

    unknown_row = pd.DataFrame([{
        "CompanyKey": 0,
        "BUKRS": "UNKNOWN",
        "CompanyName": "Company Not Available in Source",
        "Country": "India",
        "LocalCurrency": "INR"
    }])

    dim_company = pd.concat(
        [unknown_row, dim_company],
        ignore_index=True
    )

    return dim_company
# =====================================================
# DIM_GL_ACCOUNT
# =====================================================

def create_dim_gl_account(fi_df, co_df):
    """
    Creates Dim_GL_Account.
    Combines FI HKONT and CO KSTAR.
    """

    values = []

    if "HKONT" in fi_df.columns:
        values.append(fi_df["HKONT"])

    if "KSTAR" in co_df.columns:
        values.append(co_df["KSTAR"])

    gl_accounts = clean_unique_values(pd.concat(values, ignore_index=True))

    dim_gl = pd.DataFrame({
        "GLAccount": gl_accounts
    })

    dim_gl["AccountDescription"] = dim_gl["GLAccount"].apply(
        lambda x: f"GL Account {x}"
    )

    dim_gl["AccountGroup"] = dim_gl["GLAccount"].apply(map_gl_group)
    dim_gl["SubCategory"] = dim_gl["GLAccount"].apply(map_gl_subcategory)

    dim_gl = add_surrogate_key(dim_gl, "GLKey")

    dim_gl = add_unknown_row(
        dim_gl,
        "GLKey",
        {
            "GLKey": 0,
            "GLAccount": "UNKNOWN",
            "AccountDescription": "Unknown GL Account",
            "AccountGroup": "Unclassified",
            "SubCategory": "Unclassified"
        }
    )

    return dim_gl

# =====================================================
# DIM_COST_CENTER
# =====================================================

def create_dim_costcenter(fi_df, co_df):
    """
    Creates Dim_CostCenter.
    """

    values = []

    if "KOSTL" in fi_df.columns:
        values.append(fi_df["KOSTL"])

    if "KOSTL" in co_df.columns:
        values.append(co_df["KOSTL"])

    cost_centers = clean_unique_values(pd.concat(values, ignore_index=True))

    dim_cc = pd.DataFrame({
        "KOSTL": cost_centers
    })

    dim_cc["CostCenterName"] = dim_cc["KOSTL"].apply(
        lambda x: f"Cost Center {x}"
    )

    dim_cc["Department"] = dim_cc["KOSTL"].apply(map_costcenter_department)

    dim_cc["ResponsibleManagerEmail"] = dim_cc["KOSTL"].apply(
        lambda x: f"{map_costcenter_department(x).lower().replace(' ', '_').replace('&', 'and')}@company.com"
    )

    dim_cc = add_surrogate_key(dim_cc, "CostCenterKey")

    dim_cc = add_unknown_row(
        dim_cc,
        "CostCenterKey",
        {
            "CostCenterKey": 0,
            "KOSTL": "UNKNOWN",
            "CostCenterName": "Unknown Cost Center",
            "Department": "Unclassified",
            "ResponsibleManagerEmail": "not_assigned@company.com"
        }
    )

    return dim_cc

# =====================================================
# DIM_PROFIT_CENTER
# =====================================================

def create_dim_profitcenter(fi_df, co_df, pl_df, asset_df):
    """
    Creates Dim_ProfitCenter.
    """

    values = []

    for df in [fi_df, co_df, pl_df, asset_df]:
        if "PRCTR" in df.columns:
            values.append(df["PRCTR"])

    profit_centers = clean_unique_values(pd.concat(values, ignore_index=True))

    dim_pc = pd.DataFrame({
        "PRCTR": profit_centers
    })

    dim_pc["DivisionName"] = dim_pc["PRCTR"].apply(map_profitcenter_division)
    dim_pc["Segment"] = dim_pc["PRCTR"].apply(map_profitcenter_segment)

    dim_pc["BusinessArea"] = dim_pc["Segment"].apply(
        lambda x: "Unattributed" if x == "Unattributed" else "Manufacturing"
    )

    dim_pc = add_surrogate_key(dim_pc, "ProfitCenterKey")

    dim_pc = add_unknown_row(
        dim_pc,
        "ProfitCenterKey",
        {
            "ProfitCenterKey": 0,
            "PRCTR": "UNKNOWN",
            "DivisionName": "Unknown Profit Center",
            "Segment": "Unclassified",
            "BusinessArea": "Unclassified"
        }
    )

    return dim_pc

# =====================================================
# DIM_PLANT
# =====================================================

def create_dim_plant(fi_df, co_df, pl_df, asset_df):
    """
    Creates Dim_Plant.
    """

    values = []

    for df in [fi_df, co_df, pl_df, asset_df]:
        if "WERKS" in df.columns:
            values.append(df["WERKS"])

    plants = clean_unique_values(pd.concat(values, ignore_index=True))

    dim_plant = pd.DataFrame({
        "WERKS": plants
    })

    dim_plant["PlantName"] = dim_plant["WERKS"].apply(
        lambda x: f"Plant {x}"
    )

    dim_plant["City"] = dim_plant["WERKS"].apply(map_plant_city)
    dim_plant["Region"] = dim_plant["WERKS"].apply(map_plant_region)
    dim_plant["Country"] = "India"

    dim_plant = add_surrogate_key(dim_plant, "PlantKey")

    dim_plant = add_unknown_row(
        dim_plant,
        "PlantKey",
        {
            "PlantKey": 0,
            "WERKS": "UNKNOWN",
            "PlantName": "Unknown Plant",
            "City": "Unclassified",
            "Region": "Unclassified",
            "Country": "India"
        }
    )

    return dim_plant

# =====================================================
# DIM_DOCUMENT_TYPE
# =====================================================

def create_dim_document_type(fi_df):
    """
    Creates Dim_DocumentType.
    """

    if "BLART" not in fi_df.columns:
        return pd.DataFrame(
            columns=["DocumentTypeKey", "BLART", "Description", "Category"]
        )

    doc_types = clean_unique_values(fi_df["BLART"])

    dim_doc = pd.DataFrame({
        "BLART": doc_types
    })

    dim_doc["Description"] = dim_doc["BLART"].apply(map_document_type)
    dim_doc["Category"] = dim_doc["BLART"].apply(map_document_category)

    dim_doc = add_surrogate_key(dim_doc, "DocumentTypeKey")

    dim_doc = add_unknown_row(
        dim_doc,
        "DocumentTypeKey",
        {
            "DocumentTypeKey": 0,
            "BLART": "UNKNOWN",
            "Description": "Unknown Document Type",
            "Category": "Unknown"
        }
    )

    return dim_doc

# =====================================================
# DIM_ASSET_CLASS
# =====================================================

def create_dim_asset_class(asset_df):
    """
    Creates Dim_AssetClass.
    """

    if "ANLKL" not in asset_df.columns:
        return pd.DataFrame(
            columns=[
                "AssetClassKey",
                "ANLKL",
                "AssetClassDescription",
                "StandardUsefulLifeRange",
                "StandardDepKey"
            ]
        )

    asset_classes = clean_unique_values(asset_df["ANLKL"])

    dim_asset = pd.DataFrame({
        "ANLKL": asset_classes
    })

    dim_asset["AssetClassDescription"] = dim_asset["ANLKL"].apply(map_asset_class)
    dim_asset["StandardUsefulLifeRange"] = dim_asset["ANLKL"].apply(map_standard_life)
    dim_asset["StandardDepKey"] = "LINR"

    dim_asset = add_surrogate_key(dim_asset, "AssetClassKey")

    dim_asset = add_unknown_row(
        dim_asset,
        "AssetClassKey",
        {
            "AssetClassKey": 0,
            "ANLKL": "UNKNOWN",
            "AssetClassDescription": "Unknown Asset Class",
            "StandardUsefulLifeRange": "Unclassified",
            "StandardDepKey": "Unclassified"
        }
    )

    return dim_asset

# =====================================================
# RUN GOLD DIMENSIONS
# =====================================================

def run_gold_dimensions_layer():
    """
    Creates all 8 Gold dimension tables.
    """

    print("\n========== GOLD DIMENSIONS STARTED ==========")

    fi_df = pd.read_parquet(SILVER_DIR / "FI_GL.parquet")
    co_df = pd.read_parquet(SILVER_DIR / "CO_Actuals.parquet")
    pl_df = pd.read_parquet(SILVER_DIR / "ProfitCenter_PL.parquet")
    asset_df = pd.read_parquet(SILVER_DIR / "Asset.parquet")

    dimensions = {
        "Dim_Date": create_dim_date(fi_df, pl_df, co_df, asset_df),
        "Dim_Company": create_dim_company(fi_df, pl_df, asset_df),
        "Dim_GL_Account": create_dim_gl_account(fi_df, co_df),
        "Dim_CostCenter": create_dim_costcenter(fi_df, co_df),
        "Dim_ProfitCenter": create_dim_profitcenter(fi_df, co_df, pl_df, asset_df),
        "Dim_Plant": create_dim_plant(fi_df, co_df, pl_df, asset_df),
        "Dim_DocumentType": create_dim_document_type(fi_df),
        "Dim_AssetClass": create_dim_asset_class(asset_df)
    }

    for name, df in dimensions.items():
        output_path = DIMENSIONS_DIR / f"{name}.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved {name}: {len(df):,} rows")

    print("========== GOLD DIMENSIONS COMPLETED ==========\n")

    return dimensions