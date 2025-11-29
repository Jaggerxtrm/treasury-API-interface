#!/usr/bin/env python3
"""
Fetch Treasury Issuance (Auctions) Data
Endpoint: /v1/accounting/od/auctions_query
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
AUCTIONS_ENDPOINT = "/v1/accounting/od/auctions_query"

# Fields to fetch
FIELDS = [
    "record_date",
    "issue_date",
    "auction_date",
    "security_type",
    "security_term",
    "cusip",
    "bid_to_cover_ratio",
    "offering_amt",
    "total_accepted",
    "high_yield",
    "comp_accepted",
    "noncomp_accepted",
    "direct_bidder_accepted",
    "indirect_bidder_accepted",
    "primary_dealer_accepted"
]

def fetch_auction_data(start_date="2023-01-01"):
    """
    Fetch auction data from the Treasury API.
    """
    url = f"{API_BASE_URL}{AUCTIONS_ENDPOINT}"
    
    # Construct comma-separated fields string
    fields_str = ",".join(FIELDS)
    
    params = {
        "filter": f"issue_date:gte:{start_date}",
        "fields": fields_str,
        "page[size]": 1000,  # Max page size
        "sort": "issue_date"
    }
    
    df = fetch_paginated_data(url, params)
    return df

def process_data(df):
    """
    Process and clean the auction data.
    """
    if df.empty:
        return df
        
    # Convert numeric columns
    numeric_cols = [
        "bid_to_cover_ratio", "offering_amt", "total_accepted", "high_yield",
        "comp_accepted", "noncomp_accepted", 
        "direct_bidder_accepted", "indirect_bidder_accepted", "primary_dealer_accepted"
    ]
    
    amount_cols = [
        "offering_amt", "total_accepted", 
        "comp_accepted", "noncomp_accepted", 
        "direct_bidder_accepted", "indirect_bidder_accepted", "primary_dealer_accepted"
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Scale amounts to Billions
    for col in amount_cols:
        if col in df.columns:
            df[col] = df[col] / 1e9
            
    # Round all numeric columns to 4 decimal places
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].round(4)
            
    # Convert date columns
    date_cols = ["record_date", "issue_date", "auction_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
            
    return df

def main():
    print("Starting Treasury Auction Data Fetcher...")
    
    # Fetch data
    # Default to fetching last 2 years if running standalone, or configurable
    start_date = "2023-01-01"
    df = fetch_auction_data(start_date)
    
    if df.empty:
        print("No data fetched.")
        return
        
    print(f"Fetched {len(df)} auction records.")
    
    # Process data
    df_clean = process_data(df)
    
    # Save to DuckDB
    db = TimeSeriesDB()
    table_name = "treasury_auctions"
    
    # Use issue_date + cusip as unique key? 
    # The DB manager uses a single key_col for upsert logic (delete where key in new batch).
    # Since multiple auctions can happen on the same day, 'issue_date' is not unique enough if we use it as the sole key for deletion.
    # However, the upsert_data method deletes *all* records for the dates present in the new batch.
    # So if we have multiple auctions on 2023-01-01, and we fetch data for 2023-01-01, 
    # the upsert will delete ALL 2023-01-01 records and insert the new ones.
    # This is correct behavior for full-day updates.
    
    db.upsert_data(df_clean, table_name, key_col='issue_date')
    db.close()
    
    print("Done.")

if __name__ == "__main__":
    main()
