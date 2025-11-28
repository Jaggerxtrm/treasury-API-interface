import sys
import os
import pandas as pd

# Add module paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fiscal'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fed'))

from generate_desk_report import load_all_data

def inspect_data():
    try:
        fiscal_df, fed_df, ofr_df, metadata = load_all_data()
        
        print("\n--- FISCAL DATA COLUMNS ---")
        print(fiscal_df.columns.tolist())
        print("\n--- FISCAL DATA SAMPLE ---")
        print(fiscal_df.tail(3))
        
        print("\n--- FED DATA COLUMNS ---")
        print(fed_df.columns.tolist())
        
        print("\n--- OFR DATA COLUMNS ---")
        print(ofr_df.columns.tolist())
        
    except Exception as e:
        print(f"Error loading data: {e}")

if __name__ == "__main__":
    inspect_data()
