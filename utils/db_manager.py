import duckdb
import pandas as pd
import os
from datetime import datetime

class TimeSeriesDB:
    def __init__(self, db_path="database/treasury_data.duckdb"):
        """
        Initialize the DuckDB connection.
        """
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = duckdb.connect(db_path)
        print(f"🔌 Connected to DuckDB at {db_path}")

    def close(self):
        """Close the connection."""
        self.conn.close()

    def _table_exists(self, table_name):
        """Check if a table exists."""
        result = self.conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", 
            [table_name]
        ).fetchone()
        return result[0] > 0

    def initialize_table_from_df(self, df, table_name, key_col='record_date'):
        """
        Create a table based on the DataFrame schema if it doesn't exist.
        """
        if self._table_exists(table_name):
            return

        print(f"📝 Creating table '{table_name}'...")
        # DuckDB can infer schema from DataFrame
        self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df LIMIT 0")
        
        # Create a unique index on the key column to support upserts/deduplication
        # Note: DuckDB indexes are primarily for performance, constraints are limited.
        # We will handle deduplication in the upsert logic.
        print(f"✅ Table '{table_name}' created.")

    def upsert_data(self, df, table_name, key_col='record_date'):
        """
        Insert new data, updating existing records if they match the key_col.
        Strategy: Delete existing records for the dates in df, then insert new ones.
        This handles both updates and new inserts cleanly for time-series batches.
        """
        if df.empty:
            print("⚠️ No data to upsert.")
            return

        # Ensure table exists
        self.initialize_table_from_df(df, table_name, key_col)

        # Ensure key_col is in the correct format (datetime)
        if key_col in df.columns:
            # If it's the index, reset it
            pass 
        elif df.index.name == key_col:
            df = df.reset_index()
        
        # Standardize date format to match DB (usually timestamp)
        # DuckDB handles pandas timestamps well.

        try:
            # 1. Identify keys to be updated
            # We use a temporary table for the new batch
            self.conn.register('df_view', df)
            
            # 2. Delete existing rows that overlap with the new batch
            # This implements "overwrite for these specific dates"
            delete_query = f"""
            DELETE FROM {table_name} 
            WHERE {key_col} IN (SELECT {key_col} FROM df_view)
            """
            self.conn.execute(delete_query)
            
            # 3. Insert the new records
            insert_query = f"INSERT INTO {table_name} SELECT * FROM df_view"
            self.conn.execute(insert_query)
            
            print(f"💾 Upserted {len(df)} records into '{table_name}'")
            
        except Exception as e:
            print(f"❌ Error during upsert: {e}")
            raise
        finally:
            self.conn.unregister('df_view')

    def get_latest_date(self, table_name, key_col='record_date'):
        """
        Get the maximum date currently in the table.
        Returns None if table doesn't exist or is empty.
        """
        if not self._table_exists(table_name):
            return None
        
        result = self.conn.execute(f"SELECT MAX({key_col}) FROM {table_name}").fetchone()
        return result[0] if result else None

    def get_all_data(self, table_name):
        """
        Retrieve all data from a table as a DataFrame.
        """
        if not self._table_exists(table_name):
            print(f"⚠️ Table '{table_name}' does not exist.")
            return pd.DataFrame()
        
        return self.conn.execute(f"SELECT * FROM {table_name} ORDER BY 1").df()

    def query(self, sql):
        """
        Execute a raw SQL query and return a DataFrame.
        """
        return self.conn.execute(sql).df()
