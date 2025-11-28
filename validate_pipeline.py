#!/usr/bin/env python3
"""
Pipeline Validation Script
Validates database integrity, record counts, and data quality
"""

import duckdb
import sys
from datetime import datetime
from pathlib import Path

# Expected record counts from reference run
EXPECTED_COUNTS = {
    'fiscal_daily_metrics': 977,
    'fiscal_weekly_metrics': 204,
    'fed_liquidity_daily': 1428,
    'nyfed_repo_ops': 974,
    'nyfed_rrp_ops': 974,
    'nyfed_reference_rates': 273,
    'nyfed_settlement_fails': 202,
    'liquidity_composite_index': 1426,
    'ofr_financial_stress': 122
}

def validate_database(db_path='database/treasury_data.duckdb'):
    """Validate database schema and data integrity"""

    print("=" * 80)
    print("TREASURY API PIPELINE VALIDATION")
    print("=" * 80)
    print(f"\nValidation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {db_path}\n")

    if not Path(db_path).exists():
        print(f"❌ ERROR: Database not found at {db_path}")
        return False

    try:
        conn = duckdb.connect(db_path, read_only=True)

        # Get all tables
        tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        tables = conn.execute(tables_query).fetchall()
        table_names = [t[0] for t in tables]

        print(f"✓ Database connected successfully")
        print(f"✓ Found {len(table_names)} tables: {', '.join(table_names)}\n")

        # Validation results
        validation_results = {
            'tables_found': len(table_names),
            'tables_expected': len(EXPECTED_COUNTS),
            'record_count_matches': 0,
            'record_count_mismatches': [],
            'missing_tables': [],
            'null_checks': [],
            'date_range_checks': []
        }

        print("-" * 80)
        print("TABLE VALIDATION - Record Counts")
        print("-" * 80)

        for table, expected_count in EXPECTED_COUNTS.items():
            if table not in table_names:
                print(f"❌ {table}: MISSING")
                validation_results['missing_tables'].append(table)
                continue

            # Get actual count
            count_query = f"SELECT COUNT(*) FROM {table}"
            actual_count = conn.execute(count_query).fetchone()[0]

            # Check if counts match (allow small variance for recent data)
            match = abs(actual_count - expected_count) <= 5
            status = "✓" if match else "⚠️"

            if match:
                validation_results['record_count_matches'] += 1
            else:
                validation_results['record_count_mismatches'].append({
                    'table': table,
                    'expected': expected_count,
                    'actual': actual_count,
                    'diff': actual_count - expected_count
                })

            print(f"{status} {table:30s}: {actual_count:6d} records (expected: {expected_count:6d})")

        print("\n" + "-" * 80)
        print("DATA QUALITY CHECKS - NULL Values in Critical Columns")
        print("-" * 80)

        # Critical columns to check for NULLs
        critical_checks = [
            ('fiscal_daily_metrics', 'record_date'),
            ('fiscal_daily_metrics', 'Total_Spending'),
            ('fiscal_daily_metrics', 'Total_Taxes'),
            ('fiscal_daily_metrics', 'TGA_Balance'),
            ('fed_liquidity_daily', 'record_date'),
            ('fed_liquidity_daily', 'Net_Liquidity'),
            ('liquidity_composite_index', 'record_date'),
            ('liquidity_composite_index', 'LCI'),
        ]

        for table, column in critical_checks:
            if table not in table_names:
                continue

            null_query = f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL"
            null_count = conn.execute(null_query).fetchone()[0]

            status = "✓" if null_count == 0 else "⚠️"
            print(f"{status} {table}.{column:25s}: {null_count} NULL values")

            if null_count > 0:
                validation_results['null_checks'].append({
                    'table': table,
                    'column': column,
                    'null_count': null_count
                })

        print("\n" + "-" * 80)
        print("DATE RANGE CHECKS")
        print("-" * 80)

        # Check date ranges for key tables
        date_tables = [
            ('fiscal_daily_metrics', 'record_date'),
            ('fed_liquidity_daily', 'record_date'),
            ('liquidity_composite_index', 'record_date'),
        ]

        for table, date_col in date_tables:
            if table not in table_names:
                continue

            date_query = f"""
                SELECT
                    MIN({date_col}) as min_date,
                    MAX({date_col}) as max_date,
                    COUNT(DISTINCT {date_col}) as unique_dates
                FROM {table}
            """
            result = conn.execute(date_query).fetchone()
            min_date, max_date, unique_dates = result

            print(f"✓ {table:30s}: {min_date} to {max_date} ({unique_dates} dates)")
            validation_results['date_range_checks'].append({
                'table': table,
                'min_date': str(min_date),
                'max_date': str(max_date),
                'unique_dates': unique_dates
            })

        # Summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        all_passed = (
            len(validation_results['missing_tables']) == 0 and
            len(validation_results['record_count_mismatches']) <= 2 and  # Allow minor mismatches
            len(validation_results['null_checks']) == 0
        )

        print(f"\nTables Found: {validation_results['tables_found']}/{validation_results['tables_expected']}")
        print(f"Record Count Matches: {validation_results['record_count_matches']}/{len(EXPECTED_COUNTS)}")
        print(f"Missing Tables: {len(validation_results['missing_tables'])}")
        print(f"NULL Value Issues: {len(validation_results['null_checks'])}")

        if validation_results['missing_tables']:
            print(f"\n❌ Missing tables: {', '.join(validation_results['missing_tables'])}")

        if validation_results['record_count_mismatches']:
            print(f"\n⚠️  Record count discrepancies:")
            for mismatch in validation_results['record_count_mismatches']:
                diff_sign = "+" if mismatch['diff'] > 0 else ""
                print(f"   - {mismatch['table']}: {mismatch['actual']} ({diff_sign}{mismatch['diff']})")

        if validation_results['null_checks']:
            print(f"\n⚠️  NULL value warnings:")
            for check in validation_results['null_checks']:
                print(f"   - {check['table']}.{check['column']}: {check['null_count']} NULLs")

        print(f"\n{'✅ VALIDATION PASSED' if all_passed else '⚠️  VALIDATION COMPLETED WITH WARNINGS'}")
        print("=" * 80)

        conn.close()
        return all_passed

    except Exception as e:
        print(f"❌ ERROR during validation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = validate_database()
    sys.exit(0 if success else 1)
