# Manufacturing Finance Intelligence Hub

An end-to-end **Python data pipeline and Power BI dashboard** for analysing manufacturing finance data.

The project processes SAP-style Excel extracts, applies data cleaning and validation, creates a star-schema model, and produces an interactive Power BI report for financial analysis.

## Project Objective

The main goal is to replace manual Excel-based finance reporting with an automated analytical solution covering:

* Revenue and profitability
* Profit-centre performance
* Cost-centre spending
* General Ledger transactions
* Fixed assets
* Data-quality monitoring

## Technology Stack

* Python
* Pandas
* PyArrow
* OpenPyXL
* Power BI
* DAX
* Git and GitHub

## Pipeline Architecture

```text
Raw Excel Data
      ↓
Bronze Layer
      ↓
Silver Layer
      ↓
Data Quality Checks
      ↓
Gold Fact and Dimension Tables
      ↓
Power BI Dashboard
```

### Bronze Layer

Stores the original Excel sheets as raw Parquet files.

### Silver Layer

Cleans and standardises the source data.

### Gold Layer

Creates fact and dimension tables designed for Power BI reporting.

## Source Tables

The pipeline expects one Excel workbook containing four sheets:

* `FI_GL_LineItems` — General Ledger transactions
* `CO_CostCenter_Actuals` — Cost-centre monthly actuals
* `PC_ProfitCenter_PL` — Profit-centre P&L and plan data
* `AA_AssetRegister` — Fixed-asset information

## Main Data Transformations

The Python pipeline:

* Removes reversed GL entries
* Removes dummy or test postings
* Fixes invalid SAP dates
* Standardises business codes
* Uses local-currency amounts for financial reporting
* Unpivots `WKG001` to `WKG012` into monthly cost records
* Applies debit and credit sign logic
* Flags non-INR cost-centre records
* Handles unknown profit centres
* Replaces missing revenue values
* Flags missing acquisition costs
* Floors negative Net Book Value to zero
* Creates an April-to-March fiscal calendar
* Generates a historical Data Quality report

## Power BI Data Model

The report uses a star schema with four fact tables:

* `Fact_GL_Postings`
* `Fact_CostCenter_Actuals`
* `Fact_ProfitCenter_PL`
* `Fact_Asset_Balances`

And eight dimensions:

* `Dim_Date`
* `Dim_Company`
* `Dim_GL_Account`
* `Dim_CostCenter`
* `Dim_ProfitCenter`
* `Dim_Plant`
* `Dim_DocumentType`
* `Dim_AssetClass`

Relationships use single-direction filtering from dimensions to facts.

## Power BI Report Pages

The final report contains six pages:

1. **Executive Overview**
   Revenue, EBITDA, PAT, margins, profitability waterfall, and business trends.

2. **P&L Detail**
   Actual, Plan, Variance, monthly P&L matrix, and profit-centre analysis.

3. **Cost Centre Performance**
   Cost-centre spending, monthly cost trends, cost-element analysis, and plant/division comparisons.

4. **GL Line Item Detail**
   Transaction-level accounting details for audit and drill-through analysis.

5. **Fixed Asset Analytics**
   Gross Block, accumulated depreciation, Net Book Value, and asset-level analysis.

6. **Data Quality Monitoring**
   Reversed entries, dummy postings, null values, unknown profit centres, and issue trends.

The Power BI file is available at:

```text
Report/Manufacturing_Finance_Intelligence_Hub.pbix
```

## Project Structure

```text
Finance-IntelligenceHub/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── src/
│   ├── config.py
│   ├── bronze.py
│   ├── silver.py
│   ├── gold_dimensions.py
│   ├── gold_facts.py
│   └── validate.py
│
└── Report/
    └── Manufacturing_Finance_Intelligence_Hub.pbix
```

## How to Run

Clone the repository:

```bash
git clone https://github.com/skshiva4904/Finance-IntelligenceHub.git
cd Finance-IntelligenceHub
```

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Place the source workbook at:

```text
Data/MFG_Finance_Dataset.xlsx
```

Run the pipeline:

```bash
python main.py
```

The pipeline generates:

```text
Bronze/
Silver/
Gold/
dq/
```

Open the Power BI report and refresh the data after the Gold files are created.

## Dataset Note

The original dataset is not included in this repository.

A compatible Excel workbook with the four required sheets is needed to run the pipeline.

Raw data and generated pipeline outputs are excluded from GitHub.

## Current Limitations

* A genuine Cost Centre Plan source was not available.
* Cost-centre INR totals exclude non-INR records until currency conversion rates are added.
* Company filtering is limited for source tables without a reliable Company Code.
* Data-quality trends require multiple pipeline runs over time.

## Author

**Shivratna Dnyaneshwar Kedar**

Skills demonstrated:

* Python Data Engineering
* ETL Pipeline Development
* Data Cleaning
* Power BI
* DAX
* Star Schema Modelling
* Financial Analytics
* Data Quality Analysis

GitHub: `https://github.com/skshiva4904`
