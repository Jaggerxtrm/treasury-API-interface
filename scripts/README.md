# Utility Scripts

Utility scripts for analysis, validation, and investigation of the Treasury API Interface.

---

## Scripts

### verify_db.py

**Purpose:** Database inspection and verification tool

**Description:**
Quick utility to inspect the DuckDB database structure, list tables, view schemas, and sample data. Useful for debugging and understanding the database contents.

**Usage:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run database verification
python scripts/verify_db.py
```

**What It Shows:**

1. **Database Connection**
   - Confirms database file exists
   - Establishes connection to `database/treasury_data.duckdb`

2. **Table List**
   - Lists all tables in the database
   - Expected tables: `fiscal_daily_metrics`, `fed_liquidity_daily`, etc.

3. **For Each Table:**
   - Row count
   - Complete schema (column names and types)
   - Sample data (last 3 rows)

**Output Example:**
```
🔌 Connected to database/treasury_data.duckdb
📊 Tables found: ['fiscal_daily_metrics', 'fed_liquidity_daily', ...]

📋 Table: fiscal_daily_metrics
   Rows: 977
   Schema:
     - record_date (DATE)
     - Total_Receipts (DOUBLE)
     - MA20_Net_Impulse (DOUBLE)
     - GDP_Used (BIGINT)
     - Household_Share_Pct (DOUBLE)
     ...
   Sample Data (Last 3 rows):
   [Table data shown]
```

**Use Cases:**
- Verify database structure after schema changes
- Check if new columns were added successfully
- Quick inspection of latest data
- Debugging data import issues
- Understanding table relationships

---

### investigation_analysis.py

**Purpose:** Automated validation script used during the November 2025 investigation

**Description:**
This script performs comprehensive validation of fiscal and liquidity calculations against the theoretical methodology from "Fiscal Week #44" report. It was used to identify discrepancies and validate fixes during the investigation phase.

**Usage:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run investigation analysis
python scripts/investigation_analysis.py
```

**What It Checks:**

1. **GDP Normalization Unit Verification**
   - Validates the formula: `(MA20_Net_Impulse * 252 * 1_000_000) / GDP * 100`
   - Checks unit conversions (Millions → dollars)
   - Reverse-calculates GDP from reported %GDP values
   - **Finding:** Identified that code uses $31.7T (FRED) vs $29T (fallback constant)

2. **Household Share Calculation**
   - Validates formula: `household_spending / total_spending * 100`
   - Checks bounds: [0, 100]%
   - Tests edge case: negative net_impulse days (fiscal drag)
   - **Finding:** Formula was correct but not persisted to database

3. **4-Week Cumulative Reconciliation**
   - Compares sliding 20-BD window vs block 4-week aggregation
   - Validates business day alignment
   - **Finding:** Both methods agreed, implementation correct

4. **Net Liquidity Formula**
   - Validates: `Fed_Total_Assets - RRP_Balance_M - TGA_Balance`
   - Checks all components in Millions
   - **Finding:** Formula correct but 33% NULL on weekends

5. **Weekend/Holiday Imputation**
   - Checks for NULL values on non-trading days
   - Validates need for forward-fill
   - **Finding:** Identified need for RRP/TGA imputation

6. **YoY Calculation Alignment**
   - Validates `shift(252)` for business day alignment
   - Checks year-over-year comparisons
   - **Finding:** Implementation correct

7. **Fiscal Week Alignment**
   - Validates Wednesday-to-Wednesday (W-WED) alignment
   - Checks weekly aggregation logic
   - **Finding:** Implementation correct

