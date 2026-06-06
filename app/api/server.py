"""
API server for the autonomous agent system.
FastAPI server for the terminal UI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
import sys
from .routes import router

app = FastAPI(title="Dragonite API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")

# Mount static files for UI
ui_dir = Path(__file__).parent.parent / "ui"
if ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

@app.get("/")
async def root():
    # Redirect to UI
    return RedirectResponse(url="/ui/terminal.html")

@app.get("/health")
async def health():
    return {"status": "healthy"}