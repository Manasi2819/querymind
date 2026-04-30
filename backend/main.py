import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import SessionLocal, Base, engine
from models.db_models import AdminUser
from auth import get_password_hash
from config import get_settings
from routers import chat, admin, ingest, sessions
from services.pipeline_logger import log_api_request, request_id_var
import time
import uuid
from fastapi import Request


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

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Set a unique request ID for this thread/context
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    start_time = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start_time) * 1000
    
    # Log the request
    log_api_request(request.method, request.url.path, response.status_code, duration)
    
    # Add request ID to response headers for debugging
    response.headers["X-Request-ID"] = request_id
    return response

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

# ── React Frontend Static Files ───────────────────────────────────────────────
# The React build output (dist/) is copied to backend/static/ during Docker build.
# FastAPI serves it directly — no Nginx needed.
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # Serve all static assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        """Serve the React app root."""
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: return index.html for any route not matched by the API.
        This lets React Router handle client-side navigation.
        """
        # Don't intercept /api/* or /docs or /openapi.json
        if full_path.startswith(("api/", "docs", "openapi", "redoc", "widget")):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = os.path.join(static_dir, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return {"message": "QueryMind API is running", "docs": "/docs"}
else:
    # Running locally without Docker (no static/ dir) — plain API response
    @app.get("/")
    async def root():
        return {"message": "QueryMind API is running", "docs": "/docs"}
