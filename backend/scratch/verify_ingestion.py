import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

from services.ingest_service import ingest_file
import sqlite3

def test_ingestion():
    test_files_dir = Path(backend_path) / "test_data"
    os.makedirs(test_files_dir, exist_ok=True)
    
    # Create a dummy text file
    txt_path = test_files_dir / "test.txt"
    with open(txt_path, "w") as f:
        f.write("This is a test document for General Document ingestion.")
        
    print(f"Testing ingestion for {txt_path}...")
    # Mocking db session for testing (since we want to verify DB record)
    from database import SessionLocal
    db = SessionLocal()
    try:
        result = ingest_file(str(txt_path), tenant_id="user_1", file_type="general_document", db=db, user_id=1)
        print(f"Result: {result}")
    finally:
        db.close()
    
    # Check DB
    db_path = os.path.join(backend_path, "querymind_metadata.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, file_type, source_type FROM uploaded_files WHERE filename = 'test.txt'")
    row = cursor.fetchone()
    if row:
        print(f"DB Record: {row}")
    else:
        print("DB Record not found (ingest_file needs db and user_id to save to DB, let's fix that in the test if needed)")
    conn.close()

if __name__ == "__main__":
    test_ingestion()
