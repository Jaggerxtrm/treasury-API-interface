import duckdb
import pandas as pd
import os

DB_PATH = "database/treasury_data.duckdb"

def verify_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found: {DB_PATH}")
        return

    conn = duckdb.connect(DB_PATH)
    print(f"🔌 Connected to {DB_PATH}")
    
    # List tables
    tables = conn.execute("SHOW TABLES").fetchall()
    print(f"📊 Tables found: {[t[0] for t in tables]}")
    
    for table in tables:
        table_name = table[0]
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"\n📋 Table: {table_name}")
        print(f"   Rows: {count}")
        
        # Show schema
        print("   Schema:")
        schema = conn.execute(f"DESCRIBE {table_name}").fetchall()
        for col in schema:
            print(f"     - {col[0]} ({col[1]})")
            
        # Show sample
        print("   Sample Data (Last 3 rows):")
        df = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").df()
        print(df.to_string())

    conn.close()

if __name__ == "__main__":
    verify_db()
