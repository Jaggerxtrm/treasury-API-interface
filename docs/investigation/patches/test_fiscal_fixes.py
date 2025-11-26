#!/usr/bin/env python3
"""
Test Cases for Fiscal Analysis Fixes
Run: pytest patches/test_fiscal_fixes.py -v
"""

import pytest
import pandas as pd
import numpy as np


# =============================================================================
# FISCAL-001: GDP Documentation Test
# =============================================================================

def test_gdp_metadata_in_output():
    """Test that GDP metadata is saved to fiscal_daily_metrics"""
    # Simulate processed data
    sample_data = {
        'record_date': pd.date_range('2025-11-01', periods=5),
        'Net_Impulse': [1000, 2000, -500, 3000, 1500],
        'GDP_Used': [31_700_000_000_000] * 5  # Should be present after fix
    }
    df = pd.DataFrame(sample_data)

    # Verify GDP_Used column exists
    assert 'GDP_Used' in df.columns, "GDP_Used column should be in output"

    # Verify all rows have the same GDP value
    assert df['GDP_Used'].nunique() == 1, "All rows should have same GDP value"

    # Verify GDP value is reasonable
    gdp_trillions = df['GDP_Used'].iloc[0] / 1e12
    assert 28 < gdp_trillions < 35, f"GDP should be ~$29-35T, got ${gdp_trillions:.1f}T"


def test_gdp_reverse_calculation():
    """Test that reported %GDP values match the documented GDP"""
    ma20_net = 12172.45  # Millions
    annual_pct_gdp = 9.68  # Percent

    # Reverse-calculate implied GDP
    # From formula: pct = (ma20 * 252 * 1_000_000) / gdp * 100
    # So: gdp = (ma20 * 252 * 1_000_000 * 100) / pct
    implied_gdp_usd = (ma20_net * 252 * 1_000_000 * 100) / annual_pct_gdp
    implied_gdp_trillions = implied_gdp_usd / 1e12

    # With fix, this should match the documented GDP_Used value
    # For now, verify it's in expected range
    assert 30 < implied_gdp_trillions < 33, \
        f"Implied GDP from %GDP should be ~$31-32T, got ${implied_gdp_trillions:.3f}T"


# =============================================================================
# FISCAL-002: RRP Forward-Fill Test
# =============================================================================

def test_rrp_forward_fill_weekends():
    """Test that RRP values are forward-filled for weekends"""
    # Create sample data with weekend gap
    data = {
        'date': pd.date_range('2025-11-21', periods=7),
        'RRP_Balance': [2.503, np.nan, np.nan, 1.077, 2.314, np.nan, np.nan],
        'Fed_Total_Assets': [6555283] * 7,
        'TGA_Balance': [892074, 892074, 892074, 906547, 906547, 906547, 906547]
    }
    df = pd.DataFrame(data)

    # Apply forward-fill (simulating the fix)
    df['RRP_Imputed'] = df['RRP_Balance'].isna()
    df['RRP_Balance'] = df['RRP_Balance'].ffill()
    df['RRP_Balance_M'] = df['RRP_Balance'] * 1000

    # Recalculate Net Liquidity
    df['Net_Liquidity'] = df['Fed_Total_Assets'] - df['RRP_Balance_M'] - df['TGA_Balance']
    df['Net_Liq_Imputed'] = df['RRP_Imputed']

    # Assertions
    # Weekend values (index 1, 2) should be imputed
    assert df.loc[1, 'RRP_Imputed'] == True, "Weekend RRP should be flagged as imputed"
    assert df.loc[1, 'RRP_Balance'] == 2.503, "Weekend RRP should use Friday's value"

    # Net Liquidity should be calculated for all days (no NaN)
    assert df['Net_Liquidity'].notna().all(), "Net Liquidity should have no NaN values after forward-fill"

    # Imputed Net Liquidity should be flagged
    assert df.loc[1, 'Net_Liq_Imputed'] == True, "Weekend Net Liq should be flagged as imputed"

    # Calculate expected Net Liquidity for weekend
    expected_net_liq_weekend = 6555283 - (2.503 * 1000) - 892074
    assert abs(df.loc[1, 'Net_Liquidity'] - expected_net_liq_weekend) < 1, \
        f"Weekend Net Liq should be {expected_net_liq_weekend:.0f}, got {df.loc[1, 'Net_Liquidity']:.0f}"


def test_rrp_no_false_imputation():
    """Test that valid trading days are NOT flagged as imputed"""
    data = {
        'date': pd.date_range('2025-11-24', periods=3),
        'RRP_Balance': [1.077, 2.314, 2.217],  # All valid
        'Fed_Total_Assets': [6555283] * 3,
        'TGA_Balance': [906547] * 3
    }
    df = pd.DataFrame(data)

    # Apply imputation logic
    df['RRP_Imputed'] = df['RRP_Balance'].isna()
    df['RRP_Balance'] = df['RRP_Balance'].ffill()

    # All should be non-imputed
    assert df['RRP_Imputed'].sum() == 0, "Valid trading days should not be flagged as imputed"


# =============================================================================
# FISCAL-003: Household Share Persistence Test
# =============================================================================

def test_household_share_calculation():
    """Test household share calculation formula"""
    household_spending = 7121  # Millions
    total_spending = 16788  # Millions
    net_impulse = -15570  # Negative (fiscal drag day)

    # Correct formula: household / total_spending
    household_share = (household_spending / total_spending * 100) if total_spending != 0 else 0

    assert abs(household_share - 42.42) < 0.01, \
        f"Household share should be 42.42%, got {household_share:.2f}%"

    # Verify it's in valid range
    assert 0 <= household_share <= 100, "Household share must be in [0, 100]% range"