**Output:**
```
=== INVESTIGATION ANALYSIS ===
Database: database/treasury_data.duckdb

[1/7] GDP Normalization Check
  Latest MA20_Net_Impulse: 12,172.45 M
  Reported Annual_Impulse_Pct_GDP: 9.68%
  Reverse-calculated GDP: $31.70 T
  ✅ Using FRED-estimated GDP ($31.7T), not fallback ($29T)

[2/7] Household Share Calculation
  Latest record (2025-11-24):
    Household_Spending: 7,121 M
    Total_Spending: 16,788 M
    household_share (display): 42.42%
  ⚠️  household_share NOT in fiscal_daily_metrics table
  ✅ Formula correct: household / total_spending

[3/7] 4-Week Cumulative Reconciliation
  Latest 4W_Cum_Net: 243,449 M
  Sliding 20-BD sum: 243,449 M
  Difference: 0 M
  ✅ Perfect alignment

[4/7] Net Liquidity Formula
  Latest record:
    Fed_Total_Assets: 6,940,742 M
    RRP_Balance_M: 1,278,536 M
    TGA_Balance: 1,500 M
    Net_Liquidity: 5,660,706 M
  Calculated: 5,660,706 M
  Difference: 0 M
  ✅ Formula correct

[5/7] Weekend/Holiday Coverage
  Total fed_liquidity records: 1,428
  Records with NULL Net_Liquidity: 474 (33.2%)
  ⚠️  Weekend/holiday data missing
  💡 Recommend: Forward-fill RRP/TGA

[6/7] YoY Alignment
  ✅ Using shift(252) for business day alignment

[7/7] Fiscal Week Alignment
  ✅ Wednesday-to-Wednesday (W-WED) alignment confirmed

=== FINDINGS SUMMARY ===
Issues Found: 2
  1. GDP value ($31.7T) not documented in output
  2. 33% of Net_Liquidity records are NULL (weekends)
  3. household_share calculated but not persisted

Verified Correct: 5
  1. GDP normalization formula
  2. Household share formula
  3. 4-week cumulative calculation
  4. Net Liquidity formula
  5. YoY and fiscal week alignment

Recommendation: Apply HIGH priority fixes from investigation
```

**Data Sources:**
- `database/treasury_data.duckdb`
  - Tables: `fiscal_daily_metrics`, `fed_liquidity_daily`

**Requirements:**
- DuckDB connection
- pandas
- numpy

**Exit Codes:**
- `0` - Analysis completed successfully
- `1` - Database connection error or missing data

---

## Adding New Scripts

When adding new utility scripts:

1. **Document the script:**
   ```python
   """
   Script Name

   Purpose: Brief description

   Usage:
       python scripts/script_name.py [args]

   Output:
       Description of what the script produces
   """
   ```

2. **Update this README:**
   - Add script to the "Scripts" section
   - Document usage, purpose, and output
   - Note any dependencies

3. **Make it executable:**
   ```bash
   chmod +x scripts/script_name.py
   ```

4. **Add shebang if needed:**
   ```python
   #!/usr/bin/env python3
   ```

---

## Best Practices

### Script Structure

```python
#!/usr/bin/env python3
"""
Script description
"""

import sys
import duckdb
import pandas as pd

def main():
    """Main function"""
    try:
        # Script logic
        print("✅ Success")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Database Connections

Use DuckDB read-only mode for analysis scripts:
```python
conn = duckdb.connect('database/treasury_data.duckdb', read_only=True)
```

### Output Formatting

Use consistent symbols:
- `✅` - Success/verification passed
- `❌` - Error/critical issue
- `⚠️` - Warning/non-critical issue
- `💡` - Recommendation/suggestion
- `📊` - Data/statistics

---

## Related Documentation

- **[../docs/investigation/](../docs/investigation/)** - Investigation documentation
- **[../monitoring/README.md](../monitoring/README.md)** - Monitoring tools
- **[../docs/investigation/FINAL_STATUS_REPORT.md](../FINAL_STATUS_REPORT.md)** - Investigation results

---

## Common Tasks

### Validate Calculations

```bash
# Run investigation analysis
python scripts/investigation_analysis.py

# Run data quality checks
python monitoring/data_quality_checks.py
```

### Query Database Directly

```bash
# Interactive DuckDB session
duckdb database/treasury_data.duckdb

# Query example
SELECT
    record_date,
    MA20_Net_Impulse,
    Annual_Impulse_Pct_GDP,
    GDP_Used
FROM fiscal_daily_metrics
ORDER BY record_date DESC
LIMIT 10;
```

### Export Analysis Results

```python
# Example: Export validation results to CSV
import duckdb
import pandas as pd

conn = duckdb.connect('database/treasury_data.duckdb', read_only=True)

# Query data
df = conn.execute("""
    SELECT
        record_date,
        MA20_Net_Impulse,
        (MA20_Net_Impulse * 252 * 1000000.0 * 100) / GDP_Used as calculated_pct,
        Annual_Impulse_Pct_GDP as reported_pct,
        ABS(Annual_Impulse_Pct_GDP - (MA20_Net_Impulse * 252 * 1000000.0 * 100) / GDP_Used) as diff
    FROM fiscal_daily_metrics
    WHERE GDP_Used IS NOT NULL
    ORDER BY record_date DESC
""").df()

# Save to CSV
df.to_csv('outputs/validation_results.csv', index=False)
print(f"✅ Exported {len(df)} validation results to outputs/validation_results.csv")
```

---

**Last Updated:** November 2025
**Status:** ✅ Operational
