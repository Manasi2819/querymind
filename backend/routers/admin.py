from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
import os, json, shutil
from pathlib import Path
from auth import create_access_token, verify_token
from models.schemas import DBConfig, LLMConfig, TokenResponse
from services.sql_agent import test_connection
from config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

# ── In-memory state (replace with DB in production) ──────────────────
_db_config: dict = {}
_llm_config: dict = {"provider": settings.llm_provider}

@router.post("/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if (form_data.username != settings.admin_username or
            form_data.password != settings.admin_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": form_data.username})
    return TokenResponse(access_token=token)

@router.post("/db-config")
async def save_db_config(config: DBConfig, fetch_schema: bool = True, _=Depends(verify_token)):
    from services.sql_metadata_service import index_db_metadata
    
    result = test_connection(config.connection_url)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
        
    _db_config.update(config.model_dump())
    _db_config["url"] = config.connection_url
    _db_config["db_type"] = config.db_type
    
    msg = "Database configured."
    if fetch_schema:
        count = index_db_metadata(config.connection_url, tenant_id="default")
        msg += f" Auto-fetched and indexed {count} tables for RAG."
        
    return {"message": msg, "tables": result["tables"]}

@router.get("/db-config")
async def get_db_config(_=Depends(verify_token)):
    if not _db_config:
        return {"configured": False}
    safe = {k: v for k, v in _db_config.items() if k != "password"}
    return {"configured": True, **safe}

@router.post("/llm-config")
async def save_llm_config(config: LLMConfig, _=Depends(verify_token)):
    _llm_config.update(config.model_dump(exclude_none=True))
    return {"message": "LLM provider updated", "provider": _llm_config["provider"]}

@router.get("/llm-config")
async def get_llm_config(_=Depends(verify_token)):
    safe = {k: v for k, v in _llm_config.items() if k != "api_key"}
    return safe

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form("document"),   # "data_dict" | "schema" | "document"
    tenant_id: str = Form("default"),
    _=Depends(verify_token),
):
    from services.ingest_service import ingest_file
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = Path(settings.upload_dir) / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    result = ingest_file(str(dest), tenant_id, file_type)
    return result

def get_db_url() -> str:
    return _db_config.get("url", "")

def get_db_type() -> str:
    return _db_config.get("db_type", "mysql")

def get_llm_cfg() -> dict:
    return _llm_config
