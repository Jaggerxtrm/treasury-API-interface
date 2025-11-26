# Data Quality Monitoring

Automated monitoring tools for the Treasury API Interface data pipeline.

---

## Overview

This directory contains tools for monitoring data quality, detecting issues, and validating the integrity of the Treasury API Interface data pipeline.

## Tools

### data_quality_checks.py

**Purpose:** Comprehensive automated data quality validation

**Usage:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run monitoring checks
python monitoring/data_quality_checks.py

# Output is displayed in console and saved to JSON
```

**Output Files:**
- `monitoring/data_quality_report.json` - Machine-readable report with issues, warnings, and info

**Checks Performed:**

1. **Fiscal Data Coverage**
   - Validates data coverage vs expected trading days (252/year)
   - **Threshold:** Warns if coverage < 95%
   - **Status:** ✅ Currently 99.6% (977/981 trading days)

2. **Fed Liquidity Coverage**
   - Checks for NULL values in critical columns (Net_Liquidity, RRP_Balance_M, TGA_Balance)
   - Validates imputation is working correctly
   - **Threshold:** Errors if any NULLs found, warns if imputation > 40%
   - **Status:** ✅ 0% NULL, 33% imputed (weekends/holidays)

3. **Household Share Bounds**
   - Ensures all Household_Share_Pct values are within [0, 100]%
   - **Threshold:** Errors if any values outside bounds
   - **Status:** ✅ 100% within bounds

4. **Imputation Rate**
   - Monitors percentage of RRP/TGA imputed records
   - **Threshold:** Warns if average imputation > 40% (suggests data source issues)
   - **Status:** ✅ 33% (normal for weekend coverage)

5. **GDP Consistency**
   - Validates same GDP value used across all records in a run
   - **Threshold:** Errors if multiple GDP values found in same day's data
   - **Status:** ✅ 1 unique value

6. **Calculation Accuracy**
   - Reverse-calculates Net_Liquidity and Household_Share_Pct
   - Compares against stored values
   - **Threshold:** Errors if difference > $1M or 0.01%
   - **Status:** ✅ Max diff: $0M, 0.0000%

7. **Schema Integrity**
   - Validates all required columns are present
   - **Checks:** GDP_Used, Household_Share_Pct, RRP_Imputed, TGA_Imputed, Net_Liq_Imputed
   - **Status:** ✅ All columns present

**Exit Codes:**
- `0` - All checks passed
- `1` - Critical issues detected (errors)
- `0` - Warnings only (non-critical)

**Example Output:**
```
🔍 Treasury API Data Quality Monitor
=====================================

Database: database/treasury_data.duckdb
Timestamp: 2025-11-26 23:58:35

✅ [1/7] Fiscal Data Coverage: 99.6% (977/981 trading days)
✅ [2/7] Fed Liquidity Coverage: 0% NULL, 33.3% imputed
✅ [3/7] Household Share Bounds: 100% within [0,100]%
✅ [4/7] Imputation Rate: Average 33% (within threshold)
✅ [5/7] GDP Consistency: 1 unique value
✅ [6/7] Calculation Accuracy:
    - Net Liquidity: Max diff $0M ✅
    - Household Share: Max diff 0.0000% ✅
✅ [7/7] Schema Integrity: All required columns present

=====================================
✅ ALL CHECKS PASSED - No issues detected

Total: 0 errors, 0 warnings
Report saved to: monitoring/data_quality_report.json
```

---

## Integration

### Manual Checks

Run after each data pipeline execution:
```bash
source venv/bin/activate && \
python fiscal/fiscal_analysis.py && \
python fed/fed_liquidity.py && \
python fed/nyfed_operations.py && \
python fed/nyfed_reference_rates.py && \
python fed/nyfed_settlement_fails.py && \
python fed/liquidity_composite_index.py && \
python monitoring/data_quality_checks.py
```

### Automated Monitoring (Recommended)

Set up a cron job:
```bash
# Edit crontab
crontab -e

# Add daily monitoring at 6 AM (after pipeline runs at 5 AM)
0 6 * * * cd /path/to/treasury-API-interface && source venv/bin/activate && python monitoring/data_quality_checks.py && python monitoring/send_alert.py
```

### CI/CD Integration

Add to your CI/CD pipeline:
```yaml
# Example GitHub Actions
- name: Run Data Quality Checks
  run: |
    source venv/bin/activate
    python monitoring/data_quality_checks.py
  continue-on-error: false  # Fail build if errors detected
