import requests
import pandas as pd
from datetime import datetime, timedelta

"""
NY Fed Reference Rates Fetcher
Uses the official NY Fed Markets API to fetch:
- SOFR (Secured Overnight Financing Rate)
- BGCR (Broad General Collateral Rate)
- TGCR (Tri-Party General Collateral Rate)
- EFFR (Effective Federal Funds Rate)
- OBFR (Overnight Bank Funding Rate)
"""

NYFED_API_BASE = "https://markets.newyorkfed.org/api"

# Available rate types from NY Fed API
RATE_TYPES = {
    "sofr": "SOFR_Rate",
    "bgcr": "BGCR_Rate",
    "tgcr": "TGCR_Rate",
    "effr": "EFFR_Rate",
    "obfr": "OBFR_Rate"
}

def construct_url(rate_type):
    """
    Constructs the API URL for a given rate type.
    
    Args:
        rate_type (str): The type of rate (e.g., 'effr', 'sofr').
        
    Returns:
        str: The constructed URL.
    """
    # Determine if the rate is secured or unsecured
    if rate_type in ['effr', 'obfr']:
        category = 'unsecured'
    else:
        # sofr, bgcr, tgcr are secured
        category = 'secured'
        
    base = "https://markets.newyorkfed.org/api/rates"
    return f"{base}/{category}/{rate_type}/search.json"


def fetch_reference_rate(rate_type, num_records=250):
    """
    Fetches reference rate data from NY Fed API.

    Args:
        rate_type: One of 'sofr', 'bgcr', 'tgcr', 'effr', 'obfr'
        num_records: Number of most recent records to fetch (default 250, max varies by endpoint)

    Returns:
        pandas DataFrame with date index and rate data
    """
    # Try search endpoint with date range instead
    url = construct_url(rate_type)

    # Calculate start date (approx 1 year ago for 250 business days)
    start_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')

    params = {
        'startDate': start_date
    }

    print(f"Fetching {rate_type.upper()} from NY Fed API...")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # The response structure is {'refRates': [...]}
        if 'refRates' in data:
            rates_list = data['refRates']

            if not rates_list:
                print(f"No {rate_type} data found")
                return pd.DataFrame()

            df = pd.DataFrame(rates_list)

            # Parse date column
            if 'effectiveDate' in df.columns:
                df['date'] = pd.to_datetime(df['effectiveDate'])
                df.set_index('date', inplace=True)

            # Extract rate value (percentRate is the actual rate)
            if 'percentRate' in df.columns:
                df['rate'] = pd.to_numeric(df['percentRate'], errors='coerce')

            # Keep only relevant columns
            cols_to_keep = ['rate', 'percentile1', 'percentile25', 'percentile75', 'percentile99', 'volumeInBillions']
            cols_to_keep = [c for c in cols_to_keep if c in df.columns]
            df = df[cols_to_keep]

            print(f"Fetched {len(df)} {rate_type.upper()} records")
            return df.sort_index()

        else:
            print(f"Unexpected response structure for {rate_type}")
            return pd.DataFrame()

    except Exception as e:
        print(f"Error fetching {rate_type}: {e}")
        return pd.DataFrame()

def fetch_all_reference_rates(num_records=1000):
    """
    Fetches all available reference rates from NY Fed API.

    Returns:
        Dictionary of DataFrames, keyed by rate type
    """
    all_rates = {}

    for rate_type in RATE_TYPES.keys():
        df = fetch_reference_rate(rate_type, num_records)
        if not df.empty:
            all_rates[rate_type] = df

    return all_rates

def merge_reference_rates(all_rates):
    """
    Merges all reference rate DataFrames into a single DataFrame.

    Returns:
        DataFrame with columns for each rate type
    """
    if not all_rates:
        return pd.DataFrame()

    # Extract just the 'rate' column from each and rename
    rate_series = []
    for rate_type, df in all_rates.items():
        if 'rate' in df.columns:
            series = df['rate'].copy()
            series.name = RATE_TYPES[rate_type]
            rate_series.append(series)

    if not rate_series:
        return pd.DataFrame()

    # Merge all into one DataFrame
    merged = pd.concat(rate_series, axis=1, join='outer').sort_index()

    return merged

def generate_report(merged_df):
    """
    Generates a simple report on reference rates.
    """
    if merged_df.empty:
        print("No data to report")
        return

    recent = merged_df.tail(5)
    last_row = merged_df.iloc[-1]
    last_date = merged_df.index[-1].strftime('%Y-%m-%d')

    print("\n" + "="*50)
    print("NY FED REFERENCE RATES REPORT")
    print("="*50)
    print(f"Last Date: {last_date}")

    print("\n--- CURRENT RATES ---")
    for col in merged_df.columns:
        if col in last_row and not pd.isna(last_row[col]):
            print(f"{col:20s}: {last_row[col]:.2f}%")

    print("\n--- SPREADS ---")
    if 'SOFR_Rate' in last_row and 'BGCR_Rate' in last_row:
        spread = (last_row['SOFR_Rate'] - last_row['BGCR_Rate']) * 100
        print(f"SOFR - BGCR:         {spread:.1f} bps")

    if 'SOFR_Rate' in last_row and 'TGCR_Rate' in last_row:
        spread = (last_row['SOFR_Rate'] - last_row['TGCR_Rate']) * 100
        print(f"SOFR - TGCR:         {spread:.1f} bps")

    if 'BGCR_Rate' in last_row and 'TGCR_Rate' in last_row:
        spread = (last_row['BGCR_Rate'] - last_row['TGCR_Rate']) * 100
        print(f"BGCR - TGCR:         {spread:.1f} bps")

    print("\n--- RECENT TREND (Last 5 Days) ---")
    print(recent.to_string(float_format="{:.2f}".format))

    # Export
    csv_path = "nyfed_reference_rates.csv"
    merged_df.to_csv(csv_path)
    print(f"\nReference rates exported to {csv_path}")

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
