import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import matplotlib.pyplot as plt

# =============================================================================
# FISCAL ANALYSIS ENGINE - ENHANCED VERSION
# Aligned with Fiscal Week Reports methodology
# =============================================================================

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

# =============================================================================
# FISCAL CALENDAR CONFIGURATION
# =============================================================================

# Social Security Payment Schedule (2nd, 3rd, 4th Wednesday of month based on birthday)
# Medicare: End/Start of month
# Tax Days: 15th of month (or next business day)
# Settlement Days: T+1 for bills, T+2 for coupons

FISCAL_CALENDAR = {
    'ss_payment_days': [2, 3, 4],  # 2nd, 3rd, 4th Wednesday
    'medicare_days': [-3, -2, -1, 1, 2, 3],  # Last 3 / First 3 days of month
    'tax_deadline_day': 15,
    'quarterly_tax_months': [1, 4, 6, 9],  # Jan, Apr, Jun, Sep
}

# =============================================================================
# DTS CATEGORY MAPPING - DETAILED SEGMENTATION
# =============================================================================

# Spending Categories (Withdrawals) - EXPANDED to reduce "Other"
SPENDING_CATEGORIES = {
    # Household-directed spending (high MPC impact)
    'SSA_Benefits': [
        'Social Security Benefits',
        'Supple. Security Income Benefits',
        'SSI Benefits',
        'Supple. Nutrition Assist.',
        'Social Security',
    ],
    'Medicare': [
        'Medicare',
        'HHS, Centers for Medicare',
        'CMS',
        'Medicaid',
        'Health and Human',
        'HHS',
    ],
    'VA_Benefits': [
        'Veterans',
        'VA Benefits',
        'Veterans Affairs',
        'Dept of Veteran',
    ],
    'Unemployment': [
        'Unemployment',
        'Unempl. Insurance',
        'Unemployment Insurance',
    ],
    'Tax_Refunds_Individual': [
        'IRS Tax Refunds Individual',
        'IRS - Economic Impact',
        'IRS Refunds Individual',
        'Tax Refunds',
    ],
    # Interest payments (major fiscal component)
    'Interest': [
        'Interest on Treasury Securities',
        'Interest on Public Debt',
        'Interest on',
    ],
    # Defense spending
    'Defense': [
        'Defense Vendor',
        'DoD',
        'Army',
        'Navy',
        'Air Force',
        'Military',
        'Defense',
        'Dept of Defense',
    ],
    # Other transfer programs
    'SNAP_Food': [
        'SNAP',
        'Food Stamps',
        'Food and Nutrition',
        'Nutrition Assistance',
    ],
    'Education': [
        'Education',
        'Student Loan',
        'Pell Grant',
        'Dept of Education',
    ],
    'Housing': [
        'HUD',
        'Housing',
        'Section 8',
        'Housing and Urban',
    ],
    'Tax_Refunds_Corporate': [
        'IRS Tax Refunds Business',
        'IRS Refunds Business',
    ],
    # Additional categories to reduce "Other"
    'Transportation': [
        'Transportation',
        'Federal Highway',
        'FAA',
        'Federal Aviation',
        'Transit',
    ],
    'Agriculture': [
        'Agriculture',
        'USDA',
        'Farm',
        'Commodity Credit',
    ],
    'Energy': [
        'Energy',
        'Dept of Energy',
        'DOE',
    ],
    'Justice': [
        'Justice',
        'FBI',
        'Federal Bureau',
        'Dept of Justice',
    ],
    'Treasury_Ops': [
        'Treasury Department',
        'Financial Management',
        'Fiscal Service',
    ],
    'Labor': [
        'Labor',
        'Dept of Labor',
        'DOL',
    ],
    'State_Intl': [
        'State Department',
        'International',
        'Foreign Affairs',
        'USAID',
    ],
    'Commerce': [
        'Commerce',
        'Dept of Commerce',
        'Census',
        'NOAA',
    ],
    'Interior': [
        'Interior',
        'National Park',
        'Bureau of Land',
        'Indian Affairs',
    ],
    'EPA': [
        'Environmental Protection',
        'EPA',
    ],
    'GSA': [
        'General Services',
        'GSA',
    ],
    'SBA': [
        'Small Business',
        'SBA',
    ],
    'Postal': [
        'Postal Service',
        'USPS',
    ],
    'Federal_Salaries': [
        'Federal Employees',
        'OPM',
        'Personnel Management',
        'Civil Service',
    ],
}

# Tax Receipt Categories (Deposits)
TAX_CATEGORIES = {
    'Withheld_Income': [
        'Withheld Income and Employment',
        'Withheld',
        'Income and Employment Taxes'
    ],
    'Individual_Income': [
        'Individual Income Taxes',
        'Individual Income'
    ],
    'Corporate_Income': [
        'Corporate Income Taxes',
        'Corporate Income',
        'Corporation Income'
    ],
    'Excise': [
        'Excise Taxes',
        'Excise'
    ],
    'Estate_Gift': [
        'Estate and Gift',
        'Estate'
    ],
    'Customs': [
        'Customs Duties',
        'Customs'
    ],
    'Payroll': [
        'Railroad Retirement',
        'Federal Employee',
        'FICA'
    ]
}

