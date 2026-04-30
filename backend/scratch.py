import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.sql_rag_service import run_context_aware_sql_pipeline

tenant_id = "tenant1"
db_url = "postgresql://querymind:querymind@localhost:5432/querymind"
try:
    from config import get_settings
    settings = get_settings()
    db_url = settings.database_url
except:
    pass

res = run_context_aware_sql_pipeline(
    question="what is the employment status of each of them along with their names",
    tenant_id="1", # Assuming tenant_id is 1
    db_url="postgresql://postgres:postgres@localhost:5432/postgres", # Wait, I don't know the DB url. Let's look at test_fixes.py.
    db_type="postgresql"
)
print(res)
