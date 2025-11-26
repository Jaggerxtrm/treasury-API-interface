"""
NY Fed Operations Fetcher
Fetches repo operations, SOMA holdings, and primary dealer statistics.

Refactored to use shared utilities.
"""

import pandas as pd
import numpy as np
import json
import sys
import os

# Add fed directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_START_DATE
from utils.api_client import NYFedClient
from utils.data_loader import get_output_path
from utils.report_generator import ReportGenerator, format_currency, format_bps
from utils.db_manager import TimeSeriesDB


def extract_collateral_breakdown(details: list) -> dict:
    """
    Extract collateral type breakdown from operation details.
    
    Returns dict with:
        - Treasury_Accepted: Amount accepted for Treasury collateral
        - Agency_Accepted: Amount accepted for Agency collateral
        - MBS_Accepted: Amount accepted for Mortgage-Backed collateral
    """
    breakdown = {
        'Treasury_Accepted': 0,
        'Agency_Accepted': 0,
        'MBS_Accepted': 0,
        'Treasury_Rate': None,
        'Agency_Rate': None,
        'MBS_Rate': None,
    }
    
    if not details or not isinstance(details, list):
        return breakdown
    
    for item in details:
        if not isinstance(item, dict):
            continue
        sec_type = item.get('securityType', '')
        amt_accepted = item.get('amtAccepted', 0) or 0
        rate = item.get('percentWeightedAverageRate')
        
        if 'Treasury' in sec_type:
            breakdown['Treasury_Accepted'] = amt_accepted
            breakdown['Treasury_Rate'] = rate
        elif 'Agency' in sec_type:
            breakdown['Agency_Accepted'] = amt_accepted
            breakdown['Agency_Rate'] = rate
        elif 'Mortgage' in sec_type or 'MBS' in sec_type:
            breakdown['MBS_Accepted'] = amt_accepted
            breakdown['MBS_Rate'] = rate
    
    return breakdown


