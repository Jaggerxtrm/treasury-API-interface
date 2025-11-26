"""  
Fed Liquidity Monitor - Enhanced Temporal Analysis
Comprehensive analysis of Fed liquidity with MTD/QTD/3M metrics,
spread monitoring, regime detection, and forecasting.

Refactored to use shared utilities.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add fed directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from utilities
from config import (
    FRED_SERIES_MAP as SERIES_MAP,
    SERIES_FREQUENCIES,
    DEFAULT_START_DATE as START_DATE,
    ROLLING_3M_DAYS,
    SPIKE_THRESHOLD_STD,
    SPIKE_ABSOLUTE_BPS
)
from utils.api_client import FREDClient
from utils.data_loader import load_tga_data, get_output_path

# FRED client instance (reusable)
fred_client = FREDClient()

def check_data_freshness(series_metadata, report_date=None):
    """
    Check data freshness for all series and flag stale data.
    Returns dict with freshness info and warnings.
    """
    if report_date is None:
        report_date = pd.Timestamp.today()

    freshness_report = {}
    warnings = []

    for series_id, last_date in series_metadata.items():
        if last_date is None:
            continue

        days_old = (report_date - last_date).days
        frequency = SERIES_FREQUENCIES.get(series_id, "unknown")
        series_name = SERIES_MAP.get(series_id, series_id)

        # Determine expected lag
        if frequency == "daily":
            expected_lag = 2  # T-2 is normal for daily data
            stale_threshold = 5  # >5 days is stale
        elif frequency == "weekly":
            expected_lag = 6  # Wednesday + few days lag
            stale_threshold = 14  # >2 weeks is stale
        elif frequency == "policy":
            expected_lag = None  # IORB only changes on FOMC
            stale_threshold = None
        else:
            expected_lag = 7
            stale_threshold = 14

        status = "OK"
        if stale_threshold and days_old > stale_threshold:
            status = "STALE"
            warnings.append(f"⚠️  {series_name} ({series_id}): {days_old} days old (last: {last_date.strftime('%Y-%m-%d')})")
        elif expected_lag and days_old > expected_lag + 2:
            status = "DELAYED"

        freshness_report[series_id] = {
            'series_name': series_name,
            'last_date': last_date,
            'days_old': days_old,
            'frequency': frequency,
            'status': status
        }

    return freshness_report, warnings

# TGA loading is now handled by utils.data_loader.load_tga_data()
# Keeping this as a wrapper for compatibility
def load_tga_data_wrapper(csv_path=None):
    """Wrapper for backward compatibility."""
    return load_tga_data(csv_path)

def fetch_all_data():
    """
    Fetches all required series and merges them into a single DataFrame.
    Returns: (df, series_metadata)
    """
    # Use FREDClient to fetch multiple series
    print("Starting Fed Liquidity Monitor...")
    df, api_metadata = fred_client.fetch_multiple_series(SERIES_MAP, START_DATE)
    
    # Convert metadata to expected format (series_id -> last_update_date)
    series_metadata = {}
    for series_id, meta in api_metadata.items():
        if 'last_update' in meta and meta['last_update']:
            series_metadata[series_id] = pd.to_datetime(meta['last_update'])
    
    # Load TGA data and join properly with outer join
    tga_series = load_tga_data()
    if not tga_series.empty:
        # Use outer join to preserve all dates
        df = df.join(tga_series, how='outer')
        series_metadata['TGA'] = tga_series.index[-1]
        print("Merging data...")
        print(f"TGA data successfully integrated: {len(tga_series)} records")
    else:
        print("⚠️  TGA data not available - proceeding without TGA (Net Liquidity will be partial)")
        # Add placeholder TGA column with NaN to maintain structure
        df['TGA_Balance'] = np.nan
    
    # Forward fill ONLY weekly data (Fed Balance Sheet) to preserve daily data integrity
    # Weekly series from FRED (update Wednesdays, should carry forward)
    weekly_series = ['WALCL', 'WSHOMCB', 'TREAST', 'WSHOBL', 'WSHONOT', 'WSHOBND', 'SWPT']
    
    # Get column names for weekly series from our mapping
    weekly_columns = []
    for series_id in weekly_series:
        if series_id in SERIES_MAP:
            col_name = SERIES_MAP[series_id]
            if col_name in df.columns:
                weekly_columns.append(col_name)
    
    # Apply forward fill only to weekly series
    if weekly_columns:
        print(f"Applying forward fill to {len(weekly_columns)} weekly series: {weekly_columns}")
        df[weekly_columns] = df[weekly_columns].ffill()
    else:
        print("No weekly series found for forward fill")
    
    # For TGA data, apply minimal forward fill (max 3 days) to avoid weekend gaps
    if 'TGA_Balance' in df.columns:
        print("Applying limited forward fill (3 days) to TGA data")
        df['TGA_Balance'] = df['TGA_Balance'].ffill(limit=3)
    
    print("✓ Selective forward fill applied - preserving daily data integrity")
    
    # ==========================================================================
    # INTEGRATE NY FED REFERENCE RATES (more timely than FRED)
    # ==========================================================================
    nyfed_rates_path = get_output_path("nyfed_reference_rates.csv")
    if os.path.exists(nyfed_rates_path):
        try:
            nyfed_rates = pd.read_csv(nyfed_rates_path, index_col=0, parse_dates=True)
            print(f"Loading NY Fed reference rates: {len(nyfed_rates)} records")
            
            # Map NY Fed columns to our column names
            rate_mapping = {
                'SOFR_Rate': 'SOFR_Rate',
                'EFFR_Rate': 'EFFR_Rate',
                'TGCR_Rate': 'TGCR_Rate',
                'BGCR_Rate': 'BGCR_Rate',  # Additional rate
                'OBFR_Rate': 'OBFR_Rate',  # Additional rate
            }
            
            # Update FRED rates with NY Fed data where FRED has NaN
            for nyfed_col, our_col in rate_mapping.items():
                if nyfed_col in nyfed_rates.columns:
                    if our_col in df.columns:
                        # Fill NaN in FRED data with NY Fed data
                        mask = df[our_col].isna()
                        nyfed_reindexed = nyfed_rates.reindex(df.index)[nyfed_col]
                        df.loc[mask, our_col] = nyfed_reindexed.loc[mask]
                    else:
                        # Column doesn't exist, add it from NY Fed
                        df[our_col] = nyfed_rates.reindex(df.index)[nyfed_col]
            
            # Forward fill rates for recent days (max 3 days to cover weekends)
            rate_cols = [c for c in rate_mapping.values() if c in df.columns]
            for col in rate_cols:
                df[col] = df[col].ffill(limit=3)
            
            print("✓ NY Fed reference rates integrated (fills FRED gaps + 3-day forward fill)")
            series_metadata['NYFED_RATES'] = nyfed_rates.index[-1]
        except Exception as e:
            print(f"⚠️  Could not load NY Fed rates: {e}")
    else:
        print("ℹ️  NY Fed rates file not found - run nyfed_reference_rates.py first for fresher data")
    
    # Ensure START_DATE is datetime for comparison and filter
    start_dt = pd.to_datetime(START_DATE)
    df = df[df.index >= start_dt]

    return df, series_metadata

def calculate_effective_policy_stance(df):
    """
    Distingue tra QT nominale e QE effettivo.
    
    QT Nominale: Riduzione Fed_Total_Assets
    QE Effettivo: Reinvestimento MBS -> T-Bills + REPO attivo
    """
    
    # 1. Calcola il runoff MBS
    if 'Fed_MBS_Holdings' in df.columns:
        df['MBS_Runoff_Weekly'] = -df['Fed_MBS_Holdings'].diff(5)  # Negativo = runoff
    
    # 2. Calcola l'acquisto di T-Bills
    if 'Fed_Bill_Holdings' in df.columns:
        df['Bill_Purchases_Weekly'] = df['Fed_Bill_Holdings'].diff(5)
    
    # 3. Calcola il reinvestimento (MBS runoff -> T-Bills)
    if 'MBS_Runoff_Weekly' in df.columns and 'Bill_Purchases_Weekly' in df.columns:
        # Se i T-Bills aumentano mentre MBS diminuiscono = reinvestimento
        # Usiamo numpy where per gestire le condizioni vettoriali
        # Logica: Reinvestimento = min(abs(MBS_Runoff), Bill_Purchases) se entrambi attivi nella direzione giusta
        
        # Condizione: MBS scendono (runoff > 0 perché abbiamo invertito il segno sopra) E Bills salgono
        # Nota: MBS_Runoff_Weekly è calcolato come -diff, quindi se MBS scendono, diff è neg, -diff è pos.
        # Quindi cerchiamo MBS_Runoff_Weekly > 0 e Bill_Purchases_Weekly > 0
        
        df['MBS_to_Bills_Reinvestment'] = np.where(
            (df['MBS_Runoff_Weekly'] > 0) & (df['Bill_Purchases_Weekly'] > 0),
            np.minimum(df['MBS_Runoff_Weekly'], df['Bill_Purchases_Weekly']),
            0
        )
    
    # 4. Calcola la stance effettiva
    # QT Puro = riduzione totale assets senza reinvestimento
    # QE Effettivo = reinvestimento + REPO attivo
    # Repo_Ops_Balance include SRF (passivo) ma se espandiamo a OMO includerà anche attivo.
    # Per ora assumiamo che Repo_Ops_Balance rifletta l'iniezione repo totale.
    
    if 'Fed_Total_Assets' in df.columns:
        df['QT_Pace_Nominal'] = -df['Fed_Total_Assets'].diff(5)  # Negativo = QT (assets scendono)
        # Nota: se assets scendono, diff è neg, -diff è pos (pace of QT). 
        # Manteniamo la convenzione: QT Pace positivo = contrazione.
        # O meglio: usiamo convenzione "Flow": positivo = iniezione, negativo = drenaggio.
        
        # Ricalcoliamo con convenzione Flow:
        df['Flow_Nominal_Assets'] = df['Fed_Total_Assets'].diff(5) # Pos = QE, Neg = QT
        
    if 'MBS_to_Bills_Reinvestment' in df.columns and 'Repo_Ops_Balance' in df.columns:
        # QE Effettivo = Reinvestimento (che è liquidity neutral per balance sheet ma bullish per risk) + Repo Injection
        # Nota: Reinvestimento non aggiunge net liquidity ma sposta duration risk.
        # Tuttavia, l'utente lo vede come "QE".
        df['QE_Effective'] = df['MBS_to_Bills_Reinvestment'] + df['Repo_Ops_Balance']
        
        # Net Policy Stance:
        # Se Flow_Nominal_Assets è -95B (QT) ma QE_Effective è +20B (Reinvest + Repo)
        # La stance netta è complessa. 
        # L'utente vuole vedere: "Effective Policy Stance"
        # Definiamo Net_Policy_Stance come la somma dei flussi espansivi meno quelli contrattivi?
        # O semplicemente Flow_Nominal_Assets + "Boost" da Reinvestimento?
        # Il reinvestimento è uno swap, non net new money. Ma supporta il mercato.
        # Consideriamolo come un fattore additivo alla "Liquidity Quality".
        
        # Per ora seguiamo la logica proposta:
        if 'Flow_Nominal_Assets' in df.columns:
             # Net Policy Stance = Flow Totale + Reinvestimento (che conta come "shadow QE")
             df['Net_Policy_Stance'] = df['Flow_Nominal_Assets'] + df['MBS_to_Bills_Reinvestment']
    
    return df

def calculate_metrics(df):
    """
    Calculates derived metrics: Net Liquidity, Spreads, Changes.
    """
    # 0. Calculate Effective Policy Stance (New Phase 1)
    df = calculate_effective_policy_stance(df)

    # 1. Net Liquidity Calculation
    # Net Liq = Fed Assets - RRP - TGA
    # Units: All in Millions
    # - Fed_Total_Assets: Millions (WALCL from FRED)
    # - RRP_Balance: Billions (convert to Millions)
    # - TGA_Balance: Millions (from DTS)

    # Convert Billions/Millions if needed.
    # FRED RRP is in Billions.
    # FRED WALCL (Assets) is in Millions.
    # Let's standardize to Millions.

    if 'RRP_Balance' in df.columns:
        df['RRP_Balance_M'] = df['RRP_Balance'] * 1000 # Billions -> Millions

    if 'Fed_Total_Assets' in df.columns:
        # WALCL is in Millions
        pass

    # Calculate Net Liquidity
    if all(col in df.columns for col in ['Fed_Total_Assets', 'RRP_Balance_M', 'TGA_Balance']):
        # Check if TGA data has actual values (not all NaN)
        if df['TGA_Balance'].notna().any():
            df['Net_Liquidity'] = df['Fed_Total_Assets'] - df['RRP_Balance_M'] - df['TGA_Balance']
            print("✓ Net Liquidity calculated: Fed Assets - RRP - TGA")
        else:
            # Fallback without TGA (calculate but warn)
            df['Net_Liquidity_No_TGA'] = df['Fed_Total_Assets'] - df['RRP_Balance_M']
            # Use this as Net_Liquidity but mark as degraded
            df['Net_Liquidity'] = df['Net_Liquidity_No_TGA']
            print("⚠️  Net Liquidity calculated without TGA (degraded accuracy)")
    elif 'Fed_Total_Assets' in df.columns and 'RRP_Balance_M' in df.columns:
        # Fallback without TGA column
        df['Net_Liquidity_No_TGA'] = df['Fed_Total_Assets'] - df['RRP_Balance_M']
        df['Net_Liquidity'] = df['Net_Liquidity_No_TGA']
        print("⚠️  Net Liquidity calculated without TGA (TGA column missing)")
    else:
        print("❌ Cannot calculate Net Liquidity - missing required columns")
        
    # 2. Spreads (Stress Indicators)
    if 'SOFR_Rate' in df.columns and 'IORB_Rate' in df.columns:
        df['Spread_SOFR_IORB'] = (df['SOFR_Rate'] - df['IORB_Rate']) * 100 # bps
        
    # EFFR - IORB (Policy Transmission)
    if 'EFFR_Rate' in df.columns and 'IORB_Rate' in df.columns:
        df['Spread_EFFR_IORB'] = (df['EFFR_Rate'] - df['IORB_Rate']) * 100 # bps
        
    # TGCR - SOFR (Tri-party vs GC)
    if 'TGCR_Rate' in df.columns and 'SOFR_Rate' in df.columns:
        df['Spread_TGCR_SOFR'] = (df['TGCR_Rate'] - df['SOFR_Rate']) * 100 # bps

    # UST Curve Spreads (if not already provided)
    # 2s10s (most watched)
    if 'UST_10Y' in df.columns and 'UST_2Y' in df.columns:
        df['Curve_2s10s'] = df['UST_10Y'] - df['UST_2Y']  # In percent already
    # 5s30s
    if 'UST_30Y' in df.columns and 'UST_5Y' in df.columns:
        df['Curve_5s30s'] = df['UST_30Y'] - df['UST_5Y']

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
        # Rolling 5-day Standard Deviation (min_periods=2 for weekend gaps)
        df['SOFR_Vol_5D'] = df['SOFR_Rate'].rolling(window=5, min_periods=2).std()
        
        # Stress Flag: SOFR > IORB + 5bps (0.05%)
        if 'IORB_Rate' in df.columns:
            df['Stress_Flag'] = df['SOFR_Rate'] > (df['IORB_Rate'] + 0.05)
            
    # 6. Analytical Alignment (Phase 3)
    
    # Moving Averages (Smooth Noise)
    # Use min_periods to handle weekend/holiday gaps (NaN values)
    # 20-day calendar window has ~13-14 business days, use min_periods=10 for robustness
    # 5-day calendar window has ~3-4 business days, use min_periods=2
    if 'RRP_Balance' in df.columns:
        df['MA20_RRP'] = df['RRP_Balance'].rolling(window=20, min_periods=10).mean()
        df['MA5_RRP'] = df['RRP_Balance'].rolling(window=5, min_periods=2).mean()
        
    if 'Fed_Total_Assets' in df.columns:
        df['MA20_Assets'] = df['Fed_Total_Assets'].rolling(window=20, min_periods=10).mean()
        
    if 'Spread_SOFR_IORB' in df.columns:
        df['MA20_Spread_SOFR_IORB'] = df['Spread_SOFR_IORB'].rolling(window=20, min_periods=10).mean()

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
        # Let's use 3-Year Moving Average as baseline (min_periods=10 for gaps)
        df['MA20_Assets_3Y_Avg'] = (
            df['Fed_Total_Assets'].shift(252).rolling(20, min_periods=10).mean() + 
            df['Fed_Total_Assets'].shift(504).rolling(20, min_periods=10).mean() + 
            df['Fed_Total_Assets'].shift(756).rolling(20, min_periods=10).mean()
        ) / 3
        
    # MTD Flows
    # For Balance Sheet items (Stocks), MTD Change = Current - Month Start
    # For Flows (like RRP Change), MTD = Sum of daily changes
    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
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

    # Net Liquidity Analytics
    if 'Net_Liquidity' in df.columns:
        df['Net_Liq_Change'] = df['Net_Liquidity'].diff()
        df['MA20_Net_Liq'] = df['Net_Liquidity'].rolling(window=20, min_periods=10).mean()
        df['Prev_Year_Net_Liq'] = df['Net_Liquidity'].shift(252)
        df['YoY_Net_Liq_Change'] = df['Net_Liquidity'] - df['Prev_Year_Net_Liq']

        # MTD Net Liquidity Change
        df['Month_Start_Net_Liq'] = df.groupby('YearMonth')['Net_Liquidity'].transform('first')
        df['MTD_Net_Liq_Change'] = df['Net_Liquidity'] - df['Month_Start_Net_Liq']

    return df

def get_quarter_start(date):
    """Get the start date of the quarter for a given date."""
    quarter = (date.month - 1) // 3 + 1
    month = (quarter - 1) * 3 + 1
    return pd.Timestamp(year=date.year, month=month, day=1)

def calculate_mtd_metrics(df):
    """
    Calculate Month-to-Date metrics for key series.
    Returns dict with MTD metrics for the most recent month.
    """
    if df.empty:
        return {}
    
    last_date = df.index[-1]
    month_start = last_date.replace(day=1)
    mtd_data = df[df.index >= month_start]
    
    if len(mtd_data) == 0:
        return {}
    
    metrics = {
        'mtd_days': len(mtd_data),
        'month_start': month_start.strftime('%Y-%m-%d'),
        'month_end': last_date.strftime('%Y-%m-%d')
    }
    
    # RRP MTD
    if 'RRP_Balance' in df.columns:
        metrics['rrp_mtd_change'] = mtd_data['RRP_Balance'].iloc[-1] - mtd_data['RRP_Balance'].iloc[0]
        metrics['rrp_mtd_avg'] = mtd_data['RRP_Balance'].mean()
        if 'RRP_Change' in df.columns:
            metrics['rrp_mtd_flow'] = mtd_data['RRP_Change'].sum()
    
    # Net Liquidity MTD
    if 'Net_Liquidity' in df.columns:
        metrics['net_liq_mtd_change'] = mtd_data['Net_Liquidity'].iloc[-1] - mtd_data['Net_Liquidity'].iloc[0]
        metrics['net_liq_mtd_avg'] = mtd_data['Net_Liquidity'].mean()
        if 'Net_Liq_Change' in df.columns:
            metrics['net_liq_mtd_flow'] = mtd_data['Net_Liq_Change'].sum()
    
    # Balance Sheet MTD
    if 'Fed_Total_Assets' in df.columns:
        metrics['assets_mtd_change'] = mtd_data['Fed_Total_Assets'].iloc[-1] - mtd_data['Fed_Total_Assets'].iloc[0]
        metrics['assets_mtd_avg'] = mtd_data['Fed_Total_Assets'].mean()
    
    # Spread MTD Averages
    if 'Spread_SOFR_IORB' in df.columns:
        metrics['sofr_iorb_mtd_avg'] = mtd_data['Spread_SOFR_IORB'].mean()
        metrics['sofr_iorb_mtd_max'] = mtd_data['Spread_SOFR_IORB'].max()
        metrics['sofr_iorb_mtd_min'] = mtd_data['Spread_SOFR_IORB'].min()
    
    if 'Spread_EFFR_IORB' in df.columns:
        metrics['effr_iorb_mtd_avg'] = mtd_data['Spread_EFFR_IORB'].mean()
    
    return metrics

def calculate_qtd_metrics(df):
    """
    Calculate Quarter-to-Date metrics.
    Returns dict with QTD metrics for the most recent quarter.
    """
    if df.empty:
        return {}
    
    last_date = df.index[-1]
    quarter_start = get_quarter_start(last_date)
    qtd_data = df[df.index >= quarter_start]
    
    if len(qtd_data) == 0:
        return {}
    
    metrics = {
        'qtd_days': len(qtd_data),
        'quarter_start': quarter_start.strftime('%Y-%m-%d'),
        'quarter_end': last_date.strftime('%Y-%m-%d')
    }
    
    # RRP QTD
    if 'RRP_Balance' in df.columns:
        metrics['rrp_qtd_change'] = qtd_data['RRP_Balance'].iloc[-1] - qtd_data['RRP_Balance'].iloc[0]
        metrics['rrp_qtd_pct'] = (metrics['rrp_qtd_change'] / qtd_data['RRP_Balance'].iloc[0] * 100) if qtd_data['RRP_Balance'].iloc[0] != 0 else 0
        metrics['rrp_qtd_avg'] = qtd_data['RRP_Balance'].mean()
    
    # QT Pace (Annualized)
    if 'Fed_Total_Assets' in df.columns:
        qtd_change = qtd_data['Fed_Total_Assets'].iloc[-1] - qtd_data['Fed_Total_Assets'].iloc[0]
        metrics['qt_pace_qtd'] = qtd_change
        # Annualize: (change / days) * 252
        metrics['qt_pace_annualized'] = (qtd_change / len(qtd_data)) * 252 if len(qtd_data) > 0 else 0
    
    # Spread Volatility QTD
    if 'Spread_SOFR_IORB' in df.columns:
        metrics['sofr_spread_qtd_vol'] = qtd_data['Spread_SOFR_IORB'].std()
        metrics['sofr_spread_qtd_avg'] = qtd_data['Spread_SOFR_IORB'].mean()
    
    # Repo Usage QTD
    if 'Repo_Ops_Balance' in df.columns:
        metrics['repo_qtd_avg'] = qtd_data['Repo_Ops_Balance'].mean()
    
    return metrics

def calculate_rolling_3m_metrics(df):
    """
    Calculate 3-month rolling metrics.
    Returns dict with 3M rolling metrics.
    """
    if df.empty or len(df) < 63:
        return {}
    
    # Use last 63 business days (approx 3 months)
    rolling_3m_data = df.tail(63)
    current_value_idx = -1
    
    metrics = {}
    
    # 3M Rolling Averages
    if 'Net_Liquidity' in df.columns:
        metrics['net_liq_3m_avg'] = rolling_3m_data['Net_Liquidity'].mean()
        metrics['net_liq_3m_std'] = rolling_3m_data['Net_Liquidity'].std()
        # Percentile rank of current value
        current_val = df['Net_Liquidity'].iloc[current_value_idx]
        metrics['net_liq_3m_percentile'] = (rolling_3m_data['Net_Liquidity'] < current_val).sum() / len(rolling_3m_data) * 100
    
    if 'RRP_Balance' in df.columns:
        metrics['rrp_3m_avg'] = rolling_3m_data['RRP_Balance'].mean()
        metrics['rrp_3m_std'] = rolling_3m_data['RRP_Balance'].std()
        current_val = df['RRP_Balance'].iloc[current_value_idx]
        metrics['rrp_3m_percentile'] = (rolling_3m_data['RRP_Balance'] < current_val).sum() / len(rolling_3m_data) * 100
    
    # Spread 3M Averages
    if 'Spread_SOFR_IORB' in df.columns:
        metrics['sofr_spread_3m_avg'] = rolling_3m_data['Spread_SOFR_IORB'].mean()
        metrics['sofr_spread_3m_std'] = rolling_3m_data['Spread_SOFR_IORB'].std()
    
    # Trend Detection (simple linear regression slope)
    if 'Net_Liquidity' in df.columns:
        x = np.arange(len(rolling_3m_data))
        y = rolling_3m_data['Net_Liquidity'].values
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            if slope > 1000:  # Millions per day
                metrics['net_liq_3m_trend'] = "↑ Rising"
            elif slope < -1000:
                metrics['net_liq_3m_trend'] = "↓ Declining"
            else:
                metrics['net_liq_3m_trend'] = "→ Flat"
        else:
            metrics['net_liq_3m_trend'] = "N/A"
    
    return metrics

def detect_spread_spikes(df, spread_col='Spread_SOFR_IORB', threshold_std=2.0, absolute_threshold_bps=10):
    """
    Detect spikes in spread series using multiple methods.
    Returns dict with spike detection results.
    """
    if df.empty or spread_col not in df.columns:
        return {}
    
    spread = df[spread_col].dropna()
    if len(spread) < 20:
        return {}
    
    # Calculate MA20 and StdDev (min_periods=10 for weekend/holiday gaps)
    ma20 = spread.rolling(20, min_periods=10).mean()
    std20 = spread.rolling(20, min_periods=10).std()
    
    # Method 1: Threshold (MA + N*Std)
    threshold_upper = ma20 + threshold_std * std20
    spikes_threshold = spread > threshold_upper
    
    # Method 2: Absolute (> X bps)
    spikes_absolute = spread > (absolute_threshold_bps / 100)
    
    # Method 3: Percentile (95th percentile rolling 3M, min_periods=40 for gaps)
    if len(spread) >= 63:
        rolling_95th = spread.rolling(63, min_periods=40).quantile(0.95)
        spikes_percentile = spread > rolling_95th
    else:
        spikes_percentile = pd.Series([False] * len(spread), index=spread.index)
    
    # Combined spike detection (any method triggers)
    spikes_combined = spikes_threshold | spikes_absolute | spikes_percentile
    
    # Current status
    current_spike = spikes_combined.iloc[-1] if len(spikes_combined) > 0 else False
    
    # Severity classification
    current_spread = spread.iloc[-1]
    current_ma = ma20.iloc[-1]
    current_std = std20.iloc[-1]
    
    if current_spread > current_ma + 3 * current_std:
        severity = "CRITICAL"
    elif current_spread > current_ma + 2 * current_std:
        severity = "WARNING"
    elif current_spread > current_ma + 1 * current_std:
        severity = "ELEVATED"
    else:
        severity = "NORMAL"
    
    # Get MTD and QTD spike counts
    last_date = spread.index[-1]
    month_start = last_date.replace(day=1)
    quarter_start = get_quarter_start(last_date)
    
    mtd_spikes = spikes_combined[spikes_combined.index >= month_start].sum()
    qtd_spikes = spikes_combined[spikes_combined.index >= quarter_start].sum()
    
    # Max spike in last 3M
    if len(spread) >= 63:
        max_spike_3m = spread.tail(63).max()
        max_spike_date_3m = spread.tail(63).idxmax()
    else:
        max_spike_3m = spread.max()
        max_spike_date_3m = spread.idxmax()
    
    return {
        'current_spike': current_spike,
        'severity': severity,
        'current_value': current_spread,
        'ma20': current_ma,
        'threshold_upper': threshold_upper.iloc[-1] if len(threshold_upper) > 0 else 0,
        'mtd_spike_count': int(mtd_spikes),
        'qtd_spike_count': int(qtd_spikes),
        'max_spike_3m': max_spike_3m,
        'max_spike_date_3m': max_spike_date_3m.strftime('%Y-%m-%d') if pd.notna(max_spike_date_3m) else 'N/A'
    }

def calculate_stress_index(df):
    """
    Calculate composite stress index (0-100) based on multiple factors.
    """
    if df.empty:
        return {'stress_index': 0, 'stress_level': 'N/A'}
    
    last_row = df.iloc[-1]
    stress_components = []
    weights = []
    
    # Component 1: SOFR-IORB Spread (0-20 bps = 0-100 scale)
    if 'Spread_SOFR_IORB' in df.columns:
        sofr_spread = last_row['Spread_SOFR_IORB']
        sofr_stress = min((sofr_spread / 0.20) * 100, 100)  # 20bps = 100
        stress_components.append(sofr_stress)
        weights.append(0.30)
    
    # Component 2: EFFR-IORB Spread (0-15 bps = 0-100 scale)
    if 'Spread_EFFR_IORB' in df.columns:
        effr_spread = last_row['Spread_EFFR_IORB']
        effr_stress = min((effr_spread / 0.15) * 100, 100)  # 15bps = 100
        stress_components.append(effr_stress)
        weights.append(0.20)
    
    # Component 3: Spread Volatility (5-day std)
    if 'SOFR_Vol_5D' in df.columns:
        vol = last_row['SOFR_Vol_5D']
        vol_stress = min((vol / 0.10) * 100, 100)  # 0.10% std = 100
        stress_components.append(vol_stress)
        weights.append(0.15)
    
    # Component 4: RRP Usage (as % of typical range)
    if 'RRP_Balance' in df.columns and 'MA20_RRP' in df.columns:
        rrp_current = last_row['RRP_Balance']
        rrp_ma = last_row['MA20_RRP']
        # High RRP = low stress (liquidity being parked)
        # Low RRP = potential stress (liquidity tight)
        rrp_ratio = rrp_current / rrp_ma if rrp_ma > 0 else 1
        rrp_stress = max(0, (1 - rrp_ratio) * 100)  # Inverted: lower RRP = higher stress
        stress_components.append(rrp_stress)
        weights.append(0.20)
    
    # Component 5: Repo Ops Usage
    if 'Repo_Ops_Balance' in df.columns:
        repo_usage = last_row['Repo_Ops_Balance']
        # High repo usage = stress (banks need liquidity)
        repo_stress = min((repo_usage / 100000) * 100, 100)  # 100B = 100
        stress_components.append(repo_stress)
        weights.append(0.15)
    
    # Calculate weighted average
    if len(stress_components) > 0:
        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        stress_index = sum(s * w for s, w in zip(stress_components, normalized_weights))
        stress_index = max(0, min(100, stress_index))  # Clip to 0-100
    else:
        stress_index = 0
    
    # Classify stress level
    if stress_index >= 75:
        stress_level = "HIGH STRESS"
    elif stress_index >= 50:
        stress_level = "ELEVATED"
    elif stress_index >= 25:
        stress_level = "MODERATE"
    else:
        stress_level = "LOW"
    
    return {
        'stress_index': stress_index,
        'stress_level': stress_level,
        'components': {
            'sofr_spread': stress_components[0] if len(stress_components) > 0 else 0,
            'effr_spread': stress_components[1] if len(stress_components) > 1 else 0,
            'volatility': stress_components[2] if len(stress_components) > 2 else 0,
            'rrp_usage': stress_components[3] if len(stress_components) > 3 else 0,
            'repo_usage': stress_components[4] if len(stress_components) > 4 else 0
        }
    }

def detect_regime(df):
    """
    Detect current monetary policy regime: QE, QT, or Neutral.
    Based on Fed Balance Sheet trend and RRP dynamics.
    """
    if df.empty or len(df) < 20:
        return {'regime': 'UNKNOWN', 'confidence': 0}
    
    last_row = df.iloc[-1]
    
    # Use 20-day trend for regime detection
    recent_20d = df.tail(20)
    
    regime_signals = []
    
    # Signal 1: Balance Sheet Trend
    if 'Fed_Total_Assets' in df.columns:
        assets_trend = recent_20d['Fed_Total_Assets'].iloc[-1] - recent_20d['Fed_Total_Assets'].iloc[0]
        if assets_trend < -10000:  # Declining > 10B
            regime_signals.append('QT')
        elif assets_trend > 10000:  # Rising > 10B
            regime_signals.append('QE')
        else:
            regime_signals.append('NEUTRAL')
    
    # Signal 2: RRP Trend (declining RRP = liquidity returning to system)
    if 'RRP_Balance' in df.columns:
        rrp_trend = recent_20d['RRP_Balance'].iloc[-1] - recent_20d['RRP_Balance'].iloc[0]
        if rrp_trend < -50:  # Declining RRP
            regime_signals.append('EASING')  # Liquidity increasing
        elif rrp_trend > 50:  # Rising RRP
            regime_signals.append('TIGHTENING')
    
    # Signal 3: QT Pace
    if 'QT_Pace_Assets_Weekly' in last_row and pd.notna(last_row['QT_Pace_Assets_Weekly']):
        qt_pace = last_row['QT_Pace_Assets_Weekly']
        if qt_pace < -5000:  # Strong QT
            regime_signals.append('QT')
        elif qt_pace > 5000:  # QE
            regime_signals.append('QE')
    
    # Determine regime from signals
    qt_count = regime_signals.count('QT') + regime_signals.count('TIGHTENING')
    qe_count = regime_signals.count('QE') + regime_signals.count('EASING')
    
    if qt_count > qe_count:
        regime = 'QT'
        confidence = min(100, (qt_count / len(regime_signals)) * 100)
    elif qe_count > qt_count:
        regime = 'QE'
        confidence = min(100, (qe_count / len(regime_signals)) * 100)
    else:
        regime = 'NEUTRAL'
        confidence = 50
    
    return {
        'regime': regime,
        'confidence': confidence,
        'signals': regime_signals
    }

def calculate_correlations(df):
    """
    Calculate correlations between Fed liquidity metrics and fiscal data.
    Returns dict with correlation coefficients.
    """
    if df.empty or len(df) < 30:
        return {}
    
    correlations = {}
    
    # Use last 63 days (3M) for correlation
    recent_data = df.tail(63)
    
    # Correlation 1: Net Liquidity vs TGA
    if 'Net_Liquidity' in recent_data.columns and 'TGA_Balance' in recent_data.columns:
        corr = recent_data[['Net_Liquidity', 'TGA_Balance']].corr().iloc[0, 1]
        correlations['net_liq_vs_tga'] = corr
    
    # Correlation 2: RRP vs SOFR-IORB Spread
    if 'RRP_Balance' in recent_data.columns and 'Spread_SOFR_IORB' in recent_data.columns:
        corr = recent_data[['RRP_Balance', 'Spread_SOFR_IORB']].corr().iloc[0, 1]
        correlations['rrp_vs_sofr_spread'] = corr
    
    # Correlation 3: Fed Assets vs Breakeven Inflation
    if 'Fed_Total_Assets' in recent_data.columns and 'Breakeven_10Y' in recent_data.columns:
        corr = recent_data[['Fed_Total_Assets', 'Breakeven_10Y']].corr().iloc[0, 1]
        correlations['assets_vs_inflation_exp'] = corr
    
    # Correlation 4: Net Liquidity vs SOFR Spread (stress indicator)
    if 'Net_Liquidity' in recent_data.columns and 'Spread_SOFR_IORB' in recent_data.columns:
        corr = recent_data[['Net_Liquidity', 'Spread_SOFR_IORB']].corr().iloc[0, 1]
        correlations['net_liq_vs_spread'] = corr
    
    return correlations

def forecast_simple_trend(df, column, periods=5):
    """
    Simple linear trend forecast for next N periods.
    Returns dict with forecast values and trend direction.
    """
    if df.empty or column not in df.columns or len(df) < 20:
        return {}
    
    # Use last 20 days for trend
    recent = df[column].tail(20).dropna()
    
    if len(recent) < 10:
        return {}
    
    # Simple linear regression
    x = np.arange(len(recent))
    y = recent.values
    
    # Fit line: y = mx + b
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    intercept = coeffs[1]
    
    # Forecast next periods
    future_x = np.arange(len(recent), len(recent) + periods)
    forecast = slope * future_x + intercept
    
    # Determine trend
    if slope > 0:
        trend = "↑ Rising"
    elif slope < 0:
        trend = "↓ Declining"
    else:
        trend = "→ Flat"
    
    # Calculate confidence (R²)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    return {
        'forecast': forecast.tolist(),
        'trend': trend,
        'slope': slope,
        'r_squared': r_squared,
        'current': recent.iloc[-1],
        'forecast_5d': forecast[-1]
    }

def check_alerts(df, mtd_metrics, qtd_metrics, spike_analysis, stress_metrics):
    """
    Check for alert conditions and return list of alerts.
    """
    alerts = []
    
    if df.empty:
        return alerts
    
    last_row = df.iloc[-1]
    
    # Alert 1: High Stress Index
    if stress_metrics.get('stress_index', 0) >= 75:
        alerts.append({
            'severity': 'CRITICAL',
            'type': 'STRESS',
            'message': f"Stress Index at {stress_metrics['stress_index']:.0f}/100 (HIGH STRESS)"
        })
    elif stress_metrics.get('stress_index', 0) >= 50:
        alerts.append({
            'severity': 'WARNING',
            'type': 'STRESS',
            'message': f"Stress Index at {stress_metrics['stress_index']:.0f}/100 (ELEVATED)"
        })
    
    # Alert 2: Spread Spike
    if spike_analysis.get('current_spike', False):
        severity = spike_analysis.get('severity', 'NORMAL')
        if severity in ['CRITICAL', 'WARNING']:
            alerts.append({
                'severity': severity,
                'type': 'SPREAD_SPIKE',
                'message': f"SOFR-IORB Spread spike detected: {spike_analysis.get('current_value', 0):.2f} bps ({severity})"
            })
    
    # Alert 3: Large MTD RRP Change
    if 'rrp_mtd_change' in mtd_metrics:
        rrp_change_pct = abs(mtd_metrics.get('rrp_qtd_pct', 0)) if 'rrp_qtd_pct' in mtd_metrics else 0
        if rrp_change_pct > 50:  # >50% change
            alerts.append({
                'severity': 'INFO',
                'type': 'RRP_FLOW',
                'message': f"Large RRP movement: {mtd_metrics['rrp_mtd_change']:+,.0f}B MTD"
            })
    
    # Alert 4: QT Pace Acceleration
    if 'qt_pace_annualized' in qtd_metrics:
        qt_pace = qtd_metrics['qt_pace_annualized']
        if qt_pace < -1000000:  # QT > 1T/year
            alerts.append({
                'severity': 'WARNING',
                'type': 'QT_PACE',
                'message': f"Aggressive QT pace: ${qt_pace:,.0f}M/year annualized"
            })
    
    # Alert 5: Net Liquidity Extreme
    if 'Net_Liquidity' in df.columns and 'net_liq_3m_percentile' in mtd_metrics:
        percentile = mtd_metrics.get('net_liq_3m_percentile', 50)
        if percentile < 10:
            alerts.append({
                'severity': 'WARNING',
                'type': 'LIQUIDITY',
                'message': f"Net Liquidity at {percentile:.0f}th percentile (3M) - Very Low"
            })
        elif percentile > 90:
            alerts.append({
                'severity': 'INFO',
                'type': 'LIQUIDITY',
                'message': f"Net Liquidity at {percentile:.0f}th percentile (3M) - Very High"
            })
    
    # Alert 6: Swap Lines Activation
    if 'Swap_Lines' in last_row and last_row['Swap_Lines'] > 1000:  # >1B
        alerts.append({
            'severity': 'CRITICAL',
            'type': 'SWAP_LINES',
            'message': f"Central Bank Swap Lines active: ${last_row['Swap_Lines']:,.0f}M"
        })
    
    return alerts

def generate_report(df, series_metadata=None):
    """
    Generates a comprehensive console report with temporal analysis.
    """
    if df.empty:
        print("No data available for report.")
        return

    recent = df.tail(5)
    
    # Use last row with valid CORE data (RRP and Net_Liquidity are the key indicators)
    # Rates can be forward-filled but RRP/Net_Liq must be actual data
    core_cols = ['RRP_Balance', 'Net_Liquidity']
    available_core_cols = [c for c in core_cols if c in df.columns]
    
    if available_core_cols:
        # Find the last row where at least one core column is not NaN
        valid_mask = df[available_core_cols].notna().any(axis=1)
        if valid_mask.any():
            last_valid_idx = df[valid_mask].index[-1]
            last_row = df.loc[last_valid_idx]
            last_date = last_valid_idx.strftime('%Y-%m-%d')
        else:
            last_row = df.iloc[-1]
            last_date = df.index[-1].strftime('%Y-%m-%d')
    else:
        last_row = df.iloc[-1]
        last_date = df.index[-1].strftime('%Y-%m-%d')

    # Calculate all temporal metrics
    mtd_metrics = calculate_mtd_metrics(df)
    qtd_metrics = calculate_qtd_metrics(df)
    rolling_3m_metrics = calculate_rolling_3m_metrics(df)
    spike_analysis = detect_spread_spikes(df)
    stress_metrics = calculate_stress_index(df)

    # Phase 3: Advanced analytics
    regime_info = detect_regime(df)
    correlations = calculate_correlations(df)
    net_liq_forecast = forecast_simple_trend(df, 'Net_Liquidity', periods=5)
    rrp_forecast = forecast_simple_trend(df, 'RRP_Balance', periods=5)
    alerts = check_alerts(df, mtd_metrics, qtd_metrics, spike_analysis, stress_metrics)

    # Data freshness check
    freshness_report = {}
    freshness_warnings = []
    if series_metadata:
        freshness_report, freshness_warnings = check_data_freshness(series_metadata)

    print("\n" + "="*60)
    print("FED LIQUIDITY MONITOR - ENHANCED TEMPORAL ANALYSIS")
    print("="*60)
    print(f"Analysis Date: {last_date}")

    # ===== DATA FRESHNESS WARNINGS =====
    if freshness_warnings:
        print("\n" + "─"*60)
        print("⚠️  DATA FRESHNESS WARNINGS")
        print("─"*60)
        for warning in freshness_warnings:
            print(warning)

    # ===== ALERTS SECTION (if any) =====
    if alerts:
        print("\n" + "─"*60)
        print("⚠️  ALERTS")
        print("─"*60)
        for alert in alerts:
            severity_icon = {
                'CRITICAL': '🔴',
                'WARNING': '🟡',
                'INFO': 'ℹ️'
            }.get(alert['severity'], '•')
            print(f"{severity_icon} [{alert['severity']}] {alert['message']}")
    
    # ===== REGIME DETECTION =====
    if regime_info:
        print("\n" + "─"*60)
        print("MONETARY POLICY REGIME")
        print("─"*60)
        
        regime = regime_info.get('regime', 'UNKNOWN')
        confidence = regime_info.get('confidence', 0)
        
        regime_icon = {
            'QT': '📉',
            'QE': '📈',
            'NEUTRAL': '➡️',
            'UNKNOWN': '❓'
        }.get(regime, '•')
        
        print(f"Current Regime:          {regime_icon} {regime}")
        print(f"Confidence:              {confidence:.0f}%")
        if 'signals' in regime_info:
            print(f"Signals:                 {', '.join(regime_info['signals'])}")
    
    # ===== CORRELATIONS =====
    if correlations:
        print("\n" + "─"*60)
        print("CORRELATIONS (3M)")
        print("─"*60)
        
        if 'net_liq_vs_tga' in correlations:
            corr = correlations['net_liq_vs_tga']
            print(f"Net Liq vs TGA:          {corr:+.2f}")
        
        if 'rrp_vs_sofr_spread' in correlations:
            corr = correlations['rrp_vs_sofr_spread']
            print(f"RRP vs SOFR Spread:      {corr:+.2f}")
        
        if 'assets_vs_inflation_exp' in correlations:
            corr = correlations['assets_vs_inflation_exp']
            print(f"Assets vs Inflation Exp: {corr:+.2f}")
        
        if 'net_liq_vs_spread' in correlations:
            corr = correlations['net_liq_vs_spread']
            print(f"Net Liq vs Spread:       {corr:+.2f} (stress indicator)")
    
    # ===== FORECAST =====
    if net_liq_forecast or rrp_forecast:
        print("\n" + "─"*60)
        print("5-DAY TREND FORECAST")
        print("─"*60)
        
        if net_liq_forecast:
            print(f"Net Liquidity:")
            print(f"  Current:               ${net_liq_forecast.get('current', 0):,.0f}M")
            print(f"  5-Day Forecast:        ${net_liq_forecast.get('forecast_5d', 0):,.0f}M")
            print(f"  Trend:                 {net_liq_forecast.get('trend', 'N/A')}")
            print(f"  Confidence (R²):       {net_liq_forecast.get('r_squared', 0):.2f}")
        
        if rrp_forecast:
            print(f"\nRRP Balance:")
            print(f"  Current:               ${rrp_forecast.get('current', 0):,.0f}B")
            print(f"  5-Day Forecast:        ${rrp_forecast.get('forecast_5d', 0):,.0f}B")
            print(f"  Trend:                 {rrp_forecast.get('trend', 'N/A')}")
            print(f"  Confidence (R²):       {rrp_forecast.get('r_squared', 0):.2f}")
    
    # ===== MONTH-TO-DATE SECTION =====
    if mtd_metrics:
        print("\n" + "─"*60)
        print(f"MONTH-TO-DATE ({mtd_metrics.get('month_start', 'N/A')} to {mtd_metrics.get('month_end', 'N/A')})")
        print("─"*60)
        
        if 'rrp_mtd_change' in mtd_metrics:
            rrp_pct = (mtd_metrics['rrp_mtd_change'] / (last_row['RRP_Balance'] - mtd_metrics['rrp_mtd_change']) * 100) if (last_row['RRP_Balance'] - mtd_metrics['rrp_mtd_change']) != 0 else 0
            print(f"RRP MTD Change:          ${mtd_metrics['rrp_mtd_change']:,.0f}B ({rrp_pct:+.1f}%)")
        
        if 'net_liq_mtd_change' in mtd_metrics:
            print(f"Net Liquidity MTD:       ${mtd_metrics['net_liq_mtd_change']:,.0f}M")
        
        if 'assets_mtd_change' in mtd_metrics:
            print(f"Balance Sheet MTD:       ${mtd_metrics['assets_mtd_change']:,.0f}M")
        
        if 'sofr_iorb_mtd_avg' in mtd_metrics:
            print(f"Avg SOFR-IORB Spread:    {mtd_metrics['sofr_iorb_mtd_avg']:.2f} bps")
            print(f"  Range: {mtd_metrics.get('sofr_iorb_mtd_min', 0):.2f} - {mtd_metrics.get('sofr_iorb_mtd_max', 0):.2f} bps")
    
    # ===== QUARTER-TO-DATE SECTION =====
    if qtd_metrics:
        print("\n" + "─"*60)
        print(f"QUARTER-TO-DATE ({qtd_metrics.get('quarter_start', 'N/A')} to {qtd_metrics.get('quarter_end', 'N/A')})")
        print("─"*60)
        
        if 'rrp_qtd_change' in qtd_metrics:
            print(f"RRP QTD Change:          ${qtd_metrics['rrp_qtd_change']:,.0f}B ({qtd_metrics.get('rrp_qtd_pct', 0):+.1f}%)")
        
        if 'qt_pace_annualized' in qtd_metrics:
            print(f"QT Pace (Annualized):    ${qtd_metrics['qt_pace_annualized']:,.0f}M/year")
        
        if 'sofr_spread_qtd_vol' in qtd_metrics:
            print(f"Spread Volatility:       {qtd_metrics['sofr_spread_qtd_vol']:.2f} bps (std)")
            print(f"Avg SOFR-IORB Spread:    {qtd_metrics.get('sofr_spread_qtd_avg', 0):.2f} bps")
        
        if 'repo_qtd_avg' in qtd_metrics:
            print(f"Avg Repo Usage:          ${qtd_metrics['repo_qtd_avg']:,.0f}M/day")
    
    # ===== 3-MONTH ROLLING SECTION =====
    if rolling_3m_metrics:
        print("\n" + "─"*60)
        print("3-MONTH ROLLING ANALYSIS")
        print("─"*60)
        
        if 'net_liq_3m_avg' in rolling_3m_metrics:
            print(f"3M Avg Net Liquidity:    ${rolling_3m_metrics['net_liq_3m_avg']:,.0f}M")
            print(f"3M Trend:                {rolling_3m_metrics.get('net_liq_3m_trend', 'N/A')}")
            print(f"Current Percentile:      {rolling_3m_metrics.get('net_liq_3m_percentile', 0):.0f}th")
        
        if 'rrp_3m_avg' in rolling_3m_metrics:
            print(f"3M Avg RRP:              ${rolling_3m_metrics['rrp_3m_avg']:,.0f}B")
            print(f"RRP Percentile:          {rolling_3m_metrics.get('rrp_3m_percentile', 0):.0f}th")
        
        if 'sofr_spread_3m_avg' in rolling_3m_metrics:
            print(f"3M Avg SOFR-IORB:        {rolling_3m_metrics['sofr_spread_3m_avg']:.2f} bps")
    
    # ===== SPREAD ANALYSIS & SPIKE DETECTION =====
    if spike_analysis:
        print("\n" + "─"*60)
        print("SPREAD ANALYSIS & SPIKE DETECTION")
        print("─"*60)
        
        severity_emoji = {
            "NORMAL": "✅",
            "ELEVATED": "⚠️",
            "WARNING": "🟡",
            "CRITICAL": "🔴"
        }
        
        print(f"SOFR-IORB Current:       {spike_analysis.get('current_value', 0):.2f} bps ({spike_analysis.get('severity', 'N/A')}) {severity_emoji.get(spike_analysis.get('severity', 'NORMAL'), '')}")
        print(f"MA20:                    {spike_analysis.get('ma20', 0):.2f} bps")
        print(f"Spike Threshold:         {spike_analysis.get('threshold_upper', 0):.2f} bps")
        print(f"")
        print(f"Spike Count MTD:         {spike_analysis.get('mtd_spike_count', 0)}")
        print(f"Spike Count QTD:         {spike_analysis.get('qtd_spike_count', 0)}")
        print(f"Max Spike (3M):          {spike_analysis.get('max_spike_3m', 0):.2f} bps on {spike_analysis.get('max_spike_date_3m', 'N/A')}")
    
    # ===== STRESS INDEX =====
    if stress_metrics:
        print("\n" + "─"*60)
        print("COMPOSITE STRESS INDEX")
        print("─"*60)
        
        stress_idx = stress_metrics.get('stress_index', 0)
        stress_lvl = stress_metrics.get('stress_level', 'N/A')
        
        # Visual stress bar
        bar_length = 50
        filled = int((stress_idx / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        print(f"Stress Index:            {stress_idx:.0f}/100 ({stress_lvl})")
        print(f"[{bar}]")
        print(f"")
        
        components = stress_metrics.get('components', {})
        print("Components:")
        print(f"  SOFR Spread:           {components.get('sofr_spread', 0):.0f}/100")
        print(f"  EFFR Spread:           {components.get('effr_spread', 0):.0f}/100")
        print(f"  Volatility:            {components.get('volatility', 0):.0f}/100")
        print(f"  RRP Usage:             {components.get('rrp_usage', 0):.0f}/100")
        print(f"  Repo Usage:            {components.get('repo_usage', 0):.0f}/100")
    
    # ===== CURRENT SNAPSHOT =====
    print("\n" + "─"*60)
    print("CURRENT SNAPSHOT")
    print("─"*60)
    
    print("\n--- NET LIQUIDITY (Fed Assets - RRP - TGA) ---")
    if 'Net_Liquidity' in df.columns:
        print(f"Net Liquidity:         ${last_row['Net_Liquidity']:,.0f} M")
        if 'Net_Liq_Change' in last_row:
            print(f"Daily Change:          ${last_row['Net_Liq_Change']:,.0f} M")
        if 'MA20_Net_Liq' in last_row:
            print(f"MA20:                  ${last_row['MA20_Net_Liq']:,.0f} M")

    print("\n--- LIQUIDITY DRAINS (RRP) ---")
    if 'RRP_Balance' in df.columns:
        print(f"RRP Balance:       ${last_row['RRP_Balance']:,.0f} B")
        if 'RRP_Change' in last_row:
            print(f"Daily Change:      ${last_row['RRP_Change']:,.0f} B")
        if 'MA20_RRP' in last_row:
            print(f"MA20 Balance:      ${last_row['MA20_RRP']:,.0f} B")

    print("\n--- KEY RATES & SPREADS ---")
    if 'IORB_Rate' in df.columns:
        print(f"IORB (Anchor):     {last_row['IORB_Rate']:.2f}%")
    if 'SOFR_Rate' in df.columns:
        print(f"SOFR:              {last_row['SOFR_Rate']:.2f}%")
        if 'Spread_SOFR_IORB' in last_row:
            print(f"SOFR - IORB:       {last_row['Spread_SOFR_IORB']:.1f} bps")
    if 'EFFR_Rate' in df.columns:
        print(f"EFFR:              {last_row['EFFR_Rate']:.2f}%")
        if 'Spread_EFFR_IORB' in last_row:
            print(f"EFFR - IORB:       {last_row['Spread_EFFR_IORB']:.1f} bps")
    if 'TGCR_Rate' in df.columns:
        print(f"TGCR:              {last_row['TGCR_Rate']:.2f}%")

    print("\n--- UST YIELDS & CURVE ---")
    if 'UST_2Y' in df.columns:
        print(f"2Y Treasury:       {last_row['UST_2Y']:.2f}%")
    if 'UST_5Y' in df.columns:
        print(f"5Y Treasury:       {last_row['UST_5Y']:.2f}%")
    if 'UST_10Y' in df.columns:
        print(f"10Y Treasury:      {last_row['UST_10Y']:.2f}%")
    if 'UST_30Y' in df.columns:
        print(f"30Y Treasury:      {last_row['UST_30Y']:.2f}%")
    print("")
    if 'Curve_2s10s' in df.columns:
        curve_2s10s = last_row['Curve_2s10s']
        slope_icon = "⬆️" if curve_2s10s > 0 else "⬇️"
        print(f"2s10s Curve:       {slope_icon} {curve_2s10s:.1f} bps")
    elif 'Curve_10Y2Y' in df.columns:
        # Use FRED series if calculated not available
        curve_2s10s = last_row['Curve_10Y2Y']
        slope_icon = "⬆️" if curve_2s10s > 0 else "⬇️"
        print(f"2s10s Curve:       {slope_icon} {curve_2s10s:.1f} bps")
    if 'Curve_5s30s' in df.columns:
        curve_5s30s = last_row['Curve_5s30s']
        slope_icon = "⬆️" if curve_5s30s > 0 else "⬇️"
        print(f"5s30s Curve:       {slope_icon} {curve_5s30s:.1f} bps")

    print("\n--- FED BALANCE SHEET (Weekly) ---")
    if 'Fed_Total_Assets' in df.columns:
        print(f"Total Assets:      ${last_row['Fed_Total_Assets']:,.0f} M")
        if 'QT_Pace_Assets_Weekly' in last_row:
             print(f"Weekly Change (QT): ${last_row['QT_Pace_Assets_Weekly']:,.0f} M")
        if 'YoY_Assets_Change' in last_row:
             print(f"YoY Change:        ${last_row['YoY_Assets_Change']:,.0f} M")
              
    if 'Fed_Treasury_Holdings' in df.columns:
        print(f"Treasury Holdings: ${last_row['Fed_Treasury_Holdings']:,.0f} M")
    if 'Fed_Bill_Holdings' in df.columns:
        print(f"  > Bills (QE):    ${last_row['Fed_Bill_Holdings']:,.0f} M")
    if 'Fed_Coupon_Holdings' in df.columns:
        print(f"  > Coupons:       ${last_row['Fed_Coupon_Holdings']:,.0f} M")
        
    print("\n--- INFLATION & STRESS INDICATORS ---")
    if 'Breakeven_10Y' in df.columns:
        print(f"10Y Breakeven:     {last_row['Breakeven_10Y']:.2f}%")
    if 'Breakeven_5Y' in df.columns:
        print(f"5Y Breakeven:      {last_row['Breakeven_5Y']:.2f}%")
    if 'Swap_Lines' in df.columns:
        print(f"Swap Lines Usage:  ${last_row['Swap_Lines']:,.0f} M")

    print("\n--- RECENT TREND (Last 20 Trading Days) ---")
    cols = ['Net_Liquidity', 'RRP_Balance', 'SOFR_Rate', 'Spread_SOFR_IORB', 'QT_Pace_Assets_Weekly']
    cols = [c for c in cols if c in df.columns]
    if cols:
        # Get last 30 calendar days, filter out weekends/NaN, show 20
        trend_data = df.tail(30)[cols].dropna(how='all').sort_index(ascending=False).head(20)
        print(trend_data.to_string(float_format="{:,.2f}".format))
    
    # Export full data
    csv_path = get_output_path("fed_liquidity_full.csv")
    df.to_csv(csv_path)
    print(f"\n{'='*60}")
    print(f"Full data exported to {csv_path}")
    
    # Export summary metrics
    summary_data = {
        'Metric': [],
        'Current': [],
        'MTD': [],
        'QTD': [],
        '3M_Avg': [],
        'YoY': []
    }
    
    if 'RRP_Balance' in df.columns:
        summary_data['Metric'].append('RRP Balance (B)')
        summary_data['Current'].append(f"{last_row['RRP_Balance']:,.0f}")
        summary_data['MTD'].append(f"{mtd_metrics.get('rrp_mtd_change', 0):+,.0f}")
        summary_data['QTD'].append(f"{qtd_metrics.get('rrp_qtd_change', 0):+,.0f}")
        summary_data['3M_Avg'].append(f"{rolling_3m_metrics.get('rrp_3m_avg', 0):,.0f}")
        summary_data['YoY'].append(f"{last_row.get('YoY_RRP_Change', 0):+,.0f}" if 'YoY_RRP_Change' in last_row else 'N/A')
    
    if 'Net_Liquidity' in df.columns:
        summary_data['Metric'].append('Net Liquidity (M)')
        summary_data['Current'].append(f"{last_row['Net_Liquidity']:,.0f}")
        summary_data['MTD'].append(f"{mtd_metrics.get('net_liq_mtd_change', 0):+,.0f}")
        summary_data['QTD'].append('N/A')
        summary_data['3M_Avg'].append(f"{rolling_3m_metrics.get('net_liq_3m_avg', 0):,.0f}")
        summary_data['YoY'].append(f"{last_row.get('YoY_Net_Liq_Change', 0):+,.0f}" if 'YoY_Net_Liq_Change' in last_row else 'N/A')
    
    if 'Spread_SOFR_IORB' in df.columns:
        summary_data['Metric'].append('SOFR-IORB Spread (bps)')
        summary_data['Current'].append(f"{last_row['Spread_SOFR_IORB']:.2f}")
        summary_data['MTD'].append(f"{mtd_metrics.get('sofr_iorb_mtd_avg', 0):.2f}")
        summary_data['QTD'].append(f"{qtd_metrics.get('sofr_spread_qtd_avg', 0):.2f}")
        summary_data['3M_Avg'].append(f"{rolling_3m_metrics.get('sofr_spread_3m_avg', 0):.2f}")
        summary_data['YoY'].append('N/A')
    
    summary_data['Metric'].append('Stress Index')
    summary_data['Current'].append(f"{stress_metrics.get('stress_index', 0):.0f}/100")
    summary_data['MTD'].append('N/A')
    summary_data['QTD'].append('N/A')
    summary_data['3M_Avg'].append('N/A')
    summary_data['YoY'].append('N/A')
    
    summary_df = pd.DataFrame(summary_data)
    summary_csv = get_output_path("fed_liquidity_summary.csv")
    summary_df.to_csv(summary_csv, index=False)
    print(f"Summary metrics exported to {summary_csv}")
    print("="*60)


def main():
    print("Starting Fed Liquidity Monitor...")

    # Fetch
    df, series_metadata = fetch_all_data()

    if df.empty:
        print("No data fetched.")
        return

    # Process
    df_calc = calculate_metrics(df)

    # Report
    generate_report(df_calc, series_metadata)

if __name__ == "__main__":
    main()
