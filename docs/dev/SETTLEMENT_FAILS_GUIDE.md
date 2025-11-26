# Settlement Fails Data Integration Guide

## Overview

Settlement fails data tracks failures to deliver or receive securities by primary dealers. High settlement fails indicate:
- **Market stress** - liquidity constraints in Treasury markets
- **Collateral scarcity** - insufficient securities available for settlement
- **Operational issues** - problems in the settlement system

This data contributes **40% of the LCI Plumbing component** (25% of overall LCI).

---

## Data Sources

### Option 1: NY Fed Primary Dealer Statistics (Manual Download) ✅ **RECOMMENDED**

**What it is:** Weekly reports published by the NY Fed every Thursday covering the prior week.

**Steps:**
1. Visit: https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics
2. Look for "Settlement Fails" section or download historical data
3. Download the CSV file
4. Save to: `outputs/fed/nyfed_settlement_fails.csv`

**Data Format:** Weekly cumulative fails across security types:
- Treasury Securities
- Agency Securities
- Mortgage-Backed Securities (MBS)
- Corporate Securities

### Option 2: Office of Financial Research (OFR) API 🔐 Requires Auth

**What it is:** OFR provides NY Fed Primary Dealer data through their API.

**Steps:**
1. Register at: https://data.financialresearch.gov/
2. Get API key
3. Access dataset `nypd` (NY Fed Primary Dealer)
4. Filter for settlement fails series

**Note:** Requires authentication token.

### Option 3: FRED API 🔍 Check Availability

Search for settlement fails series on FRED:
- https://fred.stlouisfed.org/
- Search: "settlement fails" or "primary dealer fails"
- If series exists, add to `config.py` FRED_SERIES_MAP

---

## CSV Format Requirements

### Simple Format (Single Column)
```csv
date,totalFails
2024-11-07,1250.5
2024-11-14,1180.3
2024-11-21,1420.8
```

### Detailed Format (By Category)
```csv
date,treasury_fails,agency_fails,mbs_fails,corporate_fails
2024-11-07,850.2,200.3,180.0,20.0
2024-11-14,780.5,190.8,180.5,29.0
2024-11-21,920.1,280.2,200.3,20.2
```

**Important:**
- Date column must be named `date` and in YYYY-MM-DD format
- Fails amounts are in **millions of dollars**
- Weekly frequency (data published Thursdays)
- Script auto-calculates `totalFails` if separate categories provided

---

## Implementation Status

✅ **API Client Method Added:** `NYFedClient.fetch_settlement_fails()`
- Located in: `fed/utils/api_client.py:272-356`
- Tries multiple endpoint patterns
- Falls back to manual CSV loading

✅ **Standalone Fetcher Created:** `fed/nyfed_settlement_fails.py`
- Attempts API fetch
- Falls back to manual CSV
- Generates comprehensive report
- Calculates moving averages and Z-scores

✅ **LCI Integration Ready:** `fed/liquidity_composite_index.py`
- Automatically loads from `outputs/fed/nyfed_settlement_fails.csv`
- Handles missing data gracefully
- Uses repo stress as fallback

---

## How to Use

### 1. Try API Fetch (Will likely fail - endpoints not fully documented)
```bash
source venv/bin/activate
python fed/nyfed_settlement_fails.py
```

### 2. Manual Data Entry (If API fails)

**Option A: Use Template**
```bash
# Copy template and fill with real data
cp settlement_fails_template.csv outputs/fed/nyfed_settlement_fails.csv

# Edit the CSV with real data from NY Fed website
# Then run:
python fed/nyfed_settlement_fails.py
```

**Option B: Direct Download**
1. Download CSV from NY Fed website
2. Rename to `nyfed_settlement_fails.csv`
3. Move to `outputs/fed/` directory
4. Run script to verify format

### 3. Run Complete Pipeline
```bash
python fiscal/fiscal_analysis.py
python fed/fed_liquidity.py
python fed/nyfed_operations.py
python fed/nyfed_reference_rates.py
python fed/nyfed_settlement_fails.py  # New!
python fed/liquidity_composite_index.py
```

---

## Expected Impact on LCI

### Current State (Without Settlement Fails)
```
Plumbing_Index = Repo Stress * 100%
```

### With Settlement Fails
```
Plumbing_Index = (Repo Stress * 60%) + (Settlement Fails * 40%)
```

**Example Improvement:**
- Current: Only repo submissions tracked
- Enhanced: Repo stress + settlement fails stress = comprehensive plumbing assessment
- Result: More accurate detection of Treasury market stress conditions

---

## Data Fields Generated

The script calculates these metrics:

| Field | Description | Usage |
|-------|-------------|-------|
| `totalFails` | Sum of all fails | Primary stress indicator |
| `MA5_Fails` | 5-day moving average | Short-term trend |
| `MA20_Fails` | 20-day moving average | Long-term baseline |
| `Fails_ZScore` | Standardized score | Stress detection (>2 = elevated) |

---

## Troubleshooting

### Issue: API endpoints return empty data
**Solution:** Use manual CSV download (see Option 1)

### Issue: CSV format not recognized
**Check:**
- Date column is named exactly `date`
- Dates are in YYYY-MM-DD format
- No header rows except column names
- Values are numeric (no $ signs or commas)

### Issue: LCI still shows "Settlement fails file not found"
**Check:**
- File saved to: `outputs/fed/nyfed_settlement_fails.csv`
- Not: `fed/outputs/fed/nyfed_settlement_fails.csv`
- File has `.csv` extension (not `.txt`)

### Issue: How to verify data was loaded?
```bash
python -c "
import pandas as pd
df = pd.read_csv('outputs/fed/nyfed_settlement_fails.csv', index_col=0, parse_dates=True)
print(f'Records: {len(df)}')
print(f'Date range: {df.index.min()} to {df.index.max()}')
print(df.head())
"
```

---

## Future Enhancements

If you find the correct NY Fed API endpoint:

1. Update `api_client.py` in the `fetch_settlement_fails()` method
2. Update the endpoint configuration (lines 298-314)
3. Test with: `python fed/nyfed_settlement_fails.py`
4. Share the working endpoint! 🎉

**Helpful for discovery:**
- Check browser Network tab when downloading from NY Fed website
- Inspect XHR requests to see actual API calls
- productCode/eventCode patterns may vary

---

## Summary

**Current Status:** ✅ Infrastructure ready, awaiting data source

**Best Approach:** Manual CSV download from NY Fed website

**Impact:** Enhances LCI Plumbing component with additional stress indicator

**Time to implement:** 5-10 minutes (once you have the CSV)

**Alternative:** System works fine without it - repo stress alone provides good plumbing assessment

---

## Questions?

If you discover:
- Working API endpoints
- Better data sources
- Issues with CSV format

Update the `fetch_settlement_fails()` method in `fed/utils/api_client.py`
