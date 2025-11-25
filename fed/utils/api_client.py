"""
API Client Utilities
Unified API clients for FRED and NY Fed Markets API.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import sys
import os

# Add parent (fed) directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    FRED_API_KEY,
    FRED_BASE_URL,
    NYFED_BASE_URL,
    DEFAULT_START_DATE
)


class FREDClient:
    """
    Client for Federal Reserve Economic Data (FRED) API.
    """
    
    def __init__(self, api_key: str = FRED_API_KEY):
        self.api_key = api_key
        self.base_url = FRED_BASE_URL
    
    def fetch_series(
        self,
        series_id: str,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None
    ) -> tuple[pd.Series, Optional[str]]:
        """
        Fetch a single series from FRED API.
        
        Args:
            series_id: FRED series identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
        
        Returns:
            Tuple of (pandas Series with date index, last_update_date)
        """
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": start_date,
            "sort_order": "asc"
        }
        
        if end_date:
            params["observation_end"] = end_date
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "observations" not in data:
                print(f"No observations found for {series_id}")
                return pd.Series(dtype=float), None
            
            observations = data["observations"]
            
            if not observations:
                return pd.Series(dtype=float), None
            
            # Convert to DataFrame
            df = pd.DataFrame(observations)
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            
            # Set index and create series
            df.set_index("date", inplace=True)
            series = df["value"]
            
            # Drop NaN values to prevent propagation in outer joins
            series = series.dropna()
            
            # Get last update date
            last_update = observations[-1].get("date")
            
            return series, last_update
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {series_id}: {e}")
            return pd.Series(dtype=float), None
        except Exception as e:
            print(f"Unexpected error fetching {series_id}: {e}")
            return pd.Series(dtype=float), None
    
    def fetch_multiple_series(
        self,
        series_map: Dict[str, str],
        start_date: str = DEFAULT_START_DATE
    ) -> tuple[pd.DataFrame, Dict[str, str]]:
        """
        Fetch multiple series and merge into single DataFrame.
        
        Args:
            series_map: Dict mapping FRED IDs to column names
            start_date: Start date for all series
        
        Returns:
            Tuple of (merged DataFrame, metadata dict with last updates)
        """
        all_series = {}
        metadata = {}
        
        for series_id, col_name in series_map.items():
            print(f"Fetching {series_id} ({col_name})...")
            series, last_update = self.fetch_series(series_id, start_date)
            
            if not series.empty:
                all_series[col_name] = series
                metadata[series_id] = {
                    "column_name": col_name,
                    "last_update": last_update
                }
        
        if not all_series:
            return pd.DataFrame(), metadata
        
        # Merge all series
        df = pd.concat(all_series, axis=1, join="outer").sort_index()
        
        return df, metadata


class NYFedClient:
    """
    Client for New York Fed Markets API.
    """
    
    def __init__(self):
        self.base_url = NYFED_BASE_URL
    
    def fetch_endpoint(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generic fetch from NY Fed Markets API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
        
        Returns:
            JSON response as dict, or None on error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {endpoint}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching {endpoint}: {e}")
            return None
    
    def fetch_repo_operations(
        self,
        start_date: str = DEFAULT_START_DATE,
        operation_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch repo operations data.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            operation_type: Filter by type ('Repo' or 'Reverse Repo')
        
        Returns:
            DataFrame with repo operations
        """
        params = {"startDate": start_date}
        
        data = self.fetch_endpoint("/rp/results/search.json", params)
        
        if not data or "repo" not in data:
            return pd.DataFrame()
        
        operations = data["repo"].get("operations", [])
        
        if not operations:
            return pd.DataFrame()
        
        # Filter by operation type if specified
        if operation_type:
            operations = [
                op for op in operations
                if op.get("operationType") == operation_type
            ]
        
        df = pd.DataFrame(operations)
        
        # Parse dates
        if "operationDate" in df.columns:
            df["date"] = pd.to_datetime(df["operationDate"])
            df.set_index("date", inplace=True)
        
        return df
    
    def fetch_reference_rate(
        self,
        rate_type: str,
        num_records: int = 250
    ) -> pd.DataFrame:
        """
        Fetch reference rate data (SOFR, EFFR, etc.).
        
        Args:
            rate_type: One of 'sofr', 'bgcr', 'tgcr', 'effr', 'obfr'
            num_records: Number of records to fetch
        
        Returns:
            DataFrame with rate data
        """
        # Determine category (secured vs unsecured)
        category = "unsecured" if rate_type in ["effr", "obfr"] else "secured"
        
        # Construct URL
        url = f"{self.base_url}/rates/{category}/{rate_type}/search.json"
        
        # Calculate start date
        start_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        params = {"startDate": start_date}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "refRates" not in data:
                return pd.DataFrame()
            
            rates_list = data["refRates"]
            
            if not rates_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(rates_list)
            
            # Parse date
            if "effectiveDate" in df.columns:
                df["date"] = pd.to_datetime(df["effectiveDate"])
                df.set_index("date", inplace=True)
            
            # Extract rate value
            if "percentRate" in df.columns:
                df["rate"] = pd.to_numeric(df["percentRate"], errors="coerce")
            
            return df.sort_index()
            
        except Exception as e:
            print(f"Error fetching {rate_type}: {e}")
            return pd.DataFrame()
