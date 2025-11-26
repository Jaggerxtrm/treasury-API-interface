import pandas as pd
import numpy as np
from datetime import datetime
import sys

"""
Liquidity Composite Index (LCI)
===============================
Combines fiscal, monetary, and market plumbing data into a unified liquidity indicator.

Components:
1. Fiscal Liquidity (from fiscal_analysis.py):
   - Fiscal Impulse
   - TGA Balance
   - Tax Receipts (Withheld)

2. Monetary/Financial Liquidity (from fed_liquidity.py):
   - Fed Balance Sheet (Assets)
   - RRP Balance
   - Net Liquidity (Assets - RRP - TGA)
   - SOFR spreads

3. Market Plumbing (from nyfed_operations.py):
   - Repo operations usage
   - Settlement fails
   - Funding stress indicators
"""

# File paths for data sources (try multiple locations)
import os

def find_file(filename, search_paths):
    """Helper to find file in multiple paths"""
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None

FISCAL_SEARCH_PATHS = [
    "outputs/fiscal/fiscal_analysis_full.csv",
    "../outputs/fiscal/fiscal_analysis_full.csv",
    "fiscal/outputs/fiscal/fiscal_analysis_full.csv",
]

FED_SEARCH_PATHS = [
    "outputs/fed/fed_liquidity_full.csv",
    "../outputs/fed/fed_liquidity_full.csv",
    "fed/outputs/fed/fed_liquidity_full.csv",
]

REPO_SEARCH_PATHS = [
    "outputs/fed/nyfed_repo_ops.csv",
    "../outputs/fed/nyfed_repo_ops.csv",
    "fed/outputs/fed/nyfed_repo_ops.csv",
]

OFR_SEARCH_PATHS = [
    "outputs/fed/ofr_repo_analysis.csv",
    "../outputs/fed/ofr_repo_analysis.csv",
    "fed/outputs/fed/ofr_repo_analysis.csv",
]

FAILS_SEARCH_PATHS = [
    "outputs/fed/nyfed_settlement_fails.csv",
    "../outputs/fed/nyfed_settlement_fails.csv",
    "fed/outputs/fed/nyfed_settlement_fails.csv",
]

# ... (Weights are imported from config.py, assuming config.py is imported or defined here. 
# Wait, config.py is NOT imported in the original file! It defines WEIGHTS locally!
# I need to update the local WEIGHTS definitions to match config.py or import them.
# The original file has local dictionaries. I should update them to match the new structure.)

# Component Weights (configurable)
# Total should equal 1.0
WEIGHTS = {
    "fiscal_liquidity": 0.40,      # Fiscal impulse & TGA dynamics
    "monetary_liquidity": 0.35,    # Fed balance sheet & RRP
    "market_plumbing": 0.25        # Repo stress & fails
}

# Sub-component weights
FISCAL_WEIGHTS = {
    "impulse": 0.50,      # Fiscal spending impact
    "tga": 0.30,          # TGA drawdown = liquidity injection
    "taxes": 0.20         # Tax extraction
}

MONETARY_WEIGHTS = {
    "net_liquidity": 0.30,          # Increased importance
    "policy_stance": 0.25,          # NEW: Effective Policy Stance (QE vs QT)
    "rrp_change": 0.20,             # Reduced
    "repo_operations": 0.15,        # NEW: Active Repo Operations
    "sofr_stress": 0.10,            # Reduced
}

PLUMBING_WEIGHTS = {
    "repo_stress": 0.40,            # NY Fed Repo Submission Ratio
    "fails_stress": 0.30,           # Settlement Fails
    "ofr_stress": 0.30              # NEW: OFR Repo Market Stress
}

