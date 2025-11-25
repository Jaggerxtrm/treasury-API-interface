import requests
import pandas as pd
from datetime import datetime, timedelta
import sys

# NY Fed Markets API
NYFED_API_BASE = "https://markets.newyorkfed.org/api"
START_DATE = "2022-01-01"

# Endpoint Mapping (based on https://markets.newyorkfed.org/static/docs/markets-api.yml)
ENDPOINTS = {
    "repo": "/rp/results/search.json",  # Repo and Reverse Repo operations
    "soma": "/soma/summary.json",
    "pd_stats": "/pd/list.json",  # Primary Dealer Statistics
    "agency_mbs": "/ambs/all/results/search.json",
}

def fetch_nyfed_data(endpoint, params=None):
    """
    Generic fetcher for NY Fed Markets API.
    """
    url = f"{NYFED_API_BASE}{endpoint}"

    if params is None:
        params = {}

    print(f"Fetching NY Fed data from {endpoint}...")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Most endpoints return {"repo": {"operations": [...]}} or similar structure
        # We'll handle each endpoint's structure specifically
        return data

    except Exception as e:
        print(f"Error fetching NY Fed data from {endpoint}: {e}")
        return None

def fetch_repo_operations(start_date=START_DATE):
    """
    Fetches daily repo operations (overnight and term).
    Returns: DataFrame with operation dates, amounts, rates, submissions.
    """
    params = {
        "startDate": start_date,
        "sort": "postDt:1"  # Sort ascending by date
    }

    data = fetch_nyfed_data(ENDPOINTS["repo"], params)

    if not data or "repo" not in data:
        print("No repo operations data found")
        return pd.DataFrame()

    operations = data["repo"].get("operations", [])

    if not operations:
        print("No repo operations found")
        return pd.DataFrame()

    df = pd.DataFrame(operations)

    # Parse date
    if 'operationDate' in df.columns:
        df['operation_date'] = pd.to_datetime(df['operationDate'])
        df.set_index('operation_date', inplace=True)

    # Clean numeric columns
    numeric_cols = ['totalAmtAccepted', 'totalAmtSubmitted', 'weightedAvgRate', 'highRate', 'lowRate']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"Fetched {len(df)} repo operations")
    return df

def fetch_reverse_repo_operations(start_date=START_DATE):
    """
    Fetches daily reverse repo operations (overnight RRP).
    """
    params = {
        "startDate": start_date
    }

    data = fetch_nyfed_data(ENDPOINTS["repo"], params)

    if not data or "repo" not in data:
        print("No reverse repo data found")
        return pd.DataFrame()

    # Filter for reverse repo operations
    operations = data["repo"].get("operations", [])
    reverse_repo_ops = [op for op in operations if op.get('operationType') == 'Reverse Repo']

    if not reverse_repo_ops:
        print("No reverse repo operations found")
        return pd.DataFrame()

    df = pd.DataFrame(reverse_repo_ops)

    # Parse date
    if 'operationDate' in df.columns:
        df['operation_date'] = pd.to_datetime(df['operationDate'])
        df.set_index('operation_date', inplace=True)

    # Clean numeric columns
    numeric_cols = ['totalAmtAccepted', 'totalAmtSubmitted']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"Fetched {len(df)} reverse repo operations")
    return df

def fetch_soma_holdings():
    """
    Fetches SOMA (System Open Market Account) holdings summary.
    """
    data = fetch_nyfed_data(ENDPOINTS["soma"])

    if not data or "soma" not in data:
        print("No SOMA data found")
        return pd.DataFrame()

    # SOMA data structure varies - typically returns holdings summaries
    # This endpoint may return current holdings, not historical time series
    # For historical SOMA, use FRED TREAST, WSHOMCB, etc.

    print("SOMA data fetched (current holdings summary)")
    return pd.DataFrame([data["soma"]])  # Single row with current state

def fetch_primary_dealer_stats():
    """
    Fetches Primary Dealer statistics (weekly).
    This endpoint lists available reports; we need to fetch specific report data.
    """
    data = fetch_nyfed_data(ENDPOINTS["pd_stats"])

    if not data or "pd" not in data:
        print("No Primary Dealer data found")
        return pd.DataFrame()

    # The list endpoint returns available reports
    # To get actual data, we need to call specific report endpoints
    # This is more complex and may require parsing report links

    reports = data["pd"].get("reports", [])

    if not reports:
        print("No Primary Dealer reports found")
        return pd.DataFrame()

    print(f"Found {len(reports)} Primary Dealer reports (detailed fetching not implemented)")

    # For now, return the list of available reports
    # Full implementation would fetch each report's data
    return pd.DataFrame(reports)

# Settlement Fails endpoint is not available in the official NY Fed Markets API
# def fetch_settlement_fails(start_date=START_DATE):
#     """
#     Fetches Treasury settlement fails data.
#     NOTE: This endpoint is not available in the official Markets API
#     """
#     print("Settlement fails data is not available via the NY Fed Markets API")
#     return pd.DataFrame()


def fetch_agency_mbs_operations(start_date=START_DATE):
    """
    Fetches Agency MBS operations data.
    """
    params = {
        "startDate": start_date,
        "sort": "postDt:1"
    }

    data = fetch_nyfed_data(ENDPOINTS["agency_mbs"], params)

    if not data or "ambs" not in data:
        print("No Agency MBS data found")
        return pd.DataFrame()

    operations = data["ambs"].get("operations", [])

    if not operations:
        print("No Agency MBS operations found")
        return pd.DataFrame()

    df = pd.DataFrame(operations)

    # Parse date
    if 'operationDate' in df.columns:
        df['operation_date'] = pd.to_datetime(df['operationDate'])
        df.set_index('operation_date', inplace=True)

    print(f"Fetched {len(df)} Agency MBS operations")
    return df

