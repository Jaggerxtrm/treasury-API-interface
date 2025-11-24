import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

# Constants
FRED_API_KEY = "319c755ba8b781762ed9736f0b95604d"
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
START_DATE = "2022-01-01"

# Series Mapping
SERIES_MAP = {
    # Liquidity Components
    "RRPONTSYD": "RRP_Balance",      # Overnight Reverse Repo
    "RPONTSYD": "Repo_Ops_Balance",  # Overnight Repo Operations (Liquidity Injection)
    "WALCL": "Fed_Total_Assets",     # Total Assets (Less Eliminations from Consolidation)
    "WSHOMCB": "Fed_MBS_Holdings",   # MBS Holdings
    "TREAST": "Fed_Treasury_Holdings", # Treasury Holdings
    "WSHOBL": "Fed_Bill_Holdings",   # T-Bills Held Outright (QE/Bill-Buying)
    
    # Rates & Spreads
    "IORB": "IORB_Rate",             # Interest on Reserve Balances
    "EFFR": "EFFR_Rate",             # Effective Federal Funds Rate
    "SOFR": "SOFR_Rate",             # Secured Overnight Financing Rate
    "TGCRRATE": "TGCR_Rate",         # Tri-Party General Collateral Rate
    
    # Inflation Expectations (TIPS Breakevens)
    "T10YIE": "Breakeven_10Y",       # 10-Year Breakeven Inflation Rate
    "T5YIE": "Breakeven_5Y",         # 5-Year Breakeven Inflation Rate
    
    # Liquidity Support
    "SWPT": "Swap_Lines",            # Central Bank Liquidity Swaps
    "SRFTSYD": "SRF_Rate",           # Standing Repo Facility Minimum Bid Rate
}