# Keywords to exclude from fiscal analysis
EXCLUDE_KEYWORDS = [
    'Public Debt', 'Redemption', 'Sub-Total', 'Subtotal',
    'Total Deposits', 'Total Withdrawals', 'null', 'Null',
    'Fed Investment', 'Transfer to Federal'
]


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
    url_trans = f"{API_BASE_URL}{DTS_WITHDRAWALS_ENDPOINT}"
    params_trans = {
        "filter": f"record_date:gte:{start_date}",
        "page[size]": 10000,
        "sort": "record_date"
    }
    df_trans = fetch_paginated_data(url_trans, params_trans)
    
    # 2. Fetch TGA Balance (Table I)
    url_tga = f"{API_BASE_URL}{DTS_TGA_ENDPOINT}"
    params_tga = {
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
    Returns: (gdp_value, gdp_date, quarter_label, days_old, is_estimated)
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "GDP",
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 4
    }

    print(f"Fetching latest GDP from FRED...")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data and data['observations']:
            latest = data['observations'][0]
            gdp_billions = float(latest['value'])
            gdp_annual = gdp_billions * 1_000_000_000
            gdp_date = pd.to_datetime(latest['date'])

            quarter_num = (gdp_date.month - 1) // 3 + 1
            if quarter_num == 1:
                actual_quarter = 4
                actual_year = gdp_date.year - 1
            else:
                actual_quarter = quarter_num - 1
                actual_year = gdp_date.year

            quarter = f"Q{actual_quarter} {actual_year}"
            today = pd.Timestamp.today()
            days_old = (today - gdp_date).days

            is_estimated = False
            if days_old > 90 and len(data['observations']) >= 2:
                prev_gdp = float(data['observations'][1]['value'])
                qoq_growth = (gdp_billions - prev_gdp) / prev_gdp
                quarters_elapsed = days_old / 90
                estimated_gdp_billions = gdp_billions * ((1 + qoq_growth) ** quarters_elapsed)
                estimated_gdp_annual = estimated_gdp_billions * 1_000_000_000

                print(f"FRED GDP: ${gdp_annual/1e12:.2f}T ({quarter}, {days_old} days old)")
                print(f"Estimated current GDP: ${estimated_gdp_annual/1e12:.2f}T (QoQ growth: {qoq_growth*100:.2f}%)")

                return estimated_gdp_annual, gdp_date, quarter, days_old, True
            else:
                print(f"FRED GDP: ${gdp_annual/1e12:.2f}T ({quarter}, {days_old} days old)")
                return gdp_annual, gdp_date, quarter, days_old, False

    except Exception as e:
        print(f"Error fetching GDP from FRED: {e}")
        print(f"Using fallback GDP: ${NOMINAL_GDP_FALLBACK/1e12:.2f}T")

    return NOMINAL_GDP_FALLBACK, None, "Unknown", 0, False


# =============================================================================
# CATEGORY CLASSIFICATION FUNCTIONS
# =============================================================================

def classify_spending(category_text):
    """
    Classify a DTS spending category into our standardized groups.
    Returns: (category_group, is_household_directed)
    """
    if not isinstance(category_text, str):
        return 'Other', False
    
    for group, keywords in SPENDING_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in category_text.lower():
                # Determine if household-directed
                is_household = group in [
                    'SSA_Benefits', 'Medicare', 'VA_Benefits', 
                    'Unemployment', 'Tax_Refunds_Individual', 
                    'SNAP_Food', 'Education', 'Housing'
                ]
                return group, is_household
    
    return 'Other', False


def classify_tax(category_text):
    """
    Classify a DTS tax receipt category into our standardized groups.
    """
    if not isinstance(category_text, str):
        return 'Other_Deposits'
    
    for group, keywords in TAX_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in category_text.lower():
                return group
    
    return 'Other_Deposits'


def is_excluded(category_text):
    """Check if a category should be excluded from analysis."""
    if not isinstance(category_text, str):
        return True
    return any(k.lower() in category_text.lower() for k in EXCLUDE_KEYWORDS)


# =============================================================================
# FISCAL CALENDAR FUNCTIONS
# =============================================================================

