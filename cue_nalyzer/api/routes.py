"""FastAPI API routes for Cue Nalyzer web studio, Windows Explorer dialogs, and Rekordbox direct sync."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from cue_nalyzer.analyzer import AnalyzerEngine
from cue_nalyzer.batch.batch_processor import BatchProcessor, BatchResult
from cue_nalyzer.core.cache import AnalysisCache
from cue_nalyzer.core.models import TrackAnalysis
from cue_nalyzer.export.rekordbox_xml import RekordboxXMLExporter
from cue_nalyzer.rekordbox.db_integrator import RekordboxDBIntegrator
from cue_nalyzer.watcher.folder_watcher import WatchFolderManager

router = APIRouter(prefix="/api")
engine = AnalyzerEngine()
cache = AnalysisCache()
batch_proc = BatchProcessor()
rekordbox_exporter = RekordboxXMLExporter()
rekordbox_db = RekordboxDBIntegrator()
watcher = WatchFolderManager()
watcher.start()


class AnalyzePathRequest(BaseModel):
    file_path: str
    force_recompute: bool = False


class BatchFolderRequest(BaseModel):
    folder_path: str
    force_recompute: bool = False


# =========================================================================
# NATIVE WINDOWS EXPLORER DIALOG ENDPOINTS
# =========================================================================

@router.post("/dialog/pick-files")
def pick_files_dialog() -> Dict[str, Any]:
    """Launch native Windows File Explorer dialog to multi-select audio tracks."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        filetypes = [
            ("Audio Files", "*.mp3 *.wav *.flac *.m4a *.aiff *.ogg"),
            ("MP3 Files", "*.mp3"),
            ("WAV Files", "*.wav"),
            ("FLAC Files", "*.flac"),
            ("All Files", "*.*"),
        ]
        selected_files = filedialog.askopenfilenames(
            title="Cue Nalyzer — Select Audio Tracks for Analysis",
            filetypes=filetypes,
        )
        root.destroy()

        return {"files": list(selected_files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch file dialog: {str(e)}")


@router.post("/dialog/pick-folder")
def pick_folder_dialog() -> Dict[str, Any]:
    """Launch native Windows File Explorer dialog to select a folder / playlist directory."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        selected_folder = filedialog.askdirectory(
            title="Cue Nalyzer — Select Playlist / Music Folder",
        )
        root.destroy()

        return {"folder": selected_folder or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch folder dialog: {str(e)}")


# =========================================================================
# TRACK & BATCH ANALYSIS ENDPOINTS
# =========================================================================

@router.post("/analyze/path", response_model=TrackAnalysis)
def analyze_file_path(req: AnalyzePathRequest):
    """Analyze a single audio file by path."""
    try:
        analysis = engine.analyze_track(req.file_path, force_recompute=req.force_recompute)
        return analysis
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on local disk")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
def batch_analyze_folder(req: BatchFolderRequest) -> Dict[str, Any]:
    """Batch analyze a playlist or folder with worker pool and master.db sync."""
    try:
        res: BatchResult = batch_proc.process_folder(
            req.folder_path,
            force_recompute=req.force_recompute,
        )
        return {
            "total_found": res.total_found,
            "analyzed_count": res.analyzed_count,
            "skipped_count": res.skipped_count,
            "failed_count": res.failed_count,
            "failed_files": res.failed_files,
            "rekordbox_xml_path": res.rekordbox_xml_path,
            "rekordbox_db_synced": res.rekordbox_db_synced,
            "rekordbox_db_message": res.rekordbox_db_message,
        }
    except NotADirectoryError:
        raise HTTPException(status_code=400, detail="Invalid directory path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracks", response_model=List[TrackAnalysis])
def list_tracks(
    genre: Optional[str] = None,
    min_bpm: Optional[float] = None,
    max_bpm: Optional[float] = None,
    camelot: Optional[str] = None,
):
    """List all previously analyzed tracks from local cache."""
    return cache.query_library(genre=genre, min_bpm=min_bpm, max_bpm=max_bpm, camelot_key=camelot)


@router.get("/track/{file_hash}", response_model=TrackAnalysis)
def get_track(file_hash: str):
    """Get full analysis details for a specific track by hash."""
    track = cache.get_analysis_by_hash(file_hash)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found in cache")
    return track


@router.get("/audio/{file_hash}")
def stream_audio(file_hash: str):
    """Stream audio file for in-browser playback."""
    track = cache.get_analysis_by_hash(file_hash)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    file_path = Path(track.metadata.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Underlying audio file missing from disk")

    media_type = "audio/mpeg" if file_path.suffix.lower() == ".mp3" else "audio/wav"
    return FileResponse(file_path, media_type=media_type)


# =========================================================================
# REKORDBOX MASTER DATABASE & DIRECT SYNC ENDPOINTS
# =========================================================================

@router.get("/rekordbox/db-status")
def rekordbox_db_status():
    """Return live status of local Rekordbox master.db connection and backup snapshot count."""
    return rekordbox_db.get_database_status()


@router.post("/rekordbox/sync-master")
def rekordbox_sync_master():
    """Directly sync all analyzed library tracks to Rekordbox master.db."""
    tracks = cache.list_all_tracks()
    if not tracks:
        return {"success": False, "message": "No analyzed tracks found in library."}
    return rekordbox_db.sync_analyses_to_rekordbox(tracks)


@router.get("/export/rekordbox")
def export_rekordbox(track_hash: Optional[str] = None):
    """Download Pioneer Rekordbox XML bridge (fallback)."""
    if track_hash:
        track = cache.get_analysis_by_hash(track_hash)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        analyses = [track]
        filename = f"{track.metadata.title or 'cue_nalyzer'}_rekordbox.xml"
    else:
        analyses = cache.list_all_tracks()
        filename = "cue_nalyzer_library.xml"

    xml_content = rekordbox_exporter.generate_xml(analyses)
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =========================================================================
# BACKGROUND WATCH FOLDER ENDPOINTS
# =========================================================================

class WatchFolderRequest(BaseModel):
    folder_path: str


@router.get("/watcher/status")
def get_watcher_status():
    """Get active watch folders and running status."""
    return {
        "running": watcher._is_running,
        "watch_folders": watcher.get_watch_folders(),
    }


@router.post("/watcher/add")
def add_watch_folder(req: WatchFolderRequest):
    """Add a directory to background auto-watch list."""
    p = Path(req.folder_path).resolve()
    if not p.is_dir():
        raise HTTPException(status_code=400, detail="Invalid directory path")
    watcher.add_watch_folder(str(p))
    return {
        "success": True,
        "watch_folders": watcher.get_watch_folders(),
    }


@router.post("/watcher/remove")
def remove_watch_folder(req: WatchFolderRequest):
    """Remove a directory from background auto-watch list."""
    watcher.remove_watch_folder(req.folder_path)
    return {
        "success": True,
        "watch_folders": watcher.get_watch_folders(),
    }
