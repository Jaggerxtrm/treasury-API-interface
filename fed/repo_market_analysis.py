"""
Repo Market Analysis - OFR Data Integration
Analisi granulare del mercato repo usando dati OFR.
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Add fed directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.ofr_client import OFRClient
from config import DEFAULT_START_DATE, OUTPUT_DIR_FED
from utils.db_manager import TimeSeriesDB

def analyze_repo_collateral_stress(df):
    """
    Identifica stress nel collateral specifico usando proxy FNYR.
    
    Proxy Logic:
    - DVP (Treasury) ~= SOFR Vol - BGCR Vol
    - GCF (MBS/Agency) ~= BGCR Vol - TGCR Vol
    - Tri-Party ~= TGCR Vol
    """
    if df.empty:
        return pd.DataFrame()
        
    # Pivot to get timeseries of volumes and rates
    # We want columns: SOFR_Vol, SOFR_Rate, BGCR_Vol, etc.
    
    # Filter for volumes
    vols = df[df['data_type'] == 'volume'].pivot(index='date', columns='series_type', values='value')
    rates = df[df['data_type'] == 'rate'].pivot(index='date', columns='series_type', values='value')
    
    # Rename columns
    vols.columns = [f"{c}_Vol" for c in vols.columns]
    rates.columns = [f"{c}_Rate" for c in rates.columns]
    
    # Combine
    analysis_df = pd.concat([vols, rates], axis=1)
    analysis_df = analysis_df.fillna(0) # Fill missing days with 0? Or ffill? Repo market is daily. 0 is safer for volume.
    
    # Calculate Derived Volumes
    # Ensure columns exist
    if 'SOFR_Vol' in analysis_df.columns and 'BGCR_Vol' in analysis_df.columns:
        analysis_df['DVP_Volume'] = analysis_df['SOFR_Vol'] - analysis_df['BGCR_Vol']
        # DVP is mostly Treasury
        analysis_df['Treasury_Volume'] = analysis_df['DVP_Volume']
        
    if 'BGCR_Vol' in analysis_df.columns and 'TGCR_Vol' in analysis_df.columns:
        analysis_df['GCF_Volume'] = analysis_df['BGCR_Vol'] - analysis_df['TGCR_Vol']
        # GCF is mixed but often used for MBS/Agency
        analysis_df['MBS_Agency_Volume'] = analysis_df['GCF_Volume']
        
    if 'TGCR_Vol' in analysis_df.columns:
        analysis_df['TriParty_Volume'] = analysis_df['TGCR_Vol']
        
    # Total Volume (SOFR Vol is the broadest measure)
    if 'SOFR_Vol' in analysis_df.columns:
        analysis_df['Total_Volume'] = analysis_df['SOFR_Vol']
    
    # Calculate Shares
    # Avoid division by zero
    mask = analysis_df['Total_Volume'] > 0
    
    if 'Treasury_Volume' in analysis_df.columns:
        analysis_df.loc[mask, 'Treasury_Share'] = analysis_df.loc[mask, 'Treasury_Volume'] / analysis_df.loc[mask, 'Total_Volume']
        
    if 'MBS_Agency_Volume' in analysis_df.columns:
        analysis_df.loc[mask, 'MBS_Agency_Share'] = analysis_df.loc[mask, 'MBS_Agency_Volume'] / analysis_df.loc[mask, 'Total_Volume']
        
    if 'TriParty_Volume' in analysis_df.columns:
        analysis_df.loc[mask, 'TriParty_Share'] = analysis_df.loc[mask, 'TriParty_Volume'] / analysis_df.loc[mask, 'Total_Volume']

    # Identifica shift strutturali (MA20)
    if 'MBS_Agency_Share' in analysis_df.columns:
        analysis_df['MBS_Share_MA20'] = analysis_df['MBS_Agency_Share'].rolling(20).mean()
        
    return analysis_df

def calculate_repo_stress_index(df_analysis, df_raw):
    """
    Indice di stress repo (0-100) basato su:
    - Volumi anormali
    - Tassi spike (SOFR vs IORB ideally, but here just rate volatility)
    - Shift collateral
    """
    if df_analysis.empty:
        return df_analysis
        
    stress_components = []
    
    # Component 1: Rate spikes (SOFR Rate Volatility)
    if 'SOFR_Rate' in df_analysis.columns:
        rate = df_analysis['SOFR_Rate']
        rate_ma = rate.rolling(20).mean()
        rate_std = rate.rolling(20).std()
        
        # Z-score
        # Avoid div by zero
        rate_std = rate_std.replace(0, 1) # Dummy replacement if flat
        rate_zscore = (rate - rate_ma) / rate_std
        
        rate_stress = rate_zscore.clip(0, 3) / 3 * 100
        df_analysis['Rate_Stress'] = rate_stress
        stress_components.append('Rate_Stress')
    
    # Component 2: Volume collapse
    if 'Total_Volume' in df_analysis.columns:
        vol = df_analysis['Total_Volume']
        vol_ma = vol.rolling(20).mean()
        vol_std = vol.rolling(20).std()
        
        # Lower volume = stress? Or Higher?
        # In repo, sudden drop in volume might mean participants pulling back (fails).
        # Let's track absolute deviation.
        vol_zscore = abs(vol - vol_ma) / vol_std
        
        df_analysis['Volume_Stress'] = vol_zscore.clip(0, 3) / 3 * 100
        stress_components.append('Volume_Stress')
    
    # Component 3: Collateral shift (MBS Decline)
    if 'MBS_Agency_Share' in df_analysis.columns:
        mbs_share = df_analysis['MBS_Agency_Share']
        mbs_ma = mbs_share.rolling(20).mean()
        mbs_std = mbs_share.rolling(20).std()
        
        # Decline in MBS share
        mbs_decline = (mbs_ma - mbs_share) / mbs_std
        df_analysis['MBS_Stress'] = mbs_decline.clip(0, 3) / 3 * 100
        stress_components.append('MBS_Stress')
    
    # Weighted average
    if stress_components:
        df_analysis['Repo_Stress_Index'] = df_analysis[stress_components].mean(axis=1)
    else:
        df_analysis['Repo_Stress_Index'] = 0
        
    return df_analysis

def main():
    print("Starting Repo Market Analysis (OFR Data - FNYR Proxies)...")
    
    client = OFRClient()
    
    # Fetch data
    try:
        df_raw = client.fetch_repo_volumes(DEFAULT_START_DATE)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    if df_raw.empty:
        print("No data returned from OFR API.")
        return

    print(f"Fetched {len(df_raw)} records.")
    
    # Analyze
    df_analysis = analyze_repo_collateral_stress(df_raw)
    df_analysis = calculate_repo_stress_index(df_analysis, df_raw)
    
    # Export
    # Export to Database
    print("\n💾 Saving to DuckDB...")
    try:
        db = TimeSeriesDB("database/treasury_data.duckdb")
        
        # Reset index to make date a column
        df_save = df_analysis.reset_index()
        if 'index' in df_save.columns:
            df_save = df_save.rename(columns={'index': 'record_date'})
        elif 'date' in df_save.columns:
            df_save = df_save.rename(columns={'date': 'record_date'})
            
        db.upsert_data(df_save, "repo_market_analysis", key_col="record_date")
        print("✅ Repo market analysis saved to 'repo_market_analysis'")
        db.close()
    except Exception as e:
        print(f"❌ Database save failed: {e}")
    
    # Print summary
    if not df_analysis.empty:
        latest = df_analysis.iloc[-1]
        print("\n=== REPO MARKET SUMMARY ===")
        print(f"Date: {latest.name.strftime('%Y-%m-%d')}")
        if 'Total_Volume' in latest:
            print(f"Total Volume: ${latest['Total_Volume']/1e9:,.0f} B")
        if 'MBS_Agency_Share' in latest:
            print(f"MBS/Agency Share: {latest['MBS_Agency_Share']:.1%}")
        if 'Treasury_Share' in latest:
            print(f"Treasury Share: {latest['Treasury_Share']:.1%}")
        if 'Repo_Stress_Index' in latest:
            print(f"Repo Stress Index: {latest['Repo_Stress_Index']:.1f}/100")

if __name__ == "__main__":
    main()