def calculate_repo_metrics(df_repo: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate derived metrics for repo operations.
    Includes daily, weekly, monthly, and quarterly changes.
    Also extracts collateral type breakdown (Treasury vs MBS vs Agency).
    """
    if df_repo.empty:
        return df_repo

    # Extract collateral breakdown from 'details' column
    if 'details' in df_repo.columns:
        breakdowns = df_repo['details'].apply(extract_collateral_breakdown)
        breakdown_df = pd.DataFrame(breakdowns.tolist(), index=df_repo.index)
        
        # Add collateral columns to main dataframe
        for col in ['Treasury_Accepted', 'Agency_Accepted', 'MBS_Accepted']:
            df_repo[col] = breakdown_df[col]
        
        # Calculate percentages
        total = df_repo['totalAmtAccepted'].replace(0, np.nan)
        df_repo['Treasury_Pct'] = (df_repo['Treasury_Accepted'] / total * 100).fillna(0)
        df_repo['MBS_Pct'] = (df_repo['MBS_Accepted'] / total * 100).fillna(0)
        df_repo['Agency_Pct'] = (df_repo['Agency_Accepted'] / total * 100).fillna(0)

    # Changes in repo usage at different time horizons
    if 'totalAmtAccepted' in df_repo.columns:
        df_repo['repo_daily_change'] = df_repo['totalAmtAccepted'].diff(1)
        df_repo['repo_weekly_change'] = df_repo['totalAmtAccepted'].diff(5)
        df_repo['repo_monthly_change'] = df_repo['totalAmtAccepted'].diff(22)
        df_repo['repo_quarterly_change'] = df_repo['totalAmtAccepted'].diff(65)

    # Moving averages (use LCI-compatible column names)
    if 'totalAmtAccepted' in df_repo.columns:
        df_repo['MA5_Repo_Accepted'] = df_repo['totalAmtAccepted'].rolling(5, min_periods=3).mean()
        df_repo['MA20_Repo_Accepted'] = df_repo['totalAmtAccepted'].rolling(20, min_periods=10).mean()

    # Calculate submission ratio (for LCI Plumbing component)
    # Ratio = totalAmtSubmitted / operationLimit
    # This measures how much of the facility capacity is being used
    if 'totalAmtSubmitted' in df_repo.columns and 'operationLimit' in df_repo.columns:
        df_repo['submission_ratio'] = df_repo['totalAmtSubmitted'] / df_repo['operationLimit']
        # Handle division by zero or NaN
        df_repo['submission_ratio'] = df_repo['submission_ratio'].fillna(0)

    return df_repo


def calculate_rrp_metrics(df_rrp: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate derived metrics for reverse repo operations.
    Includes daily, weekly, monthly, and quarterly changes.
    """
    if df_rrp.empty:
        return df_rrp

    # Changes in RRP usage at different time horizons
    if 'totalAmtAccepted' in df_rrp.columns:
        df_rrp['rrp_daily_change'] = df_rrp['totalAmtAccepted'].diff(1)
        df_rrp['rrp_weekly_change'] = df_rrp['totalAmtAccepted'].diff(5)
        df_rrp['rrp_monthly_change'] = df_rrp['totalAmtAccepted'].diff(22)
        df_rrp['rrp_quarterly_change'] = df_rrp['totalAmtAccepted'].diff(65)

    # Moving averages
    if 'totalAmtAccepted' in df_rrp.columns:
        df_rrp['MA5_RRP'] = df_rrp['totalAmtAccepted'].rolling(5, min_periods=3).mean()
        df_rrp['MA20_RRP'] = df_rrp['totalAmtAccepted'].rolling(20, min_periods=10).mean()

    return df_rrp


def format_value_safe(value, divisor=1e9, fmt='+,.2f'):
    """Safely format a value, handling NaN."""
    if pd.isna(value) or not np.isfinite(value):
        return "N/A"
    return f"{value / divisor:{fmt}}"


def generate_report(df_repo: pd.DataFrame, df_rrp: pd.DataFrame) -> None:
    """
    Generate a consolidated report.
    All values displayed in BILLIONS ($B) with proper formatting.
    """
    report = ReportGenerator("NY FED OPERATIONS REPORT", width=60)
    
    # Main header
    report.print_header("NY FED OPERATIONS REPORT")
    
    if not df_repo.empty and len(df_repo.index) > 0:
        last_repo = df_repo.iloc[-1]
        last_date = df_repo.index[-1].strftime('%Y-%m-%d')
        
        print(f"Last Date: {last_date}")
        
        # Repo Operations Section
        report.print_subheader("REPO OPERATIONS (Liquidity Injection)")
        
        # Convert all values to billions for display
        metrics = {}
        if 'totalAmtAccepted' in last_repo:
            metrics['Total Accepted'] = {
                'value': last_repo['totalAmtAccepted'] / 1e9,  # Convert to billions
                'unit': 'B',
                'format': ',.2f'
            }
        
        if 'totalAmtSubmitted' in last_repo:
            metrics['Total Submitted'] = {
                'value': last_repo['totalAmtSubmitted'] / 1e9,  # Convert to billions
                'unit': 'B',
                'format': ',.2f'
            }
        
        if 'weightedAvgRate' in last_repo:
            metrics['Weighted Avg Rate'] = {
                'value': last_repo['weightedAvgRate'],
                'unit': '%',
                'format': '.2f'
            }
        
        # Time horizon changes (Daily, Weekly, Monthly, Quarterly)
        if 'repo_daily_change' in last_repo and pd.notna(last_repo['repo_daily_change']):
            metrics['Daily Change'] = {
                'value': last_repo['repo_daily_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        if 'repo_weekly_change' in last_repo and pd.notna(last_repo['repo_weekly_change']):
            metrics['Weekly Change (5D)'] = {
                'value': last_repo['repo_weekly_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        if 'repo_monthly_change' in last_repo and pd.notna(last_repo['repo_monthly_change']):
            metrics['Monthly Change (22D)'] = {
                'value': last_repo['repo_monthly_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        if 'repo_quarterly_change' in last_repo and pd.notna(last_repo['repo_quarterly_change']):
            metrics['Quarterly Change (65D)'] = {
                'value': last_repo['repo_quarterly_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        for label, value_dict in metrics.items():
            report.print_metric(
                label,
                value_dict['value'],
                value_dict.get('unit', ''),
                value_dict.get('format', '.2f')
            )
        
        # Collateral Breakdown (Treasury vs MBS vs Agency)
        if 'Treasury_Accepted' in last_repo:
            print("\n--- COLLATERAL BREAKDOWN ---")
            total = last_repo['totalAmtAccepted']
            
            treasury = last_repo.get('Treasury_Accepted', 0) or 0
            mbs = last_repo.get('MBS_Accepted', 0) or 0
            agency = last_repo.get('Agency_Accepted', 0) or 0
            
            treasury_pct = (treasury / total * 100) if total > 0 else 0
            mbs_pct = (mbs / total * 100) if total > 0 else 0
            agency_pct = (agency / total * 100) if total > 0 else 0
            
            print(f"Treasury:            ${treasury / 1e9:,.2f} B ({treasury_pct:5.1f}%)")
            print(f"Mortgage-Backed:     ${mbs / 1e9:,.2f} B ({mbs_pct:5.1f}%)")
            if agency > 0:
                print(f"Agency:              ${agency / 1e9:,.2f} B ({agency_pct:5.1f}%)")
            
            # Visual bar for breakdown
            if total > 0:
                bar_width = 40
                t_bar = int(treasury_pct / 100 * bar_width)
                m_bar = int(mbs_pct / 100 * bar_width)
                a_bar = bar_width - t_bar - m_bar
                print(f"\n[{'T'*t_bar}{'M'*m_bar}{'.'*a_bar}]")
                print(f" T=Treasury  M=MBS  .=Other")
        
        # Recent trend - convert to billions for display
        print("\n--- RECENT REPO TREND (Last 20 Trading Days) ---")
        cols = ['totalAmtAccepted', 'Treasury_Accepted', 'MBS_Accepted']
        cols = [c for c in cols if c in df_repo.columns]
        if cols:
            repo_display = df_repo[cols].copy()
            for col in cols:
                repo_display[col] = repo_display[col] / 1e9  # Convert to billions
            # Rename columns for clarity
            new_names = {
                'totalAmtAccepted': 'Total_B',
                'Treasury_Accepted': 'Treasury_B',
                'MBS_Accepted': 'MBS_B'
            }
            repo_display.columns = [new_names.get(c, c) for c in cols]
            report.print_table(repo_display, max_rows=20)
    
    if not df_rrp.empty:
        last_rrp = df_rrp.iloc[-1]
        
        # RRP Operations Section
        report.print_subheader("REVERSE REPO OPERATIONS (Liquidity Drain)")
        
        # All values in billions
        metrics = {}
        if 'totalAmtAccepted' in last_rrp:
            metrics['RRP Balance'] = {
                'value': last_rrp['totalAmtAccepted'] / 1e9,
                'unit': 'B',
                'format': ',.2f'
            }
        
        if 'totalAmtSubmitted' in last_rrp:
            metrics['Total Submitted'] = {
                'value': last_rrp['totalAmtSubmitted'] / 1e9,
                'unit': 'B',
                'format': ',.2f'
            }
        
        if 'weightedAvgRate' in last_rrp:
            metrics['Rate'] = {
                'value': last_rrp['weightedAvgRate'],
                'unit': '%',
                'format': '.2f'
            }
        
        # Time horizon changes for RRP
        if 'rrp_daily_change' in last_rrp and pd.notna(last_rrp['rrp_daily_change']):
            metrics['Daily Change'] = {
                'value': last_rrp['rrp_daily_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        if 'rrp_weekly_change' in last_rrp and pd.notna(last_rrp['rrp_weekly_change']):
            metrics['Weekly Change (5D)'] = {
                'value': last_rrp['rrp_weekly_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        if 'rrp_monthly_change' in last_rrp and pd.notna(last_rrp['rrp_monthly_change']):
            metrics['Monthly Change (22D)'] = {
                'value': last_rrp['rrp_monthly_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        if 'rrp_quarterly_change' in last_rrp and pd.notna(last_rrp['rrp_quarterly_change']):
            metrics['Quarterly Change (65D)'] = {
                'value': last_rrp['rrp_quarterly_change'] / 1e9,
                'unit': 'B',
                'format': '+,.2f'
            }
        
        for label, value_dict in metrics.items():
            report.print_metric(
                label,
                value_dict['value'],
                value_dict.get('unit', ''),
                value_dict.get('format', '.2f')
            )
        
        # Recent trend - convert to billions for display
        print("\n--- RECENT RRP TREND (Last 20 Trading Days) ---")
        cols = ['totalAmtAccepted', 'totalAmtSubmitted']
        cols = [c for c in cols if c in df_rrp.columns]
        if cols:
            rrp_display = df_rrp[cols].copy()
            for col in cols:
                rrp_display[col] = rrp_display[col] / 1e9  # Convert to billions
            rrp_display.columns = ['RRP_Balance_B', 'Submitted_B']
            report.print_table(rrp_display, max_rows=20)
    
    # Export
    # Export to Database
    print("\n" + "="*60)
    print("💾 Saving to DuckDB...")
    try:
        db = TimeSeriesDB("database/treasury_data.duckdb")
        
        if not df_repo.empty:
            # Reset index to make date a column
            df_repo_save = df_repo.reset_index()
            if 'index' in df_repo_save.columns:
                df_repo_save = df_repo_save.rename(columns={'index': 'record_date'})
            elif 'date' in df_repo_save.columns: # Sometimes index name is date
                df_repo_save = df_repo_save.rename(columns={'date': 'record_date'})

            # DIAGNOSTIC: Print DataFrame info before upsert
            print("\n🔍 === DIAGNOSTIC INFO ===")
            print("DataFrame dtypes:")
            print(df_repo_save.dtypes)
            print("\nNull values count:")
            print(df_repo_save.isna().sum())
            print("\nSample data (first 2 rows):")
            print(df_repo_save.head(2))

            # FIXED: Convert ALL columns to appropriate types before upsert
            # Handle object columns - convert nested structures to JSON strings
            object_cols = df_repo_save.select_dtypes(include=['object']).columns.tolist()
            for col in object_cols:
                # Convert nested structures (lists, dicts) to JSON strings
                if col in ['details', 'propositions']:
                    df_repo_save[col] = df_repo_save[col].apply(
                        lambda x: json.dumps(x) if isinstance(x, (list, dict)) else str(x) if pd.notna(x) else None
                    )
                else:
                    df_repo_save[col] = df_repo_save[col].astype(str)

            # Handle numeric columns that might have been converted to float due to NaN
            # Convert them back to proper numeric types or replace NaN with appropriate defaults
            numeric_cols = df_repo_save.select_dtypes(include=['float64', 'int64']).columns.tolist()
            for col in numeric_cols:
                if df_repo_save[col].isna().any():
                    print(f"⚠️  Column '{col}' contains NaN values, filling with 0")
                    df_repo_save[col] = df_repo_save[col].fillna(0)

            db.upsert_data(df_repo_save, "nyfed_repo_ops", key_col="record_date")
            print("✅ Repo operations saved to 'nyfed_repo_ops'")
        
        if not df_rrp.empty:
            # Reset index to make date a column
            df_rrp_save = df_rrp.reset_index()
            if 'index' in df_rrp_save.columns:
                df_rrp_save = df_rrp_save.rename(columns={'index': 'record_date'})
            elif 'date' in df_rrp_save.columns:
                df_rrp_save = df_rrp_save.rename(columns={'date': 'record_date'})

            # FIXED: Convert ALL object columns to appropriate types before upsert
            object_cols = df_rrp_save.select_dtypes(include=['object']).columns.tolist()
            for col in object_cols:
                # Convert nested structures (lists, dicts) to JSON strings
                if col in ['details', 'propositions']:
                    df_rrp_save[col] = df_rrp_save[col].apply(
                        lambda x: json.dumps(x) if isinstance(x, (list, dict)) else str(x) if pd.notna(x) else None
                    )
                else:
                    df_rrp_save[col] = df_rrp_save[col].astype(str)

            db.upsert_data(df_rrp_save, "nyfed_rrp_ops", key_col="record_date")
            print("✅ RRP operations saved to 'nyfed_rrp_ops'")
            
        db.close()
    except Exception as e:
        print(f"❌ Database save failed: {e}")
    
    print("="*60)


def main():
    print("Starting NY Fed Operations Fetcher...")
    
    # Initialize client
    client = NYFedClient()
    
    # Fetch repo operations (includes both repo and reverse repo)
    print("\nFetching Repo Operations...")
    df_repo = client.fetch_repo_operations(
        start_date=DEFAULT_START_DATE,
        operation_type="Repo"
    )
    
    print("\nFetching Reverse Repo Operations...")
    df_rrp = client.fetch_repo_operations(
        start_date=DEFAULT_START_DATE,
        operation_type="Reverse Repo"
    )
    
    # Aggregate data in case of multiple operations per day
    # Only sum numeric columns, take first for others
    if not df_repo.empty:
        # Separate numeric and non-numeric columns
        numeric_cols = df_repo.select_dtypes(include=['number']).columns.tolist()
        non_numeric_cols = df_repo.select_dtypes(exclude=['number']).columns.tolist()

        # Aggregate: sum numeric, first for non-numeric
        agg_dict = {col: 'sum' for col in numeric_cols}
        agg_dict.update({col: 'first' for col in non_numeric_cols})

        df_repo = df_repo.groupby(df_repo.index).agg(agg_dict)
        df_repo = calculate_repo_metrics(df_repo)

    if not df_rrp.empty:
        # Same aggregation logic for RRP
        numeric_cols = df_rrp.select_dtypes(include=['number']).columns.tolist()
        non_numeric_cols = df_rrp.select_dtypes(exclude=['number']).columns.tolist()

        agg_dict = {col: 'sum' for col in numeric_cols}
        agg_dict.update({col: 'first' for col in non_numeric_cols})

        df_rrp = df_rrp.groupby(df_rrp.index).agg(agg_dict)
        df_rrp = calculate_rrp_metrics(df_rrp)  # NEW: Calculate RRP metrics
    
    # Generate report
    generate_report(df_repo, df_rrp)
    
    print("\nNY Fed operations fetch complete.")


if __name__ == "__main__":
    main()
