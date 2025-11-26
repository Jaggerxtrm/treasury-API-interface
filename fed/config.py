"""
Fed Module Configuration
Centralized configuration for all Fed liquidity scripts.
"""

import os
from datetime import datetime

# ============================================================================
# API Configuration
# ============================================================================

# FRED API
FRED_API_KEY = os.getenv("FRED_API_KEY", "319c755ba8b781762ed9736f0b95604d")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# NY Fed Markets API
NYFED_BASE_URL = "https://markets.newyorkfed.org/api"

# ============================================================================
# Date Configuration
# ============================================================================

DEFAULT_START_DATE = "2022-01-01"

# ============================================================================
# FRED Series Mappings
# ============================================================================

FRED_SERIES_MAP = {
    # Liquidity Components
    "RRPONTSYD": "RRP_Balance",      # Overnight Reverse Repo
    "RPONTSYD": "Repo_Ops_Balance",  # Overnight Repo Operations
    "WALCL": "Fed_Total_Assets",     # Total Assets
    "WSHOMCB": "Fed_MBS_Holdings",   # MBS Holdings
    "TREAST": "Fed_Treasury_Holdings", # Treasury Holdings
    "WSHOBL": "Fed_Bill_Holdings",   # T-Bills Held Outright
    "WSHONOT": "Fed_Notes_Holdings", # Treasury Notes (2-10Y)
    "WSHOBND": "Fed_Bonds_Holdings", # Treasury Bonds (20-30Y)

    
    # Rates & Spreads
    "IORB": "IORB_Rate",             # Interest on Reserve Balances
    "EFFR": "EFFR_Rate",             # Effective Federal Funds Rate
    "SOFR": "SOFR_Rate",             # Secured Overnight Financing Rate
    "TGCRRATE": "TGCR_Rate",         # Tri-Party General Collateral Rate
    
    # Treasury Yields
    "DGS2": "UST_2Y",                # 2-Year Treasury
    "DGS5": "UST_5Y",                # 5-Year Treasury
    "DGS10": "UST_10Y",              # 10-Year Treasury
    "DGS30": "UST_30Y",              # 30-Year Treasury
    "T10Y2Y": "Curve_10Y2Y",         # 10Y-2Y Spread
    
    # Inflation Expectations
    "T10YIE": "Breakeven_10Y",       # 10-Year Breakeven Inflation
    "T5YIE": "Breakeven_5Y",         # 5-Year Breakeven Inflation
    
    # Liquidity Support
    "SWPT": "Swap_Lines",            # Central Bank Liquidity Swaps
    "SRFTSYD": "SRF_Rate",           # Standing Repo Facility Rate
}

# Series update frequencies
SERIES_FREQUENCIES = {
    # Daily series
    "RRPONTSYD": "daily",
    "SOFR": "daily",
    "EFFR": "daily",
    "TGCRRATE": "daily",
    "DGS2": "daily",
    "DGS5": "daily",
    "DGS10": "daily",
    "DGS30": "daily",
    "T10Y2Y": "daily",
    "T10YIE": "daily",
    "T5YIE": "daily",
    "RPONTSYD": "daily",
    "SRFTSYD": "daily",
    
    # Policy-dependent
    "IORB": "policy",  # Changes only on FOMC dates
    
    # Weekly series (updated Wednesdays)
    "WALCL": "weekly",
    "WSHOMCB": "weekly",
    "TREAST": "weekly",
    "WSHOBL": "weekly",
    "WSHONOT": "weekly",
    "WSHOBND": "weekly",
    "SWPT": "weekly",
}

# ============================================================================
# NY Fed API Endpoints
# ============================================================================

NYFED_ENDPOINTS = {
    "repo": "/rp/results/search.json",
    "soma": "/soma/summary.json",
    "pd_stats": "/pd/list.json",
    "agency_mbs": "/ambs/all/results/search.json",
}

# NY Fed Reference Rate Types
NYFED_RATE_TYPES = {
    "sofr": "SOFR_Rate",
    "bgcr": "BGCR_Rate",
    "tgcr": "TGCR_Rate",
    "effr": "EFFR_Rate",
    "obfr": "OBFR_Rate"
}

# ============================================================================
# File Paths
# ============================================================================

# Output directories
OUTPUT_DIR_FED = "outputs/fed"
OUTPUT_DIR_FISCAL = "outputs/fiscal"
OUTPUT_DIR_AUCTION = "outputs/auction"
OUTPUT_DIR_COMPOSITE = "outputs/composite"

# Data directories
DATA_DIR_SAMPLES = "data/samples"
DATA_DIR_CACHE = "data/cache"

# ============================================================================
# Analysis Parameters
# ============================================================================

# Temporal analysis windows
MTD_WINDOW = "M"  # Month
QTD_WINDOW = "Q"  # Quarter
ROLLING_3M_DAYS = 63  # ~3 months of business days
ROLLING_20D_DAYS = 20  # 20-day moving average

# Spike detection thresholds
SPIKE_THRESHOLD_STD = 2.0  # Standard deviations
SPIKE_ABSOLUTE_BPS = 10    # Basis points

# Stress index weights
STRESS_WEIGHTS = {
    "sofr_spread": 0.30,
    "effr_spread": 0.20,
    "volatility": 0.15,
    "rrp_usage": 0.20,
    "repo_usage": 0.15
}

# ============================================================================
# Liquidity Composite Index Weights
# ============================================================================

COMPONENT_WEIGHTS = {
    "fiscal": 0.40,
    "monetary": 0.35,
    "plumbing": 0.25
}

FISCAL_WEIGHTS = {
    "tga_change": 0.40,
    "deficit": 0.35,
    "tax_receipts": 0.25
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
