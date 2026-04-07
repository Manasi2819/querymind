import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.sql_metadata_service import index_db_metadata
from services.sql_rag_service import run_sql_rag_pipeline
from sqlalchemy import create_engine, text

def smoke_test():
    print("--- SMOKE TEST START ---")
    
    # 1. Create a dummy sqlite database
    db_url = "sqlite:///smoke_test.db"
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item TEXT, stock INTEGER)"))
        conn.execute(text("INSERT INTO inventory (item, stock) VALUES ('Laptop', 10), ('Mouse', 50)"))
        conn.commit()
    print("[OK] Created dummy SQLite database.")

    # 2. Index metadata
    try:
        count = index_db_metadata(db_url, tenant_id="smoke_test")
        print(f"[OK] Indexed {count} tables in ChromaDB.")
    except Exception as e:
        print(f"[FAIL] Metadata indexing failed: {e}")
        return

    # 3. Step through the RAG pipeline
    try:
        question = "What is the stock of Mouse?"
        answer, sql, data = run_sql_rag_pipeline(question, "smoke_test", db_url, db_type="sqlite")
        
        print(f"[OK] Question: {question}")
        print(f"[OK] Generated SQL: {sql}")
        print(f"[OK] Data Result: {data}")
        print(f"[OK] Summary: {answer}")
        
        if "50" in str(data):
            print("--- SMOKE TEST SUCCESS ---")
        else:
            print("--- SMOKE TEST FAILED (INCORRECT DATA) ---")
            
    except Exception as e:
        print(f"❌ RAG pipeline failed: {e}")

if __name__ == "__main__":
    smoke_test()
