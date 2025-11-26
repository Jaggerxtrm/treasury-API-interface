#!/usr/bin/env python3
"""
Investigation Script: Fiscal Analysis Implementation vs Methodology
Performs validation and reconciliation checks on fiscal_analysis.py output
"""

import pandas as pd
import numpy as np

# Constants (from fiscal_analysis.py)
NOMINAL_GDP_FALLBACK = 29_000_000_000_000  # $29T in USD

print("="*80)
print("FISCAL ANALYSIS INVESTIGATION")
print("Comparing Implementation vs Methodology (Fiscal Week #44)")
print("="*80)

# Load data
print("\n[1] LOADING DATA...")
fiscal_df = pd.read_csv('outputs/fiscal/fiscal_analysis_full.csv', parse_dates=['record_date'])
weekly_df = pd.read_csv('outputs/fiscal/fiscal_analysis_weekly.csv')
fed_df = pd.read_csv('outputs/fed/fed_liquidity_full.csv')

print(f"✓ Loaded {len(fiscal_df)} daily fiscal records")
print(f"✓ Loaded {len(weekly_df)} weekly fiscal records")
print(f"✓ Loaded {len(fed_df)} fed liquidity records")

# Get latest data point
latest = fiscal_df.iloc[-1]
latest_date = latest['record_date']

print(f"\n[2] LATEST DATA POINT: {latest_date}")
print(f"    MA20_Net_Impulse: ${latest['MA20_Net_Impulse']:,.2f} M")
print(f"    4W_Cum_Net: ${latest['4W_Cum_Net']:,.2f} M")
print(f"    Annual_Impulse_Pct_GDP: {latest['Annual_Impulse_Pct_GDP']:.4f}%")
print(f"    Total_Spending: ${latest['Total_Spending']:,.2f} M")
print(f"    Household_Spending: ${latest['Household_Spending']:,.2f} M")

# CRITICAL TEST 1: GDP Normalization Unit Check
print("\n" + "="*80)
print("[3] CRITICAL TEST 1: GDP Normalization Units")
print("="*80)

ma20_net = latest['MA20_Net_Impulse']  # in Millions
annual_pct_reported = latest['Annual_Impulse_Pct_GDP']

# Current implementation (from code line 989):
# Annual % = (MA20_Net_Impulse * 252 * 1_000_000) / nominal_gdp * 100
# This assumes MA20 is in Millions, multiplies by 1M to get USD, then divides by GDP in USD

print(f"\nImplementation formula:")
print(f"  Annual % = (MA20 * 252 * 1_000_000) / GDP * 100")
print(f"  Annual % = ({ma20_net:.2f} * 252 * 1,000,000) / {NOMINAL_GDP_FALLBACK:,} * 100")

annual_calc_current = (ma20_net * 252 * 1_000_000) / NOMINAL_GDP_FALLBACK * 100
print(f"  Calculated: {annual_calc_current:.4f}%")
print(f"  Reported:   {annual_pct_reported:.4f}%")
print(f"  Match: {abs(annual_calc_current - annual_pct_reported) < 0.01}")

# CORRECT formula (if MA20 is already in Millions USD):
# GDP should also be in Millions for consistent units
GDP_MILLIONS = NOMINAL_GDP_FALLBACK / 1_000_000
annual_calc_correct = (ma20_net * 252) / GDP_MILLIONS * 100

print(f"\nCORRECT formula (if all in Millions):")
print(f"  Annual % = (MA20 * 252) / GDP_Millions * 100")
print(f"  Annual % = ({ma20_net:.2f} * 252) / {GDP_MILLIONS:,.0f} * 100")
print(f"  Calculated: {annual_calc_correct:.4f}%")

discrepancy_gdp = annual_calc_current - annual_calc_correct
print(f"\n  ⚠️  DISCREPANCY: {discrepancy_gdp:.4f}%")
if abs(discrepancy_gdp) > 0.01:
    print(f"  ❌ HIGH PRIORITY: GDP normalization has 1000x error!")
else:
    print(f"  ✅ Units are consistent")

# CRITICAL TEST 2: Household Share Calculation
print("\n" + "="*80)
print("[4] CRITICAL TEST 2: Household Share")
print("="*80)

household_spend = latest['Household_Spending']
total_spend = latest['Total_Spending']
net_impulse = latest['Net_Impulse']

# Current implementation (line 1149 in report):
household_share_on_spending = (household_spend / total_spend * 100) if total_spend != 0 else 0

print(f"\nHousehold Spending: ${household_spend:,.2f} M")
print(f"Total Spending:     ${total_spend:,.2f} M")
print(f"Net Impulse:        ${net_impulse:,.2f} M")

print(f"\nMethod 1 (household / total_spending):")
print(f"  Share: {household_share_on_spending:.2f}%")
print(f"  Valid range: [0, 100]%")
print(f"  Can go negative: NO")

# Alternative (wrong) method that could go negative:
household_share_on_net = (household_spend / net_impulse * 100) if net_impulse != 0 else 0
print(f"\nMethod 2 (household / net_impulse) [WRONG]:")
print(f"  Share: {household_share_on_net:.2f}%")
print(f"  Can go negative: YES (if net_impulse < 0)")

