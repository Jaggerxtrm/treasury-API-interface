# FISCAL ANALYSIS FIXES - PATCHES & TESTS

This directory contains patches and test cases for fixes identified in the fiscal analysis implementation investigation (2025-11-26).

## CONTENTS

### Patch Files (.patch)
- `fiscal_001_gdp_documentation.patch` - Add GDP metadata to output and report
- `fiscal_002_rrp_forward_fill.patch` - Implement RRP/TGA forward-fill for weekends
- `fiscal_003_household_share_persist.patch` - Add household_share_pct to daily metrics

### Test Suite
- `test_fiscal_fixes.py` - Comprehensive pytest test cases for all fixes

## APPLYING PATCHES

### Option 1: Manual Application (Recommended)

Review each patch file and apply changes manually to ensure compatibility with your current codebase:

1. Read the patch file to understand changes
2. Locate the target lines in your source file
3. Apply the modifications
4. Run tests to verify

### Option 2: Git Apply (Advanced)

If your repository structure matches exactly:

```bash
# From project root
git apply patches/fiscal_001_gdp_documentation.patch
git apply patches/fiscal_002_rrp_forward_fill.patch
git apply patches/fiscal_003_household_share_persist.patch
```

**Note:** Patches may require adjustment if line numbers have changed since investigation.

## RUNNING TESTS

### Prerequisites
```bash
pip install pytest pandas numpy
```

### Run All Tests
```bash
pytest patches/test_fiscal_fixes.py -v
```

### Run Specific Test
```bash
pytest patches/test_fiscal_fixes.py::test_gdp_metadata_in_output -v
```

### Expected Output
```
patches/test_fiscal_fixes.py::test_gdp_metadata_in_output PASSED
patches/test_fiscal_fixes.py::test_gdp_reverse_calculation PASSED
patches/test_fiscal_fixes.py::test_rrp_forward_fill_weekends PASSED
patches/test_fiscal_fixes.py::test_rrp_no_false_imputation PASSED
patches/test_fiscal_fixes.py::test_household_share_calculation PASSED
patches/test_fiscal_fixes.py::test_household_share_negative_net_impulse PASSED
patches/test_fiscal_fixes.py::test_household_share_bounds PASSED
patches/test_fiscal_fixes.py::test_household_share_in_dataframe PASSED
patches/test_fiscal_fixes.py::test_net_liquidity_calculation PASSED
patches/test_fiscal_fixes.py::test_net_liquidity_multiple_samples PASSED
patches/test_fiscal_fixes.py::test_4w_cumulative_sliding_window PASSED

======================== 11 passed in 0.12s ========================
```

## PATCH DETAILS

### FISCAL-001: GDP Documentation (HIGH Priority)

**Problem:** GDP value used in %GDP calculations ($31.7T) not documented or saved to output.

**Changes:**
- Add `GDP_Used` column to fiscal_daily_metrics
- Enhance report header to show GDP value, source, and estimation status
- Add warning when GDP is extrapolated

**Files Modified:** `fiscal/fiscal_analysis.py` (lines 943, 1106-1122)

**Testing:**
```bash
pytest patches/test_fiscal_fixes.py::test_gdp_metadata_in_output -v
pytest patches/test_fiscal_fixes.py::test_gdp_reverse_calculation -v
```

### FISCAL-002: RRP Forward-Fill (HIGH Priority)

**Problem:** 33% of Fed liquidity records have NULL RRP/Net_Liquidity due to weekends/holidays.

**Changes:**
- Implement forward-fill for RRP_Balance on non-trading days
- Add `RRP_Imputed`, `TGA_Imputed`, `Net_Liq_Imputed` flags
- Recalculate Net_Liquidity with imputed values

**Files Modified:** `fed/fed_liquidity.py` (Net Liquidity calculation section)

**Testing:**
```bash
pytest patches/test_fiscal_fixes.py::test_rrp_forward_fill_weekends -v
pytest patches/test_fiscal_fixes.py::test_rrp_no_false_imputation -v
```

