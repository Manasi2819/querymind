import sys
import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

# Add current folder to path to import settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import get_settings
    settings = get_settings()
except ImportError:
    print("Could not load config. Ensure you run this from within the backend directory.")
    sys.exit(1)

# Absolute path to SQLite file
# It's usually in the backend directory where the app is running
SQLITE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "querymind_metadata.db"))
MYSQL_URL = settings.database_url


def clean_data(df, table_name):
    """
    Cleans dataframe data for MySQL compatibility.
    Particularly handles JSON columns stored as strings in SQLite.
    """
    import json
    
    # Handle specific table JSON column parsing if needed
    if table_name == "admin_settings":
        json_cols = ["db_config", "llm_config", "api_keys"]
        for col in json_cols:
            if col in df.columns:
                # Ensure they are valid JSON strings for MySQL
                df[col] = df[col].apply(lambda x: json.dumps(json.loads(x)) if isinstance(x, str) and x.strip() else json.dumps(x) if x is not None else None)
    
    if table_name == "chat_messages":
        if "data" in df.columns:
             df["data"] = df["data"].apply(lambda x: json.dumps(json.loads(x)) if isinstance(x, str) and x.strip() else json.dumps(x) if x is not None else None)

    return df


def migrate():
    print("==========================================================================")
    print("                     QueryMind Database Migration                        ")
    print("==========================================================================")
    print(f"Source: SQLite at {SQLITE_PATH}")
    print(f"Target: MySQL at {MYSQL_URL.split('@')[-1]}")
    print("--------------------------------------------------------------------------")
    
    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite source file not found at: {SQLITE_PATH}")
        return

    try:
        from models.db_models import Base
        lite_conn = sqlite3.connect(SQLITE_PATH)
        mysql_engine = create_engine(MYSQL_URL)

        # Force recreate MySQL schema to match current models perfectly
        print("[*] Recreating MySQL schema...")
        with mysql_engine.connect() as my_conn:
            my_conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            for table in Base.metadata.sorted_tables:
                 my_conn.execute(text(f"DROP TABLE IF EXISTS {table.name}"))
            my_conn.commit()
            my_conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            my_conn.commit()
        
        # This will create tables with identical structure to the latest Python models
        Base.metadata.create_all(mysql_engine)
        print("[PASS] MySQL tables recreated successfully.")

        # Ordered list by dependency: Parents first

        tables = [
            "admin_users",
            "admin_settings",
            "uploaded_files",
            "chat_sessions",
            "chat_messages",
            "alembic_version" # Keep migrations synced
        ]

        with mysql_engine.connect() as my_conn:
            # Disable FK checks for safer bulk migration
            my_conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            
            for table in tables:
                print(f"[*] Migrating table: {table}...", end=" ", flush=True)
                
                # Verify table exists in source
                cursor = lite_conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    print("SKIPPED (not in source)")
                    continue

                # Read from SQLite
                df = pd.read_sql(f"SELECT * FROM {table}", lite_conn)
                
                if df.empty:
                    print("EMPTY (skipping)")
                    continue
                
                # Perform any dialect-specific cleaning
                df = clean_data(df, table)

                # Clear existing table in MySQL to avoid PK collisions
                my_conn.execute(text(f"DELETE FROM {table}"))
                my_conn.commit()

                # Insert into MySQL
                # Use my_conn instead of mysql_engine to preserve session state (like FK checks disabled)
                df.to_sql(table, con=my_conn, if_exists='append', index=False)
                
                print(f"SUCCESS ({len(df)} records)")

            # Re-enable FK checks
            my_conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            my_conn.commit()

            
        print("--------------------------------------------------------------------------")
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("All history and settings have been moved to MySQL.")
        print("==========================================================================")

    except Exception as e:
        print(f"\nFATAL ERROR DURING MIGRATION: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'lite_conn' in locals():
            lite_conn.close()

if __name__ == "__main__":
    migrate()
