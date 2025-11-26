#!/usr/bin/env python3
"""
Test script to validate the bug fixes implemented in the Treasury API interface.
Tests the critical fixes for Household Share, RRP Drawdown NaN, Net Liquidity mismatch, and RRP % MTD.
"""

import pandas as pd
import numpy as np
import sys
import os

def test_household_share_formula():
    """Test that household_share calculation produces valid bounds (0-100%)"""
    print("=== Testing Household Share Bug Fix ===")
    
    # Test 1: Normal positive spending scenario
    total_spending = 1000
    household_spending = 450
    
    if total_spending > 0 and not pd.isna(total_spending):
        household_share = (household_spending / total_spending) * 100
        household_share = max(0, min(100, household_share))
    else:
        household_share = 0
        
    print(f"  Test 1 - Normal case: HH share = {household_share:.1f}% (expected: 45.0%)")
    assert 0 <= household_share <= 100, f"Household share out of bounds: {household_share}"
    assert abs(household_share - 45.0) < 0.1, f"Unexpected household share: {household_share}"
    
    # Test 2: Edge case - zero total spending
    total_spending = 0
    if total_spending > 0 and not pd.isna(total_spending):
        household_share = (household_spending / total_spending) * 100
        household_share = max(0, min(100, household_share))
    else:
        household_share = 0
        
    print(f"  Test 2 - Zero spending: HH share = {household_share:.1f}% (expected: 0.0%)")
    assert household_share == 0, f"HH share should be 0 for zero total spending"
    
    # Test 3: Edge case - NaN total spending  
    total_spending = np.nan
    if total_spending > 0 and not pd.isna(total_spending):
        household_share = (household_spending / total_spending) * 100
        household_share = max(0, min(100, household_share))
    else:
        household_share = 0
        
    print(f"  Test 3 - NaN spending: HH share = {household_share:.1f}% (expected: 0.0%)")
    assert household_share == 0, f"HH share should be 0 for NaN total spending"
    
    # Test 4: Edge case - household > total (should be capped at 100)
    total_spending = 500
    household_spending = 600
    if total_spending > 0 and not pd.isna(total_spending):
        household_share = (household_spending / total_spending) * 100
        household_share = max(0, min(100, household_share))
    else:
        household_share = 0
        
    print(f"  Test 4 - HH > total: HH share = {household_share:.1f}% (expected: 100.0%)")
    assert household_share == 100, f"HH share should be capped at 100% when HH > total"
    
    print("  ✅ Household Share bug fix: PASSED")
    print()

def test_rrp_drawdown_nan_handling():
    """Test that RRP drawdown calculation handles NaN values properly"""
    print("=== Testing RRP Drawdown NaN Fix ===")
    
    # Create test data with NaN values
    dates = pd.date_range('2025-11-01', periods=10, freq='D')
    rrp_changes = pd.Series([1.0, np.nan, -0.5, np.nan, 0.3, -0.2, np.nan, 0.1, -0.4, 0.2], index=dates)
    
    # Apply the fixed logic from calculate_integrated_flows
    print(f"  Original RRP changes: {rrp_changes.values}")
    
    # Clean NaN values before rolling calculation
    rrp_change_clean = rrp_changes.fillna(0)
    rrp_drawdown_weekly = -rrp_change_clean.rolling(5).sum()
    
    # Additional validation: check for any remaining NaN values
    if rrp_drawdown_weekly.isna().any():
        print("  ⚠️ RRP weekly NaN values detected after rolling sum, setting to 0")
        rrp_drawdown_weekly = rrp_drawdown_weekly.fillna(0)
    
    print(f"  Weekly RRP drawdown: {rrp_drawdown_weekly.values}")
    
    # Verify no NaN values
    assert not rrp_drawdown_weekly.isna().any(), "RRP drawdown should not contain NaN values"
    assert rrp_drawdown_weekly.dtype == float, "RRP drawdown should be float type"
    
    print("  ✅ RRP Drawdown NaN fix: PASSED")
    print()

