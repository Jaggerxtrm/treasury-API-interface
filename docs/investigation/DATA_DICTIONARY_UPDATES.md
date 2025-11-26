# Data Dictionary Updates - New Columns

**Date:** 2025-11-26
**Changes:** Added 5 new columns across 2 tables

---

## fiscal_daily_metrics

### GDP_Used
- **Type:** BIGINT
- **Units:** USD (not Millions)
- **Description:** The actual nominal GDP value used in all %GDP calculations for this record
- **Source:** FRED API (series: GDP), with optional QoQ growth extrapolation if data >90 days old
- **Usage:** Enables reverse-calculation and validation of Annual_Impulse_Pct_GDP and Weekly_Impulse_Pct_GDP
- **Example:** `31700000000000` ($31.7 trillion)
- **Notes:**
  - May differ from NOMINAL_GDP_FALLBACK constant ($29T) if GDP is estimated
  - Check report header for "ESTIMATED" vs "ACTUAL" status
  - Same GDP value used for all records generated in same run

### Household_Share_Pct
- **Type:** DOUBLE
- **Units:** Percentage (0-100)
- **Description:** Household-directed spending as percentage of total federal spending
- **Formula:** `(Household_Spending / Total_Spending) * 100`
- **Categories included:** SSA_Benefits, Medicare, VA_Benefits, Unemployment, Tax_Refunds_Individual, SNAP_Food, Education, Housing
- **Valid range:** [0.0, 100.0]
- **Example:** `42.42` (42.42% of spending was household-directed)
- **Notes:**
  - Remains valid even when Net_Impulse is negative (fiscal drag days)
  - Higher values on SS payment days (2nd, 3rd, 4th Wednesday) and month-end (Medicare)
  - Does NOT use Net_Impulse as denominator (that could produce negative values)

---

## fed_liquidity_daily

### RRP_Imputed
- **Type:** BOOLEAN
- **Description:** Flag indicating RRP_Balance was forward-filled from previous trading day
- **Values:**
  - `TRUE`: RRP data was not published for this date (weekend/holiday), value carried forward from last trading day
  - `FALSE`: RRP data was published by Fed for this date (actual observation)
- **Usage:** Filter out imputed days for certain analyses or weight differently
- **Typical pattern:** TRUE on Saturdays, Sundays, and federal holidays
- **Example query:**
  ```sql
  -- Get only actual (non-imputed) RRP data
  SELECT * FROM fed_liquidity_daily WHERE RRP_Imputed = FALSE;

  -- Count imputation rate
  SELECT
    SUM(CASE WHEN RRP_Imputed THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as imputation_pct
  FROM fed_liquidity_daily;
  ```

### TGA_Imputed
- **Type:** BOOLEAN
- **Description:** Flag indicating TGA_Balance was forward-filled from previous day
- **Values:**
  - `TRUE`: TGA data was missing for this date, value carried forward
  - `FALSE`: TGA data was available (actual observation)
- **Usage:** Similar to RRP_Imputed
- **Notes:** Less common than RRP_Imputed (TGA published more frequently)
- **Typical rate:** <1% of records

### Net_Liq_Imputed
- **Type:** BOOLEAN
- **Description:** Flag indicating Net_Liquidity was calculated using imputed RRP and/or TGA values
- **Values:**
  - `TRUE`: Net_Liquidity = Fed_Total_Assets - (imputed RRP) - (actual or imputed TGA)
  - `FALSE`: Net_Liquidity calculated from all actual (non-imputed) components
- **Formula:** `Net_Liq_Imputed = RRP_Imputed OR TGA_Imputed`
- **Usage:** Critical for liquidity analysis - filter or flag imputed values in reports
- **Typical pattern:** TRUE on weekends/holidays (same as RRP_Imputed)
- **Example query:**
  ```sql
  -- Weekly liquidity change using only actual data
  SELECT
    DATE_TRUNC('week', record_date) as week,
    AVG(Net_Liquidity) as avg_net_liq
  FROM fed_liquidity_daily
  WHERE Net_Liq_Imputed = FALSE
  GROUP BY week;
  ```

---

## Usage Examples