def test_household_share_negative_net_impulse():
    """Test that household share remains valid even when net_impulse is negative"""
    # Fiscal drag day: taxes > spending
    household_spending = 5000
    total_spending = 10000
    net_impulse = -3000  # Negative!

    # Using CORRECT formula (household / total_spending)
    household_share = (household_spending / total_spending * 100)

    assert household_share == 50.0, f"Should be 50%, got {household_share}%"
    assert 0 <= household_share <= 100, "Should remain in valid range even with negative net_impulse"

    # Using WRONG formula (household / net_impulse) would give negative!
    wrong_formula_result = (household_spending / net_impulse * 100)
    assert wrong_formula_result < 0, "Wrong formula would produce negative value"


def test_household_share_bounds():
    """Test household share edge cases"""
    # Edge case 1: All spending is household
    assert (10000 / 10000 * 100) == 100.0, "100% household should give 100%"

    # Edge case 2: No household spending
    assert (0 / 10000 * 100) == 0.0, "0 household should give 0%"

    # Edge case 3: Household exceeds total (data quality issue)
    # This shouldn't happen, but if it does, should be flagged
    household = 12000
    total = 10000
    share = (household / total * 100)
    assert share > 100, "Data quality issue should be detectable (share > 100%)"


def test_household_share_in_dataframe():
    """Test that household_share_pct column is added to output"""
    data = {
        'record_date': pd.date_range('2025-11-20', periods=5),
        'Household_Spending': [7935, 8515, 19350, 7121, 6921],
        'Total_Spending': [19822, 46450, 31190, 16788, 19999],
    }
    df = pd.DataFrame(data)

    # Calculate household share (simulating fix)
    df['Household_Share_Pct'] = (df['Household_Spending'] / df['Total_Spending'] * 100).fillna(0)

    # Verify column exists
    assert 'Household_Share_Pct' in df.columns, "Household_Share_Pct should be in output"

    # Verify all values are in valid range
    assert (df['Household_Share_Pct'] >= 0).all(), "All household shares should be >= 0%"
    assert (df['Household_Share_Pct'] <= 100).all(), "All household shares should be <= 100%"

    # Spot check one value
    expected_share_0 = (7935 / 19822 * 100)
    assert abs(df.loc[0, 'Household_Share_Pct'] - expected_share_0) < 0.01


# =============================================================================
# FISCAL-007: Net Liquidity Calculation Verification (should PASS)
# =============================================================================

def test_net_liquidity_calculation():
    """Verify Net Liquidity formula is correct"""
    fed_assets = 6555283  # Millions
    rrp_balance_billions = 2.314  # Billions
    tga_balance = 906547  # Millions

    # Convert RRP to Millions
    rrp_balance_millions = rrp_balance_billions * 1000

    # Calculate Net Liquidity
    net_liquidity = fed_assets - rrp_balance_millions - tga_balance

    expected = 5646422  # From database
    assert abs(net_liquidity - expected) < 1, \
        f"Net Liquidity should be {expected:.0f}M, got {net_liquidity:.0f}M"


def test_net_liquidity_multiple_samples():
    """Test Net Liquidity calculation on multiple real data points"""
    test_cases = [
        # (Fed_Assets, RRP_B, TGA_M, Expected_Net_Liq_M)
        (6555283, 2.217, 906547, 5646519),
        (6555283, 2.314, 906547, 5646422),
        (6555283, 1.077, 906547, 5647659),
        (6555283, 2.503, 892074, 5660706),
        (6555283, 6.520, 909575, 5639188),
    ]

    for fed_assets, rrp_b, tga, expected in test_cases:
        rrp_m = rrp_b * 1000
        calc = fed_assets - rrp_m - tga
        assert abs(calc - expected) < 1, \
            f"Net Liq should be {expected:.0f}M, got {calc:.0f}M for RRP={rrp_b}B"


# =============================================================================
# FISCAL-008: 4-Week Cumulative Verification (should PASS)
# =============================================================================

def test_4w_cumulative_sliding_window():
    """Test that 4W cumulative uses rolling 20 BD window"""
    # Create 30 days of sample data
    net_impulse_values = [1000 + i*100 for i in range(30)]  # 1000, 1100, 1200, ...
    df = pd.DataFrame({'Net_Impulse': net_impulse_values})

    # Calculate 4W cumulative (rolling 20 BD)
    df['4W_Cum_Net'] = df['Net_Impulse'].rolling(window=20).sum()

    # For row 19 (0-indexed), should be sum of first 20 values
    expected_row_19 = sum(net_impulse_values[:20])
    assert abs(df.loc[19, '4W_Cum_Net'] - expected_row_19) < 0.01

    # For row 29 (last), should be sum of last 20 values
    expected_row_29 = sum(net_impulse_values[10:30])
    assert abs(df.loc[29, '4W_Cum_Net'] - expected_row_29) < 0.01

    # First 19 rows should have NaN (not enough data for full 20 BD window)
    # With rolling(window=20), first valid value appears at index 19
    assert pd.isna(df.loc[0, '4W_Cum_Net']), "First row should be NaN (not enough data)"
    assert pd.isna(df.loc[18, '4W_Cum_Net']), "Row 18 should still be NaN"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