def calculate_repo_metrics(df_repo):
    """
    Calculates derived metrics for repo operations.
    """
    if df_repo.empty:
        return df_repo

    # Submission/Acceptance Ratio (stress indicator)
    if 'totalAmtSubmitted' in df_repo.columns and 'totalAmtAccepted' in df_repo.columns:
        df_repo['submission_ratio'] = df_repo['totalAmtSubmitted'] / df_repo['totalAmtAccepted'].replace(0, pd.NA)

    # Rolling averages
    if 'totalAmtAccepted' in df_repo.columns:
        df_repo['MA5_Repo_Accepted'] = df_repo['totalAmtAccepted'].rolling(window=5).mean()
        df_repo['MA20_Repo_Accepted'] = df_repo['totalAmtAccepted'].rolling(window=20).mean()

    # Rate spreads (if multiple operations on same day, already aggregated)
    if 'weightedAvgRate' in df_repo.columns:
        df_repo['Repo_Rate_Vol'] = df_repo['weightedAvgRate'].rolling(window=5).std()

    return df_repo

def calculate_fails_metrics(df_fails):
    """
    Calculates derived metrics for settlement fails.
    """
    if df_fails.empty:
        return df_fails

    # Rolling averages (fails are a stress signal)
    if 'totalFails' in df_fails.columns:
        df_fails['MA20_Fails'] = df_fails['totalFails'].rolling(window=20).mean()
        df_fails['Fails_Change'] = df_fails['totalFails'].diff()

    return df_fails

def generate_report(df_repo, df_rrp, df_fails):
    """
    Generates a consolidated report.
    """
    print("\n" + "="*50)
    print("NY FED OPERATIONS REPORT")
    print("="*50)

    # Repo Operations
    if not df_repo.empty:
        print("\n--- REPO OPERATIONS (Liquidity Injection) ---")
        last_repo = df_repo.iloc[-1]
        last_date = df_repo.index[-1].strftime('%Y-%m-%d')

        print(f"Last Date: {last_date}")
        if 'totalAmtAccepted' in last_repo:
            print(f"Amount Accepted:      ${last_repo['totalAmtAccepted']:,.0f} M")
        if 'totalAmtSubmitted' in last_repo:
            print(f"Amount Submitted:     ${last_repo['totalAmtSubmitted']:,.0f} M")
        if 'submission_ratio' in last_repo:
            print(f"Submission Ratio:     {last_repo['submission_ratio']:.2f}x")
        if 'weightedAvgRate' in last_repo:
            print(f"Weighted Avg Rate:    {last_repo['weightedAvgRate']:.2f}%")

        print("\nRecent Trend (Last 5 Days):")
        cols = ['totalAmtAccepted', 'submission_ratio', 'weightedAvgRate']
        cols = [c for c in cols if c in df_repo.columns]
        print(df_repo[cols].tail(5).to_string(float_format="{:,.2f}".format))

    # Reverse Repo
    if not df_rrp.empty:
        print("\n--- REVERSE REPO (Liquidity Drain) ---")
        last_rrp = df_rrp.iloc[-1]
        last_date = df_rrp.index[-1].strftime('%Y-%m-%d')

        print(f"Last Date: {last_date}")
        if 'totalAmtAccepted' in last_rrp:
            print(f"RRP Amount:           ${last_rrp['totalAmtAccepted']:,.0f} M")
        if 'numOfCounterparties' in last_rrp:
            print(f"Counterparties:       {last_rrp['numOfCounterparties']:.0f}")

    # Settlement Fails
    if not df_fails.empty:
        print("\n--- SETTLEMENT FAILS (Stress Indicator) ---")
        last_fails = df_fails.iloc[-1]
        last_date = df_fails.index[-1].strftime('%Y-%m-%d')

        print(f"Last Date: {last_date}")
        if 'totalFails' in last_fails:
            print(f"Total Fails:          ${last_fails['totalFails']:,.0f} M")
        if 'MA20_Fails' in last_fails:
            print(f"MA20 Fails:           ${last_fails['MA20_Fails']:,.0f} M")
        if 'Fails_Change' in last_fails:
            print(f"Daily Change:         ${last_fails['Fails_Change']:,.0f} M")

    # Export
    if not df_repo.empty:
        df_repo.to_csv("outputs/fed/nyfed_repo_ops.csv")
        print("Repo operations exported to outputs/fed/nyfed_repo_ops.csv")

    if not df_rrp.empty:
        df_rrp.to_csv("outputs/fed/nyfed_rrp_ops.csv")
        print("RRP operations exported to outputs/fed/nyfed_rrp_ops.csv")

    if not df_fails.empty:
        df_fails.to_csv("nyfed_settlement_fails.csv")
        print("Settlement fails exported to nyfed_settlement_fails.csv")

def main():
    print("Starting NY Fed Operations Monitor...")

    # Fetch all data
    df_repo = fetch_repo_operations()
    df_rrp = fetch_reverse_repo_operations()
    # df_fails = fetch_settlement_fails()  # Not available in API
    df_fails = pd.DataFrame()  # Empty placeholder
    df_mbs = fetch_agency_mbs_operations()

    # Calculate metrics
    if not df_repo.empty:
        df_repo = calculate_repo_metrics(df_repo)

    # if not df_fails.empty:
    #     df_fails = calculate_fails_metrics(df_fails)

    # Generate report
    generate_report(df_repo, df_rrp, df_fails)

    print("\nNY Fed Operations analysis complete.")

if __name__ == "__main__":
    main()
