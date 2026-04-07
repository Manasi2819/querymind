from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os, json, shutil
from pathlib import Path
from auth import create_access_token, verify_token, verify_password, get_password_hash
from models.schemas import DBConfig, LLMConfig, TokenResponse
from models.db_models import AdminUser, AdminSettings
from services.sql_agent import test_connection
from config import get_settings
from database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

@router.post("/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username, "user_id": user.id})
    return TokenResponse(access_token=token)

@router.post("/db-config")
async def save_db_config(config: DBConfig, fetch_schema: bool = True, token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    from services.sql_metadata_service import index_db_metadata
    
    user_id = token_data.get("user_id")
    result = test_connection(config.connection_url)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
        
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    if not admin_settings:
        admin_settings = AdminSettings(user_id=user_id)
        db.add(admin_settings)
    
    db_data = config.model_dump()
    db_data["url"] = config.connection_url
    admin_settings.db_config = db_data
    db.commit()
    
    msg = "Database configured."
    if fetch_schema:
        # Use user_id as tenant_id for isolation
        count = index_db_metadata(config.connection_url, tenant_id=f"user_{user_id}")
        msg += f" Auto-fetched and indexed {count} tables for RAG."
        
    return {"message": msg, "tables": result["tables"]}

@router.get("/db-config")
async def get_db_config(token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id = token_data.get("user_id")
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    
    if not admin_settings or not admin_settings.db_config:
        return {"configured": False}
        
    cfg = admin_settings.db_config
    safe = {k: v for k, v in cfg.items() if k != "password"}
    return {"configured": True, **safe}

@router.post("/llm-config")
async def save_llm_config(config: LLMConfig, token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id = token_data.get("user_id")
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    if not admin_settings:
        admin_settings = AdminSettings(user_id=user_id)
        db.add(admin_settings)
        
    admin_settings.llm_config = config.model_dump(exclude_none=True)
    db.commit()
    return {"message": "LLM provider updated", "provider": admin_settings.llm_config.get("provider")}

@router.get("/llm-config")
async def get_llm_config(token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id = token_data.get("user_id")
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    
    if not admin_settings or not admin_settings.llm_config:
        return {"provider": settings.llm_provider} # Default from env
        
    safe = {k: v for k, v in admin_settings.llm_config.items() if k != "api_key"}
    return safe

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form("document"),
    token_data: dict = Depends(verify_token),
):
    from services.ingest_service import ingest_file
    user_id = token_data.get("user_id")
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = Path(settings.upload_dir) / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # Use user_id for tenant isolation
    result = ingest_file(str(dest), f"user_{user_id}", file_type)
    return result

# ── Helper functions for internal use ─────────────────────────────────
# Note: These now need a DB session. In a real app, you'd pass the session or use a global one if safe.

def get_db_url(db_session: Session = None, user_id: int = 1) -> str:
    if not db_session: return ""
    settings = db_session.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    return settings.db_config.get("url", "") if settings and settings.db_config else ""

def get_db_type(db_session: Session = None, user_id: int = 1) -> str:
    if not db_session: return "mysql"
    settings = db_session.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    return settings.db_config.get("db_type", "mysql") if settings and settings.db_config else "mysql"

def get_llm_cfg(db_session: Session = None, user_id: int = 1) -> dict:
    if not db_session: return {"provider": settings.llm_provider}
    as_ = db_session.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    return as_.llm_config if as_ and as_.llm_config else {"provider": settings.llm_provider}
