"""
Treasury Liquidity Desk Report Generator
=========================================

Orchestrates fiscal, monetary, and plumbing data to generate
comprehensive desk-grade liquidity analysis with 8-section structure.

Author: AI-Assisted Development
Date: 2025-11-26
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, Tuple, Optional

# Add module paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fiscal'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fed'))

# Import from existing modules
from fiscal.fiscal_analysis import (
    fetch_dts_data,
    fetch_current_gdp,
    process_fiscal_analysis
)
from fed.fed_liquidity import (
    fetch_all_data as fetch_fed_data,
    calculate_metrics as calculate_fed_metrics,
    calculate_mtd_metrics,
    calculate_qtd_metrics,
    calculate_rolling_3m_metrics,
    detect_spread_spikes,
    calculate_stress_index,
    detect_regime,
    calculate_correlations,
    forecast_simple_trend
)

# Constants
REPORT_VERSION = "1.0.0"
FISCAL_IMPULSE_TARGET_PCT = 0.64  # Target weekly impulse as % of GDP


def load_all_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    """
    Execute all data collection pipelines and return processed DataFrames.

    Returns:
        Tuple of (fiscal_df, fed_df, ofr_df, metadata_dict)
    """
    print("\n" + "="*60)
    print("TREASURY LIQUIDITY DESK REPORT - DATA LOADING")
    print("="*60)

    metadata = {
        'report_date': datetime.now().strftime('%Y-%m-%d'),
        'report_time': datetime.now().strftime('%H:%M:%S'),
        'version': REPORT_VERSION
    }

    # 1. Fiscal Analysis
    print("\n[1/3] Loading Fiscal Data...")
    try:
        df_trans, df_tga = fetch_dts_data()
        gdp_info = fetch_current_gdp()
        current_gdp = gdp_info[0]

        fiscal_df, weekly_fiscal_df = process_fiscal_analysis(df_trans, df_tga, current_gdp)

        metadata['fiscal'] = {
            'gdp_value': current_gdp,
            'gdp_quarter': gdp_info[2],
            'gdp_is_estimated': gdp_info[4],
            'records': len(fiscal_df),
            'weekly_records': len(weekly_fiscal_df),
            'last_date': fiscal_df.index[-1].strftime('%Y-%m-%d')
        }
        print(f"✓ Fiscal: {len(fiscal_df)} records through {metadata['fiscal']['last_date']}")
    except Exception as e:
        print(f"❌ Fiscal data loading failed: {e}")
        fiscal_df = pd.DataFrame()
        metadata['fiscal'] = {'error': str(e)}

    # 2. Fed Liquidity
    print("\n[2/3] Loading Fed Liquidity Data...")
    try:
        fed_df_raw, series_metadata = fetch_fed_data()
        fed_df = calculate_fed_metrics(fed_df_raw)

        metadata['fed'] = {
            'records': len(fed_df),
            'last_date': fed_df.index[-1].strftime('%Y-%m-%d'),
            'series_count': len(series_metadata)
        }
        print(f"✓ Fed: {len(fed_df)} records through {metadata['fed']['last_date']}")
    except Exception as e:
        print(f"❌ Fed data loading failed: {e}")
        fed_df = pd.DataFrame()
        metadata['fed'] = {'error': str(e)}

    # 3. OFR Repo Stress (if available)
    print("\n[3/3] Loading OFR Repo Stress Data...")
    try:
        # Import OFR module if exists
        from fed import ofr_analysis
        ofr_df = ofr_analysis.main()

        if not ofr_df.empty:
            metadata['ofr'] = {
                'records': len(ofr_df),
                'last_date': ofr_df.index[-1].strftime('%Y-%m-%d')
            }
            print(f"✓ OFR: {len(ofr_df)} records through {metadata['ofr']['last_date']}")
        else:
            ofr_df = pd.DataFrame()
            metadata['ofr'] = {'status': 'no_data'}
    except ImportError:
        print("⚠️  OFR module not available - plumbing stress will use repo ops only")
        ofr_df = pd.DataFrame()
        metadata['ofr'] = {'status': 'not_available'}
    except Exception as e:
        print(f"⚠️  OFR data loading failed: {e}")
        ofr_df = pd.DataFrame()
        metadata['ofr'] = {'error': str(e)}

    print("\n" + "="*60)
    print("DATA LOADING COMPLETE")
    print("="*60)

    return fiscal_df, fed_df, ofr_df, metadata


def calculate_integrated_flows(
    fiscal_df: pd.DataFrame,
    fed_df: pd.DataFrame,
    lookback_days: int = 20
) -> pd.DataFrame:
    """
    Calculate the integrated weekly flow table (Section 6 of report).

    Aggregates fiscal and monetary flows to show net weekly liquidity impact.

    Args:
        fiscal_df: Processed fiscal analysis DataFrame
        fed_df: Processed Fed liquidity DataFrame
        lookback_days: Number of days to analyze (default 20 = ~4 weeks)

    Returns:
        DataFrame with weekly flow breakdown
    """
    print("\nCalculating Integrated Weekly Flows...")

    if fiscal_df.empty or fed_df.empty:
        print("⚠️  Cannot calculate flows - missing fiscal or Fed data")
        return pd.DataFrame()

    # Get last N days of data
    fiscal_recent = fiscal_df.tail(lookback_days)
    fed_recent = fed_df.tail(lookback_days)

    # Ensure date alignment
    common_dates = fiscal_recent.index.intersection(fed_recent.index)

    if len(common_dates) == 0:
        print("⚠️  No common dates between fiscal and Fed data")
        return pd.DataFrame()

    # Calculate weekly flows (using last 5 business days as "week")
    flows = pd.DataFrame(index=common_dates)

    # 1. Fiscal Impulse (weekly average from 4W cumulative)
    if '4W_Cum_Impulse' in fiscal_recent.columns:
        flows['fiscal_impulse_weekly'] = fiscal_recent.loc[common_dates, '4W_Cum_Impulse'] / 4
    elif 'MA20_Impulse' in fiscal_recent.columns:
        # Fallback: MA20 * 5 = weekly
        flows['fiscal_impulse_weekly'] = fiscal_recent.loc[common_dates, 'MA20_Impulse'] * 5
    else:
        flows['fiscal_impulse_weekly'] = 0

    # 2. Tax Receipts (weekly sum, negative because it's a drain)
    if 'Total_Taxes' in fiscal_recent.columns:
        flows['tax_receipts_weekly'] = -fiscal_recent.loc[common_dates, 'Total_Taxes'].rolling(5).sum()
    else:
        flows['tax_receipts_weekly'] = 0

    # 3. Fed QT Pace (weekly change in assets)
    if 'QT_Pace_Assets_Weekly' in fed_recent.columns:
        flows['fed_qt_weekly'] = fed_recent.loc[common_dates, 'QT_Pace_Assets_Weekly']
    elif 'Flow_Nominal_Assets_Weekly' in fed_recent.columns:
        flows['fed_qt_weekly'] = fed_recent.loc[common_dates, 'Flow_Nominal_Assets_Weekly']
    else:
        flows['fed_qt_weekly'] = 0

    # 4. RRP Change (weekly aggregate, positive = injection)
    if 'RRP_Change' in fed_recent.columns:
        flows['rrp_drawdown_weekly'] = -fed_recent.loc[common_dates, 'RRP_Change'].rolling(5).sum()
    else:
        flows['rrp_drawdown_weekly'] = 0

    # 5. TGA Net Change (5-day change)
    if 'TGA_Balance' in fed_recent.columns:
        tga_change = fed_recent.loc[common_dates, 'TGA_Balance'].diff(5)
        flows['tga_net_change_weekly'] = -tga_change  # Negative because TGA increase = drain
    elif 'TGA_Balance' in fiscal_recent.columns:
        tga_change = fiscal_recent.loc[common_dates, 'TGA_Balance'].diff(5)
        flows['tga_net_change_weekly'] = -tga_change
    else:
        flows['tga_net_change_weekly'] = 0

    # Calculate net weekly impact (sum of all flows)
    flows['net_weekly_impact'] = flows.sum(axis=1)

    # Direction labels
    flows['fiscal_direction'] = flows['fiscal_impulse_weekly'].apply(
        lambda x: 'Injection' if x > 0 else 'Drain' if x < 0 else 'Neutral'
    )
    flows['tax_direction'] = flows['tax_receipts_weekly'].apply(
        lambda x: 'Drain' if x < 0 else 'Injection' if x > 0 else 'Neutral'
    )
    flows['qt_direction'] = flows['fed_qt_weekly'].apply(
        lambda x: 'Drain' if x < 0 else 'Injection' if x > 0 else 'Neutral'
    )
    flows['rrp_direction'] = flows['rrp_drawdown_weekly'].apply(
        lambda x: 'Injection' if x > 0 else 'Drain' if x < 0 else 'Neutral'
    )
    flows['tga_direction'] = flows['tga_net_change_weekly'].apply(
        lambda x: 'Injection' if x > 0 else 'Drain' if x < 0 else 'Neutral'
    )
    flows['net_direction'] = flows['net_weekly_impact'].apply(
        lambda x: 'Net Injection' if x > 0 else 'Net Drain' if x < 0 else 'Balanced'
    )

    print(f"✓ Calculated integrated flows for {len(flows)} days")

    return flows


def extract_key_metrics(
    fiscal_df: pd.DataFrame,
    fed_df: pd.DataFrame,
    flows_df: pd.DataFrame
) -> Dict:
    """
    Extract key metrics from all DataFrames for report generation.

    Args:
        fiscal_df: Processed fiscal analysis DataFrame
        fed_df: Processed Fed liquidity DataFrame
        flows_df: Integrated weekly flows DataFrame

    Returns:
        Dict with all extracted metrics organized by category
    """
    print("\nExtracting Key Metrics...")

    metrics = {
        'fiscal': {},
        'monetary': {},
        'plumbing': {},
        'integrated': {},
        'temporal': {},
        'regime': {}
    }

    # Get latest row from each DataFrame
    if not fiscal_df.empty:
        fiscal_last = fiscal_df.iloc[-1]
        fiscal_date = fiscal_df.index[-1]

        # Note: Column names in fiscal_df may differ from expected names
        # Use available columns and provide fallbacks
        metrics['fiscal'] = {
            'date': fiscal_date.strftime('%Y-%m-%d'),
            'total_impulse': fiscal_last.get('Net_Impulse', 0),  # Use Net_Impulse instead of Total_Impulse
            'ma20_impulse': fiscal_last.get('MA20_Net_Impulse', 0),  # Use MA20_Net_Impulse instead of MA20_Impulse
            'ma5_impulse': fiscal_last.get('MA5_Net_Impulse', 0),    # Use MA5_Net_Impulse instead of MA5_Impulse
            'impulse_pct_gdp': fiscal_last.get('Weekly_Impulse_Pct_GDP', 0),  # This exists
            'mtd_impulse': fiscal_last.get('MTD_Net', 0),          # Use MTD_Net instead of MTD_Impulse
            'fytd_impulse': fiscal_last.get('FYTD_Net', 0),          # Use FYTD_Net instead of FYTD_Impulse
            'household_impulse': fiscal_last.get('Household_Spending', 0),  # Use Household_Spending instead
            'household_share': (fiscal_last.get('Household_Spending', 0) /
                              fiscal_last.get('Net_Impulse', 1) * 100) if fiscal_last.get('Net_Impulse', 0) != 0 else 0,
            'tga_balance': fiscal_last.get('TGA_Balance', 0),
            'yoy_fytd_change': fiscal_last.get('FYTD_YoY_Diff', 0),  # Use FYTD_YoY_Diff instead of Cum_Diff_YoY
            'vs_3y_baseline': (fiscal_last.get('MA20_Net_Impulse', 0) - fiscal_last.get('3Y_Avg_Net_Impulse', 0)),
        }

    if not fed_df.empty:
        # Use last valid values for key metrics (handles missing data for latest date)
        def get_last_valid(col_name):
            """Get last valid (non-NaN) value from a column"""
            if col_name in fed_df.columns:
                series = fed_df[col_name]
                last_valid_idx = series.last_valid_index()
                if last_valid_idx is not None:
                    return series.loc[last_valid_idx]
            return 0

        fed_last = fed_df.iloc[-1]  # For columns that are complete
        fed_date = fed_df.index[-1]

        # Calculate temporal metrics
        mtd_metrics = calculate_mtd_metrics(fed_df)
        qtd_metrics = calculate_qtd_metrics(fed_df)
        rolling_3m = calculate_rolling_3m_metrics(fed_df)

        # Spike analysis
        spike_analysis = detect_spread_spikes(fed_df)

        # Stress index
        stress_metrics = calculate_stress_index(fed_df)

        # Regime detection
        regime_info = detect_regime(fed_df)

        # Correlations
        correlations = calculate_correlations(fed_df)

        # Forecasts
        net_liq_forecast = forecast_simple_trend(fed_df, 'Net_Liquidity', periods=5)
        rrp_forecast = forecast_simple_trend(fed_df, 'RRP_Balance', periods=5)

        metrics['monetary'] = {
            'date': fed_date.strftime('%Y-%m-%d'),
            'net_liquidity': get_last_valid('Net_Liquidity'),
            'net_liq_change': fed_last.get('Net_Liq_Change', 0),
            'ma20_net_liq': get_last_valid('MA20_Net_Liq'),
            'yoy_net_liq_change': fed_last.get('YoY_Net_Liq_Change', 0),
            'fed_total_assets': fed_last.get('Fed_Total_Assets', 0),
            'qt_pace_weekly': fed_last.get('QT_Pace_Assets_Weekly', 0),
            'rrp_balance': get_last_valid('RRP_Balance'),
            'rrp_change': fed_last.get('RRP_Change', 0),
            'ma20_rrp': get_last_valid('MA20_RRP'),
            'tga_balance': fed_last.get('TGA_Balance', 0),
            # Effective Policy Stance metrics (NEW)
            'net_balance_sheet_flow': get_last_valid('Net_Balance_Sheet_Flow') if 'Net_Balance_Sheet_Flow' in fed_df.columns else get_last_valid('Flow_Nominal_Assets'),
            'qualitative_easing_support': get_last_valid('Qualitative_Easing_Support') if 'Qualitative_Easing_Support' in fed_df.columns else get_last_valid('QE_Effective'),
            'mbs_runoff_weekly': fed_last.get('MBS_Runoff_Weekly', 0),
            'bill_purchases_weekly': fed_last.get('Bill_Purchases_Weekly', 0),
            'mbs_to_bills_reinvestment': fed_last.get('MBS_to_Bills_Reinvestment', 0),
            'repo_ops_balance': fed_last.get('Repo_Ops_Balance', 0),
        }

        metrics['plumbing'] = {
            'sofr_rate': fed_last.get('SOFR_Rate', 0),
            'iorb_rate': fed_last.get('IORB_Rate', 0),
            'spread_sofr_iorb': fed_last.get('Spread_SOFR_IORB', 0),
            'spread_effr_iorb': fed_last.get('Spread_EFFR_IORB', 0),
            'sofr_vol_5d': fed_last.get('SOFR_Vol_5D', 0),
            'stress_flag': fed_last.get('Stress_Flag', False),
            'repo_ops_balance': fed_last.get('Repo_Ops_Balance', 0),
        }

        metrics['temporal'] = {
            'mtd': mtd_metrics,
            'qtd': qtd_metrics,
            'rolling_3m': rolling_3m,
            'spike_analysis': spike_analysis,
        }

        metrics['regime'] = {
            'current_regime': regime_info.get('regime', 'UNKNOWN'),
            'confidence': regime_info.get('confidence', 0),
            'signals': regime_info.get('signals', []),
            'stress_index': stress_metrics.get('stress_index', 0),
            'stress_level': stress_metrics.get('stress_level', 'N/A'),
            'stress_components': stress_metrics.get('components', {}),
        }

        metrics['integrated']['correlations'] = correlations
        metrics['integrated']['forecasts'] = {
            'net_liquidity': net_liq_forecast,
            'rrp': rrp_forecast
        }

    if not flows_df.empty:
        flows_last = flows_df.iloc[-1]

        metrics['integrated']['weekly_flows'] = {
            'fiscal_impulse': flows_last.get('fiscal_impulse_weekly', 0),
            'tax_receipts': flows_last.get('tax_receipts_weekly', 0),
            'fed_qt': flows_last.get('fed_qt_weekly', 0),
            'rrp_drawdown': flows_last.get('rrp_drawdown_weekly', 0),
            'tga_change': flows_last.get('tga_net_change_weekly', 0),
            'net_impact': flows_last.get('net_weekly_impact', 0),
        }

        # Calculate averages over lookback period
        metrics['integrated']['weekly_flows_avg'] = {
            'fiscal_impulse': flows_df['fiscal_impulse_weekly'].mean(),
            'tax_receipts': flows_df['tax_receipts_weekly'].mean(),
            'fed_qt': flows_df['fed_qt_weekly'].mean(),
            'rrp_drawdown': flows_df['rrp_drawdown_weekly'].mean(),
            'tga_change': flows_df['tga_net_change_weekly'].mean(),
            'net_impact': flows_df['net_weekly_impact'].mean(),
        }

    print(f"✓ Extracted metrics from {len(metrics)} categories")

    return metrics


def build_final_report(
    metrics: Dict,
    metadata: Dict
) -> str:
    """
    Build the final 8-section desk report from extracted metrics.

    Args:
        metrics: Dict with all extracted metrics
        metadata: Dict with report metadata

    Returns:
        Formatted report string (Markdown)
    """
    print("\nBuilding Final Report...")

    report_lines = []

    # ================================================================
    # HEADER
    # ================================================================
    report_lines.append("=" * 70)
    report_lines.append("TREASURY LIQUIDITY DESK REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"Report Date: {metadata['report_date']} {metadata['report_time']}")
    report_lines.append(f"Version: {metadata['version']}")
    report_lines.append("=" * 70)
    report_lines.append("")

    # ================================================================
    # SECTION 0: EXECUTIVE SUMMARY
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 0: EXECUTIVE SUMMARY")
    report_lines.append("━" * 70)
    report_lines.append("")

    # Generate key findings
    findings = []

    # Finding 1: Fiscal Impulse vs Target
    if 'fiscal' in metrics and 'impulse_pct_gdp' in metrics['fiscal']:
        impulse_pct = metrics['fiscal']['impulse_pct_gdp']
        delta_vs_target = impulse_pct - FISCAL_IMPULSE_TARGET_PCT
        status = "ABOVE TARGET" if delta_vs_target > 0.1 else "BELOW TARGET" if delta_vs_target < -0.1 else "ON TARGET"
        findings.append(f"• Fiscal Impulse: {impulse_pct:.2f}% of GDP "
                       f"({delta_vs_target:+.2f}% vs {FISCAL_IMPULSE_TARGET_PCT}% target) - {status}")

    # Finding 2: Net Liquidity
    if 'monetary' in metrics and 'net_liquidity' in metrics['monetary']:
        net_liq = metrics['monetary']['net_liquidity'] / 1_000_000  # Convert to trillions
        net_liq_change_mtd = metrics['temporal']['mtd'].get('net_liq_mtd_change', 0) / 1_000_000
        findings.append(f"• Net Liquidity: ${net_liq:.2f}T ({net_liq_change_mtd:+.2f}T MTD)")

    # Finding 3: RRP Status
    if 'monetary' in metrics and 'rrp_balance' in metrics['monetary']:
        rrp = metrics['monetary']['rrp_balance']
        rrp_mtd_pct = (metrics['temporal']['mtd'].get('rrp_mtd_change', 0) /
                       (rrp - metrics['temporal']['mtd'].get('rrp_mtd_change', 0)) * 100) if rrp > 0 else 0
        rrp_status = "CRITICAL" if rrp < 50 else "WARNING" if rrp < 150 else "NORMAL"
        findings.append(f"• RRP Balance: ${rrp:,.0f}B ({rrp_mtd_pct:+.1f}% MTD) - {rrp_status}")

    # Finding 4: Monetary Regime
    if 'regime' in metrics:
        regime = metrics['regime']['current_regime']
        confidence = metrics['regime']['confidence']
        findings.append(f"• Monetary Regime: {regime} ({confidence:.0f}% confidence)")

    # Finding 5: Stress Level
    if 'regime' in metrics and 'stress_index' in metrics['regime']:
        stress = metrics['regime']['stress_index']
        stress_level = metrics['regime']['stress_level']
        stress_emoji = "🔴" if stress >= 75 else "🟡" if stress >= 50 else "✅"
        findings.append(f"• Market Stress: {stress:.0f}/100 ({stress_level}) {stress_emoji}")

    report_lines.append("Key Findings:")
    report_lines.extend(findings)
    report_lines.append("")

    # Metrics Table
    report_lines.append("Quick Metrics:")
    report_lines.append("Metric                         Current      Target       Status")
    report_lines.append("─" * 70)

    if 'fiscal' in metrics:
        impulse_pct = metrics['fiscal'].get('impulse_pct_gdp', 0)
        delta = impulse_pct - FISCAL_IMPULSE_TARGET_PCT
        status_symbol = "↑" if delta > 0.1 else "↓" if delta < -0.1 else "→"
        report_lines.append(f"Weekly Impulse % GDP           {impulse_pct:5.2f}%      {FISCAL_IMPULSE_TARGET_PCT:.2f}%       {status_symbol} {delta:+.2f}%")

    if 'monetary' in metrics:
        net_liq_t = metrics['monetary'].get('net_liquidity', 0) / 1_000_000
        mtd_change = metrics['temporal']['mtd'].get('net_liq_mtd_change', 0) / 1_000_000
        report_lines.append(f"Net Liquidity (T)              ${net_liq_t:5.2f}T      —            {mtd_change:+.2f}T MTD")

        rrp = metrics['monetary'].get('rrp_balance', 0)
        rrp_mtd = metrics['temporal']['mtd'].get('rrp_mtd_change', 0)
        report_lines.append(f"RRP Balance (B)                ${rrp:5.0f}B      —            {rrp_mtd:+.0f}B MTD")

    if 'regime' in metrics:
        regime = metrics['regime'].get('current_regime', 'N/A')
        confidence = metrics['regime'].get('confidence', 0)
        report_lines.append(f"Regime                         {regime:10s}   —            {confidence:.0f}% conf")

    report_lines.append("")

    # ================================================================
    # SECTION 1: FISCAL IMPULSE ANALYSIS
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 1: FISCAL IMPULSE ANALYSIS")
    report_lines.append("━" * 70)
    report_lines.append("")

    if 'fiscal' in metrics and metrics['fiscal']:
        fiscal = metrics['fiscal']

        report_lines.append("1.1 Current Standing vs Target")
        report_lines.append("")
        report_lines.append("Metric                    Current        Target        Gap")
        report_lines.append("─" * 70)
        report_lines.append(f"Weekly Impulse % GDP      {fiscal.get('impulse_pct_gdp', 0):6.2f}%       {FISCAL_IMPULSE_TARGET_PCT:.2f}%       "
                           f"{fiscal.get('impulse_pct_gdp', 0) - FISCAL_IMPULSE_TARGET_PCT:+.2f}%")
        report_lines.append(f"MA20 Daily Impulse        ${fiscal.get('ma20_impulse', 0):,.0f}M      —             —")
        report_lines.append(f"Daily Impulse (latest)    ${fiscal.get('total_impulse', 0):,.0f}M      —             —")
        report_lines.append("")

        # Interpretation
        impulse_vs_target = fiscal.get('impulse_pct_gdp', 0) - FISCAL_IMPULSE_TARGET_PCT
        if impulse_vs_target > 0.1:
            interp = f"Impulse is ELEVATED (+{impulse_vs_target:.2f}% vs target), indicating expansionary fiscal stance."
        elif impulse_vs_target < -0.1:
            interp = f"Impulse is BELOW TARGET ({impulse_vs_target:.2f}%), indicating contractionary fiscal stance."
        else:
            interp = "Impulse is ON TARGET, indicating balanced fiscal flow."

        report_lines.append(f"Interpretation: {interp}")
        report_lines.append("")

        report_lines.append("1.2 Household Absorption")
        report_lines.append(f"Household Impulse:        ${fiscal.get('household_impulse', 0):,.0f}M")
        report_lines.append(f"Household Share:          {fiscal.get('household_share', 0):.1f}% of total")
        report_lines.append("")
    else:
        report_lines.append("⚠️  Fiscal data not available")
        report_lines.append("")

    # ================================================================
    # SECTION 2: TIME-FRAME DECOMPOSITION
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 2: TIME-FRAME DECOMPOSITION")
    report_lines.append("━" * 70)
    report_lines.append("")

    if 'temporal' in metrics and metrics['temporal']:
        mtd = metrics['temporal'].get('mtd', {})
        qtd = metrics['temporal'].get('qtd', {})
        rolling_3m = metrics['temporal'].get('rolling_3m', {})

        report_lines.append("2.1 Month-to-Date (MTD)")
        report_lines.append("")

        if mtd:
            report_lines.append(f"Period: {mtd.get('month_start', 'N/A')} to {mtd.get('month_end', 'N/A')}")
            report_lines.append(f"RRP MTD Change:           ${mtd.get('rrp_mtd_change', 0):,.0f}B")
            report_lines.append(f"Net Liquidity MTD:        ${mtd.get('net_liq_mtd_change', 0):,.0f}M")
            report_lines.append(f"Balance Sheet MTD:        ${mtd.get('assets_mtd_change', 0):,.0f}M")
            report_lines.append(f"Avg SOFR-IORB Spread:     {mtd.get('sofr_iorb_mtd_avg', 0):.2f} bps")
            report_lines.append("")

        report_lines.append("2.2 Quarter-to-Date (QTD)")
        report_lines.append("")

        if qtd:
            report_lines.append(f"Period: {qtd.get('quarter_start', 'N/A')} to {qtd.get('quarter_end', 'N/A')}")
            report_lines.append(f"RRP QTD Change:           ${qtd.get('rrp_qtd_change', 0):,.0f}B ({qtd.get('rrp_qtd_pct', 0):+.1f}%)")
            report_lines.append(f"QT Pace (Annualized):     ${qtd.get('qt_pace_annualized', 0):,.0f}M/year")
            report_lines.append(f"Spread Volatility:        {qtd.get('sofr_spread_qtd_vol', 0):.2f} bps (std)")
            report_lines.append("")

        report_lines.append("2.3 3-Month Rolling")
        report_lines.append("")

        if rolling_3m:
            report_lines.append(f"3M Avg Net Liquidity:     ${rolling_3m.get('net_liq_3m_avg', 0):,.0f}M")
            report_lines.append(f"3M Trend:                 {rolling_3m.get('net_liq_3m_trend', 'N/A')}")
            report_lines.append(f"Current Percentile:       {rolling_3m.get('net_liq_3m_percentile', 0):.0f}th")
            report_lines.append("")
    else:
        report_lines.append("⚠️  Temporal metrics not available")
        report_lines.append("")

    # ================================================================
    # SECTION 3: HISTORICAL COMPARISON
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 3: HISTORICAL COMPARISON & DEVIATION ANALYSIS")
    report_lines.append("━" * 70)
    report_lines.append("")

    if 'fiscal' in metrics and metrics['fiscal']:
        fiscal = metrics['fiscal']

        report_lines.append("3.1 Year-over-Year Delta")
        report_lines.append("")
        report_lines.append("Timeframe        Current        vs LY          Change")
        report_lines.append("─" * 70)
        report_lines.append(f"FYTD Cumulative  ${fiscal.get('fytd_impulse', 0):,.0f}M    —              {fiscal.get('yoy_fytd_change', 0):+,.0f}M")
        report_lines.append("")

        report_lines.append("3.2 3-Year Baseline Comparison")
        report_lines.append(f"Current MA20:             ${fiscal.get('ma20_impulse', 0):,.0f}M")
        report_lines.append(f"vs 3-Year Baseline:       {fiscal.get('vs_3y_baseline', 0):+,.0f}M")
        report_lines.append("")

    # ================================================================
    # SECTION 4: LIQUIDITY COMPOSITION & FLOW DYNAMICS
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 4: LIQUIDITY COMPOSITION & FLOW DYNAMICS")
    report_lines.append("━" * 70)
    report_lines.append("")

    if 'fiscal' in metrics and metrics['fiscal']:
        fiscal = metrics['fiscal']

        report_lines.append("4.1 TGA (Treasury General Account) Balance")
        report_lines.append("")
        report_lines.append(f"Current Balance:          ${fiscal.get('tga_balance', 0):,.0f}M")
        report_lines.append("")

        # TGA status interpretation
        tga = fiscal.get('tga_balance', 0)
        if tga < 100_000:
            tga_status = "LOW - potential cash constraint signals"
        elif tga > 500_000:
            tga_status = "HIGH - pre-funding buildup or reduced issuance ahead"
        else:
            tga_status = "NORMAL range"
        report_lines.append(f"Status: {tga_status}")
        report_lines.append("")

    if 'fiscal' in metrics and metrics['fiscal']:
        report_lines.append("4.2 Household Absorption Breakdown")
        report_lines.append("")
        report_lines.append(f"Total Household:          ${metrics['fiscal'].get('household_impulse', 0):,.0f}M ({metrics['fiscal'].get('household_share', 0):.1f}%)")
        report_lines.append("")

    # ================================================================
    # SECTION 5: FED LIQUIDITY & MONETARY CONDITIONS
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 5: FED LIQUIDITY & MONETARY CONDITIONS")
    report_lines.append("━" * 70)
    report_lines.append("")

    if 'monetary' in metrics and metrics['monetary']:
        mon = metrics['monetary']

        report_lines.append("5.1 Net Liquidity Status")
        report_lines.append("")
        report_lines.append("Component              Current        MTD Δ          Trend")
        report_lines.append("─" * 70)

        mtd = metrics['temporal'].get('mtd', {})
        report_lines.append(f"Fed Assets             ${mon.get('fed_total_assets', 0):,.0f}M    {mtd.get('assets_mtd_change', 0):+,.0f}M    {mon.get('qt_pace_weekly', 0):+,.0f}M/wk")
        report_lines.append(f"RRP Balance            ${mon.get('rrp_balance', 0):,.0f}B     {mtd.get('rrp_mtd_change', 0):+,.0f}B")
        report_lines.append(f"TGA Balance            ${mon.get('tga_balance', 0):,.0f}M    —")
        report_lines.append("─" * 70)
        report_lines.append(f"NET LIQUIDITY          ${mon.get('net_liquidity', 0):,.0f}M    {mtd.get('net_liq_mtd_change', 0):+,.0f}M")
        report_lines.append("")

    if 'plumbing' in metrics and 'temporal' in metrics:
        plumb = metrics['plumbing']
        spike = metrics['temporal'].get('spike_analysis', {})

        report_lines.append("5.2 Repo Market Stress Indicators")
        report_lines.append("")
        report_lines.append("Metric                  Current    MA20       Threshold   Status")
        report_lines.append("─" * 70)

        sofr_spread = plumb.get('spread_sofr_iorb', 0)
        sofr_status = "🔴 CRITICAL" if sofr_spread > 20 else "🟡 WARNING" if sofr_spread > 10 else "✅ NORMAL"
        report_lines.append(f"SOFR-IORB Spread        {sofr_spread:5.1f} bps  {spike.get('ma20', 0):5.1f} bps  >10 bps     {sofr_status}")

        effr_spread = plumb.get('spread_effr_iorb', 0)
        report_lines.append(f"EFFR-IORB Spread        {effr_spread:5.1f} bps  —          —           ✅")

        rrp = metrics['monetary'].get('rrp_balance', 0)
        rrp_status = "🔴 CRITICAL" if rrp < 50 else "🟡 WARNING" if rrp < 150 else "✅ NORMAL"
        report_lines.append(f"RRP Usage               ${rrp:5.0f}B    —          <$50B       {rrp_status}")

        stress_idx = metrics['regime'].get('stress_index', 0)
        stress_status = "🔴 HIGH" if stress_idx >= 75 else "🟡 ELEVATED" if stress_idx >= 50 else "✅ LOW"
        report_lines.append(f"Stress Index            {stress_idx:5.0f}/100  —          >50         {stress_status}")
        report_lines.append("")

    if 'regime' in metrics:
        regime = metrics['regime']

        report_lines.append("5.3 Monetary Regime Confidence")
        report_lines.append("")
        report_lines.append(f"Regime:                   {regime.get('current_regime', 'UNKNOWN')} ({regime.get('confidence', 0):.0f}% confidence)")
        report_lines.append(f"Signals:                  {', '.join(regime.get('signals', []))}")
        report_lines.append("")

    # NEW: 5.4 Effective Policy Stance
    if 'monetary' in metrics:
        mon = metrics['monetary']

        report_lines.append("5.4 Effective Policy Stance (QT/QE Decomposition)")
        report_lines.append("")

        # Quantità: Net Balance Sheet Flow
        flow = mon.get('net_balance_sheet_flow', 0)
        flow_direction = "QE (Injection)" if flow > 0 else "QT (Drain)" if flow < 0 else "Neutral"
        flow_icon = "💰" if flow > 0 else "📉" if flow < 0 else "➡️"

        report_lines.append(f"QUANTITÀ - Net Balance Sheet Flow:")
        report_lines.append(f"  Weekly Change:        {flow_icon} ${flow:,.0f}M")
        report_lines.append(f"  Direction:            {flow_direction}")
        report_lines.append("")

        # Open Market Operations
        mbs_runoff = mon.get('mbs_runoff_weekly', 0)
        bill_purchases = mon.get('bill_purchases_weekly', 0)
        reinvestment = mon.get('mbs_to_bills_reinvestment', 0)

        if mbs_runoff != 0 or bill_purchases != 0:
            report_lines.append(f"Open Market Operations:")
            report_lines.append(f"  MBS Runoff:           ${mbs_runoff:,.0f}M")
            report_lines.append(f"  Bill Purchases:       ${bill_purchases:,.0f}M")
            if reinvestment > 0:
                report_lines.append(f"  > Reinvestimento:     ${reinvestment:,.0f}M (MBS→Bills)")
            report_lines.append("")

        # Qualità: Shadow QE Support
        qual = mon.get('qualitative_easing_support', 0)
        repo = mon.get('repo_ops_balance', 0)

        report_lines.append(f"QUALITÀ - Shadow QE Support:")
        report_lines.append(f"  Total Support:        ${qual:,.0f}M")
        if reinvestment > 0 or repo > 0:
            report_lines.append(f"  Components:")
            if reinvestment > 0:
                report_lines.append(f"    • Reinvestimento:   ${reinvestment:,.0f}M")
            if repo > 0:
                report_lines.append(f"    • Repo Operations:  ${repo:,.0f}M")
        report_lines.append(f"  (Supporto qualitativo: duration, risk appetite)")
        report_lines.append("")

        # Interpretazione
        report_lines.append(f"Interpretazione:")
        if flow < -50:
            if qual > 20:
                report_lines.append(f"  • QT aggressivo (${flow:,.0f}M) parzialmente compensato")
                report_lines.append(f"    da shadow QE (${qual:,.0f}M)")
            else:
                report_lines.append(f"  • QT aggressivo senza compensazione significativa")
        elif flow > 50:
            report_lines.append(f"  • QE attivo: sia quantità che qualità espansive")
        else:
            if qual > 20:
                report_lines.append(f"  • Balance sheet stabile ma supporto qualitativo attivo")
            else:
                report_lines.append(f"  • Policy stance sostanzialmente neutrale")
        report_lines.append("")

    # ================================================================
    # SECTION 6: INTEGRATED LIQUIDITY VIEW
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 6: INTEGRATED LIQUIDITY VIEW")
    report_lines.append("━" * 70)
    report_lines.append("")

    if 'integrated' in metrics and 'weekly_flows' in metrics['integrated']:
        flows = metrics['integrated']['weekly_flows']
        flows_avg = metrics['integrated'].get('weekly_flows_avg', {})

        report_lines.append("6.1 Fiscal + Monetary Net Effect (Latest Week)")
        report_lines.append("")
        report_lines.append("Source              Weekly Flow    Direction       Net Liquidity Impact")
        report_lines.append("━" * 70)
        report_lines.append(f"Fiscal Impulse      {flows.get('fiscal_impulse', 0)/1000:+7.1f}B/week   Injection       {flows.get('fiscal_impulse', 0)/1000:+7.1f}B")
        report_lines.append(f"Tax Receipts        {flows.get('tax_receipts', 0)/1000:+7.1f}B/week   Drain           {flows.get('tax_receipts', 0)/1000:+7.1f}B")
        report_lines.append(f"Fed QT (Assets)     {flows.get('fed_qt', 0)/1000:+7.1f}B/week   {'Drain' if flows.get('fed_qt', 0)<0 else 'Injection':15s} {flows.get('fed_qt', 0)/1000:+7.1f}B")
        report_lines.append(f"RRP Drawdown        {flows.get('rrp_drawdown', 0):+7.1f}B/week   {'Injection' if flows.get('rrp_drawdown', 0)>0 else 'Drain':15s} {flows.get('rrp_drawdown', 0):+7.1f}B")
        report_lines.append(f"TGA Net Change      {flows.get('tga_change', 0)/1000:+7.1f}B/week   {'Injection' if flows.get('tga_change', 0)>0 else 'Drain':15s} {flows.get('tga_change', 0)/1000:+7.1f}B")
        report_lines.append("━" * 70)
        net_impact_b = flows.get('net_impact', 0) / 1000
        net_direction = "Net Injection" if net_impact_b > 0 else "Net Drain" if net_impact_b < 0 else "Balanced"
        report_lines.append(f"NET WEEKLY          —              {net_direction:15s} {net_impact_b:+7.1f}B/week")
        report_lines.append("")

        # Interpretation
        if net_impact_b > 50:
            conclusion = "STRONG NET INJECTION - Highly supportive of risk assets and liquidity conditions."
        elif net_impact_b > 10:
            conclusion = "Moderate net injection - Supportive liquidity environment."
        elif net_impact_b > -10:
            conclusion = "Balanced flows - Neutral liquidity impact."
        elif net_impact_b > -50:
            conclusion = "Moderate net drain - Tightening liquidity conditions."
        else:
            conclusion = "SEVERE NET DRAIN - Significant liquidity headwind."

        report_lines.append(f"Conclusion: {conclusion}")
        report_lines.append("")

    if 'integrated' in metrics and 'correlations' in metrics['integrated']:
        corr = metrics['integrated']['correlations']

        report_lines.append("6.2 Correlations (3-Month)")
        report_lines.append("")
        if 'net_liq_vs_tga' in corr:
            report_lines.append(f"Net Liq vs TGA:           {corr['net_liq_vs_tga']:+.2f} (mechanical inverse expected)")
        if 'rrp_vs_sofr_spread' in corr:
            report_lines.append(f"RRP vs SOFR Spread:       {corr['rrp_vs_sofr_spread']:+.2f}")
        if 'net_liq_vs_spread' in corr:
            report_lines.append(f"Net Liq vs SOFR Spread:   {corr['net_liq_vs_spread']:+.2f} (stress indicator)")
        report_lines.append("")

    # ================================================================
    # SECTION 7: RISK ASSESSMENT & OUTLOOK
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 7: RISK ASSESSMENT & OUTLOOK")
    report_lines.append("━" * 70)
    report_lines.append("")

    report_lines.append("7.1 Key Risks")
    report_lines.append("")

    # Risk assessment based on thresholds
    risks = []

    if 'monetary' in metrics:
        rrp = metrics['monetary'].get('rrp_balance', 0)
        if rrp < 50:
            risks.append({
                'name': 'RRP Depletion Risk',
                'severity': 'CRITICAL',
                'description': f'RRP at ${rrp:.0f}B, below $50B critical threshold',
                'implication': 'Reserve scarcity imminent - Fed may slow QT or activate SRF'
            })
        elif rrp < 150:
            risks.append({
                'name': 'RRP Depletion Watch',
                'severity': 'ELEVATED',
                'description': f'RRP at ${rrp:.0f}B, approaching $50B floor',
                'implication': 'Monitor for potential policy adjustment'
            })

    if 'regime' in metrics:
        stress_idx = metrics['regime'].get('stress_index', 0)
        if stress_idx >= 75:
            risks.append({
                'name': 'Market Stress',
                'severity': 'CRITICAL',
                'description': f'Stress Index at {stress_idx:.0f}/100 (HIGH STRESS)',
                'implication': 'Elevated volatility and potential funding disruptions'
            })
        elif stress_idx >= 50:
            risks.append({
                'name': 'Market Stress Watch',
                'severity': 'ELEVATED',
                'description': f'Stress Index at {stress_idx:.0f}/100 (ELEVATED)',
                'implication': 'Monitor for escalation in funding pressures'
            })

    if 'fiscal' in metrics:
        impulse_vs_target = metrics['fiscal'].get('impulse_pct_gdp', 0) - FISCAL_IMPULSE_TARGET_PCT
        if impulse_vs_target < -0.3:
            risks.append({
                'name': 'Fiscal Impulse Fade',
                'severity': 'MODERATE',
                'description': f'Impulse {impulse_vs_target:.2f}% below target',
                'implication': 'Reduced fiscal support for growth and liquidity'
            })

    if not risks:
        report_lines.append("• No significant risks identified at this time ✅")
    else:
        for i, risk in enumerate(risks, 1):
            severity_emoji = {"CRITICAL": "🔴", "ELEVATED": "🟡", "MODERATE": "🟢"}.get(risk['severity'], "•")
            report_lines.append(f"{i}. {risk['name']} ({risk['severity']}) {severity_emoji}")
            report_lines.append(f"   - {risk['description']}")
            report_lines.append(f"   - Implication: {risk['implication']}")
            report_lines.append("")

    report_lines.append("7.2 Base Case Outlook (30 Days)")
    report_lines.append("")

    # Generate outlook based on forecasts
    if 'integrated' in metrics and 'forecasts' in metrics['integrated']:
        forecasts = metrics['integrated']['forecasts']

        if 'net_liquidity' in forecasts and forecasts['net_liquidity']:
            nl_forecast = forecasts['net_liquidity']
            trend = nl_forecast.get('trend', 'N/A')
            report_lines.append(f"• Net Liquidity: Expected to trend {trend} (R²={nl_forecast.get('r_squared', 0):.2f})")

        if 'rrp' in forecasts and forecasts['rrp']:
            rrp_forecast = forecasts['rrp']
            trend = rrp_forecast.get('trend', 'N/A')
            report_lines.append(f"• RRP: Expected to trend {trend}")

    if 'regime' in metrics:
        regime = metrics['regime'].get('current_regime', 'UNKNOWN')
        report_lines.append(f"• Fed Policy: {regime} regime likely to continue barring major market disruption")

    report_lines.append("")

    # ================================================================
    # SECTION 8: ACTIONABLE INTELLIGENCE
    # ================================================================
    report_lines.append("━" * 70)
    report_lines.append("SECTION 8: ACTIONABLE INTELLIGENCE")
    report_lines.append("━" * 70)
    report_lines.append("")

    report_lines.append("For Rates Traders:")
    if 'monetary' in metrics:
        rrp = metrics['monetary'].get('rrp_balance', 0)
        if rrp < 150:
            report_lines.append("• Front-end: RRP depletion suggests floor risk on short rates - favor receivers")
        if 'plumbing' in metrics:
            spread = metrics['plumbing'].get('spread_sofr_iorb', 0)
            if spread > 10:
                report_lines.append(f"• Curve: SOFR-IORB at {spread:.1f}bps signals stress - flattener bias")
    report_lines.append("")

    report_lines.append("For Equity/Credit:")
    if 'integrated' in metrics and 'weekly_flows' in metrics['integrated']:
        net_impact = metrics['integrated']['weekly_flows'].get('net_impact', 0) / 1000
        if net_impact > 10:
            report_lines.append(f"• Risk-on: Net liquidity injection of ${net_impact:+.1f}B/week supportive")
        elif net_impact < -10:
            report_lines.append(f"• Risk-off: Net liquidity drain of ${net_impact:+.1f}B/week - headwind for risk assets")
    if 'regime' in metrics:
        stress = metrics['regime'].get('stress_index', 0)
        if stress >= 50:
            report_lines.append(f"• Volatility: Stress index at {stress:.0f}/100 - expect elevated vol")
    report_lines.append("")

    report_lines.append("For Macro Strategy:")
    if 'regime' in metrics:
        regime = metrics['regime'].get('current_regime', 'UNKNOWN')
        confidence = metrics['regime'].get('confidence', 0)
        report_lines.append(f"• Regime: {regime} with {confidence:.0f}% confidence")
    if 'fiscal' in metrics:
        impulse_pct = metrics['fiscal'].get('impulse_pct_gdp', 0)
        report_lines.append(f"• GDP Impact: Fiscal impulse at {impulse_pct:.2f}% GDP annualized")
    report_lines.append("")

    # ================================================================
    # FOOTER
    # ================================================================
    report_lines.append("=" * 70)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 70)

    print(f"✓ Built report with {len(report_lines)} lines")

    return "\n".join(report_lines)


def main():
    """
    Main execution function for desk report generation.
    """
    try:
        # Step 1: Load all data
        fiscal_df, fed_df, ofr_df, metadata = load_all_data()

        # Step 2: Calculate integrated flows
        flows_df = calculate_integrated_flows(fiscal_df, fed_df)

        # Step 3: Extract key metrics
        metrics = extract_key_metrics(fiscal_df, fed_df, flows_df)

        # Step 4: Build final report
        report = build_final_report(metrics, metadata)

        # Step 5: Output report
        print("\n")
        print(report)

        # Step 6: Save to file
        output_path = f"outputs/desk_report_{metadata['report_date']}.md"
        os.makedirs("outputs", exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(report)

        print(f"\n✓ Report saved to: {output_path}")

        return report

    except Exception as e:
        print(f"\n❌ Report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