def get_fiscal_week(date):
    """
    Returns the fiscal week number (Wed-Wed aligned).
    Week starts on Wednesday.
    """
    # Find the Wednesday of this week
    days_since_wednesday = (date.weekday() - 2) % 7
    week_start = date - timedelta(days=days_since_wednesday)
    
    # Calculate week number from start of fiscal year (Oct 1)
    fiscal_year_start = datetime(date.year if date.month >= 10 else date.year - 1, 10, 1)
    # Adjust to first Wednesday on or after Oct 1
    days_to_wed = (2 - fiscal_year_start.weekday()) % 7
    first_fiscal_wed = fiscal_year_start + timedelta(days=days_to_wed)
    
    week_num = ((week_start - first_fiscal_wed).days // 7) + 1
    return max(1, week_num)


def get_fiscal_week_bounds(date):
    """
    Returns (start_date, end_date) for the fiscal week containing the given date.
    Fiscal week runs Wed-Tue (7 days starting Wednesday).
    """
    days_since_wednesday = (date.weekday() - 2) % 7
    week_start = date - timedelta(days=days_since_wednesday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def is_ss_payment_day(date):
    """
    Check if date is a Social Security payment day.
    SS pays on 2nd, 3rd, 4th Wednesday of month.
    """
    if date.weekday() != 2:  # Not Wednesday
        return False
    
    # Find which Wednesday of the month this is
    first_day = date.replace(day=1)
    days_to_first_wed = (2 - first_day.weekday()) % 7
    first_wednesday = first_day + timedelta(days=days_to_first_wed)
    
    wednesday_num = ((date - first_wednesday).days // 7) + 1
    return wednesday_num in [2, 3, 4]


def is_medicare_day(date):
    """
    Check if date is near month boundary (Medicare payment timing).
    Last 3 or first 3 days of month.
    """
    day = date.day
    # Get last day of month
    if date.month == 12:
        next_month = date.replace(year=date.year + 1, month=1, day=1)
    else:
        next_month = date.replace(month=date.month + 1, day=1)
    last_day = (next_month - timedelta(days=1)).day
    
    return day <= 3 or day >= last_day - 2


def is_tax_deadline(date):
    """
    Check if date is a tax deadline (15th or adjusted for weekend).
    """
    if date.day == 15:
        return True
    # Check if 15th was weekend and this is the next Monday
    potential_15th = date.replace(day=15) if date.day > 15 else None
    if potential_15th and potential_15th.weekday() >= 5:  # Weekend
        # Find next Monday
        days_to_monday = (7 - potential_15th.weekday()) % 7
        if days_to_monday == 0:
            days_to_monday = 7
        adjusted_date = potential_15th + timedelta(days=days_to_monday)
        return date == adjusted_date
    return False


def get_settlement_adjustment(date, instrument_type='bill'):
    """
    Calculate settlement date adjustment.
    Bills: T+1, Coupons: T+2
    """
    if instrument_type == 'bill':
        return 1
    else:  # coupon
        return 2


# =============================================================================
# ADVANCED METRICS CALCULATIONS
# =============================================================================

def calculate_fiscal_pressure_index(df):
    """
    Calculate the Fiscal Pressure Index (FPI).
    Composite indicator combining spending pressure and tax extraction.
    
    FPI = (Spending Z-score - Tax Z-score) / 2
    Positive = net fiscal injection
    Negative = net fiscal drain
    """
    # Use 60-day rolling window for normalization
    window = 60
    
    spending_mean = df['Total_Spending'].rolling(window=window).mean()
    spending_std = df['Total_Spending'].rolling(window=window).std()
    spending_zscore = (df['Total_Spending'] - spending_mean) / spending_std
    
    tax_mean = df['Total_Taxes'].rolling(window=window).mean()
    tax_std = df['Total_Taxes'].rolling(window=window).std()
    tax_zscore = (df['Total_Taxes'] - tax_mean) / tax_std
    
    fpi = (spending_zscore - tax_zscore) / 2
    return fpi


def calculate_seasonal_baseline(df):
    """
    Calculate seasonal baseline using 3-year historical average.
    Aligned by fiscal calendar day (day of fiscal year).
    """
    df = df.copy()
    
    # Calculate day of fiscal year
    df['Day_of_FY'] = df.index.map(lambda x: (
        x - datetime(x.year if x.month >= 10 else x.year - 1, 10, 1)
    ).days)
    
    # Group by day of fiscal year and calculate 3-year average
    # Use available historical data
    seasonal_avg = df.groupby('Day_of_FY')['Total_Spending'].mean()
    
    # Map back to full series
    df['Seasonal_Baseline'] = df['Day_of_FY'].map(seasonal_avg)
    df['Deviation_from_Seasonal'] = df['Total_Spending'] - df['Seasonal_Baseline']
    
    return df[['Seasonal_Baseline', 'Deviation_from_Seasonal']]


def calculate_qtd_metrics(df):
    """
    Calculate Quarter-to-Date metrics.
    QTD Fiscal Injection = cumulative spending - cumulative taxes within quarter
    """
    df = df.copy()
    
    # Identify fiscal quarters
    df['Fiscal_Quarter'] = df.index.map(lambda x: (
        f"FY{x.year + 1 if x.month >= 10 else x.year}Q{((x.month - 10) % 12) // 3 + 1}"
    ))
    
    # Calculate QTD cumulative
    df['QTD_Spending'] = df.groupby('Fiscal_Quarter')['Total_Spending'].cumsum()
    df['QTD_Taxes'] = df.groupby('Fiscal_Quarter')['Total_Taxes'].cumsum()
    df['QTD_Net_Injection'] = df['QTD_Spending'] - df['QTD_Taxes']
    
    return df[['Fiscal_Quarter', 'QTD_Spending', 'QTD_Taxes', 'QTD_Net_Injection']]


def calculate_3month_moving_sum(df):
    """
    Calculate 3-month (63 business days) moving sum of fiscal impulse.
    """
    window = 63  # ~3 months of business days
    return df['Net_Impulse'].rolling(window=window).sum()


def calculate_forward_impulse_estimate(df, weeks_forward=6):
    """
    Estimate forward fiscal impulse based on:
    1. Known scheduled payments (SS, Medicare)
    2. Historical seasonal patterns
    3. Recent trend extrapolation
    
    Returns estimated total impulse for next N weeks.
    """
    if len(df) < 252:  # Need at least 1 year of data
        return np.nan
    
    # Get recent trend (last 4 weeks)
    recent_avg = df['Net_Impulse'].tail(20).mean()
    
    # Get same period last year
    last_year_avg = df['Net_Impulse'].iloc[-272:-252].mean() if len(df) >= 272 else recent_avg
    
    # Calculate trend adjustment
    trend_factor = recent_avg / last_year_avg if last_year_avg != 0 else 1
    
    # Project forward (simple model)
    # Sum of next 6 weeks from last year, adjusted for trend
    future_start = len(df) - 252
    future_end = future_start + (weeks_forward * 5)
    
    if future_end <= len(df) and future_start >= 0:
        historical_forward = df['Net_Impulse'].iloc[future_start:future_end].sum()
        forward_estimate = historical_forward * trend_factor
    else:
        forward_estimate = recent_avg * weeks_forward * 5  # Fallback
    
    return forward_estimate


def calculate_tga_forecast(df, days_forward=5):
    """
    Forecast TGA balance based on:
    1. Known auction settlements
    2. Expected spending patterns
    3. Recent change rate
    """
    if len(df) < 20:
        return np.nan
    
    # Calculate recent daily change
    recent_change = df['TGA_Balance'].diff().tail(10).mean()
    
    # Simple linear projection
    current_tga = df['TGA_Balance'].iloc[-1]
    forecast = current_tga + (recent_change * days_forward)
    
    return forecast


def calculate_implied_liquidity_effect(df):
    """
    Calculate implied liquidity effect for next week.
    Based on expected TGA changes and Fed operations.
    
    Liquidity Effect = -ΔtGA + Fed Operations
    (TGA drain = liquidity injection)
    """
    if len(df) < 5:
        return np.nan
    
    # Expected TGA change (based on recent pattern)
    recent_tga_change = df['TGA_Balance'].diff().tail(5).mean()
    expected_tga_change = recent_tga_change * 5  # Next week
    
    # Negative TGA change = positive liquidity
    implied_liquidity = -expected_tga_change
    
    return implied_liquidity


# =============================================================================
# RECONCILIATION & AUDIT FUNCTIONS
# =============================================================================

def calculate_block_4w_sum(weekly_df):
    """
    Calculate sum of last 4 Wed-Wed weeks (block method).
    Used for comparison with sliding 20-BD cumulative.
    """
    if weekly_df.empty or len(weekly_df) < 4:
        return None
    
    last4weeks = weekly_df.tail(4)
    return {
        'sum_spending': last4weeks['Total_Spending'].sum(),
        'sum_taxes': last4weeks['Total_Taxes'].sum(),
        'sum_net': last4weeks['Net_Impulse'].sum(),
        'weeks_included': [idx.strftime('%Y-%m-%d') for idx in last4weeks.index]
    }


def perform_reconciliation_check(daily_df, weekly_df):
    """
    Perform reconciliation between sliding 20-BD cumulative and 
    block 4-week (Wed-Wed) sum.
    
    Returns dict with reconciliation results and discrepancy analysis.
    """
    if daily_df.empty:
        return {'status': 'NO_DATA', 'messages': ['No daily data available']}
    
    results = {
        'status': 'OK',
        'messages': [],
        'sliding_20bd': {},
        'block_4weeks': {},
        'discrepancy': {}
    }
    
    # Get sliding 20-BD values (last trading day)
    latest = daily_df.iloc[-1]
    results['sliding_20bd'] = {
        'spending': latest.get('4W_Cum_Spending', np.nan),
        'taxes': latest.get('4W_Cum_Taxes', np.nan),
        'net': latest.get('4W_Cum_Net', np.nan),
        'date': latest.name.strftime('%Y-%m-%d'),
        'method': 'Rolling 20 business days'
    }
    
    # Get block 4-week values
    block_values = calculate_block_4w_sum(weekly_df)
    if block_values:
        results['block_4weeks'] = {
            'spending': block_values['sum_spending'],
            'taxes': block_values['sum_taxes'],
            'net': block_values['sum_net'],
            'weeks': block_values['weeks_included'],
            'method': 'Sum of last 4 Wed-Wed weeks'
        }
        
        # Calculate discrepancy
        if pd.notna(results['sliding_20bd']['net']) and pd.notna(results['block_4weeks']['net']):
            disc_net = results['sliding_20bd']['net'] - results['block_4weeks']['net']
            disc_spending = results['sliding_20bd']['spending'] - results['block_4weeks']['spending']
            
            results['discrepancy'] = {
                'net': disc_net,
                'spending': disc_spending,
                'net_pct': (disc_net / results['block_4weeks']['net'] * 100) if results['block_4weeks']['net'] != 0 else 0
            }
            
            # Check if discrepancy is significant (> 5% or > $10B)
            TOLERANCE_ABS = 10_000  # $10B in millions
            TOLERANCE_PCT = 5.0
            
            if abs(disc_net) > TOLERANCE_ABS or abs(results['discrepancy']['net_pct']) > TOLERANCE_PCT:
                results['status'] = 'WARNING'
                results['messages'].append(
                    f"Significant discrepancy: ${disc_net:,.0f}M ({results['discrepancy']['net_pct']:.1f}%)"
                )
                results['messages'].append(
                    "Possible causes: settlement timing, month-end bursts, incomplete week"
                )
            else:
                results['messages'].append(f"Discrepancy within tolerance: ${disc_net:,.0f}M")
    else:
        results['messages'].append("Insufficient weekly data for block comparison")
    
    return results


def get_analysis_period_aligned(daily_df, weekly_df):
    """
    Get analysis period aligned to the weekly data shown.
    Returns start/end dates that match the fiscal weeks in the report.
    """
    if weekly_df.empty:
        return daily_df.index.min(), daily_df.index.max()
    
    # Get the weeks that will be shown (last 4)
    shown_weeks = weekly_df.tail(4)
    if shown_weeks.empty:
        return daily_df.index.min(), daily_df.index.max()
    
    # Analysis period should cover these weeks
    week_start = shown_weeks.index.min()
    week_end = shown_weeks.index.max() + pd.Timedelta(days=6)  # End of last week
    
    return week_start, week_end


# =============================================================================
# WEEKLY ANALYSIS (WED-WED ALIGNED)
# =============================================================================

def calculate_weekly_metrics(df):
    """
    Calculate weekly aggregates aligned to fiscal week (Wed-Wed).
    """
    df = df.copy()
    
    # Add fiscal week identifiers
    df['Fiscal_Week'] = df.index.map(lambda x: get_fiscal_week(x))
    df['Fiscal_Week_Start'], df['Fiscal_Week_End'] = zip(*df.index.map(get_fiscal_week_bounds))
    
    # Create unique week identifier
    df['Week_ID'] = df['Fiscal_Week_Start'].astype(str)
    
    # Weekly aggregations
    weekly = df.groupby('Week_ID').agg({
        'Total_Spending': 'sum',
        'Total_Taxes': 'sum',
        'Net_Impulse': 'sum',
        'Household_Spending': 'sum',
        'TGA_Balance': 'last',
        # Category breakdowns
        **{col: 'sum' for col in df.columns if col.startswith('Cat_')},
        **{col: 'sum' for col in df.columns if col.startswith('Tax_')},
    }).dropna(how='all')
    
    weekly.index = pd.to_datetime(weekly.index)
    weekly = weekly.sort_index()
    
    # Add week number
    weekly['Fiscal_Week_Num'] = weekly.index.map(get_fiscal_week)
    
    # Calculate weekly YoY
    weekly['Weekly_YoY_Spending'] = weekly['Total_Spending'] - weekly['Total_Spending'].shift(52)
    weekly['Weekly_YoY_Net'] = weekly['Net_Impulse'] - weekly['Net_Impulse'].shift(52)
    
    # Weekly moving averages
    weekly['MA4W_Spending'] = weekly['Total_Spending'].rolling(window=4).mean()
    weekly['MA4W_Net_Impulse'] = weekly['Net_Impulse'].rolling(window=4).mean()
    
    # Block 4-week sum (for reconciliation)
    weekly['Block_4W_Spending'] = weekly['Total_Spending'].rolling(window=4).sum()
    weekly['Block_4W_Taxes'] = weekly['Total_Taxes'].rolling(window=4).sum()
    weekly['Block_4W_Net'] = weekly['Net_Impulse'].rolling(window=4).sum()
    
    # Add week definition metadata
    weekly['Week_Definition'] = 'Wed-Wed'
    
    return weekly


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_fiscal_analysis(df_trans, df_tga, nominal_gdp):
    """
    Process data to calculate comprehensive fiscal metrics.
    """
    if df_trans.empty or df_tga.empty:
        print("Insufficient data.")
        return pd.DataFrame(), pd.DataFrame()

    # --- Preprocessing Transactions ---
    df_trans['record_date'] = pd.to_datetime(df_trans['record_date'])
    df_trans['transaction_today_amt'] = pd.to_numeric(df_trans['transaction_today_amt'], errors='coerce')
    
    # Exclude non-fiscal items
    df_clean = df_trans[~df_trans['transaction_catg'].apply(is_excluded)].copy()
    
    print(f"Cleaned data: {len(df_clean)} records (excluded {len(df_trans) - len(df_clean)} non-fiscal items)")

    # ==========================================================================
    # SPENDING ANALYSIS (WITHDRAWALS)
    # ==========================================================================
    
    df_withdrawals = df_clean[df_clean['transaction_type'] == 'Withdrawals'].copy()
    
    # Classify each transaction
    df_withdrawals['category_group'], df_withdrawals['is_household'] = zip(
        *df_withdrawals['transaction_catg'].apply(classify_spending)
    )
    
    # Daily spending by category
    daily_spending = df_withdrawals.pivot_table(
        index='record_date',
        columns='category_group',
        values='transaction_today_amt',
        aggfunc='sum',
        fill_value=0
    )
    
    # Rename columns with Cat_ prefix for clarity
    daily_spending.columns = ['Cat_' + col for col in daily_spending.columns]
    
    # Total spending
    daily_spending['Total_Spending'] = daily_spending.sum(axis=1)
    
    # Household-directed spending
    household_cols = [col for col in daily_spending.columns 
                     if any(hh in col for hh in ['SSA', 'Medicare', 'VA', 'Unemployment', 
                                                  'Tax_Refunds_Individual', 'SNAP', 'Education', 'Housing'])]
    daily_spending['Household_Spending'] = daily_spending[household_cols].sum(axis=1) if household_cols else 0

    # ==========================================================================
    # TAX RECEIPTS ANALYSIS (DEPOSITS)
    # ==========================================================================
    
    df_deposits = df_clean[df_clean['transaction_type'] == 'Deposits'].copy()
    
    # Classify each tax receipt
    df_deposits['tax_group'] = df_deposits['transaction_catg'].apply(classify_tax)
    
    # Daily taxes by category
    daily_taxes = df_deposits.pivot_table(
        index='record_date',
        columns='tax_group',
        values='transaction_today_amt',
        aggfunc='sum',
        fill_value=0
    )
    
    # Rename columns with Tax_ prefix
    daily_taxes.columns = ['Tax_' + col for col in daily_taxes.columns]
    
    # Total taxes
    daily_taxes['Total_Taxes'] = daily_taxes.sum(axis=1)

    # ==========================================================================
    # TGA BALANCE PROCESSING
    # ==========================================================================
    
    df_tga['record_date'] = pd.to_datetime(df_tga['record_date'])
    df_tga['close_today_bal'] = pd.to_numeric(df_tga['close_today_bal'], errors='coerce')
    df_tga['open_today_bal'] = pd.to_numeric(df_tga['open_today_bal'], errors='coerce')
    
    tga_closing = df_tga[df_tga['account_type'].str.contains("Closing Balance", na=False)].copy()
    tga_closing['balance'] = tga_closing['close_today_bal'].fillna(tga_closing['open_today_bal'])
    daily_tga = tga_closing.groupby('record_date')['balance'].sum().rename('TGA_Balance')

    # ==========================================================================
    # MERGE ALL DAILY METRICS
    # ==========================================================================
    
    merged = pd.concat([daily_spending, daily_taxes, daily_tga], axis=1).fillna(0).sort_index()
    
    # Net Impulse (Spending - Taxes)
    merged['Net_Impulse'] = merged['Total_Spending'] - merged['Total_Taxes']

    # ==========================================================================
    # FISCAL CALENDAR FLAGS
    # ==========================================================================
    
    merged['Is_SS_Payment_Day'] = merged.index.map(is_ss_payment_day)
    merged['Is_Medicare_Day'] = merged.index.map(is_medicare_day)
    merged['Is_Tax_Deadline'] = merged.index.map(is_tax_deadline)
    merged['Is_Trading_Day'] = merged['Total_Spending'] > 1_000_000_000
    
    # Fiscal year and week
    merged['Fiscal_Year'] = merged.index.map(lambda x: x.year + 1 if x.month >= 10 else x.year)
    merged['Fiscal_Week'] = merged.index.map(get_fiscal_week)

    # ==========================================================================
    # MOVING AVERAGES AND TRENDS
    # ==========================================================================
    
    # Daily moving averages
    merged['MA5_Spending'] = merged['Total_Spending'].rolling(window=5).mean()
    merged['MA20_Spending'] = merged['Total_Spending'].rolling(window=20).mean()
    merged['MA5_Net_Impulse'] = merged['Net_Impulse'].rolling(window=5).mean()
    merged['MA20_Net_Impulse'] = merged['Net_Impulse'].rolling(window=20).mean()
    
    # 4-week cumulative
    merged['4W_Cum_Spending'] = merged['Total_Spending'].rolling(window=20).sum()
    merged['4W_Cum_Taxes'] = merged['Total_Taxes'].rolling(window=20).sum()
    merged['4W_Cum_Net'] = merged['Net_Impulse'].rolling(window=20).sum()
    
    # 3-month moving sum
    merged['3M_Sum_Net_Impulse'] = calculate_3month_moving_sum(merged)

    # ==========================================================================
    # GDP NORMALIZATION
    # ==========================================================================
    
    # Weekly impulse as % of GDP (MA20 * 5 trading days)
    merged['Weekly_Impulse_Pct_GDP'] = (merged['MA20_Net_Impulse'] * 5 * 1_000_000) / nominal_gdp * 100
    
    # Annualized impulse as % of GDP
    merged['Annual_Impulse_Pct_GDP'] = (merged['MA20_Net_Impulse'] * 252 * 1_000_000) / nominal_gdp * 100

    # ==========================================================================
    # HISTORICAL COMPARISONS (YoY)
    # ==========================================================================
    
    # Daily YoY
    merged['YoY_Spending'] = merged['Total_Spending'] - merged['Total_Spending'].shift(252)
    merged['YoY_Taxes'] = merged['Total_Taxes'] - merged['Total_Taxes'].shift(252)
    merged['YoY_Net_Impulse'] = merged['Net_Impulse'] - merged['Net_Impulse'].shift(252)
    
    # 4-week cumulative YoY
    merged['4W_YoY_Spending'] = merged['4W_Cum_Spending'] - merged['4W_Cum_Spending'].shift(252)
    merged['4W_YoY_Net'] = merged['4W_Cum_Net'] - merged['4W_Cum_Net'].shift(252)
    
    # 2-year and 3-year comparisons
    merged['Prev_2Y_Net'] = merged['Net_Impulse'].shift(504)
    merged['Prev_3Y_Net'] = merged['Net_Impulse'].shift(756)
    
    # 3-year average baseline
    merged['3Y_Avg_Net_Impulse'] = (
        merged['Net_Impulse'].shift(252) + 
        merged['Prev_2Y_Net'] + 
        merged['Prev_3Y_Net']
    ) / 3
    merged['Deviation_3Y_Avg'] = merged['Net_Impulse'] - merged['3Y_Avg_Net_Impulse']

    # ==========================================================================
    # FISCAL-TO-DATE CUMULATIVE
    # ==========================================================================
    
    # MTD
    merged['YearMonth'] = merged.index.to_period('M')
    merged['MTD_Spending'] = merged.groupby('YearMonth')['Total_Spending'].cumsum()
    merged['MTD_Taxes'] = merged.groupby('YearMonth')['Total_Taxes'].cumsum()
    merged['MTD_Net'] = merged.groupby('YearMonth')['Net_Impulse'].cumsum()
    
    # FYTD
    merged['FY_Group'] = merged['Fiscal_Year']
    merged['FYTD_Spending'] = merged.groupby('FY_Group')['Total_Spending'].cumsum()
    merged['FYTD_Taxes'] = merged.groupby('FY_Group')['Total_Taxes'].cumsum()
    merged['FYTD_Net'] = merged.groupby('FY_Group')['Net_Impulse'].cumsum()
    
    # FYTD YoY comparison
    merged['Prev_FYTD_Net'] = merged['FYTD_Net'].shift(252)
    merged['FYTD_YoY_Diff'] = merged['FYTD_Net'] - merged['Prev_FYTD_Net']

    # ==========================================================================
    # ADVANCED METRICS
    # ==========================================================================
    
    # Fiscal Pressure Index
    merged['Fiscal_Pressure_Index'] = calculate_fiscal_pressure_index(merged)
    
    # Seasonal baseline and deviation
    seasonal_metrics = calculate_seasonal_baseline(merged)
    merged['Seasonal_Baseline'] = seasonal_metrics['Seasonal_Baseline']
    merged['Deviation_from_Seasonal'] = seasonal_metrics['Deviation_from_Seasonal']
    
    # QTD metrics
    qtd_metrics = calculate_qtd_metrics(merged)
    merged['Fiscal_Quarter'] = qtd_metrics['Fiscal_Quarter']
    merged['QTD_Spending'] = qtd_metrics['QTD_Spending']
    merged['QTD_Taxes'] = qtd_metrics['QTD_Taxes']
    merged['QTD_Net_Injection'] = qtd_metrics['QTD_Net_Injection']
    
    # TGA dynamics
    merged['TGA_Change'] = merged['TGA_Balance'].diff()
    merged['TGA_5D_Change'] = merged['TGA_Balance'].diff(5)
    merged['TGA_20D_Change'] = merged['TGA_Balance'].diff(20)
    
    # ==========================================================================
    # FORWARD-LOOKING ESTIMATES
    # ==========================================================================
    
    # Calculate for most recent data point
    merged['Forward_6W_Impulse_Est'] = np.nan
    merged['TGA_5D_Forecast'] = np.nan
    merged['Implied_Weekly_Liquidity'] = np.nan
    
    # Only calculate for recent periods (last 252 days)
    if len(merged) > 252:
        for i in range(max(0, len(merged) - 252), len(merged)):
            subset = merged.iloc[:i+1]
            merged.iloc[i, merged.columns.get_loc('Forward_6W_Impulse_Est')] = calculate_forward_impulse_estimate(subset)
            merged.iloc[i, merged.columns.get_loc('TGA_5D_Forecast')] = calculate_tga_forecast(subset)
            merged.iloc[i, merged.columns.get_loc('Implied_Weekly_Liquidity')] = calculate_implied_liquidity_effect(subset)

    # ==========================================================================
    # CALCULATE WEEKLY AGGREGATES
    # ==========================================================================
    
    weekly_df = calculate_weekly_metrics(merged)

    return merged, weekly_df


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(df, weekly_df, gdp_info):
    """
    Generates comprehensive console report and CSV outputs.
    """
    nominal_gdp, gdp_date, quarter, days_old, is_estimated = gdp_info
    
    recent = df.tail(10).copy()
    latest = df.iloc[-1]
    
    # Get analysis period aligned to weekly data
    period_start, period_end = get_analysis_period_aligned(df, weekly_df)
    
    print("\n" + "="*70)
    print("FISCAL ANALYSIS REPORT - ENHANCED (Fiscal Week Aligned)")
    print("="*70)
    
    print(f"\n📅 Report Date:     {latest.name.strftime('%Y-%m-%d')}")
    print(f"📅 Fiscal Week:     #{int(latest['Fiscal_Week'])} of FY{int(latest['Fiscal_Year'])}")
    print(f"📅 Analysis Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')} (Wed-Wed aligned)")
    
    # GDP Info with sensitivity analysis
    gdp_status = "ESTIMATED" if is_estimated else "ACTUAL"
    print(f"\n💰 Nominal GDP:     ${nominal_gdp/1e12:.2f}T ({gdp_status})")
    if gdp_date:
        print(f"💰 GDP Reference:   {quarter} (published {gdp_date.strftime('%Y-%m-%d')}, {days_old} days ago)")
    
    if days_old > 120:
        print(f"⚠️  WARNING: GDP data is {days_old} days old.")
        # Sensitivity analysis
        gdp_sensitivity = latest['MA20_Net_Impulse'] * 252 * 1_000_000 / (nominal_gdp * 1.01) * 100
        gdp_base = latest['MA20_Net_Impulse'] * 252 * 1_000_000 / nominal_gdp * 100
        sensitivity_bps = (gdp_base - gdp_sensitivity) * 100  # in bps
        print(f"    Sensitivity: ±1% GDP change → ±{abs(sensitivity_bps):.1f} bps on Annual %GDP")
    
    # ==========================================================================
    # METHODOLOGY NOTES
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📋 METHODOLOGY NOTES")
    print("-"*70)
    print("  Week Definition:     Wed-Wed (Fiscal Week starts Wednesday)")
    print("  4W Cumulative:       Rolling 20 business days (sliding window)")
    print("  Weekly % GDP:        (MA20_Net_Impulse × 5) / GDP × 100")
    print("  Annual % GDP:        (MA20_Net_Impulse × 252) / GDP × 100")
    print("  All amounts in:      Millions USD (M)")
    
    # ==========================================================================
    # SECTION 1: FISCAL IMPULSE OVERVIEW
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 1: FISCAL IMPULSE OVERVIEW")
    print("-"*70)
    
    print(f"\n  Daily Metrics (Latest: {latest.name.strftime('%Y-%m-%d')}):")
    print(f"    Total Spending:        ${latest['Total_Spending']:>15,.0f} M")
    print(f"    Total Taxes:           ${latest['Total_Taxes']:>15,.0f} M")
    print(f"    Net Impulse:           ${latest['Net_Impulse']:>15,.0f} M")
    print(f"    Household Spending:    ${latest['Household_Spending']:>15,.0f} M ({latest['Household_Spending']/latest['Total_Spending']*100:.1f}% of total)")
    
    print(f"\n  Moving Averages:")
    print(f"    MA5 Net Impulse:       ${latest['MA5_Net_Impulse']:>15,.0f} M")
    print(f"    MA20 Net Impulse:      ${latest['MA20_Net_Impulse']:>15,.0f} M")
    print(f"    Weekly % GDP:          {latest['Weekly_Impulse_Pct_GDP']:>15.3f}%")
    print(f"    Annual % GDP:          {latest['Annual_Impulse_Pct_GDP']:>15.2f}%")
    
    print(f"\n  4-Week Cumulative (Sliding 20 BD):")
    print(f"    Spending:              ${latest['4W_Cum_Spending']:>15,.0f} M")
    print(f"    Taxes:                 ${latest['4W_Cum_Taxes']:>15,.0f} M")
    print(f"    Net Injection:         ${latest['4W_Cum_Net']:>15,.0f} M")
    
    # ==========================================================================
    # RECONCILIATION CHECK
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("🔍 RECONCILIATION CHECK (Sliding vs Block)")
    print("-"*70)
    
    recon = perform_reconciliation_check(df, weekly_df)
    
    print(f"\n  Method Comparison:")
    print(f"    Sliding 20-BD Net:     ${recon['sliding_20bd'].get('net', 0):>15,.0f} M")
    if recon['block_4weeks']:
        print(f"    Block 4-Week Net:      ${recon['block_4weeks'].get('net', 0):>15,.0f} M")
        if recon['discrepancy']:
            disc = recon['discrepancy']['net']
            disc_pct = recon['discrepancy']['net_pct']
            status_icon = "✅" if recon['status'] == 'OK' else "⚠️"
            print(f"    Discrepancy:           ${disc:>15,.0f} M ({disc_pct:+.1f}%) {status_icon}")
    
    if recon['messages']:
        print(f"\n  Notes:")
        for msg in recon['messages']:
            print(f"    → {msg}")
    
    if recon['block_4weeks'] and 'weeks' in recon['block_4weeks']:
        print(f"\n  Block 4-Week includes: {', '.join(recon['block_4weeks']['weeks'])}")
    
    # ==========================================================================
    # SECTION 2: WEEKLY ANALYSIS (WED-WED)
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 2: WEEKLY ANALYSIS (Wed-Wed Aligned)")
    print("-"*70)
    
    if not weekly_df.empty:
        recent_weeks = weekly_df.tail(4)
        print(f"\n  Last 4 Fiscal Weeks:")
        print(f"  {'Week Start':<12} {'FW#':>4} {'Spending':>12} {'Taxes':>12} {'Net':>12} {'YoY Net':>12}")
        print(f"  {'-'*64}")
        for idx, row in recent_weeks.iterrows():
            yoy_str = f"${row['Weekly_YoY_Net']:>10,.0f}" if pd.notna(row['Weekly_YoY_Net']) else "N/A"
            print(f"  {idx.strftime('%Y-%m-%d'):<12} {row['Fiscal_Week_Num']:>4.0f} ${row['Total_Spending']:>10,.0f} ${row['Total_Taxes']:>10,.0f} ${row['Net_Impulse']:>10,.0f} {yoy_str}")
    
    # ==========================================================================
    # SECTION 3: CATEGORY BREAKDOWN
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 3: SPENDING CATEGORY BREAKDOWN")
    print("-"*70)
    
    # Get category columns
    cat_cols = [col for col in df.columns if col.startswith('Cat_')]
    
    if cat_cols:
        print(f"\n  Last Trading Day Categories:")
        cat_values = [(col.replace('Cat_', ''), latest[col]) for col in cat_cols if latest[col] > 0]
        cat_values.sort(key=lambda x: x[1], reverse=True)
        
        for cat, val in cat_values[:10]:  # Top 10
            pct = val / latest['Total_Spending'] * 100
            print(f"    {cat:<25} ${val:>12,.0f} M  ({pct:>5.1f}%)")
    
    # Tax categories
    tax_cols = [col for col in df.columns if col.startswith('Tax_') and col != 'Total_Taxes']
    
    if tax_cols:
        print(f"\n  Tax Receipt Categories:")
        tax_values = [(col.replace('Tax_', ''), latest[col]) for col in tax_cols if latest[col] > 0]
        tax_values.sort(key=lambda x: x[1], reverse=True)
        
        for tax, val in tax_values[:5]:  # Top 5
            pct = val / latest['Total_Taxes'] * 100 if latest['Total_Taxes'] > 0 else 0
            print(f"    {tax:<25} ${val:>12,.0f} M  ({pct:>5.1f}%)")
    
    # ==========================================================================
    # SECTION 4: HISTORICAL CONTEXT
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 4: HISTORICAL CONTEXT (YoY & Baseline)")
    print("-"*70)
    
    print(f"\n  Year-over-Year Comparison:")
    print(f"    Daily YoY Spending:    ${latest['YoY_Spending']:>15,.0f} M" if pd.notna(latest['YoY_Spending']) else "    Daily YoY Spending:    N/A (insufficient history)")
    print(f"    Daily YoY Net:         ${latest['YoY_Net_Impulse']:>15,.0f} M" if pd.notna(latest['YoY_Net_Impulse']) else "    Daily YoY Net:         N/A")
    print(f"    4-Week YoY Net:        ${latest['4W_YoY_Net']:>15,.0f} M" if pd.notna(latest['4W_YoY_Net']) else "    4-Week YoY Net:        N/A")
    
    print(f"\n  3-Year Baseline:")
    print(f"    3Y Avg Net Impulse:    ${latest['3Y_Avg_Net_Impulse']:>15,.0f} M" if pd.notna(latest['3Y_Avg_Net_Impulse']) else "    3Y Avg Net Impulse:    N/A")
    print(f"    Deviation from 3Y:     ${latest['Deviation_3Y_Avg']:>15,.0f} M" if pd.notna(latest['Deviation_3Y_Avg']) else "    Deviation from 3Y:     N/A")
    
    print(f"\n  Fiscal Year-to-Date:")
    print(f"    FYTD Spending:         ${latest['FYTD_Spending']:>15,.0f} M")
    print(f"    FYTD Taxes:            ${latest['FYTD_Taxes']:>15,.0f} M")
    print(f"    FYTD Net:              ${latest['FYTD_Net']:>15,.0f} M")
    print(f"    FYTD YoY Difference:   ${latest['FYTD_YoY_Diff']:>15,.0f} M" if pd.notna(latest['FYTD_YoY_Diff']) else "    FYTD YoY Difference:   N/A")
    
    # ==========================================================================
    # SECTION 5: FISCAL CALENDAR EVENTS
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 5: FISCAL CALENDAR CONTEXT")
    print("-"*70)
    
    print(f"\n  Today's Calendar Flags:")
    print(f"    SS Payment Day:        {'✓ YES' if latest['Is_SS_Payment_Day'] else '✗ No'}")
    print(f"    Medicare Day:          {'✓ YES' if latest['Is_Medicare_Day'] else '✗ No'}")
    print(f"    Tax Deadline:          {'✓ YES' if latest['Is_Tax_Deadline'] else '✗ No'}")
    print(f"    Valid Trading Day:     {'✓ YES' if latest['Is_Trading_Day'] else '✗ No'}")
    
    # Find upcoming events in recent data
    upcoming_ss = recent[recent['Is_SS_Payment_Day'] == True]
    if not upcoming_ss.empty:
        print(f"\n  SS Payment Days in Period: {', '.join(upcoming_ss.index.strftime('%Y-%m-%d'))}")
    
    # ==========================================================================
    # SECTION 6: ADVANCED METRICS
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 6: ADVANCED METRICS & INDICATORS")
    print("-"*70)
    
    print(f"\n  Fiscal Pressure Index:")
    print(f"    Current FPI:           {latest['Fiscal_Pressure_Index']:>15.2f}" if pd.notna(latest['Fiscal_Pressure_Index']) else "    Current FPI:           N/A")
    fpi_interpretation = "Net fiscal INJECTION" if latest['Fiscal_Pressure_Index'] > 0 else "Net fiscal DRAIN" if pd.notna(latest['Fiscal_Pressure_Index']) else "Unknown"
    print(f"    Interpretation:        {fpi_interpretation}")
    
    print(f"\n  Seasonal Analysis:")
    print(f"    Seasonal Baseline:     ${latest['Seasonal_Baseline']:>15,.0f} M" if pd.notna(latest['Seasonal_Baseline']) else "    Seasonal Baseline:     N/A")
    print(f"    Deviation:             ${latest['Deviation_from_Seasonal']:>15,.0f} M" if pd.notna(latest['Deviation_from_Seasonal']) else "    Deviation:             N/A")
    
    print(f"\n  Quarter-to-Date:")
    print(f"    Quarter:               {latest['Fiscal_Quarter']}")
    print(f"    QTD Net Injection:     ${latest['QTD_Net_Injection']:>15,.0f} M")
    
    print(f"\n  3-Month Rolling:")
    print(f"    3M Sum Net Impulse:    ${latest['3M_Sum_Net_Impulse']:>15,.0f} M" if pd.notna(latest['3M_Sum_Net_Impulse']) else "    3M Sum Net Impulse:    N/A")
    
    # ==========================================================================
    # SECTION 7: TGA & LIQUIDITY
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 7: TGA & LIQUIDITY DYNAMICS")
    print("-"*70)
    
    print(f"\n  TGA Balance:")
    print(f"    Current Balance:       ${latest['TGA_Balance']:>15,.0f} M")
    print(f"    Daily Change:          ${latest['TGA_Change']:>15,.0f} M" if pd.notna(latest['TGA_Change']) else "    Daily Change:          N/A")
    print(f"    5-Day Change:          ${latest['TGA_5D_Change']:>15,.0f} M" if pd.notna(latest['TGA_5D_Change']) else "    5-Day Change:          N/A")
    print(f"    20-Day Change:         ${latest['TGA_20D_Change']:>15,.0f} M" if pd.notna(latest['TGA_20D_Change']) else "    20-Day Change:         N/A")
    
    tga_interpretation = "→ Liquidity INJECTION (TGA drawdown)" if latest['TGA_5D_Change'] < 0 else "→ Liquidity DRAIN (TGA buildup)" if pd.notna(latest['TGA_5D_Change']) else ""
    if tga_interpretation:
        print(f"    Interpretation:        {tga_interpretation}")
    
    # ==========================================================================
    # SECTION 8: FORWARD-LOOKING ESTIMATES
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 8: FORWARD-LOOKING ESTIMATES")
    print("-"*70)
    
    print(f"\n  6-Week Forward Impulse:  ${latest['Forward_6W_Impulse_Est']:>15,.0f} M" if pd.notna(latest['Forward_6W_Impulse_Est']) else "\n  6-Week Forward Impulse:  N/A (insufficient history)")
    print(f"  TGA 5-Day Forecast:      ${latest['TGA_5D_Forecast']:>15,.0f} M" if pd.notna(latest['TGA_5D_Forecast']) else "  TGA 5-Day Forecast:      N/A")
    print(f"  Implied Weekly Liquidity: ${latest['Implied_Weekly_Liquidity']:>15,.0f} M" if pd.notna(latest['Implied_Weekly_Liquidity']) else "  Implied Weekly Liquidity: N/A")
    
    # ==========================================================================
    # SECTION 9: RECENT TREND TABLE
    # ==========================================================================
    
    print("\n" + "-"*70)
    print("📊 SECTION 9: RECENT TREND (Last 5 Trading Days)")
    print("-"*70)
    
    cols_to_show = ['Total_Spending', 'Total_Taxes', 'Net_Impulse', 'MA20_Net_Impulse', 
                    'Weekly_Impulse_Pct_GDP', 'TGA_Balance', 'Fiscal_Pressure_Index']
    available_cols = [c for c in cols_to_show if c in recent.columns]
    
    print(f"\n{recent[available_cols].tail(5).to_string(float_format='{:,.2f}'.format)}")
    
    # ==========================================================================
    # EXPORT DATA
    # ==========================================================================
    
    # Ensure output directory exists
    os.makedirs("outputs/fiscal", exist_ok=True)
    
    # Daily data
    output_file = "outputs/fiscal/fiscal_analysis_full.csv"
    df.to_csv(output_file)
    print(f"\n✅ Daily data exported to {output_file}")
    
    # Weekly data
    if not weekly_df.empty:
        weekly_output = "outputs/fiscal/fiscal_analysis_weekly.csv"
        weekly_df.to_csv(weekly_output)
        print(f"✅ Weekly data exported to {weekly_output}")
    
    print("\n" + "="*70)
    print("END OF REPORT")
    print("="*70)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    print("="*70)
    print("FISCAL ANALYSIS ENGINE - ENHANCED VERSION")
    print("Aligned with Fiscal Week Reports methodology")
    print("="*70)
    
    # Fetch data
    print("\n📡 Fetching DTS data...")
    df_trans, df_tga = fetch_dts_data()
    
    if df_trans.empty:
        print("❌ No transaction data fetched.")
        return
    
    print(f"✅ Fetched {len(df_trans)} transactions and {len(df_tga)} TGA records.")
    
    # Fetch GDP
    print("\n📡 Fetching GDP data...")
    gdp_info = fetch_current_gdp()
    current_gdp = gdp_info[0]
    
    # Process
    print("\n⚙️ Processing fiscal analysis...")
    daily_df, weekly_df = process_fiscal_analysis(df_trans, df_tga, current_gdp)
    
    if daily_df.empty:
        print("❌ Processing failed.")
        return
    
    print(f"✅ Processed {len(daily_df)} daily records and {len(weekly_df)} weekly records.")
    
    # Generate report
    generate_report(daily_df, weekly_df, gdp_info)


if __name__ == "__main__":
    main()
