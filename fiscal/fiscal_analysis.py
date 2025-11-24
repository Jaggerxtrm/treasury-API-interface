import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import matplotlib.pyplot as plt

# Constants
API_BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
# Endpoints
DTS_WITHDRAWALS_ENDPOINT = "/v1/accounting/dts/deposits_withdrawals_operating_cash"
DTS_TGA_ENDPOINT = "/v1/accounting/dts/operating_cash_balance"
DATE_FORMAT = "%Y-%m-%d"

# FRED API Key
FRED_API_KEY = "319c755ba8b781762ed9736f0b95604d"

# Nominal GDP Estimate (Annualized) - Default fallback
NOMINAL_GDP_FALLBACK = 29_000_000_000_000  # Approx $29T

def fetch_paginated_data(url, params):
    """
    Helper to fetch all pages from an API endpoint.
    """
    print(f"Fetching data from {url} with params {params}...")
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
            
            meta = data.get('meta', {})
            total_pages = meta.get('total-pages', 1)
            
            # Print progress every 5 pages to avoid clutter
            if page_num % 5 == 0 or page_num == total_pages:
                print(f"Fetched page {page_num}/{total_pages} ({len(data['data'])} records)")
            
            if page_num >= total_pages:
                break
                
            page_num += 1
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    return pd.DataFrame(all_data)

def fetch_dts_data(start_date="2022-01-01"):
    """
    Fetches DTS withdrawals (Table II) and TGA balance (Table I).
    """
    # 1. Fetch Withdrawals & Deposits (Table II)
    # We need both Withdrawals (Spending) and Deposits (Taxes)
    # The endpoint is the same, we filter by transaction_type later or fetch all
    
    url_trans = f"{API_BASE_URL}{DTS_WITHDRAWALS_ENDPOINT}"
    params_trans = {
        "filter": f"record_date:gte:{start_date}", # Fetch both Deposits and Withdrawals
        "page[size]": 10000,
        "sort": "record_date"
    }
    df_trans = fetch_paginated_data(url_trans, params_trans)
    
    # 2. Fetch TGA Balance (Table I)
    url_tga = f"{API_BASE_URL}{DTS_TGA_ENDPOINT}"
    params_tga = {
        "filter": f"record_date:gte:{start_date},account_type:eq:Treasury General Account (TGA) Closing Balance", # Check account_type filter validity
        # Actually Table I usually has "Federal Reserve Account" or similar. 
        # Let's just fetch all for Table I and filter in pandas to be safe on account names.
        "filter": f"record_date:gte:{start_date}",
        "page[size]": 10000,
        "sort": "record_date"
    }
    df_tga = fetch_paginated_data(url_tga, params_tga)
    
    return df_trans, df_tga

