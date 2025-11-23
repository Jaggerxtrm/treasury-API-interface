import requests
import pandas as pd
from datetime import datetime, timedelta
import sys

# Constants
API_BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
DTS_ENDPOINT = "/v1/accounting/dts/deposits_withdrawals_operating_cash"
DATE_FORMAT = "%Y-%m-%d"

def fetch_dts_data(start_date):
    """
    Fetches DTS withdrawals data starting from a specific date.
    """
    start_date = "2022-01-01"
    url = f"{API_BASE_URL}{DTS_ENDPOINT}"
    params = {
        "filter": f"record_date:gte:{start_date},transaction_type:eq:Withdrawals",
        "page[size]": 10000,
        "sort": "record_date"
    }
    
    print(f"Fetching data from {url} starting {start_date}...")
    
    all_data = []
    page_num = 1
    while True:
        params['page[number]'] = page_num
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data['data']:
                break
                
            all_data.extend(data['data'])
            
            # Check if we have more pages
            meta = data.get('meta', {})
            total_pages = meta.get('total-pages', 1)
            
            print(f"Fetched page {page_num}/{total_pages} ({len(data['data'])} records)")
            
            if page_num >= total_pages:
                break
                
            page_num += 1
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    return pd.DataFrame(all_data)

def process_data(df):
    """
    Processes the raw DataFrame to calculate Fiscal Impulse.
    """
    if df.empty:
        print("No data found.")
        return pd.DataFrame()

    # Convert types
    df['record_date'] = pd.to_datetime(df['record_date'])
    df['transaction_today_amt'] = pd.to_numeric(df['transaction_today_amt'])

    # Filter out Debt Redemption and Sub-Totals
    exclude_cats = [
        'Public Debt Cash Redemp. (Table IIIB)',
        'Sub-Total Withdrawals',
        'null'
    ]
    df = df[~df['transaction_catg'].isin(exclude_cats)]

    # Filter for relevant categories if needed, or just sum up for "Total Fiscal Impulse"
    # The document implies "Total fiscal impulse" is the aggregate.
    # We aggregate by date.
    daily_total = df.groupby('record_date')['transaction_today_amt'].sum().reset_index()
    daily_total.rename(columns={'transaction_today_amt': 'total_impulse'}, inplace=True)
    
    # Sort by date
    daily_total = daily_total.sort_values('record_date')
    
    # Calculate Moving Averages (20-day / 4-week)
    daily_total['ma_20'] = daily_total['total_impulse'].rolling(window=20).mean()
    
    # Calculate YoY Change
    # We need to shift by ~252 trading days or 365 calendar days. 
    # Since this is daily data including potentially weekends/holidays (DTS is working days),
    # let's try to match by date.
    
    # Create a copy for last year
    last_year = daily_total.copy()
    last_year['match_date'] = last_year['record_date'] + pd.DateOffset(years=1)
    
    # Merge to compare
    merged = pd.merge(
        daily_total, 
        last_year[['match_date', 'total_impulse', 'ma_20']], 
        left_on='record_date', 
        right_on='match_date', 
        how='left', 
        suffixes=('', '_prev_year')
    )
    
    merged['yoy_change'] = merged['total_impulse'] - merged['total_impulse_prev_year']
    merged['yoy_ma_change'] = merged['ma_20'] - merged['ma_20_prev_year']
    
    return merged

def main():
    # Start date is handled in fetch_dts_data now
    df = fetch_dts_data(None)
    
    if df.empty:
        return

    print(f"Fetched {len(df)} records.")
    
    # Process
    analysis = process_data(df)
    
    # Show recent data (last 5 records)
    print("\nRecent Fiscal Impulse Data (Millions USD):")
    # The API returns data in Millions usually? Or actual dollars?
    # Documentation says: "Dollar amounts are in millions." usually for DTS.
    # Let's verify with a sample.
    
    pd.options.display.float_format = '{:,.2f}'.format
    print(analysis[['record_date', 'total_impulse', 'ma_20', 'yoy_change']].tail(10).to_string(index=False))

if __name__ == "__main__":
    main()
