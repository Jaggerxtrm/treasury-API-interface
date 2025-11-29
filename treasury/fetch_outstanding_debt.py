#!/usr/bin/env python3
"""
Fetch Treasury Securities Outstanding (MSPD) Data
Endpoints:
- Summary: /v1/debt/mspd/mspd_table_1
- Marketable Detail: /v1/debt/mspd/mspd_table_3_market
- Non-Marketable Detail: /v1/debt/mspd/mspd_table_3_nonmarket
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from treasury.api_utils import fetch_paginated_data
from utils.db_manager import TimeSeriesDB

# Constants
API_BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
MSPD_SUMMARY_ENDPOINT = "/v1/debt/mspd/mspd_table_1"
MSPD_MARKETABLE_ENDPOINT = "/v1/debt/mspd/mspd_table_3_market"
MSPD_NONMARKETABLE_ENDPOINT = "/v1/debt/mspd/mspd_table_3_nonmarket"

def fetch_mspd_summary(start_date="2023-01-01"):
    """Fetch MSPD Summary (Table 1)."""
    url = f"{API_BASE_URL}{MSPD_SUMMARY_ENDPOINT}"
    params = {
        "filter": f"record_date:gte:{start_date}",
        "page[size]": 1000,
        "sort": "record_date"
    }
    return fetch_paginated_data(url, params)

def fetch_mspd_marketable(start_date="2023-01-01"):
    """Fetch MSPD Marketable Details (Table 3 Market)."""
    url = f"{API_BASE_URL}{MSPD_MARKETABLE_ENDPOINT}"
    params = {
        "filter": f"record_date:gte:{start_date}",
        "page[size]": 1000,
        "sort": "record_date"
    }
    return fetch_paginated_data(url, params)

def fetch_mspd_nonmarketable(start_date="2023-01-01"):
    """Fetch MSPD Non-Marketable Details (Table 3 Non-Market)."""
    url = f"{API_BASE_URL}{MSPD_NONMARKETABLE_ENDPOINT}"
    params = {
        "filter": f"record_date:gte:{start_date}",
        "page[size]": 1000,
        "sort": "record_date"
    }
    return fetch_paginated_data(url, params)

def process_data(df, numeric_cols):
    """Process and clean data."""
    if df.empty:
        return df
        
    # Convert numeric columns
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Scale based on column name
            if "mil_amt" in col:
                # Millions -> Billions
                df[col] = df[col] / 1000
            elif "_amt" in col:
                # Ones -> Billions
                df[col] = df[col] / 1e9
            
            # Round to 4 decimal places
            df[col] = df[col].round(4)
            
    # Convert record_date
    if "record_date" in df.columns:
        df["record_date"] = pd.to_datetime(df["record_date"])
        
    return df

def main():
    print("Starting Treasury Outstanding Debt (MSPD) Fetcher...")
    start_date = "2023-01-01"
    db = TimeSeriesDB()
    
    # 1. Fetch Summary
    print("\n--- Fetching MSPD Summary (Table 1) ---")
    df_summary = fetch_mspd_summary(start_date)
    if not df_summary.empty:
        print(f"Fetched {len(df_summary)} summary records.")
        numeric_cols_summary = ["debt_held_public_mil_amt", "intragov_hold_mil_amt", "total_mil_amt"]
        df_summary = process_data(df_summary, numeric_cols_summary)
        db.upsert_data(df_summary, "mspd_summary", key_col='record_date')
    
    # 2. Fetch Marketable Details
    print("\n--- Fetching MSPD Marketable Details (Table 3) ---")
    df_market = fetch_mspd_marketable(start_date)
    if not df_market.empty:
        print(f"Fetched {len(df_market)} marketable records.")
        numeric_cols_market = ["issued_amt", "inflation_adj_amt", "redeemed_amt", "outstanding_amt", "interest_rate_pct", "yield_pct"]
        df_market = process_data(df_market, numeric_cols_market)
        db.upsert_data(df_market, "mspd_marketable", key_col='record_date')

    # 3. Fetch Non-Marketable Details
    print("\n--- Fetching MSPD Non-Marketable Details (Table 3) ---")
    df_nonmarket = fetch_mspd_nonmarketable(start_date)
    if not df_nonmarket.empty:
        print(f"Fetched {len(df_nonmarket)} non-marketable records.")
        numeric_cols_nonmarket = ["issued_amt", "inflation_adj_amt", "redeemed_amt", "outstanding_amt", "interest_rate_pct", "yield_pct"]
        df_nonmarket = process_data(df_nonmarket, numeric_cols_nonmarket)
        db.upsert_data(df_nonmarket, "mspd_nonmarketable", key_col='record_date')
    
    db.close()
    print("\nDone.")

if __name__ == "__main__":
    main()
