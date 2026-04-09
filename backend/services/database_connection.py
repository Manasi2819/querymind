"""
Database Connection Utility
Handles creating engines, connection testing, and schema extraction explicitly.
"""
from sqlalchemy import create_engine, text, inspect
import json

def connect_db(db_url: str):
    """
    Creates a SQLAlchemy engine with connection pooling and timeouts.
    """
    try:
        # Patch db_url to use the installed drivers
        if db_url.startswith("mysql://"):
            db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            
        # Fix common typo to resolve DNS error
        if "@loaclhost:" in db_url:
            db_url = db_url.replace("@loaclhost:", "@localhost:")

        # We wrap in try block to catch engine creation errors early
        engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 5} if "sqlite" not in db_url and "mssql" not in db_url and "oracle" not in db_url else {}
        )
        # Test quick execution to ensure connection is valid
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
        return engine
    except Exception as e:
        raise Exception(f"Connection failed: {str(e)}")

def test_connection(db_url: str) -> dict:
    """
    Tests connection to the database. Same signature as before for backward compat.
    """
    try:
        engine = connect_db(db_url)
        
        # Test getting tables to match previous test_connection signature return types
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        return {"success": True, "tables": tables}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_schema(engine) -> str:
    """
    Extracts the schema from the standard SQLAlchemy inspector and returns a formatted JSON string.
    """
    inspector = inspect(engine)
    
    schema = {}
    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        schema[table] = [col['name'] for col in columns]

    return json.dumps(schema, indent=2)
