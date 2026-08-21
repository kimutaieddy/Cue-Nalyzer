"""FastAPI API routes for Cue Nalyzer web studio and endpoints."""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from cue_nalyzer.analyzer import AnalyzerEngine
from cue_nalyzer.core.cache import AnalysisCache
from cue_nalyzer.core.models import TrackAnalysis, TransitionAdvice
from cue_nalyzer.export.rekordbox_xml import RekordboxXMLExporter
from cue_nalyzer.intelligence.set_planner import SetPlanner

router = APIRouter(prefix="/api")
engine = AnalyzerEngine()
cache = AnalysisCache()
planner = SetPlanner()
rekordbox_exporter = RekordboxXMLExporter()


class AnalyzePathRequest(BaseModel):
    file_path: str
    force_recompute: bool = False


class MatchRequest(BaseModel):
    track_a_hash: str
    track_b_hash: str


@router.post("/analyze/path", response_model=TrackAnalysis)
def analyze_file_path(req: AnalyzePathRequest):
    """Analyze a local audio file by its system path."""
    try:
        analysis = engine.analyze_track(req.file_path, force_recompute=req.force_recompute)
        return analysis
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on local disk")
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


@router.post("/match", response_model=TransitionAdvice)
def match_tracks(req: MatchRequest):
    """Compute transition compatibility between two tracks."""
    track_a = cache.get_analysis_by_hash(req.track_a_hash)
    track_b = cache.get_analysis_by_hash(req.track_b_hash)

    if not track_a or not track_b:
        raise HTTPException(status_code=404, detail="One or both tracks not found in cache")

    advice = planner.evaluate_transition(track_a, track_b)
    return advice


@router.get("/export/rekordbox")
def export_rekordbox(track_hash: Optional[str] = None):
    """Download Pioneer Rekordbox XML."""
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

