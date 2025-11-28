#!/usr/bin/env python3
"""
Test script to verify NY Fed RRP data availability
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fed'))

from utils.api_client import NYFedClient
import pandas as pd

def test_nyfed_rrp_fetch():
    """Test fetching RRP data from NY Fed API"""
    print("=" * 60)
    print("Testing NY Fed RRP Data Fetch")
    print("=" * 60)

    client = NYFedClient()

    # Fetch reverse repo operations from the last 30 days
    print("\n1. Fetching RRP operations from NY Fed API...")
    df_rrp = client.fetch_repo_operations(
        start_date="2025-10-01",
        operation_type="Reverse Repo"
    )

    if df_rrp.empty:
        print("❌ FAILED: No RRP data returned")
        return False

    print(f"✓ Success! Fetched {len(df_rrp)} RRP operations")

    # Show data structure
    print("\n2. Data Structure:")
    print(f"   Columns: {list(df_rrp.columns)[:10]}...")
    print(f"   Date range: {df_rrp.index.min()} to {df_rrp.index.max()}")

    # Check for required fields
    print("\n3. Checking required fields...")
    required_fields = ['totalAmtAccepted', 'totalAmtSubmitted']
    for field in required_fields:
        if field in df_rrp.columns:
            print(f"   ✓ {field}: present")
        else:
            print(f"   ❌ {field}: MISSING")
            return False

    # Show recent data
    print("\n4. Recent RRP data (last 5 days):")
    print(df_rrp[['totalAmtAccepted', 'totalAmtSubmitted']].tail(5))

    # Check data freshness
    print("\n5. Data Freshness Check:")
    latest_date = df_rrp.index.max()
    today = pd.Timestamp.today()
    days_old = (today - latest_date).days
    print(f"   Latest data: {latest_date.strftime('%Y-%m-%d')}")
    print(f"   Days old: {days_old}")
    if days_old <= 3:
        print(f"   ✓ Data is fresh (within 3 days)")
    else:
        print(f"   ⚠️  Data is {days_old} days old")

    print("\n" + "=" * 60)
    print("✅ NY Fed RRP API Test: PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_nyfed_rrp_fetch()
    sys.exit(0 if success else 1)