def fetch_current_gdp():
    """
    Fetches the latest Nominal GDP (Annualized) from FRED.
    Series: GDP (Billions of Dollars, SAAR)
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "GDP",
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1
    }
    
    print(f"Fetching latest GDP from FRED...")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'observations' in data and data['observations']:
            # Value is in Billions
            gdp_billions = float(data['observations'][0]['value'])
            gdp_annual = gdp_billions * 1_000_000_000
            date = data['observations'][0]['date']
            print(f"FRED GDP: ${gdp_annual/1e12:.2f}T (as of {date})")
            return gdp_annual
            
    except Exception as e:
        print(f"Error fetching GDP from FRED: {e}")
        print(f"Using fallback GDP: ${NOMINAL_GDP_FALLBACK/1e12:.2f}T")
        
    return NOMINAL_GDP_FALLBACK

def process_fiscal_analysis(df_trans, df_tga, nominal_gdp):
    """
    Process data to calculate Fiscal Impulse, Tax Flows, and TGA dynamics.
    """
    if df_trans.empty or df_tga.empty:
        print("Insufficient data.")
        return pd.DataFrame()

    # --- Preprocessing Transactions ---
    df_trans['record_date'] = pd.to_datetime(df_trans['record_date'])
    df_trans['transaction_today_amt'] = pd.to_numeric(df_trans['transaction_today_amt'])
    
    # Exclude Debt and Subtotals
    exclude_keywords = ['Public Debt', 'Redemption', 'Sub-Total', 'null']
    # Helper to check exclusion
    def is_excluded(catg):
        if not isinstance(catg, str): return True
        return any(k in catg for k in exclude_keywords)

    df_clean = df_trans[~df_trans['transaction_catg'].apply(is_excluded)].copy()

    # --- 1. Fiscal Impulse (Spending) ---
    # Filter Withdrawals
    df_withdrawals = df_clean[df_clean['transaction_type'] == 'Withdrawals'].copy()
    
    # Categorization
    # Household: HHS, SSA, UI, VA, IRS Refunds (Individual)
    # Note: IRS Refunds are Withdrawals.
    
    def categorize_spending(row):
        cat = row['transaction_catg']
        if 'Medicare' in cat or 'HHS' in cat: return 'HHS_Medicare'
        if 'Social Security' in cat or 'SSA' in cat: return 'SSA_Benefits'
        if 'Veterans' in cat or 'VA' in cat: return 'VA_Benefits'
        if 'Unemployment' in cat: return 'Unemployment'
        if 'IRS Tax Refunds Individual' in cat: return 'Tax_Refunds_Indiv'
        if 'Interest on Treasury Securities' in cat: return 'Interest'
        return 'Other'

    df_withdrawals['category_group'] = df_withdrawals.apply(categorize_spending, axis=1)
    
    # Pivot to get daily sums per category
    daily_spending = df_withdrawals.pivot_table(
        index='record_date', 
        columns='category_group', 
        values='transaction_today_amt', 
        aggfunc='sum',
        fill_value=0
    )
    daily_spending['Total_Impulse'] = daily_spending.sum(axis=1)
    
    # Household Directed Spending (Proxy)
    household_cols = ['HHS_Medicare', 'SSA_Benefits', 'VA_Benefits', 'Unemployment', 'Tax_Refunds_Indiv']
    # Only sum columns that exist
    avail_hh_cols = [c for c in household_cols if c in daily_spending.columns]
    daily_spending['Household_Impulse'] = daily_spending[avail_hh_cols].sum(axis=1)

    # --- 2. Tax Receipts (Extraction) ---
    # Filter Deposits
    df_deposits = df_clean[df_clean['transaction_type'] == 'Deposits'].copy()
    
    def categorize_tax(row):
        cat = row['transaction_catg']
        if 'Withheld Income' in cat: return 'Withheld_Tax'
        if 'Corporate' in cat and 'Tax' in cat: return 'Corporate_Tax'
        return 'Other_Deposits'
        
    df_deposits['tax_group'] = df_deposits.apply(categorize_tax, axis=1)
    
    daily_taxes = df_deposits.pivot_table(
        index='record_date',
        columns='tax_group',
        values='transaction_today_amt',
        aggfunc='sum',
        fill_value=0
    )
    daily_taxes['Total_Taxes'] = daily_taxes.sum(axis=1)

    # --- 3. TGA Balance ---
    df_tga['record_date'] = pd.to_datetime(df_tga['record_date'])
    df_tga['close_today_bal'] = pd.to_numeric(df_tga['close_today_bal'], errors='coerce')
    df_tga['open_today_bal'] = pd.to_numeric(df_tga['open_today_bal'], errors='coerce')
    
    # Filter for TGA Closing Balance (usually Table I, account_type='Federal Reserve Account' or similar)
    # Let's inspect unique account types if needed, but usually it's just one main account in Table I
    # or "Treasury General Account (TGA) Closing Balance" in recent data.
    # We'll sum by date to be safe (usually 1 record per date).
    print(f"DEBUG: TGA DataFrame shape: {df_tga.shape}")
    
    # Filter for Closing Balance
    tga_closing = df_tga[df_tga['account_type'].str.contains("Closing Balance", na=False)].copy()
    
    # Handle null close_today_bal by using open_today_bal (API quirk)
    tga_closing['balance'] = tga_closing['close_today_bal'].fillna(tga_closing['open_today_bal'])
    
    # If still null (or 0 if coerced), try open_today_bal explicitly if close was 0
    # The previous coercion might have made "null" into NaN.
    # Let's just take open_today_bal if close is NaN
    tga_closing['balance'] = tga_closing['close_today_bal']
    mask_nan = tga_closing['balance'].isna()
    tga_closing.loc[mask_nan, 'balance'] = tga_closing.loc[mask_nan, 'open_today_bal']
    
    daily_tga = tga_closing.groupby('record_date')['balance'].sum().rename('TGA_Balance')
    
    # --- Merge All Metrics ---
    merged = pd.concat([daily_spending, daily_taxes, daily_tga], axis=1).fillna(0).sort_index()
    
    # --- Advanced Calculations (Fiscal Week Aligned) ---
    
    # 1. Shutdown / Holiday Adjustment
    # Filter out days with < $1B spending (likely holidays/shutdowns) for averages
    # We keep them in the DataFrame but set a flag or use a filtered series for MA
    merged['Is_Trading_Day'] = merged['Total_Impulse'] > 1_000_000_000
    
    # 2. Moving Averages (using only valid trading days for smoother trend)
    # We'll use the raw series for now to match standard practice, but note the adjustment
    merged['MA20_Impulse'] = merged['Total_Impulse'].rolling(window=20).mean()
    merged['MA5_Impulse'] = merged['Total_Impulse'].rolling(window=5).mean()
    merged['MA20_Household'] = merged['Household_Impulse'].rolling(window=20).mean()
    
    # 3. 4-Week Cumulative & Average
    merged['4W_Cum_Impulse'] = merged['Total_Impulse'].rolling(window=20).sum()
    merged['4W_Avg_Impulse'] = merged['MA20_Impulse'] # Explicit alias
    
    # 4. GDP Normalization (Weekly Basis)
    # Target: ~0.64% magnitude. Formula: (MA20 * 5) / GDP
    merged['Impulse_Weekly_Pct_GDP'] = (merged['MA20_Impulse'] * 5 * 1_000_000) / nominal_gdp * 100
    
    # 5. MTD (Month-to-Date)
    merged['YearMonth'] = merged.index.to_period('M')
    merged['MTD_Impulse'] = merged.groupby('YearMonth')['Total_Impulse'].cumsum()
    
    # 6. LTD (Late-to-Date / Month-End)
    # Identify last 3 business days of the month
    # We can do this by checking if the next 3 days span into a new month
    # Simple proxy: Day > 25 and high spending? 
    # Better: Just report the MTD at month end.
    
    # 7. Fiscal YTD Cumulative vs Last Year
    # Fiscal Year starts Oct 1
    merged['Fiscal_Year'] = merged.index.map(lambda x: x.year + 1 if x.month >= 10 else x.year)
    # Create a unique group for FY logic
    merged['FY_Group'] = merged['Fiscal_Year']
    merged['FYTD_Impulse'] = merged.groupby('FY_Group')['Total_Impulse'].cumsum()
    
    # 8. Historical Comparisons (YoY, 3-Year)
    # Shift 252 days (1 year), 504 (2 years), 756 (3 years)
    merged['Prev_Year_Impulse'] = merged['Total_Impulse'].shift(252)
    merged['Prev_Year_MA20'] = merged['MA20_Impulse'].shift(252)
    merged['Prev_Year_FYTD'] = merged['FYTD_Impulse'].shift(252)
    
    merged['Prev_2Year_Impulse'] = merged['Total_Impulse'].shift(504)
    merged['Prev_2Year_MA20'] = merged['MA20_Impulse'].shift(504)
    
    merged['Prev_3Year_Impulse'] = merged['Total_Impulse'].shift(756)
    merged['Prev_3Year_MA20'] = merged['MA20_Impulse'].shift(756)
    
    # 3-Year Average Baseline (MA20)
    merged['3Y_Avg_MA20'] = (merged['Prev_Year_MA20'] + merged['Prev_2Year_MA20'] + merged['Prev_3Year_MA20']) / 3
    
    # Implied Value (Expected based on YoY)
    # Simple model: Last Year's Impulse adjusted for ... just use Last Year's as base implied
    merged['Implied_Daily_Impulse'] = merged['Prev_Year_Impulse']
    merged['Delta_vs_Implied'] = merged['Total_Impulse'] - merged['Implied_Daily_Impulse']
    
    # Cumulative Difference YoY
    merged['Cum_Diff_YoY'] = merged['FYTD_Impulse'] - merged['Prev_Year_FYTD']
    
    # YoY 4-Week Change
    merged['Prev_Year_4W_Cum'] = merged['4W_Cum_Impulse'].shift(252)
    merged['YoY_4W_Cum_Impulse'] = merged['4W_Cum_Impulse'] - merged['Prev_Year_4W_Cum']
    
    return merged

def generate_report(df, nominal_gdp):
    """
    Generates console report and CSV.
    """
    # Recent Data
    recent = df.tail(10).copy()
    
    print("\n" + "="*50)
    print("FISCAL ANALYSIS REPORT (Advanced)")
    print("="*50)
    
    print(f"Last Date: {recent.index[-1].strftime('%Y-%m-%d')}")
    print(f"Nominal GDP Used: ${nominal_gdp/1e12:.2f}T")
    
    # 1. Fiscal Impulse Overview
    print("\n--- FISCAL IMPULSE (Fiscal Week Aligned) ---")
    last_row = recent.iloc[-1]
    
    print(f"Daily Total Impulse:     ${last_row['Total_Impulse']:,.0f} M")
    print(f"MTD Impulse:             ${last_row['MTD_Impulse']:,.0f} M")
    print(f"4-Week Average (MA20):   ${last_row['MA20_Impulse']:,.0f} M")
    print(f"Weekly Impulse % GDP:    {last_row['Impulse_Weekly_Pct_GDP']:.2f}% (Target: ~0.64%)")
    
    # 2. Historical Context
    print("\n--- HISTORICAL CONTEXT ---")
    print(f"Implied Daily (YoY):     ${last_row['Implied_Daily_Impulse']:,.0f} M")
    print(f"Delta vs Implied:        ${last_row['Delta_vs_Implied']:,.0f} M")
    print(f"3-Year Avg Baseline:     ${last_row['3Y_Avg_MA20']:,.0f} M")
    print(f"vs 3-Year Baseline:      ${last_row['MA20_Impulse'] - last_row['3Y_Avg_MA20']:,.0f} M")
    print(f"FYTD Cumulative:         ${last_row['FYTD_Impulse']:,.0f} M")
    print(f"FYTD vs Last Year:       ${last_row['Cum_Diff_YoY']:,.0f} M")

    # 3. Household vs Total
    print("\n--- HOUSEHOLD ABSORPTION ---")
    print(f"Household Impulse:       ${last_row['Household_Impulse']:,.0f} M")
    print(f"Household Share:         {last_row['Household_Impulse'] / last_row['Total_Impulse'] * 100:.1f}%")
    
    # 4. Tax & TGA
    print("\n--- LIQUIDITY & TAXES ---")
    print(f"TGA Balance:             ${last_row['TGA_Balance']:,.0f} M")
    if 'Withheld_Tax' in recent.columns:
        print(f"Daily Withheld Tax:      ${last_row['Withheld_Tax']:,.0f} M")
        
    # 5. Monthly Breakdown (Last complete month or current MTD)
    print("\n--- MONTHLY BREAKDOWN (Top Categories) ---")
    # Resample to monthly sum
    monthly_cat = df.resample('ME')[['HHS_Medicare', 'SSA_Benefits', 'VA_Benefits', 'Unemployment', 'Tax_Refunds_Indiv', 'Interest', 'Total_Impulse']].sum()
    last_month = monthly_cat.iloc[-1]
    print(f"Month: {last_month.name.strftime('%Y-%m')}")
    print(last_month.sort_values(ascending=False).to_string(float_format="${:,.0f} M".format))

    # Recent Trend Table
    print("\n--- RECENT TREND (Last 5 Days) ---")
    cols = ['Total_Impulse', 'MTD_Impulse', 'MA20_Impulse', 'Impulse_Weekly_Pct_GDP', 'Cum_Diff_YoY', 'TGA_Balance']
    print(recent[cols].sort_index(ascending=False).head(5).to_string(float_format="{:,.2f}".format))
    
    # Export
    csv_path = "fiscal_analysis_full.csv"
    df.to_csv(csv_path)
    print(f"\nFull data exported to {csv_path}")

def main():
    print("Starting Advanced Fiscal Analysis...")
    
    # Fetch
    df_trans, df_tga = fetch_dts_data()
    
    if df_trans.empty:
        print("No transaction data fetched.")
        return

    print(f"Fetched {len(df_trans)} transactions and {len(df_tga)} TGA records.")
    
    # Fetch GDP
    current_gdp = fetch_current_gdp()
    
    # Process
    analysis_df = process_fiscal_analysis(df_trans, df_tga, current_gdp)
    
    # Report
    generate_report(analysis_df, current_gdp)

if __name__ == "__main__":
    main()
