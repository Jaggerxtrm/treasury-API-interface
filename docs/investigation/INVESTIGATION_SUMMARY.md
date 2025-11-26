# FISCAL ANALYSIS IMPLEMENTATION - INVESTIGATION SUMMARY

**Date:** 2025-11-26
**Investigator:** Automated Investigation Agent
**Scope:** Compare `fiscal_analysis.py` implementation against Fiscal Week #44 methodology

---

## EXECUTIVE SUMMARY

Investigation of the `fiscal_analysis.py` implementation revealed **3 HIGH priority issues** and **2 MEDIUM priority issues** requiring immediate attention. The analysis covered:
- GDP normalization calculations
- Net Liquidity calculation and NaN handling
- Household share definition
- 4-week cumulative calculation methodology
- Fiscal calendar alignment

### ✅ CRITICAL FINDINGS (HIGH PRIORITY)

1. **GDP Value Documentation Mismatch** (HIGH)
   - **Issue:** Code uses FRED-fetched GDP ($30.5T) with estimation, but fallback shows $29T
   - **Impact:** %GDP metrics appear understated to users expecting $29T baseline
   - **Root Cause:** fetch_current_gdp() estimates future GDP but doesn't document this clearly
   - **Recommended Fix:** Add GDP metadata to output CSV and report header

2. **Net Liquidity NaN Propagation** (HIGH)
   - **Issue:** 32% of recent Fed liquidity records have NaN for RRP/Net_Liquidity
   - **Impact:** Missing liquidity data on weekends/holidays breaks analysis continuity
   - **Root Cause:** No forward-fill or imputation for non-trading days
   - **Recommended Fix:** Implement forward-fill for weekends with warning flags

3. **Household Share Not Persisted** (HIGH)
   - **Issue:** household_share calculated for display but NOT saved to CSV
   - **Impact:** Cannot audit historical household share or detect negative values
   - **Root Cause:** Calculation only happens in report generation, not in processing
   - **Recommended Fix:** Add household_share column to daily metrics calculation

### ⚠️ MEDIUM PRIORITY FINDINGS

4. **GDP %GDP Formula Unit Ambiguity** (MEDIUM)
   - **Issue:** Formula `(MA20 * 252 * 1_000_000) / gdp * 100` unclear on units
   - **Impact:** Confusion about whether MA20 is in Millions or raw USD
   - **Status:** Calculation is CORRECT (MA20 in Millions × 1M to get USD ÷ GDP in USD)
   - **Recommended Fix:** Add inline comments clarifying unit conversions

5. **Block vs Sliding 4W Reconciliation** (MEDIUM)
   - **Issue:** Code calculates both but tolerance checking could be more robust
   - **Impact:** Subtle discrepancies might go unnoticed
   - **Status:** Current implementation CORRECT, sliding 20 BD matches spec
   - **Recommended Fix:** Add automated reconciliation check to report

### ✅ VALIDATED AS CORRECT

- **4-Week Cumulative:** Rolling 20 BD window implementation is correct ✓
- **Fiscal Week Definition:** Wed-Wed alignment is correct ✓
- **YoY Calculations:** shift(252) for business day alignment is correct ✓
- **Category Mapping:** Comprehensive and well-structured ✓

---

## DETAILED FINDINGS

### 1. GDP Normalization & Documentation (HIGH PRIORITY)

#### Evidence
```python
# fiscal_analysis.py line 30
NOMINAL_GDP_FALLBACK = 29_000_000_000_000  # $29T

# But fetch_current_gdp() returns:
# FRED GDP: $30,485.73B (Q4 2024, 235 days old)
# Estimated current GDP: $31.696T (QoQ growth: 0.81%)
```

**Sample Data (2025-11-24):**
- MA20_Net_Impulse: $12,172.45 M
- Annual_Impulse_Pct_GDP: 9.68%
- **Implied GDP:** $31.7T (reverse-calculated)
- **Expected GDP:** $29.0T (per fallback constant)
- **Discrepancy:** +9.3%

#### Root Cause
The `fetch_current_gdp()` function (lines 310-369) fetches latest GDP from FRED ($30.5T) and then **estimates forward** using QoQ growth if data is >90 days old. This estimated GDP (~$31.7T) is used in all %GDP calculations, but:
1. Not documented in CSV output
2. Not shown in report header
3. Fallback constant is misleading

