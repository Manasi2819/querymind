import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import SessionLocal, Base, engine
from models.db_models import AdminUser
from auth import get_password_hash
from config import get_settings
from routers import chat, admin, ingest, sessions

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create DB tables and seed the default admin user."""
    # Create all tables defined by the ORM models
    Base.metadata.create_all(bind=engine)

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
    yield


app = FastAPI(
    title="QueryMind API",
    description="Enterprise chatbot platform — plug into any application",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(ingest.router)
app.include_router(sessions.router)

# ── Widget static files (served at /widget if the dir exists) ─────────────────
widget_dir = os.path.join(os.path.dirname(__file__), "../widget")
if os.path.exists(widget_dir):
    app.mount("/widget", StaticFiles(directory=widget_dir), name="widget")


@app.get("/")
async def root():
    return {"message": "QueryMind API is running", "docs": "/docs"}
