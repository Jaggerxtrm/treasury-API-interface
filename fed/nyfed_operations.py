"""
NY Fed Operations Fetcher
Fetches repo operations, SOMA holdings, and primary dealer statistics.

Refactored to use shared utilities.
"""

import pandas as pd
import sys
import os

# Add fed directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_START_DATE
from utils.api_client import NYFedClient
from utils.data_loader import get_output_path
from utils.report_generator import ReportGenerator, format_currency, format_bps


def calculate_repo_metrics(df_repo: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate derived metrics for repo operations.
    """
    if df_repo.empty:
        return df_repo

    # Daily change in repo usage
    if 'totalAmtAccepted' in df_repo.columns:
        df_repo['repo_change'] = df_repo['totalAmtAccepted'].diff()

    # Moving averages (use LCI-compatible column names)
    if 'totalAmtAccepted' in df_repo.columns:
        df_repo['MA5_Repo_Accepted'] = df_repo['totalAmtAccepted'].rolling(5).mean()
        df_repo['MA20_Repo_Accepted'] = df_repo['totalAmtAccepted'].rolling(20).mean()

    # Calculate submission ratio (for LCI Plumbing component)
    # Ratio = totalAmtSubmitted / operationLimit
    # This measures how much of the facility capacity is being used
    if 'totalAmtSubmitted' in df_repo.columns and 'operationLimit' in df_repo.columns:
        df_repo['submission_ratio'] = df_repo['totalAmtSubmitted'] / df_repo['operationLimit']
        # Handle division by zero or NaN
        df_repo['submission_ratio'] = df_repo['submission_ratio'].fillna(0)

    return df_repo


def generate_report(df_repo: pd.DataFrame, df_rrp: pd.DataFrame) -> None:
    """
    Generate a consolidated report.
    """
    report = ReportGenerator("NY FED OPERATIONS REPORT", width=60)
    
    # Main header
    report.print_header("NY FED OPERATIONS REPORT")
    
    if not df_repo.empty:
        last_repo = df_repo.iloc[-1]
        last_date = df_repo.index[-1].strftime('%Y-%m-%d')
        
        print(f"Last Date: {last_date}")
        
        # Repo Operations Section
        report.print_subheader("REPO OPERATIONS (Liquidity Injection)")
        
        metrics = {}
        if 'totalAmtAccepted' in last_repo:
            metrics['Total Accepted'] = {
                'value': last_repo['totalAmtAccepted'],
                'unit': 'M',
                'format': ',.0f'
            }
        
        if 'totalAmtSubmitted' in last_repo:
            metrics['Total Submitted'] = {
                'value': last_repo['totalAmtSubmitted'],
                'unit': 'M',
                'format': ',.0f'
            }
        
        if 'weightedAvgRate' in last_repo:
            metrics['Weighted Avg Rate'] = {
                'value': last_repo['weightedAvgRate'],
                'unit': '%',
                'format': '.2f'
            }
        
        if 'repo_change' in last_repo:
            metrics['Daily Change'] = {
                'value': last_repo['repo_change'],
                'unit': 'M',
                'format': '+,.0f'
            }
        
        for label, value_dict in metrics.items():
            report.print_metric(
                label,
                value_dict['value'],
                value_dict.get('unit', ''),
                value_dict.get('format', '.2f')
            )
        
        # Recent trend
        print("\n--- RECENT REPO TREND (Last 5 Days) ---")
        cols = ['totalAmtAccepted', 'totalAmtSubmitted', 'weightedAvgRate']
        cols = [c for c in cols if c in df_repo.columns]
        if cols:
            report.print_table(df_repo[cols], max_rows=5)
    
    if not df_rrp.empty:
        last_rrp = df_rrp.iloc[-1]
        
        # RRP Operations Section
        report.print_subheader("REVERSE REPO OPERATIONS (Liquidity Drain)")
        
        metrics = {}
        if 'totalAmtAccepted' in last_rrp:
            metrics['RRP Balance'] = {
                'value': last_rrp['totalAmtAccepted'],
                'unit': 'B',
                'format': ',.0f'
            }
        
        if 'totalAmtSubmitted' in last_rrp:
            metrics['Total Submitted'] = {
                'value': last_rrp['totalAmtSubmitted'],
                'unit': 'B',
                'format': ',.0f'
            }
        
        if 'weightedAvgRate' in last_rrp:
            metrics['Rate'] = {
                'value': last_rrp['weightedAvgRate'],
                'unit': '%',
                'format': '.2f'
            }
        
        for label, value_dict in metrics.items():
            report.print_metric(
                label,
                value_dict['value'],
                value_dict.get('unit', ''),
                value_dict.get('format', '.2f')
            )
        
        # Recent trend
        print("\n--- RECENT RRP TREND (Last 5 Days) ---")
        cols = ['totalAmtAccepted', 'totalAmtSubmitted', 'weightedAvgRate']
        cols = [c for c in cols if c in df_rrp.columns]
        if cols:
            report.print_table(df_rrp[cols], max_rows=5)
    
    # Export
    print("\n" + "="*60)
    if not df_repo.empty:
        repo_path = get_output_path("nyfed_repo_ops.csv")
        df_repo.to_csv(repo_path)
        print(f"Repo operations exported to {repo_path}")
    
    if not df_rrp.empty:
        rrp_path = get_output_path("nyfed_rrp_ops.csv")
        df_rrp.to_csv(rrp_path)
        print(f"RRP operations exported to {rrp_path}")
    
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
    
    # Generate report
    generate_report(df_repo, df_rrp)
    
    print("\nNY Fed operations fetch complete.")


if __name__ == "__main__":
    main()
