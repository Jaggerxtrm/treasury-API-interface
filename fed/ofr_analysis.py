#!/usr/bin/env python3
"""
OFR Repo Market Analysis
Fetches OFR repo data and calculates stress indicators for the Liquidity Composite Index.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add current directory to path for fed imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.ofr_client import OFRClient
from utils.data_loader import get_output_path
import config
from utils.db_manager import TimeSeriesDB

def calculate_repo_stress_index(df):
    """
    Calculate composite stress index from OFR repo data.
    
    Components:
    1. Volume Stress: High volume = funding pressure
    2. Rate Spread: Elevated rates = stress
    3. Volume Volatility: High volatility =不安
    
    Returns DataFrame with Repo_Stress_Index column
    """
    if df.empty:
        return pd.DataFrame()
    
    print("Calculating repo stress indicators...")
    
    # Pivot data to have rates and volumes as columns
    df_pivot = df.pivot_table(
        index='date',
        columns='mnemonic',
        values='value',
        aggfunc='first'
    )
    
    # Parse dates and sort
    df_pivot.index = pd.to_datetime(df_pivot.index)
    df_pivot = df_pivot.sort_index()
    
    # Forward fill missing values (repo data has gaps)
    df_pivot = df_pivot.ffill()
    
    # Calculate stress components
    stress_df = pd.DataFrame(index=df_pivot.index)
    
    # Component 1: Volume Stress
    # Using SOFR underlying volume as total repo proxy
    if 'FNYR-SOFR_UV-A' in df_pivot.columns:
        volume = df_pivot['FNYR-SOFR_UV-A']
        # Normalize volume (z-score) - higher volume = higher stress
        volume_stress = (volume - volume.rolling(20).mean()) / volume.rolling(20).std()
        stress_df['volume_stress'] = volume_stress.fillna(0)
    
    # Component 2: Rate Stress  
    # Rate itself (higher = stress)
    if 'FNYR-SOFR-A' in df_pivot.columns:
        sofr_rate = df_pivot['FNYR-SOFR-A']
        rate_stress = (sofr_rate - sofr_rate.rolling(20).mean()) / sofr_rate.rolling(20).std()
        stress_df['rate_stress'] = rate_stress.fillna(0)
    
    # Component 3: Spread Stress (TGCR vs SOFR)
    # Tri-Party premium indicates compartment-specific stress
    if 'FNYR-TGCR-A' in df_pivot.columns and 'FNYR-SOFR-A' in df_pivot.columns:
        tgcr_sofr_spread = df_pivot['FNYR-TGCR-A'] - df_pivot['FNYR-SOFR-A']
        spread_stress = (tgcr_sofr_spread - tgcr_sofr_spread.rolling(20).mean()) / tgcr_sofr_spread.rolling(20).std()
        stress_df['spread_stress'] = spread_stress.fillna(0)
    
    # Component 4: Volume Volatility
    if 'FNYR-SOFR_UV-A' in df_pivot.columns:
        volume_vol = df_pivot['FNYR-SOFR_UV-A'].pct_change().rolling(5).std()
        vol_stress = (volume_vol - volume_vol.rolling(20).mean()) / volume_vol.rolling(20).std()
        stress_df['volatility_stress'] = vol_stress.fillna(0)
    
    # Composite Stress Index (equal weighted components)
    stress_components = ['volume_stress', 'rate_stress', 'spread_stress', 'volatility_stress']
    available_components = [c for c in stress_components if c in stress_df.columns]
    
    if available_components:
        stress_df['Repo_Stress_Index'] = stress_df[available_components].mean(axis=1)
    else:
        stress_df['Repo_Stress_Index'] = 0
    
    # Clip extreme values
    stress_df['Repo_Stress_Index'] = stress_df['Repo_Stress_Index'].clip(-3, 3)
    
    print(f"✓ Calculated stress index with {len(available_components)} components")
    
    return stress_df

def main():
    """
    Main function to fetch OFR data and generate stress analysis.
    """
    print("Starting OFR Repo Market Analysis...")
    
    # Initialize OFR client
    ofr_client = OFRClient()
    
    # Fetch data (use last 6 months for current analysis)
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Fetching OFR repo data from {start_date} to {end_date}...")
    
    # Fetch repo volumes and rates
    repo_data = ofr_client.fetch_repo_volumes(start_date, end_date)
    
    if repo_data.empty:
        print("❌ No OFR data fetched")
        return pd.DataFrame()
    
    print(f"✓ Fetched {len(repo_data)} OFR data points")
    
    # Calculate stress index
    stress_analysis = calculate_repo_stress_index(repo_data)
    
    if stress_analysis.empty:
        print("❌ Failed to calculate stress analysis")
        return pd.DataFrame()
    
    # Prepare output dataset
    # Use stress analysis as base, keep raw data columns for reference
    output_df = stress_analysis.copy()
    
    # Add key raw series for transparency
    if not repo_data.empty:
        # Pivot raw data for selected series
        raw_pivot = repo_data.pivot_table(
            index='date', 
            columns='mnemonic', 
            values='value',
            aggfunc='first'
        ).sort_index()
        
        # Select key series to include
        key_series = ['FNYR-SOFR-A', 'FNYR-TGCR-A', 'FNYR-BGCR-A', 'FNYR-SOFR_UV-A']
        available_key = [s for s in key_series if s in raw_pivot.columns]
        
        if available_key:
            output_df = pd.concat([output_df, raw_pivot[available_key]], axis=1)
    
    # Export to CSV
    # Export to Database
    print("\n💾 Saving to DuckDB...")
    try:
        db = TimeSeriesDB("database/treasury_data.duckdb")
        
        # Reset index to make date a column
        df_save = output_df.reset_index()
        if 'index' in df_save.columns:
            df_save = df_save.rename(columns={'index': 'record_date'})
        elif 'date' in df_save.columns:
            df_save = df_save.rename(columns={'date': 'record_date'})
            
        db.upsert_data(df_save, "ofr_financial_stress", key_col="record_date")
        print("✅ OFR analysis saved to 'ofr_financial_stress'")
        db.close()
    except Exception as e:
        print(f"❌ Database save failed: {e}")
    
    # Quick summary
    if not output_df.empty and 'Repo_Stress_Index' in output_df.columns:
        latest = output_df['Repo_Stress_Index'].iloc[-1]
        ma20 = output_df['Repo_Stress_Index'].rolling(20).mean().iloc[-1]
        
        print(f"\n=== OFR Repo Stress Summary ===")
        print(f"Latest Stress Index:     {latest:+.2f}")
        print(f"20-Day Average:         {ma20:+.2f}")
        print(f"Data Points:            {len(output_df)}")
        print(f"Date Range:             {output_df.index[0].strftime('%Y-%m-%d')} to {output_df.index[-1].strftime('%Y-%m-%d')}")
    
    return output_df

if __name__ == "__main__":
    analysis_df = main()
    
    if analysis_df.empty:
        print("❌ OFR analysis failed")
        sys.exit(1)
    else:
        print("✅ OFR analysis completed successfully")
