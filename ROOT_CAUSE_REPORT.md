# Pipeline Date Issue Root Cause Report

**Date:** 2025-11-29  
**Issue:** Pipeline showingDecember 1st dates instead of November 28th  
**Status:** COMPLETE - Root cause identified and solutions provided

---

## Executive Summary

The pipeline is incorrectly displaying December 1st, 2025 as the "current date" instead of November 28th, 2025 (last trading day). This is causing:

- Month-to-Date calculations to show $0M values (Dec 1-1 instead of Nov 1-28)
- SOFR-IORB spread showing NaN (no valid data for Dec 1)
- Composite Stress Index showing mostly 0/100 values

**Root Cause:** Forward-fill logic creating future dates from weekly FRED data series.

---

## Detailed Analysis

### 1. Where the Problem Originates

**File:** `fed/fed_liquidity.py`  
**Function:** `calculate_metrics()` around lines 1200-1250  
**Issue Line:** `df[weekly_columns] = df[weekly_columns].ffill()`

### 2. Technical Root Cause

The problem occurs in this sequence:

1. **Weekly Data Gaps**: FRED weekly series (like balance sheet data) are published on Wednesdays. The latest actual data might be from Nov 26 or Nov 27.

2. **Forward Fill Logic**: The script applies `df[weekly_columns].ffill()` which:
   - Takes the last known weekly value (e.g., Nov 26)
   - Forward-fills it to create continuous daily series
   - This creates entries for Nov 27, Nov 28, **Nov 29, Nov 30, Dec 1...**

3. **Date Index Extension**: The forward fill extends the DataFrame index to include future dates where no real data exists.

4. **MTD Calculation**: `calculate_mtd_metrics()` uses `last_date = df.index[-1]` which now points to Dec 1st.

### 3. Why Some Sections Show Data and Others Don't

| Section | Data Source | Why It Works | Why It Doesn't |
|---------|-------------|--------------|----------------|
| **QT/QE Decomposition** | NY Fed API (real-time) | Gets actual Nov 28 data | Shows current-ish numbers |
| **Composite Stress Index** | FRED (forward-filled) | Uses forward-filled data | Shows 0/100 (Dec 1 has no spread history) |
| **Liquidity Composite Index** | Database (inherits issue) | Uses the same forward-filled index | Shows last date as 2025-12-01 |

### 4. Nan Propagation in SOFR-IORB

The NaN values occur because:
1. SOFR and IORB are daily rates that have real data through Nov 28
2. The forward-fill logic extends the index to Dec 1
3. No SOFR/IORB data exists for Dec 1 (future date)
4. MTD calculations on the Dec 1 range find no valid data points

---

## Specific Code Issues

### File: `fed/fed_liquidity.py`

```python
# PROBLEMATIC CODE (lines ~1220):
weekly_columns = ['Fed_Total_Assets', 'Fed_Total_Assets', ...]
df[weekly_columns] = df[weekly_columns].ffill()  # Creates future dates!

# PROBLEMATIC CODE (line ~1500):
def calculate_mtd_metrics(df):
    last_date = df.index[-1]  # Gets Dec 1 instead of Nov 28!
    month_start = last_date.replace(day=1)  # Dec 1 instead of Nov 1
```

### File: `fed/liquidity_composite_index.py`

```python
# PROBLEMATIC CODE:
last_date = indices.index[-1].strftime('%Y-%m-%d')  # Inherits Dec 1 issue
```

---

## Solutions (Implement in Priority Order)

### [PRIORITY 1] Fix Forward Fill Logic

```python
# In fed/fed_liquidity.py, around line 1220:

# CURRENT (PROBLEMATIC):
df[weekly_columns] = df[weekly_columns].ffill()

# FIX: Limit forward fill to actual data range
def safe_forward_fill(df, columns, max_days=3):
    """Forward fill only within reasonable dates, not into future"""
    today = pd.Timestamp.today().normalize()
    future_cutoff = today  # Don't fill past today
    
    for col in columns:
        if col in df.columns:
            # Create mask for valid dates only
            valid_dates = df.index <= future_cutoff
            df.loc[valid_dates, col] = df.loc[valid_dates, col].ffill()
    
    return df

# Replace forward fill call with:
df = safe_forward_fill(df, weekly_columns, max_days=3)
```

### [PRIORITY 2] Fix MTD Calculation

