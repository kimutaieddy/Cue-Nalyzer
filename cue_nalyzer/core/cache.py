"""Local SQLite + JSON analysis cache for instant retrieval and library indexing."""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis


class AnalysisCache:
    """Manages persistent analysis results in SQLite database and JSON files."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.db_path = self.config.DB_PATH
        self._init_db()

    def _init_db(self):
        """Ensure database table schema exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS track_analyses (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    title TEXT,
                    artist TEXT,
                    bpm REAL,
                    key_camelot TEXT,
                    genre TEXT,
                    duration_sec REAL,
                    analysis_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON track_analyses(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bpm ON track_analyses(bpm)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON track_analyses(key_camelot)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_genre ON track_analyses(genre)")
            conn.commit()

    def get_analysis_by_hash(self, file_hash: str) -> Optional[TrackAnalysis]:
        """Fetch cached analysis by SHA-256 file hash."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT analysis_json FROM track_analyses WHERE file_hash = ?", (file_hash,))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return TrackAnalysis.model_validate(data)
        return None

    def get_analysis_by_path(self, file_path: str) -> Optional[TrackAnalysis]:
        """Fetch cached analysis by file path."""
        p_str = str(Path(file_path).resolve())
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT analysis_json FROM track_analyses WHERE file_path = ?", (p_str,))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return TrackAnalysis.model_validate(data)
        return None

    def save_analysis(self, analysis: TrackAnalysis):
        """Save or update track analysis in SQLite database."""
        json_data = analysis.model_dump_json()
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO track_analyses (
                    file_hash, file_path, file_name, title, artist, bpm, key_camelot, genre, duration_sec, analysis_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis.metadata.file_hash,
                    analysis.metadata.file_path,
                    analysis.metadata.file_name,
                    analysis.metadata.title,
                    analysis.metadata.artist,
                    analysis.beat_grid.bpm,
                    analysis.key_info.camelot,
                    analysis.genre.primary_genre,
                    analysis.metadata.duration_sec,
                    json_data,
                ),
            )
            conn.commit()

    def list_all_tracks(self) -> List[TrackAnalysis]:
        """List all analyzed tracks from the database."""
        tracks = []
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT analysis_json FROM track_analyses ORDER BY created_at DESC")
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[0])
                    tracks.append(TrackAnalysis.model_validate(data))
                except Exception:
                    continue
        return tracks

    def query_library(
        self,
        genre: Optional[str] = None,
        min_bpm: Optional[float] = None,
        max_bpm: Optional[float] = None,
        camelot_key: Optional[str] = None,
    ) -> List[TrackAnalysis]:
        """Query library with flexible DJ filters."""
        query = "SELECT analysis_json FROM track_analyses WHERE 1=1"
        params = []

        if genre:
            query += " AND genre LIKE ?"
            params.append(f"%{genre}%")
        if min_bpm is not None:
            query += " AND bpm >= ?"
            params.append(min_bpm)
        if max_bpm is not None:
            query += " AND bpm <= ?"
            params.append(max_bpm)
        if camelot_key:
            query += " AND key_camelot = ?"
            params.append(camelot_key)

        tracks = []
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[0])
                    tracks.append(TrackAnalysis.model_validate(data))
                except Exception:
                    continue
        return tracks

