from generate_desk_report import load_all_data
import pandas as pd

try:
    fiscal_df, fed_df, ofr_df, metadata = load_all_data()
    
    print("FISCAL DF Index Name:", fiscal_df.index.name)
    print("FED DF Index Name:", fed_df.index.name)
    print("OFR DF Index Name:", ofr_df.index.name)
    
    print("FISCAL DF Columns:", fiscal_df.columns.tolist())
    
except Exception as e:
    print(e)