```python
# In calculate_mtd_metrics() function:

# CURRENT (PROBLEMATIC):
last_date = df.index[-1]

# FIX: Use actual data date, not filled dates
def get_actual_last_date(df):
    """Get the last date with real data, ignoring forward-filled values"""
    # Find columns with actual daily data (not weekly)
    daily_columns = ['RRP_Balance', 'SOFR_Rate', 'IORB_Rate']
    
    for col in daily_columns:
        if col in df.columns:
            # Find last non-NaN value
            last_valid_idx = df[col].last_valid_index()
            if last_valid_idx:
                return last_valid_idx
    
    # Fallback to last index
    return df.index[-1]

# Replace in calculate_mtd_metrics():
last_date = get_actual_last_date(df)
```

### [PRIORITY 3] Add Date Validation

```python
# Add validation at start of generate_report():

def validate_data_dates(df):
    """Check if data contains future dates and warn user"""
    today = pd.Timestamp.today().normalize()
    last_date = df.index[-1]
    
    if last_date > today:
        print(f"⚠️  WARNING: Data extends to {last_date.strftime('%Y-%m-%d')}")
        print(f"    Current date: {today.strftime('%Y-%m-%d')}")
        print(f"    Forward fill may have created future dates")
        print(f"    MTD calculations will be affected")
        return False
    return True

# Add at start of generate_report():
if not validate_data_dates(df):
    print("❌ Date validation failed - using last actual data date")
    # Truncate to actual date
    today = pd.Timestamp.today().normalize()
    df = df[df.index <= today]
```

### [PRIORITY 4] Quick Fix (Immediate)

```python
# Temporary fix - add at end of fetch_all_data():
# Truncate any future dates created by forward fill
today = pd.Timestamp.today().normalize()
df = df[df.index <= today]
```

---

## Files That Need Changes

1. **fed/fed_liquidity.py** (Primary fix location)
   - Fix forward fill logic (~line 1220)
   - Fix `calculate_mtd_metrics()` (~line 1500)
   - Add date validation in `generate_report()` (~line 1580)

2. **fed/liquidity_composite_index.py** (Secondary)
   - Add similar date validation
   - Use actual data date instead of last index date

3. **fiscal/fiscal_analysis.py** (Check needed)
   - Verify this script also uses `pd.Timestamp.today()` correctly
   - May need same forward-fill fixes

---

## Testing Plan

### 1. Validation Tests
```python
# Test the fixes before implementing:
def test_date_fix():
    # Create sample data with future dates
    dates = pd.date_range('2025-11-25', '2025-12-02', freq='D')
    df = pd.DataFrame({'value': [100, 120, 130, 130, 130, 130, 130, 130]}, index=dates)
    
    # Apply fix
    today = pd.Timestamp.today().normalize()
    df_fixed = df[df.index <= today]
    
    assert df_fixed.index[-1] <= today, "Future dates should be removed"
    print("✅ Date validation works")
```

### 2. Integration Test
After implementing fixes:
1. Run `python fed/fed_liquidity.py`
2. Verify output shows November dates, not December
3. Check MTD section shows "2025-11-01 to 2025-11-28"
4. Verify SOFR-IORB spread has numeric values, not NaN

### 3. Pipeline Test
1. Run full pipeline: `python run_pipeline.py`
2. Check output report shows consistent dates across all sections
3. Verify Stress Index components have realistic values (not all 0/100)

---

## Expected Results After Fix

| Current Issue | Expected After Fix |
|---------------|-------------------|
| `MONTH-TO-DATE (2025-12-01 to 2025-12-01)` | `MONTH-TO-DATE (2025-11-01 to 2025-11-28)` |
| `Balance Sheet MTD: $0M` | `Balance Sheet MTD: $[actual value]M` |
| `Avg SOFR-IORB Spread: nan bps` | `Avg SOFR-IORB Spread: [value] bps` |
| `Stress Index: 4/100 (LOW)` | `Stress Index: [realistic value]/100` |
| Components showing 0/100 | Components showing realistic stress values |

---

## Implementation Notes

1. **Careful with Forward Fill**: The forward fill is useful for handling weekends but shouldn't create future dates. Limit it to 3-4 days maximum.

2. **Daily vs Weekly Data**: Use actual daily data series (RRP, SOFR) to determine the real last data date, not weekly series that get forward-filled.

3. **Timezone Handling**: Ensure all date comparisons use the same timezone (local time for the system running the pipeline).

4. **Date Normalization**: Use `pd.Timestamp.today().normalize()` to avoid time-of-day issues in comparisons.

5. **Backwards Compatibility**: Test changes don't break existing functionality when data is current.

---

## Root Cause Summary

**Technical**: Forward fill algorithm creates future dates → MTD calculations use Dec 1 → No real data exists for Dec 1 → MTD shows $0/NaN

**Business Impact**: Pipeline appears broken on the first day of each month, confusing users with incorrect date displays

**Data Impact**: Monthly performance metrics become unusable for the first ~3 days of each month

---
**Report Status: COMPLETE - Ready for implementation**