#### Impact
- Users see %GDP values but don't know which GDP baseline is used
- Comparing to external reports using different GDP creates confusion
- Sensitivity to GDP changes not transparent

#### Recommended Fix
```python
# Add to CSV output:
merged['GDP_Used'] = nominal_gdp
merged['GDP_Source'] = 'FRED_Estimated' if is_estimated else 'FRED_Actual'
merged['GDP_Reference_Date'] = gdp_date

# Add to report header (line 1110):
print(f"💰 Nominal GDP:     ${nominal_gdp/1e12:.3f}T ({gdp_status})")
print(f"💰 GDP Reference:   {quarter} (published {gdp_date}, {days_old} days old)")
if is_estimated:
    print(f"    ⚠️  Using extrapolated GDP based on {qoq_growth*100:.2f}% QoQ growth")
```

---

### 2. Net Liquidity NaN Handling (HIGH PRIORITY)

#### Evidence
Fed liquidity data shows systematic NaN pattern:

| Date | RRP_Balance | Net_Liquidity | TGA_Balance | Issue |
|------|-------------|---------------|-------------|-------|
| 2025-11-21 | 2.503 B | 5,660,706 M | 892,074 M | ✓ Valid |
| 2025-11-22 | **NaN** | **NaN** | 892,074 M | ❌ Weekend |
| 2025-11-23 | **NaN** | **NaN** | 892,074 M | ❌ Weekend |
| 2025-11-24 | 1.077 B | 5,647,659 M | 906,547 M | ✓ Valid |