# Check if there are any negative household_share in the dataset
if 'household_share' in fiscal_df.columns:
    negative_shares = fiscal_df[fiscal_df['household_share'] < 0]
    print(f"\n  Negative household_share instances: {len(negative_shares)}")
    if len(negative_shares) > 0:
        print(f"  ❌ FOUND NEGATIVE VALUES - indicates wrong formula!")
        print(f"     Sample dates with negative:")
        print(negative_shares[['record_date', 'household_share', 'Net_Impulse']].head())

# CRITICAL TEST 3: 4-Week Cumulative (Sliding vs Block)
print("\n" + "="*80)
print("[5] CRITICAL TEST 3: 4-Week Cumulative (Sliding vs Block)")
print("="*80)

# Get last 20 business days for sliding calculation
last_20 = fiscal_df.tail(20)
sliding_20bd_net = last_20['Net_Impulse'].sum()
sliding_20bd_spend = last_20['Total_Spending'].sum()

reported_4w_net = latest['4W_Cum_Net']
reported_4w_spend = latest['4W_Cum_Spending']

print(f"\nSliding 20 BD (manual calculation):")
print(f"  Sum Net:      ${sliding_20bd_net:,.2f} M")
print(f"  Sum Spending: ${sliding_20bd_spend:,.2f} M")

print(f"\nReported 4W_Cum values:")
print(f"  Net:      ${reported_4w_net:,.2f} M")
print(f"  Spending: ${reported_4w_spend:,.2f} M")

disc_net = abs(sliding_20bd_net - reported_4w_net)
disc_spend = abs(sliding_20bd_spend - reported_4w_spend)

print(f"\nDiscrepancy:")
print(f"  Net:      ${disc_net:,.2f} M ({disc_net/reported_4w_net*100:.2f}%)")
print(f"  Spending: ${disc_spend:,.2f} M ({disc_spend/reported_4w_spend*100:.2f}%)")

TOLERANCE_ABS = 10_000  # $10B
TOLERANCE_PCT = 1.0

if disc_net > TOLERANCE_ABS or (disc_net/reported_4w_net*100) > TOLERANCE_PCT:
    print(f"  ❌ HIGH PRIORITY: Significant discrepancy in 4W cumulative!")
else:
    print(f"  ✅ Within tolerance")

# CRITICAL TEST 4: Net Liquidity Calculation
print("\n" + "="*80)
print("[6] CRITICAL TEST 4: Net Liquidity Calculation")
print("="*80)

# Get latest fed data
fed_latest = fed_df.iloc[-1]
print(f"\nFed Liquidity Data (latest):")
print(f"  Fed_Total_Assets: ${fed_latest.get('Fed_Total_Assets', np.nan):,.0f} M")
print(f"  RRP_Balance_M:    ${fed_latest.get('RRP_Balance_M', np.nan):,.0f} M")
print(f"  TGA_Balance:      ${fed_latest.get('TGA_Balance', np.nan):,.0f} M")

if 'Net_Liquidity' in fed_latest.index:
    reported_net_liq = fed_latest['Net_Liquidity']
    print(f"  Net_Liquidity (reported): ${reported_net_liq:,.0f} M")

    # Calculate manually
    fed_assets = fed_latest.get('Fed_Total_Assets', np.nan)
    rrp = fed_latest.get('RRP_Balance_M', np.nan)
    tga = fed_latest.get('TGA_Balance', np.nan)

    if pd.notna(fed_assets) and pd.notna(rrp) and pd.notna(tga):
        calc_net_liq = fed_assets - rrp - tga
        print(f"  Net_Liquidity (calculated): ${calc_net_liq:,.0f} M")

        diff = abs(reported_net_liq - calc_net_liq)
        tol = max(1_000, abs(reported_net_liq) * 0.0005)

        print(f"\n  Difference: ${diff:,.0f} M")
        print(f"  Tolerance:  ${tol:,.0f} M")

        if diff > tol:
            print(f"  ❌ HIGH PRIORITY: Net Liquidity mismatch!")
        else:
            print(f"  ✅ Within tolerance")

# SUMMARY
print("\n" + "="*80)
print("[7] SUMMARY OF FINDINGS")
print("="*80)

findings = []
findings.append({
    'Issue': 'GDP Normalization Units',
    'Priority': 'HIGH' if abs(discrepancy_gdp) > 0.01 else 'LOW',
    'Description': f'Potential 1000x error in %GDP calculation. Discrepancy: {discrepancy_gdp:.4f}%'
})

findings.append({
    'Issue': '4W Cumulative Calculation',
    'Priority': 'HIGH' if disc_net > TOLERANCE_ABS else 'LOW',
    'Description': f'Sliding vs reported discrepancy: ${disc_net:,.0f}M'
})

print("\n{:<30} {:<10} {}".format("ISSUE", "PRIORITY", "DESCRIPTION"))
print("-" * 80)
for f in findings:
    print("{:<30} {:<10} {}".format(f['Issue'], f['Priority'], f['Description']))

print("\n" + "="*80)
print("Investigation complete. Review findings above.")
print("="*80)