def load_data():
    """
    Loads data from all modules.
    """
    print("Loading data from CSV files...")

    data = {}

    # Resolve paths
    fiscal_path = find_file("fiscal_analysis_full.csv", FISCAL_SEARCH_PATHS)
    fed_path = find_file("fed_liquidity_full.csv", FED_SEARCH_PATHS)
    repo_path = find_file("nyfed_repo_ops.csv", REPO_SEARCH_PATHS)
    fails_path = find_file("nyfed_settlement_fails.csv", FAILS_SEARCH_PATHS)
    ofr_path = find_file("ofr_repo_analysis.csv", OFR_SEARCH_PATHS)

    try:
        if fiscal_path:
            df_fiscal = pd.read_csv(fiscal_path, index_col=0, parse_dates=True)
            data['fiscal'] = df_fiscal
            print(f"Fiscal data loaded: {len(df_fiscal)} records")
        else:
            print("Fiscal data file not found")
            data['fiscal'] = pd.DataFrame()
    except Exception as e:
        print(f"Could not load fiscal data: {e}")
        data['fiscal'] = pd.DataFrame()

    try:
        if fed_path:
            df_fed = pd.read_csv(fed_path, index_col=0, parse_dates=True)
            data['fed'] = df_fed
            print(f"Fed liquidity data loaded: {len(df_fed)} records")
        else:
            print("Fed liquidity data file not found")
            data['fed'] = pd.DataFrame()
    except Exception as e:
        print(f"Could not load Fed data: {e}")
        data['fed'] = pd.DataFrame()

    try:
        if repo_path:
            df_repo = pd.read_csv(repo_path, index_col=0, parse_dates=True)
            data['repo'] = df_repo
            print(f"Repo operations data loaded: {len(df_repo)} records")
        else:
            print("Repo operations data file not found")
            data['repo'] = pd.DataFrame()
    except Exception as e:
        print(f"Could not load repo data: {e}")
        data['repo'] = pd.DataFrame()

    try:
        if fails_path:
            df_fails = pd.read_csv(fails_path, index_col=0, parse_dates=True)
            data['fails'] = df_fails
            print(f"Settlement fails data loaded: {len(df_fails)} records")
        else:
            print("Settlement fails data file not found")
            data['fails'] = pd.DataFrame()
    except Exception as e:
        print(f"Could not load fails data: {e}")
        data['fails'] = pd.DataFrame()
        
    try:
        if ofr_path:
            df_ofr = pd.read_csv(ofr_path, index_col=0, parse_dates=True)
            data['ofr'] = df_ofr
            print(f"OFR repo analysis data loaded: {len(df_ofr)} records")
        else:
            print("OFR repo analysis data file not found")
            data['ofr'] = pd.DataFrame()
    except Exception as e:
        print(f"Could not load OFR data: {e}")
        data['ofr'] = pd.DataFrame()

    return data

def normalize_series(series, method='zscore'):
    """
    Normalizes a series using z-score or min-max scaling.
    """
    if series.empty or series.isna().all():
        return series

    if method == 'zscore':
        # Z-score normalization (mean=0, std=1)
        mean = series.mean()
        std = series.std()
        if std == 0:
            return series - mean
        return (series - mean) / std

    elif method == 'minmax':
        # Min-Max scaling to [0, 1]
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series * 0
        return (series - min_val) / (max_val - min_val)

    return series

def calculate_fiscal_component(df_fiscal):
    """
    Calculates Fiscal Liquidity sub-index.
    Higher = More fiscal liquidity injection.
    """
    if df_fiscal.empty:
        return pd.Series(dtype=float)

    # Remove duplicate dates by aggregating
    if df_fiscal.index.duplicated().any():
        df_fiscal = df_fiscal.groupby(df_fiscal.index).mean()

    fiscal_index = pd.Series(0.0, index=df_fiscal.index)

    # 1. Fiscal Impulse (MA20, normalized)
    if 'MA20_Impulse' in df_fiscal.columns:
        impulse_norm = normalize_series(df_fiscal['MA20_Impulse'], method='zscore')
        fiscal_index += impulse_norm * FISCAL_WEIGHTS['impulse']

    # 2. TGA Drawdown (negative change = injection, so invert sign)
    if 'TGA_Balance' in df_fiscal.columns:
        tga_change = df_fiscal['TGA_Balance'].diff()
        tga_drawdown = -tga_change  # Negative change = positive liquidity
        tga_norm = normalize_series(tga_drawdown, method='zscore')
        fiscal_index += tga_norm * FISCAL_WEIGHTS['tga']

    # 3. Tax Receipts (negative impact on liquidity, invert)
    # Try Withheld_Tax first, fall back to Total_Taxes
    tax_col = None
    if 'Withheld_Tax' in df_fiscal.columns:
        tax_col = 'Withheld_Tax'
    elif 'Total_Taxes' in df_fiscal.columns:
        tax_col = 'Total_Taxes'

    if tax_col:
        tax_extraction = -df_fiscal[tax_col]  # Tax = drain
        tax_norm = normalize_series(tax_extraction, method='zscore')
        fiscal_index += tax_norm * FISCAL_WEIGHTS['taxes']

    return fiscal_index

