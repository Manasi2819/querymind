import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, admin, ingest

app = FastAPI(
    title="QueryMind API",
    description="Enterprise chatbot platform — plug into any application",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict in production
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