### Validating %GDP Calculations
```sql
-- Verify Annual_Impulse_Pct_GDP calculation
SELECT
  record_date,
  MA20_Net_Impulse,
  Annual_Impulse_Pct_GDP,
  GDP_Used,
  -- Reverse-calculate: should match Annual_Impulse_Pct_GDP
  (MA20_Net_Impulse * 252 * 1000000.0 * 100) / GDP_Used as calculated_pct,
  -- Check difference
  ABS(Annual_Impulse_Pct_GDP - (MA20_Net_Impulse * 252 * 1000000.0 * 100) / GDP_Used) as diff
FROM fiscal_daily_metrics
WHERE record_date >= '2025-11-01'
ORDER BY diff DESC
LIMIT 10;
-- Expected: diff < 0.01 for all rows
```

### Household Share Trends
```sql
-- Monthly average household share
SELECT
  DATE_TRUNC('month', record_date) as month,
  AVG(Household_Share_Pct) as avg_hh_share,
  MIN(Household_Share_Pct) as min_hh_share,
  MAX(Household_Share_Pct) as max_hh_share
FROM fiscal_daily_metrics
WHERE record_date >= '2024-01-01'
GROUP BY month
ORDER BY month;
```

### Imputation Rate Monitoring
```sql
-- Weekly imputation statistics
SELECT
  DATE_TRUNC('week', record_date) as week,
  COUNT(*) as total_days,
  SUM(CASE WHEN RRP_Imputed THEN 1 ELSE 0 END) as rrp_imputed_days,
  SUM(CASE WHEN RRP_Imputed THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as rrp_imputed_pct
FROM fed_liquidity_daily
WHERE record_date >= '2025-01-01'
GROUP BY week
ORDER BY week DESC;
-- Expected: ~28-29% (weekends) in normal weeks, higher during holiday weeks
```

### Data Quality Alerts
```sql
-- Alert if household share outside valid range
SELECT
  record_date,
  Household_Share_Pct,
  Household_Spending,
  Total_Spending
FROM fiscal_daily_metrics
WHERE Household_Share_Pct < 0 OR Household_Share_Pct > 100
ORDER BY record_date DESC;
-- Expected: 0 rows (validation should prevent this)

-- Alert if imputation rate too high (data source issue)
SELECT
  COUNT(*) as recent_days,
  SUM(CASE WHEN RRP_Imputed THEN 1 ELSE 0 END) as imputed_days,
  SUM(CASE WHEN RRP_Imputed THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as imputed_pct
FROM (
  SELECT * FROM fed_liquidity_daily
  ORDER BY record_date DESC
  LIMIT 30
);
-- Alert if imputed_pct > 40% (suggests data source down for extended period)
```

---

## Migration Notes

### Backward Compatibility
- **fiscal_daily_metrics:** New columns added, no existing columns modified ✓
- **fed_liquidity_daily:** New columns added, no existing columns modified ✓
- All existing queries continue to work without modification

### Column Defaults
- **GDP_Used:** Populated for all new records, NULL for historical records before 2025-11-26
- **Household_Share_Pct:** Populated for all new records, NULL for historical records
- **RRP_Imputed, TGA_Imputed, Net_Liq_Imputed:** Populated for all new records, NULL for historical

### Backfill Recommendation
To populate new columns for historical records:
```bash
# Re-run fiscal_analysis.py with full date range
python fiscal/fiscal_analysis.py --start-date 2022-01-01

# Re-run fed_liquidity.py with full date range
python fed/fed_liquidity.py --start-date 2022-01-01
```

---

## Validation Queries

Run these after backfill to verify data integrity:

```sql
-- Check GDP_Used consistency (should be constant within each run)
SELECT
  DATE(record_date) as date,
  COUNT(DISTINCT GDP_Used) as distinct_gdp_values
FROM fiscal_daily_metrics
WHERE GDP_Used IS NOT NULL
GROUP BY DATE(record_date)
HAVING COUNT(DISTINCT GDP_Used) > 1;
-- Expected: 0 rows (all records from same day should use same GDP)

-- Check Household_Share_Pct bounds
SELECT
  MIN(Household_Share_Pct) as min_share,
  MAX(Household_Share_Pct) as max_share,
  AVG(Household_Share_Pct) as avg_share
FROM fiscal_daily_metrics
WHERE Household_Share_Pct IS NOT NULL;
-- Expected: min >= 0, max <= 100

-- Check imputation flag consistency
SELECT COUNT(*) as inconsistent_rows
FROM fed_liquidity_daily
WHERE (RRP_Balance IS NULL AND RRP_Imputed = FALSE)
   OR (RRP_Balance IS NOT NULL AND RRP_Imputed = TRUE);
-- Expected: 0 rows
```

---

**Last Updated:** 2025-11-26
**Related Documents:** INVESTIGATION_SUMMARY.md, BUG_HUNT_REPORT.md