```

---

## Alerting

### Custom Alerts

The monitoring script outputs JSON for easy integration with alerting systems:

```python
# Example: Send email alerts on errors
import json

with open('monitoring/data_quality_report.json', 'r') as f:
    report = json.load(f)

if report['summary']['total_issues'] > 0:
    send_email_alert(
        subject=f"Data Quality Alert: {report['summary']['total_issues']} issues",
        body=json.dumps(report['issues'], indent=2)
    )
```

### Slack/Discord Integration

```python
# Example: Post to Slack webhook
import requests

with open('monitoring/data_quality_report.json', 'r') as f:
    report = json.load(f)

if report['summary']['status'] != 'PASS':
    requests.post(
        'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
        json={
            'text': f"⚠️ Data Quality Alert: {report['summary']['status']}",
            'attachments': [{'text': json.dumps(report, indent=2)}]
        }
    )
```

---

## Thresholds

Current monitoring thresholds can be adjusted in `data_quality_checks.py`:

| Check | Threshold | Type |
|-------|-----------|------|
| Fiscal Coverage | < 95% | Warning |
| Fed Liquidity NULL | Any NULL | Error |
| Imputation Rate | > 40% | Warning |
| Household Share Bounds | Outside [0,100]% | Error |
| Calculation Diff | > $1M or 0.01% | Error |
| GDP Consistency | > 1 value/day | Error |

---

## Troubleshooting

### Issue: High Imputation Rate

**Symptom:** Monitoring warns "Imputation rate above threshold (>40%)"

**Causes:**
- Fed data source down for extended period
- Holiday weeks with multiple non-trading days
- API rate limiting

**Actions:**
1. Check Fed data source availability
2. Review imputation flags in database: `SELECT * FROM fed_liquidity_daily WHERE RRP_Imputed = TRUE`
3. If data source is down, consider using backup source or manual input

### Issue: NULL Values in Fed Liquidity

**Symptom:** Monitoring errors "Found NULL values in Net_Liquidity"

**Causes:**
- Forward-fill logic not working
- Database not updated after fix application
- New data source with different format

**Actions:**
1. Re-run `fed/fed_liquidity.py` to regenerate data
2. Check if RRP_Imputed flag is being set correctly
3. Verify database schema has imputation flag columns

### Issue: Household Share Outside Bounds

**Symptom:** Monitoring errors "Found records with household_share outside [0,100]% range"

**Causes:**
- Division by zero (total_spending = 0)
- Negative total_spending (data error)
- Calculation bug

**Actions:**
1. Query problematic records: `SELECT * FROM fiscal_daily_metrics WHERE Household_Share_Pct < 0 OR Household_Share_Pct > 100`
2. Check Total_Spending values for those dates
3. Investigate upstream data source issues

---

## Development

### Adding New Checks

1. Add check method to `DataQualityMonitor` class:
```python
def check_new_metric(self):
    """Check description"""
    # Query data
    result = self.conn.execute("SELECT ...").fetchone()

    # Validate
    if condition_failed:
        self.issues.append({
            'check': 'new_metric',
            'severity': 'ERROR',
            'message': 'Description of issue',
            'details': {...}
        })
    else:
        self.info.append({
            'check': 'new_metric',
            'message': '✅ Check passed'
        })
```

2. Add to `run_all_checks()`:
```python
def run_all_checks(self):
    # ... existing checks ...
    self.check_new_metric()
```

3. Update tests to cover new check

### Testing

```bash
# Run with test database
python -c "
from monitoring.data_quality_checks import DataQualityMonitor
monitor = DataQualityMonitor('test_database.duckdb')
monitor.run_all_checks()
"
```

---

## Related Documentation

- **[../docs/investigation/DATA_DICTIONARY_UPDATES.md](../docs/investigation/DATA_DICTIONARY_UPDATES.md)** - New column documentation
- **[../docs/investigation/FINAL_STATUS_REPORT.md](../FINAL_STATUS_REPORT.md)** - Investigation and fix summary
- **[../scripts/README.md](../scripts/README.md)** - Utility scripts for analysis

**Last Updated:** November 2025
**Status:** ✅ Operational - All checks passing
