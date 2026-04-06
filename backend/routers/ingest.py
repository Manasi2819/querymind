from fastapi import APIRouter, UploadFile, File, Form
import os, shutil
from pathlib import Path
from services.ingest_service import ingest_file
from config import get_settings

router = APIRouter(prefix="/ingest", tags=["ingest"])
settings = get_settings()

@router.post("/file")
async def ingest(
    file: UploadFile = File(...),
    file_type: str = Form("document"),
    tenant_id: str = Form("default"),
):
    """Public ingest endpoint (no auth). For internal service calls."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = Path(settings.upload_dir) / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    result = ingest_file(str(dest), tenant_id, file_type)
    return result
