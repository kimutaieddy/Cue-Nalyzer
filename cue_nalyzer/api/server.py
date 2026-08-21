"""FastAPI Server Application for Cue Nalyzer Web Studio."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from cue_nalyzer.api.routes import router

app = FastAPI(
    title="Cue Nalyzer API",
    description="Intelligent Local DJ Music Intelligence System",
    version="0.1.0",
)

# Enable CORS for local web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount Static UI directory
ui_dir = Path(__file__).parent.parent / "ui"
if ui_dir.exists():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

