from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, admin, ingest
from sqlalchemy.orm import Session
from database import SessionLocal
from models.db_models import AdminUser
from auth import get_password_hash
from config import get_settings

settings = get_settings()

app = FastAPI(
    title="QueryMind API",
    description="Enterprise chatbot platform — plug into any application",
    version="1.0.0",
)

@app.on_event("startup")
def startup_event():
    # Seed initial admin user if not exists
    db = SessionLocal()
    try:
        admin_user = db.query(AdminUser).filter(AdminUser.username == settings.admin_username).first()
        if not admin_user:
            print(f"Seeding initial admin user: {settings.admin_username}")
            new_admin = AdminUser(
                username=settings.admin_username,
                password_hash=get_password_hash(settings.admin_password)
            )
            db.add(new_admin)
            db.commit()
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(ingest.router)

from fastapi.staticfiles import StaticFiles
script_dir = os.path.dirname(__file__)
widget_dir = os.path.join(script_dir, "../widget")
if os.path.exists(widget_dir):
    app.mount("/widget", StaticFiles(directory=widget_dir), name="widget")

@app.get("/")
async def root():
    return {"message": "QueryMind API is running", "docs": "/docs"}