**NaN Statistics:**
- Last 100 rows: 32% have NaN in RRP/Net_Liquidity
- Pattern: Weekends and holidays (Fed doesn't publish RRP on non-trading days)

#### Root Cause
Fed RRP data not published on weekends/holidays. Code doesn't implement forward-fill, causing:
1. NaN propagation in Net_Liquidity calculations
2. Gaps in integrated analysis requiring both fiscal and liquidity data
3. `perform_reconciliation_check()` fails on these dates

#### Impact
- Reports generated on Mondays show incomplete liquidity context
- Week-over-week liquidity changes distorted by gaps
- Automated analysis pipelines may crash on NaN

#### Recommended Fix
```python
# In fed liquidity processing (after initial calculation):
def forward_fill_non_trading_days(df):
    """
    Forward-fill RRP and Net Liquidity for non-trading days.
    Flag these as imputed for transparency.
    """
    df['RRP_Imputed'] = df['RRP_Balance'].isna()
    df['RRP_Balance'] = df['RRP_Balance'].fillna(method='ffill')
    df['RRP_Balance_M'] = df['RRP_Balance'] * 1000

    # Recalculate Net Liquidity with imputed values
    df['Net_Liquidity'] = df['Fed_Total_Assets'] - df['RRP_Balance_M'] - df['TGA_Balance']
    df['Net_Liq_Imputed'] = df['RRP_Imputed']

    return df

# Usage:
merged = forward_fill_non_trading_days(merged)
```

**Test Case:**
```python
def test_rrp_forward_fill():
    # Create sample with weekend gap
    data = {
        'date': ['2025-11-21', '2025-11-22', '2025-11-24'],
        'RRP_Balance': [2.503, np.nan, 1.077],
        'Fed_Total_Assets': [6555283, 6555283, 6555283],
        'TGA_Balance': [892074, 892074, 906547]
    }
    df = pd.DataFrame(data)
    result = forward_fill_non_trading_days(df)

    # Weekend should have imputed RRP = 2.503 (from Friday)
    assert result.loc[1, 'RRP_Balance'] == 2.503
    assert result.loc[1, 'RRP_Imputed'] == True

    # Net Liquidity should be calculated with imputed RRP
    expected_net_liq = 6555283 - 2503 - 892074
    assert abs(result.loc[1, 'Net_Liquidity'] - expected_net_liq) < 1
```

---

### 3. Household Share Column Missing (HIGH PRIORITY)

#### Evidence
```python
# fiscal_analysis.py line 1149 (in generate_report):
household_pct = latest['Household_Spending']/latest['Total_Spending']*100

# ❌ But this is NOT saved to CSV!
# ✓ Only Household_Spending column exists in output
```

**CSV Columns Check:**
- ✓ `Household_Spending` - Present
- ❌ `household_share` - MISSING
- ❌ `household_share_pct` - MISSING

#### Root Cause
Household share calculation happens in `generate_report()` for display only, not during `process_fiscal_analysis()` where other derived metrics are calculated.

#### Impact
1. Cannot audit historical household share trends
2. Cannot detect if negative household share ever occurred
3. Cannot validate formula correctness across different fiscal conditions
4. Historical analysis requires reprocessing raw data

#### Prompt Requirement Violated
From spec: *"Household share: `household_outlays / total_outlays` (0–100%)"*

The implementation calculates correctly, but doesn't persist the metric for validation.

#### Recommended Fix
```python
# In process_fiscal_analysis(), after line 903:
# After calculating Household_Spending
merged['Household_Share_Pct'] = (
    merged['Household_Spending'] / merged['Total_Spending'] * 100
).fillna(0)

# Add validation
assert (merged['Household_Share_Pct'] >= 0).all(), "Household share should never be negative"
assert (merged['Household_Share_Pct'] <= 100).all(), "Household share should not exceed 100%"
```

**Test Case:**
```python
def test_household_share_bounds():
    # Normal day
    assert calculate_household_share(7121, 16788, 1234) == 42.42

    # Edge case: all spending is household
    assert calculate_household_share(10000, 10000, 5000) == 100.0

    # Edge case: no household spending
    assert calculate_household_share(0, 10000, 5000) == 0.0

    # Edge case: negative net impulse (taxes > spending)
    # Household share should still be valid [0-100]
    share = calculate_household_share(5000, 10000, -3000)
    assert 0 <= share <= 100
```

---

### 4. GDP Formula Unit Documentation (MEDIUM PRIORITY)

#### Current Code
```python
# line 986
merged['Weekly_Impulse_Pct_GDP'] = (merged['MA20_Net_Impulse'] * 5 * 1_000_000) / nominal_gdp * 100

# line 989
merged['Annual_Impulse_Pct_GDP'] = (merged['MA20_Net_Impulse'] * 252 * 1_000_000) / nominal_gdp * 100
```

#### Analysis
The formula is **mathematically CORRECT** but **poorly documented**:
- `MA20_Net_Impulse` is in **Millions USD** (column header confirms "M")
- Multiply by `1_000_000` converts to **USD**
- `nominal_gdp` is in **USD** (from FRED API)
- Result is percentage

**Verification:**
```
MA20 = 12,172.45 M
GDP = 31,696 B = 31,696,000 M
Annual % = (12,172.45 * 252) / 31,696,000 * 100 = 9.68% ✓
```

#### Issue
Without comments, this formula creates confusion:
1. Why multiply Millions by 1,000,000 instead of just using raw values?
2. Is GDP in correct units?
3. Should we use GDP in Millions for consistency?

#### Recommended Fix
```python
# GDP NORMALIZATION - All calculations convert to USD for consistency
# Note: MA20_Net_Impulse is in Millions, nominal_gdp from FRED is in USD

# Weekly impulse as % of GDP (MA20 represents average daily, multiply by 5 for weekly)
# Formula: (MA20_M * 1,000,000 to_USD * 5 days/week) / GDP_USD * 100
merged['Weekly_Impulse_Pct_GDP'] = (
    merged['MA20_Net_Impulse'] * 5 * 1_000_000  # Convert M to USD, then weekly
) / nominal_gdp * 100

# Annualized impulse as % of GDP (252 trading days)
# Formula: (MA20_M * 1,000,000 to_USD * 252 days/year) / GDP_USD * 100
merged['Annual_Impulse_Pct_GDP'] = (
    merged['MA20_Net_Impulse'] * 252 * 1_000_000  # Convert M to USD, then annualize
) / nominal_gdp * 100

# Alternative (cleaner): Convert GDP to Millions for unit consistency
GDP_MILLIONS = nominal_gdp / 1_000_000
merged['Annual_Impulse_Pct_GDP'] = (
    merged['MA20_Net_Impulse'] * 252  # Already in Millions
) / GDP_MILLIONS * 100
```

---

### 5. Reconciliation Monitoring (MEDIUM PRIORITY)

#### Current Implementation
`perform_reconciliation_check()` (lines 708-775) correctly:
- ✓ Calculates sliding 20-BD cumulative
- ✓ Compares to block 4-week sum
- ✓ Applies tolerance checks (>$10B or >5%)

#### Evidence
Testing shows **perfect match**:
```
Sliding 20 BD:  $243,449 M
Reported 4W:    $243,449 M
Discrepancy:    $0 M (0.00%)
```

#### Issue
While implementation is correct, the reconciliation check:
1. Only runs in `generate_report()`, not automatically
2. Doesn't save reconciliation results to CSV for trending
3. No alerting mechanism if discrepancy exceeds tolerance

#### Recommended Enhancement
```python
# Add to process_fiscal_analysis() output:
merged['4W_Sliding_BD'] = merged['Net_Impulse'].rolling(window=20).sum()
merged['4W_Block_Week'] = np.nan  # Populate from weekly aggregation

# Add reconciliation metric
merged['4W_Reconciliation_Delta'] = merged['4W_Sliding_BD'] - merged['4W_Block_Week']
merged['4W_Reconciliation_Flag'] = (
    (abs(merged['4W_Reconciliation_Delta']) > 10_000) |
    (abs(merged['4W_Reconciliation_Delta'] / merged['4W_Sliding_BD']) > 0.05)
)

# Alert in report if flags found
flagged = merged[merged['4W_Reconciliation_Flag'] == True]
if len(flagged) > 0:
    print(f"\n⚠️  {len(flagged)} dates with reconciliation discrepancy >tolerance")
```

---

## RECONCILIATION CALCULATIONS (Sample Dates)

### Date 1: 2025-11-24 (Typical Day)

| Metric | Implementation | Manual Calc | Match |
|--------|----------------|-------------|-------|
| MA20_Net_Impulse | $12,172.45 M | $12,172.45 M | ✅ |
| 4W_Cum_Net | $243,449 M | $243,449 M | ✅ |
| Annual %GDP | 9.68% | 9.68% | ✅ |
| Household Share | 42.42% | 42.42% | ✅ |

**Formulas Used:**
```
MA20 = sum(last 20 Net_Impulse) / 20
4W_Cum = sum(last 20 Net_Impulse)
Annual % = (12,172.45 * 252) / 31,696,000 * 100
Household % = 7,121 / 16,788 * 100
```

### Date 2: 2025-11-20 (Month-End Burst)

| Metric | Value | Notes |
|--------|-------|-------|
| Net_Impulse | $7,451 M | Positive injection |
| 4W_Cum_Net | $223,326 M | High cumulative |
| YoY_Net_Impulse | $31,601 M | Strong YoY growth |

### Date 3: 2025-10-30 (Low Activity)

| Metric | Value | Notes |
|--------|-------|-------|
| Net_Impulse | $3,230 M | Low daily activity |
| 4W_Cum_Net | $19,234 M | Very low 4W cumulative |
| Weekly %GDP | 0.015% | Minimal fiscal impact |

---

## PRIORITY MATRIX

| Issue # | Issue | Priority | Effort | Impact | Urgency |
|---------|-------|----------|--------|--------|---------|
| 1 | GDP Documentation | HIGH | Low | High | Immediate |
| 2 | Net Liq NaN | HIGH | Medium | High | Immediate |
| 3 | Household Share Persist | HIGH | Low | Medium | Next Sprint |
| 4 | Formula Comments | MEDIUM | Low | Low | Next Sprint |
| 5 | Reconciliation Monitor | MEDIUM | Medium | Low | Backlog |

---

## NEXT STEPS

1. **Immediate (Today):**
   - Add GDP metadata to output CSV
   - Document GDP in report header

2. **Sprint 1 (This Week):**
   - Implement RRP forward-fill with imputation flags
   - Add household_share column to daily CSV
   - Add unit documentation comments to formulas

3. **Sprint 2 (Next Week):**
   - Enhanced reconciliation monitoring
   - Automated test suite for all fixes
   - Regression testing with historical data

4. **Validation:**
   - Re-run analysis on last 6 months of data
   - Compare outputs before/after to ensure no regressions
   - Document any breaking changes to downstream consumers

---

## TOOLS & TEST CASES

See `DETAILED_FINDINGS.csv` for line-by-line patch locations.
See `patches/` directory for implementation fixes with pytest test cases.

**Generated:** 2025-11-26
**Investigation Tool:** investigation_analysis.py
**Data Sources:** outputs/fiscal/fiscal_analysis_full.csv (976 records), outputs/fed/fed_liquidity_full.csv (1426 records)
