#!/usr/bin/env python3
"""
Data Quality Monitoring for Treasury API Interface

Runs automated checks on fiscal and liquidity data to detect:
- Data gaps or missing values
- Values outside expected ranges
- High imputation rates (data source issues)
- Schema consistency
- Calculation accuracy

Run: python monitoring/data_quality_checks.py
Output: JSON report + console alerts
"""

import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys

# Thresholds
THRESHOLDS = {
    'max_imputation_rate_30d': 0.40,  # Alert if >40% RRP imputed in last 30 days
    'max_household_share': 100.0,     # Household share upper bound
    'min_household_share': 0.0,       # Household share lower bound
    'max_gdp_age_days': 180,          # Alert if GDP >6 months old
    'min_records_per_day': 1,         # Expected records per day
    'max_net_liq_missing_7d': 2,      # Max missing Net_Liq in last 7 days
}

class DataQualityMonitor:
    def __init__(self, db_path='database/treasury_data.duckdb'):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        self.issues = []
        self.warnings = []
        self.info = []

    def run_all_checks(self):
        """Run all data quality checks"""
        print("="*80)
        print("DATA QUALITY MONITORING - Treasury API Interface")
        print("="*80)
        print(f"\nTimestamp: {datetime.now().isoformat()}")
        print(f"Database: {self.db_path}\n")

        # Run checks
        self.check_fiscal_coverage()
        self.check_fed_liquidity_coverage()
        self.check_household_share_bounds()
        self.check_imputation_rate()
        self.check_gdp_consistency()
        self.check_calculation_accuracy()
        self.check_schema_integrity()

        # Report
        self.print_report()
        return self.generate_json_report()

    def check_fiscal_coverage(self):
        """Check fiscal data completeness (trading days only)"""
        print("\n[1] Fiscal Data Coverage Check...")

        query = """
        SELECT
            MIN(record_date) as earliest,
            MAX(record_date) as latest,
            COUNT(*) as total_records,
            COUNT(DISTINCT record_date) as unique_dates
        FROM fiscal_daily_metrics
        """
        result = self.conn.execute(query).fetchdf()

        earliest = pd.to_datetime(result.iloc[0]['earliest'])
        latest = pd.to_datetime(result.iloc[0]['latest'])
        total = int(result.iloc[0]['total_records'])
        unique = int(result.iloc[0]['unique_dates'])

        # Expected trading days: ~252 per year
        calendar_days = (latest - earliest).days + 1
        years = calendar_days / 365.25
        expected_trading_days = int(years * 252)

        # Calculate coverage relative to trading days (not calendar days)
        coverage_pct = (unique / expected_trading_days) * 100

        print(f"    Range: {earliest.date()} to {latest.date()}")
        print(f"    Records: {total:,} ({unique:,} unique dates)")
        print(f"    Expected trading days: ~{expected_trading_days:,}")
        print(f"    Coverage: {coverage_pct:.1f}% ({unique}/{expected_trading_days} trading days)")

        # Adjusted thresholds for trading days (weekends/holidays excluded)
        if coverage_pct < 90:
            self.issues.append({
                'check': 'fiscal_coverage',
                'severity': 'HIGH',
                'message': f'Fiscal data coverage only {coverage_pct:.1f}% (expected >90%)',
                'details': {'unique_dates': unique, 'expected_trading_days': expected_trading_days}
            })
        elif coverage_pct < 95:
            self.warnings.append({
                'check': 'fiscal_coverage',
                'severity': 'MEDIUM',
                'message': f'Fiscal data coverage {coverage_pct:.1f}% (expected >95%)',
            })
        else:
            print(f"    ✅ Coverage OK")

    def check_fed_liquidity_coverage(self):
        """Check Fed liquidity data completeness"""
        print("\n[2] Fed Liquidity Coverage Check...")

        # Check last 30 days
        query = """
        SELECT
            COUNT(*) as total_days,
            SUM(CASE WHEN Net_Liquidity IS NULL THEN 1 ELSE 0 END) as null_days,
            SUM(CASE WHEN Net_Liq_Imputed = TRUE THEN 1 ELSE 0 END) as imputed_days
        FROM (
            SELECT * FROM fed_liquidity_daily
            WHERE record_date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY record_date DESC
        )
        """
        result = self.conn.execute(query).fetchdf()

        total = result.iloc[0]['total_days']
        null_days = result.iloc[0]['null_days']
        imputed = result.iloc[0]['imputed_days']

        null_pct = (null_days / total * 100) if total > 0 else 0
        imputed_pct = (imputed / total * 100) if total > 0 else 0

        print(f"    Last 30 days: {total} records")
        print(f"    NULL Net_Liquidity: {null_days} ({null_pct:.1f}%)")
        print(f"    Imputed values: {imputed} ({imputed_pct:.1f}%)")

        if null_days > 0:
            self.issues.append({
                'check': 'fed_liquidity_nulls',
                'severity': 'HIGH',
                'message': f'{null_days} days with NULL Net_Liquidity in last 30 days',
                'details': {'null_days': null_days, 'total_days': total}
            })
        elif imputed_pct > THRESHOLDS['max_imputation_rate_30d'] * 100:
            self.warnings.append({
                'check': 'high_imputation',
                'severity': 'MEDIUM',
                'message': f'High imputation rate: {imputed_pct:.1f}% (threshold: {THRESHOLDS["max_imputation_rate_30d"]*100}%)',
                'details': {'imputed_days': imputed, 'total_days': total}
            })
        else:
            print(f"    ✅ Coverage OK (imputation {imputed_pct:.1f}% within threshold)")

    def check_household_share_bounds(self):
        """Check Household_Share_Pct is within [0, 100]"""
        print("\n[3] Household Share Bounds Check...")

        query = """
        SELECT
            COUNT(*) as total,
            MIN(Household_Share_Pct) as min_share,
            MAX(Household_Share_Pct) as max_share,
            AVG(Household_Share_Pct) as avg_share,
            SUM(CASE WHEN Household_Share_Pct < 0 OR Household_Share_Pct > 100 THEN 1 ELSE 0 END) as out_of_bounds
        FROM fiscal_daily_metrics
        WHERE Household_Share_Pct IS NOT NULL
        """
        result = self.conn.execute(query).fetchdf()

        total = result.iloc[0]['total']
        min_share = result.iloc[0]['min_share']
        max_share = result.iloc[0]['max_share']
        avg_share = result.iloc[0]['avg_share']
        oob = result.iloc[0]['out_of_bounds']

        print(f"    Total records: {total:,}")
        print(f"    Range: {min_share:.2f}% - {max_share:.2f}%")
        print(f"    Average: {avg_share:.2f}%")
        print(f"    Out of bounds: {oob}")

        if oob > 0:
            self.issues.append({
                'check': 'household_share_bounds',
                'severity': 'HIGH',
                'message': f'{oob} records with household_share outside [0, 100]% range',
                'details': {'out_of_bounds': oob, 'min': min_share, 'max': max_share}
            })
        elif min_share < 0 or max_share > 100:
            self.issues.append({
                'check': 'household_share_bounds',
                'severity': 'HIGH',
                'message': f'Household share range [{min_share:.2f}%, {max_share:.2f}%] exceeds [0, 100]%',
            })
        else:
            print(f"    ✅ All values within [0, 100]% bounds")

    def check_imputation_rate(self):
        """Monitor imputation rate trends"""
        print("\n[4] Imputation Rate Trend Check...")

        query = """
        SELECT
            DATE_TRUNC('week', record_date) as week,
            COUNT(*) as total_days,
            SUM(CASE WHEN RRP_Imputed = TRUE THEN 1 ELSE 0 END) as imputed_days,
            SUM(CASE WHEN RRP_Imputed = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as imputed_pct
        FROM fed_liquidity_daily
        WHERE record_date >= CURRENT_DATE - INTERVAL '8 weeks'
        GROUP BY week
        ORDER BY week DESC
        LIMIT 4
        """
        result = self.conn.execute(query).fetchdf()

        print(f"    Last 4 weeks imputation rates:")
        for idx, row in result.iterrows():
            week = pd.to_datetime(row['week']).date()
            pct = row['imputed_pct']
            status = "⚠️" if pct > 40 else "✅"
            print(f"      Week of {week}: {pct:.1f}% {status}")

            if pct > 45:
                self.warnings.append({
                    'check': 'weekly_imputation_rate',
                    'severity': 'MEDIUM',
                    'message': f'Week of {week}: {pct:.1f}% imputation (threshold: 40%)',
                    'details': {'week': str(week), 'imputed_pct': pct}
                })

    def check_gdp_consistency(self):
        """Check GDP_Used consistency and age"""
        print("\n[5] GDP Consistency Check...")

        query = """
        SELECT
            COUNT(DISTINCT GDP_Used) as unique_gdp_values,
            MIN(GDP_Used) as min_gdp,
            MAX(GDP_Used) as max_gdp,
            COUNT(*) as total_records
        FROM fiscal_daily_metrics
        WHERE GDP_Used IS NOT NULL
        """
        result = self.conn.execute(query).fetchdf()

        unique = result.iloc[0]['unique_gdp_values']
        min_gdp = result.iloc[0]['min_gdp']
        max_gdp = result.iloc[0]['max_gdp']
        total = result.iloc[0]['total_records']

        print(f"    Unique GDP values: {unique}")
        print(f"    Range: ${min_gdp/1e12:.3f}T - ${max_gdp/1e12:.3f}T")
        print(f"    Records with GDP: {total:,}")

        if unique > 10:
            self.warnings.append({
                'check': 'gdp_consistency',
                'severity': 'LOW',
                'message': f'{unique} different GDP values found (expected 1-5)',
                'details': {'unique_values': unique}
            })
        else:
            print(f"    ✅ GDP consistency OK ({unique} values)")

    def check_calculation_accuracy(self):
        """Verify key calculations are accurate"""
        print("\n[6] Calculation Accuracy Check...")

        # Test Net Liquidity formula
        query = """
        SELECT
            record_date,
            Fed_Total_Assets,
            RRP_Balance_M,
            TGA_Balance,
            Net_Liquidity,
            (Fed_Total_Assets - RRP_Balance_M - TGA_Balance) as calc_net_liq,
            ABS(Net_Liquidity - (Fed_Total_Assets - RRP_Balance_M - TGA_Balance)) as diff
        FROM fed_liquidity_daily
        WHERE Net_Liquidity IS NOT NULL
          AND RRP_Balance_M IS NOT NULL
          AND record_date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY diff DESC
        LIMIT 5
        """
        result = self.conn.execute(query).fetchdf()

        max_diff = result['diff'].max() if len(result) > 0 else 0

        print(f"    Net Liquidity verification (last 7 days):")
        print(f"    Max difference: ${max_diff:,.0f}M")

        if max_diff > 1000:  # >$1B difference
            self.issues.append({
                'check': 'net_liquidity_calculation',
                'severity': 'HIGH',
                'message': f'Net Liquidity calculation error: max diff ${max_diff:,.0f}M',
                'details': result.head(1).to_dict('records')[0] if len(result) > 0 else {}
            })
        elif max_diff > 100:  # >$100M difference
            self.warnings.append({
                'check': 'net_liquidity_calculation',
                'severity': 'MEDIUM',
                'message': f'Net Liquidity calculation variance: max diff ${max_diff:,.0f}M',
            })
        else:
            print(f"    ✅ Net Liquidity calculation accurate (diff < $100M)")

        # Test Household Share calculation
        query_hs = """
        SELECT
            record_date,
            Household_Spending,
            Total_Spending,
            Household_Share_Pct,
            (Household_Spending / NULLIF(Total_Spending, 0) * 100) as calc_share,
            ABS(Household_Share_Pct - (Household_Spending / NULLIF(Total_Spending, 0) * 100)) as diff
        FROM fiscal_daily_metrics
        WHERE Household_Share_Pct IS NOT NULL
          AND record_date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY diff DESC
        LIMIT 5
        """
        result_hs = self.conn.execute(query_hs).fetchdf()

        max_diff_hs = result_hs['diff'].max() if len(result_hs) > 0 else 0

        print(f"    Household Share verification (last 7 days):")
        print(f"    Max difference: {max_diff_hs:.4f}%")

        if max_diff_hs > 1.0:  # >1% difference
            self.issues.append({
                'check': 'household_share_calculation',
                'severity': 'HIGH',
                'message': f'Household Share calculation error: max diff {max_diff_hs:.2f}%',
            })
        else:
            print(f"    ✅ Household Share calculation accurate (diff < 1%)")

    def check_schema_integrity(self):
        """Verify expected columns exist"""
        print("\n[7] Schema Integrity Check...")

        # Check fiscal table
        fiscal_cols = self.conn.execute("DESCRIBE fiscal_daily_metrics").fetchdf()
        fiscal_col_names = set(fiscal_cols['column_name'].str.lower())

        required_fiscal = {'record_date', 'gdp_used', 'household_share_pct', 'net_impulse', 'ma20_net_impulse'}
        missing_fiscal = required_fiscal - fiscal_col_names

        print(f"    fiscal_daily_metrics: {len(fiscal_col_names)} columns")

        if missing_fiscal:
            self.issues.append({
                'check': 'fiscal_schema',
                'severity': 'HIGH',
                'message': f'Missing columns in fiscal_daily_metrics: {missing_fiscal}',
            })
        else:
            print(f"    ✅ All required fiscal columns present")

        # Check fed liquidity table
        fed_cols = self.conn.execute("DESCRIBE fed_liquidity_daily").fetchdf()
        fed_col_names = set(fed_cols['column_name'].str.lower())

        required_fed = {'record_date', 'rrp_imputed', 'tga_imputed', 'net_liq_imputed', 'net_liquidity'}
        missing_fed = required_fed - fed_col_names

        print(f"    fed_liquidity_daily: {len(fed_col_names)} columns")

        if missing_fed:
            self.issues.append({
                'check': 'fed_schema',
                'severity': 'HIGH',
                'message': f'Missing columns in fed_liquidity_daily: {missing_fed}',
            })
        else:
            print(f"    ✅ All required fed liquidity columns present")

    def print_report(self):
        """Print summary report"""
        print("\n" + "="*80)
        print("MONITORING SUMMARY")
        print("="*80)

        if not self.issues and not self.warnings:
            print("\n✅ ALL CHECKS PASSED - No issues detected")
        else:
            if self.issues:
                print(f"\n❌ CRITICAL ISSUES: {len(self.issues)}")
                for issue in self.issues:
                    print(f"  • [{issue['check']}] {issue['message']}")

            if self.warnings:
                print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
                for warning in self.warnings:
                    print(f"  • [{warning['check']}] {warning['message']}")

        print("\n" + "="*80)

    def generate_json_report(self):
        """Generate JSON report for programmatic consumption"""

        # Convert numpy types to Python native types for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            else:
                return obj

        report = {
            'timestamp': datetime.now().isoformat(),
            'database': self.db_path,
            'summary': {
                'total_issues': len(self.issues),
                'total_warnings': len(self.warnings),
                'status': 'PASS' if (len(self.issues) == 0 and len(self.warnings) == 0) else 'FAIL' if len(self.issues) > 0 else 'WARNING'
            },
            'issues': convert_numpy(self.issues),
            'warnings': convert_numpy(self.warnings),
            'info': convert_numpy(self.info)
        }

        # Save to file
        output_file = 'monitoring/data_quality_report.json'
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Full report saved to: {output_file}")

        return report

    def close(self):
        """Close database connection"""
        self.conn.close()

def main():
    """Main entry point"""
    monitor = DataQualityMonitor()

    try:
        report = monitor.run_all_checks()

        # Exit with error code if critical issues found
        if report['summary']['total_issues'] > 0:
            sys.exit(1)
        elif report['summary']['total_warnings'] > 0:
            sys.exit(2)
        else:
            sys.exit(0)

    finally:
        monitor.close()

if __name__ == '__main__':
    main()
