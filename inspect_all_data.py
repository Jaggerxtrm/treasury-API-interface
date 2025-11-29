from generate_desk_report import load_all_data
import pandas as pd

# Set options to display all rows
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

print("Loading data...")
try:
    fiscal_df, fed_df, ofr_df, metadata = load_all_data()

    print("\n" + "="*50)
    print("FISCAL DATAFRAME")
    print("="*50)
    print(f"Shape: {fiscal_df.shape}")
    print(fiscal_df.dtypes)
    print("\nSample (last 1 row):")
    print(fiscal_df.tail(1).T)

    print("\n" + "="*50)
    print("FED DATAFRAME")
    print("="*50)
    print(f"Shape: {fed_df.shape}")
    print(fed_df.dtypes)
    print("\nSample (last 1 row):")
    print(fed_df.tail(1).T)

    print("\n" + "="*50)
    print("OFR DATAFRAME")
    print("="*50)
    print(f"Shape: {ofr_df.shape}")
    print(ofr_df.dtypes)
    print("\nSample (last 1 row):")
    print(ofr_df.tail(1).T)

except Exception as e:
    print(f"Error loading data: {e}")
