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
    print("🚀 App lifespan: Syncing admin user...")
    
    # Wait for entrypoint.sh to finish migrations. 
    # We NO LONGER call Base.metadata.create_all(bind=engine) here 
    # because it conflicts with Alembic's initial migration on MySQL.

    db = SessionLocal()
    try:
        admin_user = db.query(AdminUser).filter(AdminUser.username == settings.admin_username).first()
        if not admin_user:
            print(f"👤 Seeding initial admin user: {settings.admin_username}")
            new_admin = AdminUser(
                username=settings.admin_username,
                password_hash=get_password_hash(settings.admin_password)
            )
            db.add(new_admin)
            db.commit()
            print("✅ Admin user seeded successfully.")
        else:
            # Sync password with .env to ensure login works
            print(f"👤 Syncing password for admin user: {settings.admin_username}")
            admin_user.password_hash = get_password_hash(settings.admin_password)
            db.commit()
            print("✅ Admin password synced.")
    except Exception as e:
        print(f"❌ Error during admin sync: {str(e)}")
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
