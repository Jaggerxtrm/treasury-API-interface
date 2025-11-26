# Database Migration: CSV to DuckDB

## Overview
This document details the migration of the Treasury API Interface storage from flat CSV files to a local DuckDB time-series database.

## Architecture
- **Database Engine**: DuckDB (Embedded OLAP database).
- **Storage Location**: `database/treasury_data.duckdb`.
- **Access Pattern**: In-process via Python `duckdb` library.
- **Schema Management**: Implicit schema inference from Pandas DataFrames with automatic table creation.

## Components

### 1. Database Manager (`utils/db_manager.py`)
A shared utility class `TimeSeriesDB` that handles:
- Connection management.
- Schema inference (`initialize_table_from_df`).
- Upsert logic (`upsert_data`):
    - Uses a `DELETE ... WHERE key IN (batch)` + `INSERT` strategy to handle updates and prevent duplicates.
    - Supports batch processing.

### 2. POC Script (`fiscal/fiscal_analysis_poc.py`)
A modified version of the fiscal analysis engine that:
- Fetches data from Treasury API.
- Processes daily and weekly metrics.
- **Saves to DuckDB**:
    - `fiscal_daily_metrics`: Daily transaction data.
    - `fiscal_weekly_metrics`: Weekly aggregated data.
- **Data Transformations**:
    - Converts Pandas `Period` objects to strings (DuckDB compatibility).
    - Renames index columns to explicit keys (`record_date`, `week_start_date`).

## Schema

### Table: `fiscal_daily_metrics`
- **Primary Key**: `record_date` (Date/Timestamp)
- **Metrics**: `Total_Spending`, `Total_Taxes`, `Net_Impulse`, `TGA_Balance`, etc.
- **Categories**: `Cat_Defense`, `Cat_Medicare`, etc.

### Table: `fiscal_weekly_metrics`
- **Primary Key**: `week_start_date` (Date/Timestamp)
- **Metrics**: Weekly aggregates of spending, taxes, and net impulse.
- **Metadata**: `week_id` (String identifier).

## Migration Strategy
1. **Pilot**: Use `fiscal_analysis_poc.py` to validate data storage.
2. **Integration**: Update other scripts (`fed_liquidity.py`, etc.) to use `TimeSeriesDB`.
3. **Backfill**: (Optional) Load existing CSVs into the database using a one-time script.
4. **Cutover**: Switch default output to DB, keeping CSV export as an optional flag (`--export-csv`).

## Usage
```python
from utils.db_manager import TimeSeriesDB

# Initialize
db = TimeSeriesDB("database/treasury_data.duckdb")

# Save Data
db.upsert_data(df, "my_table", key_col="date")

# Query Data
df_result = db.query("SELECT * FROM my_table WHERE date > '2023-01-01'")
```

## Dependencies
- `duckdb`
- `pandas`
