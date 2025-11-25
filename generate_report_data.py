import pandas as pd
import numpy as np
from datetime import datetime

def analyze_data():
    try:
        # Load Fiscal Data
        fiscal_df = pd.read_csv('outputs/fiscal/fiscal_analysis_full.csv')
        fiscal_df['record_date'] = pd.to_datetime(fiscal_df['record_date'])
        
        # Filter for current month (Nov 2025 based on last data)
        current_month = '2025-11'
        mtd_df = fiscal_df[fiscal_df['record_date'].astype(str).str.startswith(current_month)]
        
        # Calculate MTD sums
        mtd_sums = {
            'Total_Impulse': mtd_df['Total_Impulse'].sum(),
            'HHS_Medicare': mtd_df['HHS_Medicare'].sum(),
            'SSA_Benefits': mtd_df['SSA_Benefits'].sum(),
            'Interest': mtd_df['Interest'].sum(),
            'VA_Benefits': mtd_df['VA_Benefits'].sum(),
            'Unemployment': mtd_df['Unemployment'].sum(),
            'Tax_Refunds': mtd_df['Tax_Refunds_Indiv'].sum(),
            'Other': mtd_df['Other'].sum()
        }
        
        # Household Absorption
        household_total = (mtd_sums['HHS_Medicare'] + mtd_sums['SSA_Benefits'] + 
                          mtd_sums['VA_Benefits'] + mtd_sums['Unemployment'] + 
                          mtd_sums['Tax_Refunds'])
        household_pct = (household_total / mtd_sums['Total_Impulse']) * 100 if mtd_sums['Total_Impulse'] else 0
        
        # Load Fed Data
        # Fed data has date in index (col 0)
        fed_df = pd.read_csv('outputs/fed/fed_liquidity_full.csv', index_col=0, parse_dates=True)
        fed_df.index.name = 'record_date'
        fed_df = fed_df.reset_index()
        
        # Merge for correlations (last 3 months)
        merged_df = pd.merge(fiscal_df, fed_df, on='record_date', how='inner')
        last_3m = merged_df.tail(60) # Approx 3 months of trading days
        
        # Correlations
        correlations = {
            'NetLiq_vs_TGA': last_3m['Net_Liquidity'].corr(last_3m['TGA_Balance_x']), # TGA might be in both, use _x from fiscal or _y from fed
            'RRP_vs_Spread': last_3m['RRP_Balance'].corr(last_3m['Spread_SOFR_IORB']),
            'NetLiq_vs_Spread': last_3m['Net_Liquidity'].corr(last_3m['Spread_SOFR_IORB'])
        }
        
        # Latest Values
        latest_fiscal = fiscal_df.iloc[-1]
        latest_fed = fed_df.iloc[-1]
        
        print("--- DATA START ---")
        print(f"MTD_Sums: {mtd_sums}")
        print(f"Household_Absorption: {household_total} ({household_pct:.2f}%)")
        print(f"Correlations: {correlations}")
        print(f"Latest_Fiscal_Date: {latest_fiscal['record_date']}")
        print(f"Latest_Fed_Date: {latest_fed['record_date']}")
        print(f"Latest_Net_Liquidity: {latest_fed['Net_Liquidity']}")
        print(f"Latest_RRP: {latest_fed['RRP_Balance']}")
        print(f"Latest_TGA: {latest_fiscal['TGA_Balance']}")
        print(f"Latest_SOFR_Spread: {latest_fed['Spread_SOFR_IORB']}")
        print(f"Latest_EFFR_Spread: {latest_fed['Spread_EFFR_IORB']}")
        print(f"Latest_SOFR_Vol: {latest_fed['SOFR_Vol_5D']}")
        print(f"Latest_Stress_Index: {latest_fed['Stress_Flag']}") # Or calculate if not in CSV
        
        # Weekly Flows (approx last 5 days sum/avg)
        last_5_fiscal = fiscal_df.tail(5)
        last_5_fed = fed_df.tail(5)
        
        print(f"Weekly_Fiscal_Impulse: {last_5_fiscal['Total_Impulse'].sum()}")
        print(f"Weekly_Tax_Receipts: {last_5_fiscal['Total_Taxes'].sum()}")
        # Fed assets change
        fed_assets_change = latest_fed['Fed_Total_Assets'] - fed_df.iloc[-6]['Fed_Total_Assets'] if len(fed_df) > 5 else 0
        print(f"Weekly_Fed_Assets_Change: {fed_assets_change}")
        
        print("--- DATA END ---")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_data()