def calculate_monetary_component(df_fed):
    """
    Calculates Monetary Liquidity sub-index.
    Higher = More Fed liquidity in the system.
    """
    if df_fed.empty:
        return pd.Series(dtype=float)

    # Remove duplicate dates by aggregating
    if df_fed.index.duplicated().any():
        df_fed = df_fed.groupby(df_fed.index).mean()

    monetary_index = pd.Series(0.0, index=df_fed.index)

    # 1. Net Liquidity (primary driver)
    if 'Net_Liquidity' in df_fed.columns:
        net_liq_norm = normalize_series(df_fed['Net_Liquidity'], method='zscore')
        monetary_index += net_liq_norm * MONETARY_WEIGHTS['net_liquidity']

    # 2. Policy Stance (Effective QE/QT)
    if 'Net_Policy_Stance' in df_fed.columns:
        # Positive = QE (Injection)
        policy_norm = normalize_series(df_fed['Net_Policy_Stance'], method='zscore')
        monetary_index += policy_norm * MONETARY_WEIGHTS['policy_stance']
    elif 'QT_Pace_Assets_Weekly' in df_fed.columns:
        # Fallback: QT Pace is negative for liquidity (if positive number represents contraction)
        # Usually QT Pace is negative number in my script?
        # Let's check fed_liquidity.py: df['QT_Pace_Assets_Weekly'] = df['Fed_Total_Assets'].diff(5)
        # So if assets drop, diff is negative.
        # So negative value = contraction.
        # So we can just normalize it directly.
        qt_norm = normalize_series(df_fed['QT_Pace_Assets_Weekly'], method='zscore')
        monetary_index += qt_norm * MONETARY_WEIGHTS['policy_stance']

    # 3. RRP Change (decline = liquidity release)
    if 'RRP_Change' in df_fed.columns:
        rrp_release = -df_fed['RRP_Change']  # Decline in RRP = positive
        rrp_norm = normalize_series(rrp_release, method='zscore')
        monetary_index += rrp_norm * MONETARY_WEIGHTS['rrp_change']
        
    # 4. Repo Operations (Active Injection)
    if 'Repo_Ops_Balance' in df_fed.columns:
        repo_ops_norm = normalize_series(df_fed['Repo_Ops_Balance'], method='zscore')
        monetary_index += repo_ops_norm * MONETARY_WEIGHTS['repo_operations']

    # 5. SOFR Stress (wider spread = tighter, negative for liquidity)
    if 'Spread_SOFR_IORB' in df_fed.columns:
        sofr_stress = -df_fed['Spread_SOFR_IORB']  # Higher spread = stress
        sofr_norm = normalize_series(sofr_stress, method='zscore')
        monetary_index += sofr_norm * MONETARY_WEIGHTS['sofr_stress']

    return monetary_index

def calculate_plumbing_component(df_repo, df_fails, df_ofr):
    """
    Calculates Market Plumbing sub-index.
    Higher = Less stress in market plumbing.
    """
    # Remove duplicate dates by aggregating (numeric columns only)
    if not df_repo.empty and df_repo.index.duplicated().any():
        df_repo = df_repo.groupby(df_repo.index).mean(numeric_only=True)

    if not df_fails.empty and df_fails.index.duplicated().any():
        df_fails = df_fails.groupby(df_fails.index).mean(numeric_only=True)
        
    if not df_ofr.empty and df_ofr.index.duplicated().any():
        df_ofr = df_ofr.groupby(df_ofr.index).mean(numeric_only=True)

    plumbing_index = pd.Series(dtype=float)

    # Need a common index
    # Merge all available
    dfs_to_merge = []
    if not df_repo.empty: dfs_to_merge.append(df_repo)
    if not df_fails.empty: dfs_to_merge.append(df_fails)
    if not df_ofr.empty: dfs_to_merge.append(df_ofr)
    
    if not dfs_to_merge:
        return plumbing_index
        
    combined = pd.concat(dfs_to_merge, axis=1, join='outer').sort_index()
    plumbing_index = pd.Series(0.0, index=combined.index)

    # 1. Repo Stress (high submission ratio = stress, invert)
    if not df_repo.empty and 'submission_ratio' in df_repo.columns:
        # High submission ratio = stress = negative
        repo_stress = -df_repo['submission_ratio'].reindex(plumbing_index.index)
        repo_norm = normalize_series(repo_stress, method='zscore')
        plumbing_index += repo_norm * PLUMBING_WEIGHTS['repo_stress']

    # 2. Settlement Fails (high fails = stress, invert)
    if not df_fails.empty and 'totalFails' in df_fails.columns:
        fails_stress = -df_fails['totalFails'].reindex(plumbing_index.index)
        fails_norm = normalize_series(fails_stress, method='zscore')
        plumbing_index += fails_norm * PLUMBING_WEIGHTS['fails_stress']
        
    # 3. OFR Repo Stress (high index = stress, invert)
    if not df_ofr.empty and 'Repo_Stress_Index' in df_ofr.columns:
        ofr_stress = -df_ofr['Repo_Stress_Index'].reindex(plumbing_index.index)
        ofr_norm = normalize_series(ofr_stress, method='zscore')
        plumbing_index += ofr_norm * PLUMBING_WEIGHTS['ofr_stress']

    return plumbing_index