def fetch_fred_series(series_id, start_date=START_DATE):
    """
    Fetches a single series from FRED API.
    """
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "sort_order": "asc"
    }
    
    print(f"Fetching {series_id} ({SERIES_MAP.get(series_id, series_id)})...")
    try:
        response = requests.get(FRED_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "observations" not in data:
            print(f"No observations found for {series_id}")
            return pd.Series(dtype=float)
            
        df = pd.DataFrame(data["observations"])
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        
        # Set index to date
        series = df.set_index("date")["value"]
        series.name = SERIES_MAP.get(series_id, series_id)
        
        # Handle frequency (some are weekly, fill forward for daily alignment)
        # We'll handle alignment in the merge step, but basic cleaning here is good.
        return series.dropna()
        
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return pd.Series(dtype=float)

def fetch_all_data():
    """
    Fetches all required series and merges them into a single DataFrame.
    """
    all_series = []
    for series_id in SERIES_MAP.keys():
        s = fetch_fred_series(series_id)
        all_series.append(s)
        
    print("Merging data...")
    # Merge using outer join to keep all dates, then sort
    df = pd.concat(all_series, axis=1).sort_index()
    
    # Forward fill weekly data (Balance Sheet is weekly - Wednesday)
    # RRP and Rates are daily (business days)
    # We forward fill to propagate the last known value (e.g. Balance Sheet holds for the week)
    df = df.ffill()
    
    # Filter to start date again just in case
    # Ensure START_DATE is datetime for comparison
    start_dt = pd.to_datetime(START_DATE)
    df = df[df.index >= start_dt]
    
    return df

def calculate_metrics(df):
    """
    Calculates derived metrics: Net Liquidity, Spreads, Changes.
    """
    # 1. Net Liquidity (Simple Proxy)
    # Net Liq = Fed Assets - RRP - TGA (We need TGA from Fiscal script or fetch here)
    # For now, we'll calculate "Fed Liquidity Injection" = Assets - RRP
    # TGA integration will come in the composite step.
    
    # Convert Billions/Millions if needed.
    # FRED RRP is in Billions.
    # FRED WALCL (Assets) is in Millions.
    # Let's standardize to Millions.
    
    if 'RRP_Balance' in df.columns:
        df['RRP_Balance_M'] = df['RRP_Balance'] * 1000 # Billions -> Millions
    
    if 'Fed_Total_Assets' in df.columns:
        # WALCL is in Millions
        pass
        
    # 2. Spreads (Stress Indicators)
    # SOFR - IORB (Collateral Scarcity)
    if 'SOFR_Rate' in df.columns and 'IORB_Rate' in df.columns:
        df['Spread_SOFR_IORB'] = (df['SOFR_Rate'] - df['IORB_Rate']) * 100 # bps
        
    # EFFR - IORB (Policy Transmission)
    if 'EFFR_Rate' in df.columns and 'IORB_Rate' in df.columns:
        df['Spread_EFFR_IORB'] = (df['EFFR_Rate'] - df['IORB_Rate']) * 100 # bps
        
    # TGCR - SOFR (Tri-party vs GC)
    if 'TGCR_Rate' in df.columns and 'SOFR_Rate' in df.columns:
        df['Spread_TGCR_SOFR'] = (df['TGCR_Rate'] - df['SOFR_Rate']) * 100 # bps

    # 3. RRP Change
    if 'RRP_Balance' in df.columns:
        df['RRP_Change'] = df['RRP_Balance'].diff()
        
    # 4. QT Pace (Weekly Change in Assets)
    # Resample to weekly to get a smoother trend or just take 5-day diff
    if 'Fed_Total_Assets' in df.columns:
        df['QT_Pace_Assets_Weekly'] = df['Fed_Total_Assets'].diff(5) # 5 business days approx 1 week
        
    if 'Fed_Treasury_Holdings' in df.columns:
        df['QT_Pace_Treasury_Weekly'] = df['Fed_Treasury_Holdings'].diff(5)
        
    if 'Fed_Bill_Holdings' in df.columns:
        df['Bill_Buying_Pace_Weekly'] = df['Fed_Bill_Holdings'].diff(5)
        
    # Derive Coupons (Notes + Bonds) = Total Treasuries - Bills
    if 'Fed_Treasury_Holdings' in df.columns and 'Fed_Bill_Holdings' in df.columns:
        df['Fed_Coupon_Holdings'] = df['Fed_Treasury_Holdings'] - df['Fed_Bill_Holdings']

    # 5. Volatility & Stress
    if 'SOFR_Rate' in df.columns:
        # Rolling 5-day Standard Deviation
        df['SOFR_Vol_5D'] = df['SOFR_Rate'].rolling(window=5).std()
        
        # Stress Flag: SOFR > IORB + 5bps (0.05%)
        if 'IORB_Rate' in df.columns:
            df['Stress_Flag'] = df['SOFR_Rate'] > (df['IORB_Rate'] + 0.05)
            
    # 6. Analytical Alignment (Phase 3)
    
    # Moving Averages (Smooth Noise)
    if 'RRP_Balance' in df.columns:
        df['MA20_RRP'] = df['RRP_Balance'].rolling(window=20).mean()
        df['MA5_RRP'] = df['RRP_Balance'].rolling(window=5).mean()
        
    if 'Fed_Total_Assets' in df.columns:
        df['MA20_Assets'] = df['Fed_Total_Assets'].rolling(window=20).mean()
        
    if 'Spread_SOFR_IORB' in df.columns:
        df['MA20_Spread_SOFR_IORB'] = df['Spread_SOFR_IORB'].rolling(window=20).mean()

    # YoY Comparisons (Shift 252 days)
    if 'RRP_Balance' in df.columns:
        df['Prev_Year_RRP'] = df['RRP_Balance'].shift(252)
        df['YoY_RRP_Change'] = df['RRP_Balance'] - df['Prev_Year_RRP']
        
    if 'Fed_Total_Assets' in df.columns:
        df['Prev_Year_Assets'] = df['Fed_Total_Assets'].shift(252)
        df['YoY_Assets_Change'] = df['Fed_Total_Assets'] - df['Prev_Year_Assets'] # Cumulative QT over 1 year

    # 3-Year Baseline (Assets)
    if 'Fed_Total_Assets' in df.columns:
        df['Prev_3Year_Assets'] = df['Fed_Total_Assets'].shift(756)
        # Simple baseline: Average of last 3 years? Or just vs 3 years ago?
        # Let's use 3-Year Moving Average as baseline
        df['MA20_Assets_3Y_Avg'] = (
            df['Fed_Total_Assets'].shift(252).rolling(20).mean() + 
            df['Fed_Total_Assets'].shift(504).rolling(20).mean() + 
            df['Fed_Total_Assets'].shift(756).rolling(20).mean()
        ) / 3
        
    # MTD Flows
    # For Balance Sheet items (Stocks), MTD Change = Current - Month Start
    # For Flows (like RRP Change), MTD = Sum of daily changes
    df['YearMonth'] = df.index.to_period('M')
    
    if 'Fed_Total_Assets' in df.columns:
        # Get the first value of the month for each row's month
        # This is a bit tricky with daily data gaps. 
        # Easier: Resample to month start, reindex?
        # Or: Groupby transform 'first'
        df['Month_Start_Assets'] = df.groupby('YearMonth')['Fed_Total_Assets'].transform('first')
        df['MTD_Assets_Change'] = df['Fed_Total_Assets'] - df['Month_Start_Assets']
        
    if 'RRP_Change' in df.columns:
        df['MTD_RRP_Flow'] = df.groupby('YearMonth')['RRP_Change'].cumsum()

    return df

def generate_report(df):
    """
    Generates a console report.
    """
    recent = df.tail(5)
    last_row = df.iloc[-1]
    last_date = df.index[-1].strftime('%Y-%m-%d')
    
    print("\n" + "="*50)
    print("FED LIQUIDITY MONITOR")
    print("="*50)
    print(f"Last Date: {last_date}")
    
    print("\n--- LIQUIDITY DRAINS (RRP) ---")
    print("\n--- LIQUIDITY DRAINS (RRP) ---")
    if 'RRP_Balance' in df.columns:
        print(f"RRP Balance:       ${last_row['RRP_Balance']:,.0f} B")
        print(f"Daily Change:      ${last_row['RRP_Change']:,.0f} B")
        if 'MTD_RRP_Flow' in last_row:
            print(f"MTD Flow:          ${last_row['MTD_RRP_Flow']:,.0f} B")
        if 'YoY_RRP_Change' in last_row:
            print(f"YoY Change:        ${last_row['YoY_RRP_Change']:,.0f} B")
        if 'MA20_RRP' in last_row:
            print(f"MA20 Balance:      ${last_row['MA20_RRP']:,.0f} B")

    print("\n--- LIQUIDITY INJECTIONS (Repo) ---")
    if 'Repo_Ops_Balance' in df.columns:
        print(f"Repo Ops Balance:  ${last_row['Repo_Ops_Balance']:,.0f} B")
    if 'SRF_Rate' in df.columns:
        print(f"SRF Rate (Min Bid): {last_row['SRF_Rate']:.2f}%")
    
    print("\n--- KEY RATES & SPREADS ---")
    if 'IORB_Rate' in df.columns:
        print(f"IORB (Anchor):     {last_row['IORB_Rate']:.2f}%")
    if 'SOFR_Rate' in df.columns:
        print(f"SOFR:              {last_row['SOFR_Rate']:.2f}%")
        print(f"SOFR - IORB:       {last_row['Spread_SOFR_IORB']:.1f} bps")
    if 'EFFR_Rate' in df.columns:
        print(f"EFFR:              {last_row['EFFR_Rate']:.2f}%")
        
    print("\n--- FED BALANCE SHEET (Weekly) ---")
    if 'Fed_Total_Assets' in df.columns:
        print(f"Total Assets:      ${last_row['Fed_Total_Assets']:,.0f} M")
        if 'QT_Pace_Assets_Weekly' in last_row:
             print(f"Weekly Change (QT): ${last_row['QT_Pace_Assets_Weekly']:,.0f} M")
        if 'MTD_Assets_Change' in last_row:
             print(f"MTD Change:        ${last_row['MTD_Assets_Change']:,.0f} M")
        if 'YoY_Assets_Change' in last_row:
             print(f"YoY Change:        ${last_row['YoY_Assets_Change']:,.0f} M")
        if 'MA20_Assets_3Y_Avg' in last_row:
             print(f"vs 3Y Baseline:    ${last_row['Fed_Total_Assets'] - last_row['MA20_Assets_3Y_Avg']:,.0f} M")
             
    if 'Fed_Treasury_Holdings' in df.columns:
        print(f"Treasury Holdings: ${last_row['Fed_Treasury_Holdings']:,.0f} M")
    if 'Fed_Bill_Holdings' in df.columns:
        print(f"  > Bills (QE):    ${last_row['Fed_Bill_Holdings']:,.0f} M")
        if 'Bill_Buying_Pace_Weekly' in last_row:
             print(f"  > Bills Change:  ${last_row['Bill_Buying_Pace_Weekly']:,.0f} M")
             
    if 'Fed_Coupon_Holdings' in df.columns:
        print(f"  > Coupons:       ${last_row['Fed_Coupon_Holdings']:,.0f} M")
        
    print("\n--- INFLATION & STRESS INDICATORS ---")
    if 'Breakeven_10Y' in df.columns:
        print(f"10Y Breakeven:     {last_row['Breakeven_10Y']:.2f}%")
    if 'Breakeven_5Y' in df.columns:
        print(f"5Y Breakeven:      {last_row['Breakeven_5Y']:.2f}%")
    if 'Swap_Lines' in df.columns:
        print(f"Swap Lines Usage:  ${last_row['Swap_Lines']:,.0f} M")
    if 'SOFR_Vol_5D' in df.columns:
        print(f"SOFR Vol (5d std): {last_row['SOFR_Vol_5D']:.4f}")
    if 'Stress_Flag' in df.columns:
        status = "STRESS" if last_row['Stress_Flag'] else "NORMAL"
        print(f"Funding Status:    {status}")

    print("\n--- RECENT TREND (Last 5 Days) ---")
    cols = ['RRP_Balance', 'SOFR_Rate', 'Spread_SOFR_IORB', 'QT_Pace_Assets_Weekly', 'Breakeven_10Y']
    # Filter cols that exist
    cols = [c for c in cols if c in df.columns]
    print(recent[cols].sort_index(ascending=False).to_string(float_format="{:,.2f}".format))
    
    # Export
    csv_path = "fed_liquidity_full.csv"
    df.to_csv(csv_path)
    print(f"\nFull data exported to {csv_path}")

def main():
    print("Starting Fed Liquidity Monitor...")
    
    # Fetch
    df = fetch_all_data()
    
    if df.empty:
        print("No data fetched.")
        return
        
    # Process
    df_calc = calculate_metrics(df)
    
    # Report
    generate_report(df_calc)

if __name__ == "__main__":
    main()