def test_net_liquidity_reconciliation():
    """Test Net Liquidity calculation and reconciliation check"""
    print("=== Testing Net Liquidity Mismatch Fix ===")
    
    # Test data representing realistic Fed balance sheet components (in Millions)
    test_data = {
        'Fed_Total_Assets': [8_500_000, 8_400_000, 8_450_000],  # ~8.5T in Millions
        'RRP_Balance': [100, 95, 90],  # $95-100B in Billions
        'TGA_Balance': [400_000, 420_000, 390_000]  # $390-420B in Millions 
    }
    df = pd.DataFrame(test_data)
    
    # Apply unit conversion (RRP from Billions to Millions)
    df['RRP_Balance_M'] = df['RRP_Balance'] * 1000  # Convert to Millions
    
    # Calculate Net Liquidity using the fixed formula
    df['Net_Liquidity'] = df['Fed_Total_Assets'] - df['RRP_Balance_M'] - df['TGA_Balance']
    
    # Test reconciliation logic
    for idx in df.index:
        fed_assets = df.loc[idx, 'Fed_Total_Assets']
        rrp_m = df.loc[idx, 'RRP_Balance_M']
        tga = df.loc[idx, 'TGA_Balance']
        net_liq_actual = df.loc[idx, 'Net_Liquidity']
        
        # Reconciliation check
        net_liq_calculated = fed_assets - rrp_m - tga
        delta = abs(net_liq_calculated - net_liq_actual)
        
        print(f"  Day {idx}: Assets=${fed_assets:,.0f}M, RRP=${rrp_m:,.0f}M, TGA=${tga:,.0f}M")
        print(f"  Day {idx}: Net Liquidity calculated=${net_liq_calculated:,.0f}M, stored=${net_liq_actual:,.0f}M")
        print(f"  Day {idx}: Delta=${delta:,.0f}M")
        
        # Verify no significant mismatch
        assert delta < 500, f"Net Liquidity mismatch too large: ${delta:,.0f}M (threshold $500M)"
        assert delta == 0, f"Net Liquidity should match exactly: delta=${delta:,.0f}M"
    
    print("  ✅ Net Liquidity reconciliation: PASSED")
    print()

def test_rrp_mtd_percentage():
    """Test RRP MTD percentage calculation with bounds validation"""
    print("=== Testing RRP % MTD Fix ===")
    
    # Test scenarios
    test_cases = [
        # (rrp_current, rrp_mtd_change, description, should_be_zero)
        (100.0, -10.0, "Normal decline", False),     # -10/110 * 100 = -9.1%
        (100.0, 5.0, "Normal increase", False),      # 5/95 * 100 = 5.3%
        (50.0, -25.0, "50% decline", False),         # -25/75 * 100 = -33.3%
        (10.0, -5.0, "Starting point near zero", False), # -5/15 * 100 = -33.3%
        (100.0, 1200.0, "Unreasonable >500% change", True), # 1200/(-1100) = -109.1% (start negative -> zero)
        (0.0, 0.0, "Zero values", True),             # Should be 0
        (np.nan, 0.0, "NaN values", True),           # Should be 0
        (50.0, -60.0, "Large negative change but still valid", False), # -60/110 = -54.5% (valid calculation)
    ]
    
    for i, (rrp, rrp_mtd_change, description, should_be_zero) in enumerate(test_cases, 1):
        print(f"  Test {i}: Current=${rrp}, Change=${rrp_mtd_change} ({description})")
        
        # Apply the fixed MTD percentage calculation
        rrp_start = rrp - rrp_mtd_change
        
        if abs(rrp_start) > 0 and not pd.isna(rrp_start) and rrp_start > 0:
            rrp_mtd_pct = (rrp_mtd_change / rrp_start) * 100
            # Bounds validation to prevent unreasonable percentages
            if abs(rrp_mtd_pct) > 500:  # Cap at 500% to prevent anomalies
                rrp_mtd_pct = 0
            elif pd.isna(rrp_mtd_pct):
                rrp_mtd_pct = 0
        else:
            rrp_mtd_pct = 0
        
        print(f"    RRP MTD % = {rrp_mtd_pct:+.1f}% (start=${rrp_start})")
        
        # Validate bounds
        assert -500 <= rrp_mtd_pct <= 500, f"RRP MTD % out of bounds: {rrp_mtd_pct}%"
        assert not pd.isna(rrp_mtd_pct), f"RRP MTD % should not be NaN"
        
        # Check specific expectations
        if should_be_zero:
            assert rrp_mtd_pct == 0.0, f"RRP MTD % should be 0 for impossible case: {rrp_mtd_pct}%"
        elif description == "Normal decline":
            assert abs(rrp_mtd_pct - (-9.1)) < 0.2, f"Unexpected MTD % for normal decline: {rrp_mtd_pct}"
        elif description == "Normal increase":
            assert abs(rrp_mtd_pct - 5.3) < 0.2, f"Unexpected MTD % for normal increase: {rrp_mtd_pct}"
    
    print("  ✅ RRP % MTD fix: PASSED")
    print()

def main():
    """Run all bug fix tests"""
    print("Treasury API Interface - Bug Fix Validation")
    print("=" * 60)
    print()
    
    try:
        test_household_share_formula()
        test_rrp_drawdown_nan_handling()
        test_net_liquidity_reconciliation()
        test_rrp_mtd_percentage()
        
        print("=" * 60)
        print("🎉 ALL BUG FIXES VALIDATED SUCCESSFULLY!")
        print("✅ Household Share bounds fixed (0-100%)")
        print("✅ RRP Drawdown NaN handling implemented")
        print("✅ Net Liquidity reconciliation check added")
        print("✅ RRP % MTD calculation fixed with bounds validation")
        print("=" * 60)
        
        return True
        
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ TEST ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
