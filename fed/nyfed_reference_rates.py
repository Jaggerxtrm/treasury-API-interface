"""
NY Fed Reference Rates Fetcher
Uses the official NY Fed Markets API to fetch reference rates.

Refactored to use shared utilities.
"""

import pandas as pd
import sys
import os

# Add fed directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import NYFED_RATE_TYPES
from utils.api_client import NYFedClient
from utils.data_loader import get_output_path
from utils.db_manager import TimeSeriesDB


def fetch_all_reference_rates(num_records: int = 1000) -> dict:
    """
    Fetch all available reference rates from NY Fed API.
    
    Returns:
        Dictionary of DataFrames, keyed by rate type
    """
    client = NYFedClient()
    all_rates = {}
    
    for rate_type in NYFED_RATE_TYPES.keys():
        df = client.fetch_reference_rate(rate_type, num_records)
        if not df.empty:
            all_rates[rate_type] = df
    
    return all_rates


def merge_reference_rates(all_rates: dict) -> pd.DataFrame:
    """
    Merge all reference rate DataFrames into a single DataFrame.
    
    Returns:
        DataFrame with columns for each rate type
    """
    if not all_rates:
        return pd.DataFrame()
    
    # Extract just the 'rate' column from each and rename
    rate_series = []
    for rate_type, df in all_rates.items():
        if "rate" in df.columns:
            series = df["rate"].copy()
            series.name = NYFED_RATE_TYPES[rate_type]
            rate_series.append(series)
    
    if not rate_series:
        return pd.DataFrame()
    
    # Merge all into one DataFrame
    merged = pd.concat(rate_series, axis=1, join="outer").sort_index()
    
    return merged


def generate_report(merged_df: pd.DataFrame) -> None:
    """
    Generate a simple report on reference rates.
    """
    if merged_df.empty or len(merged_df.index) == 0:
        print("No data to report")
        return
    
    recent = merged_df.tail(5)
    last_row = merged_df.iloc[-1]
    last_date = merged_df.index[-1].strftime("%Y-%m-%d")
    
    print("\n" + "="*50)
    print("NY FED REFERENCE RATES REPORT")
    print("="*50)
    print(f"Last Date: {last_date}")
    
    print("\n--- CURRENT RATES ---")
    for col in merged_df.columns:
        if col in last_row and not pd.isna(last_row[col]):
            print(f"{col:20s}: {last_row[col]:.2f}%")
    
    print("\n--- SPREADS ---")
    if "SOFR_Rate" in last_row and "BGCR_Rate" in last_row:
        spread = (last_row["SOFR_Rate"] - last_row["BGCR_Rate"]) * 100
        print(f"SOFR - BGCR:         {spread:.1f} bps")
    
    if "SOFR_Rate" in last_row and "TGCR_Rate" in last_row:
        spread = (last_row["SOFR_Rate"] - last_row["TGCR_Rate"]) * 100
        print(f"SOFR - TGCR:         {spread:.1f} bps")
    
    if "BGCR_Rate" in last_row and "TGCR_Rate" in last_row:
        spread = (last_row["BGCR_Rate"] - last_row["TGCR_Rate"]) * 100
        print(f"BGCR - TGCR:         {spread:.1f} bps")
    
    print("\n--- RECENT TREND (Last 20 Trading Days) ---")
    trend_data = merged_df.tail(20).sort_index(ascending=False)
    print(trend_data.to_string(float_format="{:.2f}".format))
    
    # Export
    # Export to Database
    print("\n💾 Saving to DuckDB...")
    try:
        db = TimeSeriesDB("database/treasury_data.duckdb")
        
        # Reset index to make date a column
        df_save = merged_df.reset_index()
        # The index name from the DataFrame becomes the column name
        index_col_name = df_save.columns[0]  # First column after reset_index
        if index_col_name != 'record_date':
            df_save = df_save.rename(columns={index_col_name: 'record_date'})
            
        db.upsert_data(df_save, "nyfed_reference_rates", key_col="record_date")
        print("✅ Data successfully saved to database/treasury_data.duckdb")
        db.close()
    except Exception as e:
        print(f"❌ Database save failed: {e}")


def main():
    print("Starting NY Fed Reference Rates Fetcher...")
    
    # Fetch all rates
    all_rates = fetch_all_reference_rates(num_records=1000)
    
    # Merge into single DataFrame
    merged = merge_reference_rates(all_rates)
    
    if merged.empty:
        print("No reference rate data fetched")
        return
    
    # Generate report
    generate_report(merged)
    
    print("\nReference rates fetch complete.")


if __name__ == "__main__":
    main()
