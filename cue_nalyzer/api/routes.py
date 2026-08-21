"""FastAPI API routes for Cue Nalyzer web studio and batch engine."""

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

router = APIRouter(prefix="/api")
engine = AnalyzerEngine()
cache = AnalysisCache()
batch_proc = BatchProcessor()
rekordbox_exporter = RekordboxXMLExporter()


class AnalyzePathRequest(BaseModel):
    file_path: str
    force_recompute: bool = False


class BatchFolderRequest(BaseModel):
    folder_path: str
    force_recompute: bool = False


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
    """Batch analyze a playlist or folder with parallel workers and caching."""
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


@router.get("/export/rekordbox")
def export_rekordbox(track_hash: Optional[str] = None):
    """Download Pioneer Rekordbox XML bridge."""
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


@router.get("/rekordbox/bridge-info")
def rekordbox_bridge_info():
    """Get status and path of master Rekordbox XML bridge."""
    master_path = Path.cwd() / RekordboxXMLExporter.DEFAULT_MASTER_XML_NAME
    return {
        "master_xml_path": str(master_path.resolve()),
        "exists": master_path.exists(),
        "instructions": [
            "1. Open Rekordbox.",
            "2. Go to File -> Preferences -> Advanced -> Database.",
            "3. Under 'rekordbox xml', set the file path to this generated XML file.",
            "4. In Rekordbox's left sidebar, click 'rekordbox xml' to view and import your analyzed playlists with all Hot Cues on the pads.",
        ],
    }
