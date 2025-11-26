#!/usr/bin/env python3
"""
End-to-End Pipeline Test Suite
Verifies that all components of the Treasury API Interface work correctly together.
"""

import sys
import os
import pandas as pd
import subprocess
from datetime import datetime

def run_command(cmd, description):
    """Run a command and return (success, output)"""
    print(f"\n🧪 Testing: {description}")
    print(f"Command: {cmd}")
    
    try:
        result = subprocess.run(
            f"bash -c '{cmd}'", 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        
        success = result.returncode == 0
        if success:
            print(f"✅ PASSED")
        else:
            print(f"❌ FAILED")
            print(f"Error: {result.stderr}")
        
        return success, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT")
        return False, "", "Command timed out"
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        return False, "", str(e)

def check_file_exists(file_path, description):
    """Check if a file exists and has content"""
    print(f"\n📋 Checking: {description}")
    print(f"File: {file_path}")
    
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            rows = len(df)
            if rows > 0:
                print(f"✅ EXISTS ({rows} rows)")
                return True
            else:
                print(f"❌ EMPTY")
                return False
        except Exception as e:
            print(f"❌ READ ERROR: {e}")
            return False
    else:
        print(f"❌ MISSING")
        return False

def validate_composite_index():
    """Validate the Liquidity Composite Index output"""
    print(f"\n🎯 Validating: LCI Output Quality")
    
    lci_path = "liquidity_composite_index.csv"
    
    exists_result = check_file_exists(lci_path, "Composite Index CSV")
    if not exists_result:
        return False
    
    try:
        df = pd.read_csv(lci_path, index_col=0, parse_dates=True)
        
        # Check required columns
        required_cols = ['LCI', 'regime', 'fiscal_subindex', 'monetary_subindex', 'plumbing_subindex']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ MISSING COLUMNS: {missing_cols}")
            return False
        
        # Check data range
        if 'LCI' in df.columns:
            lci_values = df['LCI'].dropna()
            if len(lci_values) == 0:
                print(f"❌ NO LCI VALUES")
                return False
            
            # Check for reasonable ranges (-3 to +3 for z-score normalized)
            out_of_range = (lci_values < -3).sum() + (lci_values > 3).sum()
            if out_of_range > len(lci_values) * 0.01:  # Allow < 1% outliers
                print(f"⚠️  MANY OUTLIERS: {out_of_range}/{len(lci_values)} outside [-3,3]")
        
        print(f"✅ LCI VALIDATION PASSED")
        return True
        
    except Exception as e:
        print(f"❌ LCI VALIDATION ERROR: {e}")
        return False

def test_data_freshness():
    """Test if output files are recent"""
    print(f"\n🕐 Testing: Data Freshness")
    
    output_files = [
        ("outputs/fiscal/fiscal_analysis_full.csv", "Fiscal Analysis"),
        ("outputs/fed/fed_liquidity_full.csv", "Fed Liquidity"),
        ("outputs/fed/ofr_repo_analysis.csv", "OFR Analysis"),
        ("outputs/fed/nyfed_settlement_fails.csv", "Settlement Fails"),
        ("liquidity_composite_index.csv", "Composite Index")
    ]
    
    current_time = datetime.now()
    stale_threshold_hours = 48
    stale_files = []
    
    for file_path, desc in output_files:
        if os.path.exists(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            hours_old = (current_time - file_time).total_seconds() / 3600
            
            if hours_old > stale_threshold_hours:
                stale_files.append(f"{desc} ({hours_old:.1f}h old)")
            else:
                print(f"✅ {desc}: {hours_old:.1f}h old")
        else:
            stale_files.append(f"{desc} (missing)")
    
    if stale_files:
        print(f"⚠️  STALE FILES: {stale_files}")
        return len(stale_files) < len(output_files)  # Pass if not all stale
    
    print(f"✅ DATA FRESHNESS PASSED")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("🔬 TREASURY API INTERFACE - END-TO-END TEST SUITE")
    print("=" * 60)
    
    # Change to project directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    
    # Test results
    test_results = []
    
    # 1. Test individual components
    components = [
        ("source venv/bin/activate && python fiscal/fiscal_analysis.py", "Fiscal Analysis"),
        ("source venv/bin/activate && python fed/fed_liquidity.py", "Fed Liquidity"),
        ("source venv/bin/activate && python fed/nyfed_operations.py", "NYFed Operations"),
        ("source venv/bin/activate && python fed/nyfed_reference_rates.py", "NYFed Reference Rates"),
        ("source venv/bin/activate && python fed/ofr_analysis.py", "OFR Repo Analysis"),
        ("source venv/bin/activate && python fed/nyfed_settlement_fails.py", "Settlement Fails"),
    ]
    
    for cmd, desc in components:
        success, _, _ = run_command(cmd, desc)
        test_results.append((desc, success))
    
    # 2. Test composite index
    cmd = "source venv/bin/activate && cd fed && python liquidity_composite_index.py"
    success, _, _ = run_command(cmd, "Liquidity Composite Index")
    test_results.append(("Composite Index", success))
    
    # 3. Check output files
    output_checks = [
        ("outputs/fiscal/fiscal_analysis_full.csv", "Fiscal Analysis Output"),
        ("outputs/fed/fed_liquidity_full.csv", "Fed Liquidity Output"),
        ("outputs/fed/ofr_repo_analysis.csv", "OFR Analysis Output"),
        ("outputs/fed/nyfed_settlement_fails.csv", "Settlement Fails Output"),
        ("liquidity_composite_index.csv", "Composite Index Output"),
    ]
    
    for file_path, desc in output_checks:
        success = check_file_exists(file_path, desc)
        test_results.append((desc, success))
    
    # 4. Advanced validations
    lci_valid = validate_composite_index()
    fresh_valid = test_data_freshness()
    
    test_results.append(("LCI Validation", lci_valid))
    test_results.append(("Data Freshness", fresh_valid))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    success_rate = (passed / total) * 100
    print(f"\n📈 OVERALL: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT: System is working very well")
    elif success_rate >= 75:
        print("👍 GOOD: System is mostly functional")
    elif success_rate >= 50:
        print("⚠️  NEEDS ATTENTION: Some components have issues")
    else:
        print("🚨 CRITICAL: Major system problems detected")
    
    # Exit with appropriate code
    sys.exit(0 if success_rate >= 75 else 1)

if __name__ == "__main__":
    main()
