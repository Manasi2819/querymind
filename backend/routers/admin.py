from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os, json, shutil
from pathlib import Path
from auth import create_access_token, verify_token, verify_password, get_password_hash
from models.schemas import DBConfig, LLMConfig, TokenResponse, UserRegistration
from models.db_models import AdminUser, AdminSettings, UploadedFile
from services.database_connection import test_connection
from services.encryption import encrypt_db_url, decrypt_db_url
from config import get_settings
from database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

@router.post("/register")
async def register(data: UserRegistration, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(AdminUser).filter(AdminUser.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create user
    new_user = AdminUser(
        username=data.username,
        password_hash=get_password_hash(data.password)
    )
    db.add(new_user)
    db.flush() # Get ID
    
    # Init settings
    settings = AdminSettings(user_id=new_user.id)
    db.add(settings)
    db.commit()
    
    return {"message": "User registered successfully", "user_id": new_user.id}

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
    
    if config.url:
        config.db_type = DBConfig.detect_db_type(config.url)
        
    result = test_connection(config.connection_url)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
        
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    if not admin_settings:
        admin_settings = AdminSettings(user_id=user_id)
        db.add(admin_settings)
    
    db_data = config.model_dump()
    db_data["url"] = encrypt_db_url(config.connection_url)
    if db_data.get("password"):
        db_data["password"] = encrypt_db_url(db_data["password"])
        
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

@router.get("/stats")
async def get_stats(token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id = token_data.get("user_id")
    file_count = db.query(UploadedFile).filter(UploadedFile.user_id == user_id).count()
    
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    table_count = 0
    db_name = None
    
    if admin_settings and admin_settings.db_config:
        cfg = admin_settings.db_config
        db_name = cfg.get("database")
        
        enc_url = cfg.get("url")
        if enc_url:
            try:
                url = decrypt_db_url(enc_url)
                # If database field is missing (e.g. direct URL), extract from URL
                if not db_name:
                    db_name = url.split("/")[-1].split("?")[0]
                
                res = test_connection(url)
                table_count = len(res.get("tables", []))
            except Exception:
                # Fallback if decryption fails or URL is malformed
                pass
    
    return {
        "files": file_count,
        "tables": table_count,
        "llm": admin_settings.llm_config.get("provider", "Not configured") if admin_settings else "Not configured",
        "db_connected": bool(admin_settings.db_config) if admin_settings else False,
        "db_name": db_name
    }


@router.get("/files")
async def list_files(token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id = token_data.get("user_id")
    files = db.query(UploadedFile).filter(UploadedFile.user_id == user_id).all()
    return files

@router.delete("/files/{filename}")
async def delete_file(filename: str, token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    from services.embed_service import delete_by_metadata
    user_id = token_data.get("user_id")
    
    # Delete from Vector Store (both collections)
    tenant_id = f"user_{user_id}"
    delete_by_metadata(f"{tenant_id}_document", {"source": filename})
    delete_by_metadata(f"{tenant_id}_knowledge_base", {"source": filename})
    
    # Delete from DB
    db.query(UploadedFile).filter(
        UploadedFile.user_id == user_id, 
        UploadedFile.filename == filename
    ).delete()
    db.commit()
    
    # Optional: delete physical file if exists
    filepath = Path(settings.upload_dir) / filename
    if filepath.exists(): os.remove(filepath)
        
    return {"message": f"Deleted {filename} from knowledge store"}

@router.delete("/db-config")
async def delete_db_config(token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id = token_data.get("user_id")
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    if admin_settings:
        admin_settings.db_config = {}
        db.commit()
    return {"message": "Database access removed"}

@router.post("/llm-config")
async def save_llm_config(config: LLMConfig, token_data: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id = token_data.get("user_id")
    admin_settings = db.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    if not admin_settings:
        admin_settings = AdminSettings(user_id=user_id)
        db.add(admin_settings)
        admin_settings.llm_config = {}
        
    incoming_cfg = config.model_dump(exclude_none=True)
    if "api_key" in incoming_cfg and incoming_cfg["api_key"]:
        incoming_cfg["api_key"] = encrypt_db_url(incoming_cfg["api_key"])
        
    # Create a new dictionary to ensure SQLAlchemy detects the change
    current_cfg = dict(admin_settings.llm_config) if admin_settings.llm_config else {}
    current_cfg.update(incoming_cfg)
    admin_settings.llm_config = current_cfg
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
    db: Session = Depends(get_db),
):
    from services.ingest_service import ingest_file
    user_id = token_data.get("user_id")
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = Path(settings.upload_dir) / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # Use user_id for tenant isolation
    result = ingest_file(str(dest), f"user_{user_id}", file_type, db=db, user_id=user_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Unknown ingestion error"))
    return result

# ── Helper functions for internal use ─────────────────────────────────
# Note: These now need a DB session. In a real app, you'd pass the session or use a global one if safe.

def get_db_url(db_session: Session = None, user_id: int = 1) -> str:
    if not db_session: return ""
    settings = db_session.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    if settings and settings.db_config:
        enc_url = settings.db_config.get("url", "")
        if enc_url:
            try:
                return decrypt_db_url(enc_url)
            except Exception:
                return enc_url # backward-compatible fallback if previously plain text
    return ""

def get_db_type(db_session: Session = None, user_id: int = 1) -> str:
    if not db_session: return "mysql"
    settings = db_session.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    return settings.db_config.get("db_type", "mysql") if settings and settings.db_config else "mysql"

def get_llm_cfg(db_session: Session = None, user_id: int = 1) -> dict:
    if not db_session: return {"provider": settings.llm_provider}
    as_ = db_session.query(AdminSettings).filter(AdminSettings.user_id == user_id).first()
    cfg = as_.llm_config.copy() if as_ and as_.llm_config else {"provider": settings.llm_provider}
    
    # Decrypt API key safely, with plain-text fallback for backward compatibility
    if "api_key" in cfg and cfg["api_key"]:
        try:
            cfg["api_key"] = decrypt_db_url(cfg["api_key"])
        except Exception:
            pass
            
    return cfg
