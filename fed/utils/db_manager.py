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
        If table exists but schema doesn't match, recreate it.
        """
        if self._table_exists(table_name):
            # Check if schema matches
            if not self._schema_matches(df, table_name):
                print(f"⚠️  Schema mismatch for '{table_name}', recreating table...")
                self.conn.execute(f"DROP TABLE {table_name}")
            else:
                return

        print(f"📝 Creating table '{table_name}'...")
        # DuckDB can infer schema from DataFrame
        self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df LIMIT 0")
        
        # Create a unique index on the key column to support upserts/deduplication
        # Note: DuckDB indexes are primarily for performance, constraints are limited.
        # We will handle deduplication in the upsert logic.
        print(f"✅ Table '{table_name}' created.")
    
    def _schema_matches(self, df, table_name):
        """
        Check if DataFrame columns match table columns (ignoring order).
        """
        try:
            table_cols = self.conn.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
            ).fetchall()
            table_cols = set(col[0] for col in table_cols)
            df_cols = set(df.columns.tolist())
            return table_cols == df_cols
        except Exception:
            return False

    def upsert_data(self, df, table_name, key_col='record_date', force_recreate=False):
        """
        Insert new data, updating existing records if they match the key_col.
        Strategy: Delete existing records for the dates in df, then insert new ones.
        This handles both updates and new inserts cleanly for time-series batches.
        """
        if df.empty:
            print("⚠️ No data to upsert.")
            return

        # Validate that key_col exists in the DataFrame
        if key_col not in df.columns:
            raise ValueError(f"Key column '{key_col}' not found in DataFrame. Available columns: {df.columns.tolist()}")
        
        # Force recreate if requested
        if force_recreate and self._table_exists(table_name):
            print(f"🔄 Force recreating table '{table_name}'...")
            self.conn.execute(f"DROP TABLE {table_name}")
        
        # Ensure table exists
        self.initialize_table_from_df(df, table_name, key_col)

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
            # If schema mismatch, try recreating the table
            if "Conversion Error" in str(e) or "Type Error" in str(e) or "Binder Error" in str(e):
                print(f"⚠️  Schema mismatch detected, recreating table '{table_name}'...")
                try:
                    self.conn.unregister('df_view')
                except:
                    pass
                # Re-register the DataFrame and recreate table
                self.conn.register('df_new', df)
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df_new")
                self.conn.unregister('df_new')
                print(f"💾 Recreated and inserted {len(df)} records into '{table_name}'")
            else:
                print(f"❌ Error during upsert: {e}")
                raise
        finally:
            try:
                self.conn.unregister('df_view')
            except:
                pass

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