def calculate_composite_index(data):
    """
    Combines all components into a single Liquidity Composite Index.
    """
    print("\nCalculating Liquidity Composite Index...")

    # Calculate sub-indices
    fiscal_index = calculate_fiscal_component(data['fiscal'])
    monetary_index = calculate_monetary_component(data['fed'])
    plumbing_index = calculate_plumbing_component(data['repo'], data['fails'], data['ofr'])

    # Merge all on common dates
    indices = pd.concat([
        fiscal_index.rename('Fiscal_Index'),
        monetary_index.rename('Monetary_Index'),
        plumbing_index.rename('Plumbing_Index')
    ], axis=1, join='outer').sort_index()

    # Fill NaN with 0 for missing components
    indices = indices.fillna(0)

    # Calculate composite
    indices['LCI'] = (
        indices['Fiscal_Index'] * WEIGHTS['fiscal_liquidity'] +
        indices['Monetary_Index'] * WEIGHTS['monetary_liquidity'] +
        indices['Plumbing_Index'] * WEIGHTS['market_plumbing']
    )

    # Smooth with MA (min_periods for weekend gaps)
    indices['LCI_MA20'] = indices['LCI'].rolling(window=20, min_periods=14).mean()
    indices['LCI_MA5'] = indices['LCI'].rolling(window=5, min_periods=3).mean()

    # Regime indicators
    indices['LCI_Regime'] = pd.cut(
        indices['LCI'],
        bins=[-np.inf, -1, -0.5, 0.5, 1, np.inf],
        labels=['Very Tight', 'Tight', 'Neutral', 'Easy', 'Very Easy']
    )

    return indices

def generate_report(indices):
    """
    Generates a report on the Liquidity Composite Index.
    """
    if indices.empty:
        print("No data available for report")
        return

    recent = indices.tail(10)
    last_row = indices.iloc[-1]
    last_date = indices.index[-1].strftime('%Y-%m-%d')

    print("\n" + "="*60)
    print("LIQUIDITY COMPOSITE INDEX (LCI) REPORT")
    print("="*60)
    print(f"Last Date: {last_date}")

    print("\n--- COMPOSITE INDEX ---")
    print(f"LCI (Raw):             {last_row['LCI']:.2f}")
    print(f"LCI MA20:              {last_row['LCI_MA20']:.2f}")
    print(f"LCI MA5:               {last_row['LCI_MA5']:.2f}")
    print(f"Regime:                {last_row['LCI_Regime']}")

    print("\n--- SUB-COMPONENTS ---")
    print(f"Fiscal Liquidity:      {last_row['Fiscal_Index']:.2f} (Weight: {WEIGHTS['fiscal_liquidity']:.0%})")
    print(f"Monetary Liquidity:    {last_row['Monetary_Index']:.2f} (Weight: {WEIGHTS['monetary_liquidity']:.0%})")
    print(f"Market Plumbing:       {last_row['Plumbing_Index']:.2f} (Weight: {WEIGHTS['market_plumbing']:.0%})")

    print("\n--- INTERPRETATION ---")
    lci_val = last_row['LCI']
    if lci_val > 1:
        print("Status: VERY EASY - Abundant liquidity conditions")
    elif lci_val > 0.5:
        print("Status: EASY - Supportive liquidity environment")
    elif lci_val > -0.5:
        print("Status: NEUTRAL - Balanced liquidity")
    elif lci_val > -1:
        print("Status: TIGHT - Constrained liquidity conditions")
    else:
        print("Status: VERY TIGHT - Stressed liquidity environment")

    print("\n--- RECENT TREND (Last 5 Days) ---")
    cols = ['LCI', 'LCI_MA20', 'Fiscal_Index', 'Monetary_Index', 'Plumbing_Index']
    print(recent[cols].sort_index(ascending=False).head(5).to_string(float_format="{:.2f}".format))

    # Export
    csv_path = "liquidity_composite_index.csv"
    indices.to_csv(csv_path)
    print(f"\nFull LCI data exported to {csv_path}")

def main():
    print("="*60)
    print("LIQUIDITY COMPOSITE INDEX (LCI) CALCULATOR")
    print("="*60)

    print("\nComponent Weights:")
    print(f"  Fiscal:    {WEIGHTS['fiscal_liquidity']:.0%}")
    print(f"  Monetary:  {WEIGHTS['monetary_liquidity']:.0%}")
    print(f"  Plumbing:  {WEIGHTS['market_plumbing']:.0%}")

    # Load all data
    data = load_data()

    # Calculate composite index
    indices = calculate_composite_index(data)

    # Generate report
    generate_report(indices)

    print("\nLiquidity Composite Index calculation complete.")

if __name__ == "__main__":
    main()
