"""
NY Fed Settlement Fails Fetcher
Fetches primary dealer settlement fails data (failures to deliver/receive).

Settlement fails are a key stress indicator - high fails suggest:
- Liquidity constraints in Treasury market
- Operational issues at primary dealers
- Collateral scarcity

Data published weekly by NY Fed, typically on Thursdays.
"""

import pandas as pd
import sys
import os

# Add fed directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_START_DATE
from utils.api_client import NYFedClient
from utils.data_loader import get_output_path
from utils.report_generator import ReportGenerator


def aggregate_fails(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate settlement fails data.

    Typical fields:
    - failsToReceive: Amount failed to receive
    - failsToDeliver: Amount failed to deliver
    - totalFails: Total fails (receive + deliver)
    - asOfDate: Report date
    - Security categories: Treasury, Agency, MBS, Corporate
    """
    if df.empty:
        return df

    # If we have separate columns for different security types, sum them
    # Common column patterns: treasury_fails, agency_fails, mbs_fails, corporate_fails
    fail_cols = [col for col in df.columns if 'fail' in col.lower() and col != 'totalFails']

    if fail_cols and 'totalFails' not in df.columns:
        # Sum all fails columns to get total
        df['totalFails'] = df[fail_cols].sum(axis=1)

    # Calculate 5-day and 20-day moving averages
    if 'totalFails' in df.columns:
        df['MA5_Fails'] = df['totalFails'].rolling(5).mean()
        df['MA20_Fails'] = df['totalFails'].rolling(20).mean()

        # Calculate Z-score (for stress detection)
        mean = df['totalFails'].mean()
        std = df['totalFails'].std()
        if std > 0:
            df['Fails_ZScore'] = (df['totalFails'] - mean) / std

    return df


def generate_report(df: pd.DataFrame) -> None:
    """
    Generate settlement fails report.
    """
    if df.empty:
        print("\n" + "="*60)
        print("SETTLEMENT FAILS REPORT")
        print("="*60)
        print("\n⚠️  No settlement fails data available")
        print("\nTo add this data manually:")
        print("  1. Visit: https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics")
        print("  2. Download the settlement fails CSV")
        print("  3. Save to: outputs/fed/nyfed_settlement_fails.csv")
        print("  4. Ensure columns include: date, totalFails (or fails by category)")
        print("\nRequired CSV format:")
        print("  date,treasury_fails,agency_fails,mbs_fails,corporate_fails")
        print("  2024-11-20,1234.5,567.8,890.1,123.4")
        print("\nOr simpler format:")
        print("  date,totalFails")
        print("  2024-11-20,2815.8")
        return

    report = ReportGenerator("SETTLEMENT FAILS REPORT", width=60)
    report.print_header("SETTLEMENT FAILS REPORT")

    last_row = df.iloc[-1]
    last_date = df.index[-1].strftime('%Y-%m-%d')

    print(f"Last Date: {last_date}")

    # Main metrics
    report.print_subheader("CURRENT METRICS")

    if 'totalFails' in df.columns:
        report.print_metric("Total Fails", last_row['totalFails'], "M", ",.0f")

        if 'MA20_Fails' in last_row:
            report.print_metric("20-Day Average", last_row['MA20_Fails'], "M", ",.0f")

        if 'Fails_ZScore' in last_row:
            zscore = last_row['Fails_ZScore']
            status = "ELEVATED" if zscore > 2 else "NORMAL" if zscore > -1 else "LOW"
            print(f"  Stress Level (Z-Score): {zscore:.2f} ({status})")

    # By category if available
    category_cols = [col for col in df.columns if any(x in col.lower() for x in ['treasury', 'agency', 'mbs', 'corporate'])]
    if category_cols:
        report.print_subheader("FAILS BY CATEGORY")
        for col in category_cols:
            if col in last_row:
                report.print_metric(col.replace('_', ' ').title(), last_row[col], "M", ",.0f")

    # Recent trend
    print("\n--- RECENT TREND (Last 5 Days) ---")
    cols = ['totalFails', 'MA20_Fails'] if 'totalFails' in df.columns else []
    if cols:
        report.print_table(df[cols], max_rows=5)

    # Export
    print("\n" + "="*60)
    output_path = get_output_path("nyfed_settlement_fails.csv")
    df.to_csv(output_path)
    print(f"Settlement fails data exported to {output_path}")
    print("="*60)


def load_manual_csv() -> pd.DataFrame:
    """
    Load manually downloaded settlement fails CSV if available.
    """
    possible_paths = [
        "outputs/fed/nyfed_settlement_fails.csv",
        "nyfed_settlement_fails.csv",
        "settlement_fails.csv"
    ]

    for path in possible_paths:
        if os.path.exists(path):
            print(f"Loading settlement fails from {path}...")
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            print(f"Loaded {len(df)} records")
            return df

    return pd.DataFrame()


def main():
    print("Starting NY Fed Settlement Fails Fetcher...\n")

    # Try API first
    client = NYFedClient()
    df = client.fetch_settlement_fails(start_date=DEFAULT_START_DATE)

    # If API fails, try to load manual CSV
    if df.empty:
        print("\nAPI fetch unsuccessful. Checking for manual CSV...")
        df = load_manual_csv()

    # Process if we have data
    if not df.empty:
        df = aggregate_fails(df)

    # Generate report
    generate_report(df)

    if df.empty:
        print("\nNote: Settlement fails data enhances the LCI Plumbing component.")
        print("The LCI will still work without it, using repo stress indicators only.")


if __name__ == "__main__":
    main()