### FISCAL-003: Household Share Persistence (HIGH Priority)

**Problem:** household_share calculated for display but not saved to database/CSV.

**Changes:**
- Add `Household_Share_Pct` calculation to process_fiscal_analysis()
- Add validation to ensure [0, 100]% bounds
- Persist column to fiscal_daily_metrics table

**Files Modified:** `fiscal/fiscal_analysis.py` (lines 899-957)

**Testing:**
```bash
pytest patches/test_fiscal_fixes.py::test_household_share_calculation -v
pytest patches/test_fiscal_fixes.py::test_household_share_negative_net_impulse -v
pytest patches/test_fiscal_fixes.py::test_household_share_bounds -v
pytest patches/test_fiscal_fixes.py::test_household_share_in_dataframe -v
```

## VALIDATION

### Pre-Apply Checklist
- [ ] Backup current database: `cp database/treasury_data.duckdb database/treasury_data.duckdb.backup`
- [ ] Review all patch files for conflicts with local changes
- [ ] Ensure test environment has pandas, numpy, pytest installed
- [ ] Run existing tests (if any) to establish baseline

### Post-Apply Checklist
- [ ] Run full test suite: `pytest patches/test_fiscal_fixes.py -v`
- [ ] Verify 11/11 tests pass
- [ ] Re-run fiscal_analysis.py and check output
- [ ] Query database to verify new columns exist
- [ ] Compare outputs before/after using reconciliation_before_after.md

### Database Schema Verification

After applying patches, verify new columns exist:

```python
import duckdb
conn = duckdb.connect('database/treasury_data.duckdb')

# Check fiscal_daily_metrics
fiscal_schema = conn.execute("DESCRIBE fiscal_daily_metrics").fetchdf()
print("New columns in fiscal_daily_metrics:")
print(fiscal_schema[fiscal_schema['column_name'].isin(['GDP_Used', 'Household_Share_Pct'])])

# Check fed_liquidity_daily
fed_schema = conn.execute("DESCRIBE fed_liquidity_daily").fetchdf()
print("\nNew columns in fed_liquidity_daily:")
print(fed_schema[fed_schema['column_name'].str.contains('Imputed', case=False)])

conn.close()
```

Expected output:
```
New columns in fiscal_daily_metrics:
   column_name  column_type
XX  GDP_Used     BIGINT
YY  Household_Share_Pct  DOUBLE

New columns in fed_liquidity_daily:
   column_name       column_type
AA  RRP_Imputed       BOOLEAN
BB  TGA_Imputed       BOOLEAN
CC  Net_Liq_Imputed   BOOLEAN
```

## ROLLBACK

If issues arise after applying patches:

```bash
# Restore database backup
mv database/treasury_data.duckdb.backup database/treasury_data.duckdb

# Revert code changes
git checkout fiscal/fiscal_analysis.py fed/fed_liquidity.py
```

## SUPPORT

For issues or questions:
1. Review `INVESTIGATION_SUMMARY.md` for detailed context
2. Check `DETAILED_FINDINGS.csv` for root cause analysis
3. Consult `reconciliation_before_after.md` for numerical examples

## NEXT STEPS

After successfully applying patches:

1. **Immediate:**
   - Re-run fiscal_analysis.py to regenerate outputs
   - Verify new columns in database
   - Run test suite to confirm all tests pass

2. **Short-term:**
   - Update documentation to reflect new columns
   - Notify downstream consumers of new household_share_pct column
   - Add GDP metadata to any dashboards/reports

3. **Long-term:**
   - Consider implementing remaining MEDIUM priority fixes
   - Set up automated testing as part of CI/CD
   - Monitor imputation flags to track data quality

---

**Generated:** 2025-11-26
**Investigation:** INVESTIGATION_SUMMARY.md
**Test Coverage:** 11 tests, 3 HIGH priority fixes
