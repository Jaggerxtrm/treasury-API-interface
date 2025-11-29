#!/usr/bin/env python3
"""
Generate Debt Raw Report
Creates a markdown report containing:
1. Last 30 days of auction results
2. Latest full report of MSPD (Summary, Marketable, Non-Marketable)
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from treasury.fetch_issuance_data import fetch_auction_data, process_data as process_auction_data
from treasury.fetch_outstanding_debt import fetch_mspd_summary, fetch_mspd_marketable, fetch_mspd_nonmarketable, process_data as process_mspd_data
from utils.db_manager import TimeSeriesDB
from cleanup_empty_lines import integrated_cleanup_for_current_file

def get_db_connection():
    return TimeSeriesDB()

def generate_markdown_table(df, title):
    if df.empty:
        return f"## {title}\n\nNo data available.\n\n"
    
    # Create a copy for formatting to avoid modifying the original DF if reused
    df_fmt = df.copy()
    
    # Identify columns to format with " B"
    # We look for columns that likely contain amounts based on our known schema
    # Auctions: offering_amt, total_accepted, *_accepted
    # MSPD: *_amt
    
    for col in df_fmt.columns:
        if (col.endswith("_amt") or col.endswith("_accepted")) and pd.api.types.is_numeric_dtype(df_fmt[col]):
            # Format as string with " B"
            df_fmt[col] = df_fmt[col].apply(lambda x: f"{x:.4f} B" if pd.notnull(x) else x)
            
    markdown = f"## {title}\n\n"
    markdown += df_fmt.to_markdown(index=False)
    markdown += "\n\n"
    return markdown

def main():
    print("Generating Debt Raw Report...")
    
    # 1. Ensure data is fresh (optional, but good practice)
    # We'll fetch the last 30 days for auctions to be sure
    print("Refreshing auction data...")
    start_date_30d = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    df_auctions_fresh = fetch_auction_data(start_date=start_date_30d)
    if not df_auctions_fresh.empty:
        df_auctions_fresh = process_auction_data(df_auctions_fresh)
        db = get_db_connection()
        db.upsert_data(df_auctions_fresh, "treasury_auctions", key_col='issue_date')
        db.close()

    # We'll assume MSPD data is relatively static or updated via pipeline, 
    # but let's fetch the latest available just in case.
    # MSPD is monthly, so we check the last 2 months to be safe.
    print("Refreshing MSPD data...")
    start_date_60d = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    
    df_mspd_sum = fetch_mspd_summary(start_date=start_date_60d)
    if not df_mspd_sum.empty:
        df_mspd_sum = process_mspd_data(df_mspd_sum, ["debt_held_public_mil_amt", "intragov_hold_mil_amt", "total_mil_amt"])
        db = get_db_connection()
        db.upsert_data(df_mspd_sum, "mspd_summary", key_col='record_date')
        db.close()
        
    # Marketable/Non-marketable are large, so we might skip re-fetching if we trust the DB,
    # but the user asked for "results of...", so let's try to get the latest if missing.
    # For now, we'll query the DB.

    # 2. Query Data from DB
    db = get_db_connection()
    
    # Auctions: Last 30 days
    print("Querying Auctions (Last 30 Days)...")
    query_auctions = f"""
        SELECT * FROM treasury_auctions 
        WHERE issue_date >= '{start_date_30d}'
        ORDER BY issue_date DESC
    """
    df_auctions = db.query(query_auctions)
    
    # MSPD: Latest available full report
    # Find the latest record_date in mspd_summary
    print("Querying Latest MSPD Report...")
    latest_date_row = db.query("SELECT MAX(record_date) as max_date FROM mspd_summary")
    if not latest_date_row.empty and latest_date_row.iloc[0]['max_date']:
        latest_date = latest_date_row.iloc[0]['max_date']
        # Ensure it's a string YYYY-MM-DD
        if isinstance(latest_date, pd.Timestamp):
            latest_date_str = latest_date.strftime("%Y-%m-%d")
        else:
            latest_date_str = str(latest_date)
            
        print(f"Latest MSPD Date: {latest_date_str}")
        
        df_mspd_summary = db.query(f"SELECT * FROM mspd_summary WHERE record_date = '{latest_date_str}'")
        df_mspd_market = db.query(f"SELECT * FROM mspd_marketable WHERE record_date = '{latest_date_str}'")
        df_mspd_nonmarket = db.query(f"SELECT * FROM mspd_nonmarketable WHERE record_date = '{latest_date_str}'")
    else:
        print("No MSPD data found.")
        df_mspd_summary = pd.DataFrame()
        df_mspd_market = pd.DataFrame()
        df_mspd_nonmarket = pd.DataFrame()

    db.close()

    # 3. Generate Markdown Report
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join("outputs", f"debt_raw_{timestamp_str}.md")
    
    report_content = f"# Debt Raw Report - {timestamp_str}\n\n"
    
    report_content += generate_markdown_table(df_auctions, "Treasury Auctions (Last 30 Days)")
    
    if not df_mspd_summary.empty:
        report_content += f"# MSPD Report (As of {latest_date_str})\n\n"
        report_content += generate_markdown_table(df_mspd_summary, "Summary of Treasury Securities Outstanding")
        report_content += generate_markdown_table(df_mspd_market, "Detail of Marketable Treasury Securities")
        report_content += generate_markdown_table(df_mspd_nonmarket, "Detail of Non-Marketable Treasury Securities")
    else:
        report_content += "# MSPD Report\n\nNo data available.\n"

    # Write to file
    os.makedirs("outputs", exist_ok=True)
    with open(output_file, "w") as f:
        f.write(report_content)
    
    print(f"Report generated: {output_file}")

    # 4. Cleanup Empty Lines
    print("Running cleanup...")
    if integrated_cleanup_for_current_file(output_file):
        print("Cleanup successful.")
    else:
        print("Cleanup failed.")

if __name__ == "__main__":
    main()
