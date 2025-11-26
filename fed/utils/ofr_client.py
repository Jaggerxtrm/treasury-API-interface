"""
OFR Short-term Funding Monitor API Client
"""

import requests
import pandas as pd
from datetime import datetime
import time

class OFRClient:
    BASE_URL = "https://data.financialresearch.gov/v1"
    
    def __init__(self):
        # OFR API is public, no auth required
        pass
    
    def fetch_repo_volumes(self, start_date, end_date=None):
        """
        Fetches disaggregated repo volumes using NY Fed Reference Rates as proxies.
        
        Proxies:
        - Total Repo ~= SOFR Volume
        - Tri-Party ~= TGCR Volume
        - GCF (MBS/Agency) ~= BGCR Volume - TGCR Volume
        - DVP (Treasury) ~= SOFR Volume - BGCR Volume
        """
        if end_date is None:
            end_date = datetime.today().strftime('%Y-%m-%d')
            
        print(f"Fetching OFR Repo data (FNYR Proxies) from {start_date} to {end_date}...")
        
        # Mnemonics for Reference Rates (Volume and Rate)
        mnemonics = [
            # SOFR (Secured Overnight Financing Rate) - Broadest measure (Tri-Party + GCF + DVP)
            "FNYR-SOFR_UV-A", # Underlying Volume
            "FNYR-SOFR-A",    # Rate
            
            # BGCR (Broad General Collateral Rate) - Tri-Party + GCF
            "FNYR-BGCR_UV-A", # Underlying Volume
            "FNYR-BGCR-A",    # Rate
            
            # TGCR (Tri-Party General Collateral Rate) - Tri-Party only
            "FNYR-TGCR_UV-A", # Underlying Volume
            "FNYR-TGCR-A",    # Rate
        ]
        
        # Fetch data
        dfs = []
        for mnemonic in mnemonics:
            df = self._fetch_series(mnemonic, start_date, end_date)
            if not df.empty:
                dfs.append(df)
                
        if not dfs:
            print("No repo data fetched.")
            return pd.DataFrame()
            
        # Combine all
        full_df = pd.concat(dfs, ignore_index=True)
        
        return full_df
    
    def _fetch_series(self, mnemonic, start_date, end_date):
        """Helper to fetch a single series."""
        endpoint = f"{self.BASE_URL}/series/timeseries"
        
        params = {
            'mnemonic': mnemonic,
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            response = requests.get(endpoint, params=params)
            if response.status_code != 200:
                return pd.DataFrame()
                
            data = response.json()
            
            # OFR timeseries response format: [[date, value], ...]
            if not data or not isinstance(data, list):
                if isinstance(data, dict) and 'timeseries' in data:
                     pass # Should not happen with this endpoint usually
                elif isinstance(data, dict) and mnemonic in data:
                     data = data[mnemonic]
                
            if not data or not isinstance(data, list) or len(data) == 0:
                return pd.DataFrame()
                
            # Parse
            records = []
            meta = self._parse_mnemonic(mnemonic)
            
            for point in data:
                if len(point) >= 2:
                    records.append({
                        'date': point[0],
                        'value': point[1],
                        'mnemonic': mnemonic,
                        **meta
                    })
            
            df = pd.DataFrame(records)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                
            return df
            
        except Exception as e:
            print(f"Error fetching {mnemonic}: {e}")
            return pd.DataFrame()

    def _parse_mnemonic(self, mnemonic):
        """
        Parses FNYR mnemonic to extract metadata.
        """
        meta = {}
        
        # Determine Type
        if 'SOFR' in mnemonic:
            meta['series_type'] = 'SOFR'
        elif 'BGCR' in mnemonic:
            meta['series_type'] = 'BGCR'
        elif 'TGCR' in mnemonic:
            meta['series_type'] = 'TGCR'
        else:
            meta['series_type'] = 'Unknown'
            
        # Determine Data Type
        if '_UV' in mnemonic:
            meta['data_type'] = 'volume'
        else:
            meta['data_type'] = 'rate'
            
        return meta
