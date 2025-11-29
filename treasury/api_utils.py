import requests
import pandas as pd
import time

def fetch_paginated_data(url, params, max_pages=None):
    """
    Helper to fetch all pages from an API endpoint.
    """
    print(f"Fetching data from {url} with params {params}...")
    all_data = []
    page_num = 1
    
    while True:
        params['page[number]'] = page_num
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('data'):
                break
                
            all_data.extend(data['data'])
            
            meta = data.get('meta', {})
            total_pages = meta.get('total-pages', 1)
            
            if page_num % 5 == 0 or page_num == total_pages:
                print(f"Fetched page {page_num}/{total_pages} ({len(data['data'])} records)")
            
            if page_num >= total_pages:
                break
            
            if max_pages and page_num >= max_pages:
                print(f"Reached max pages limit ({max_pages})")
                break
                
            page_num += 1
            time.sleep(0.1)  # Be nice to the API
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
            
    return pd.DataFrame(all_data)
