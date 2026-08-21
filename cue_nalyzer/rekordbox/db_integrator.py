"""Direct Rekordbox Master Database (master.db) Integrator for zero-manual-step cue sync."""

from datetime import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

try:
    from pyrekordbox import Rekordbox6Database
    from pyrekordbox.db6.tables import DjmdContent, DjmdCue
    PYREKORDBOX_AVAILABLE = True
except ImportError:
    PYREKORDBOX_AVAILABLE = False

from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis
from cue_nalyzer.rekordbox.safety import RekordboxSafetyManager


class RekordboxDBIntegrator:
    """
    Directly writes Hot Cues, Beatgrids, and metadata into Rekordbox 6/7 master.db,
    enabling zero-manual-step automated synchronization.
    """

    def __init__(self, config: Optional[Config] = None, custom_db_path: Optional[str] = None):
        self.config = config or Config()
        self.safety = RekordboxSafetyManager(custom_db_path)
        self.db_path = self.safety.db_path

    def is_available(self) -> bool:
        """Check if direct database integration is supported on this machine."""
        return PYREKORDBOX_AVAILABLE and self.db_path is not None and self.db_path.exists()

    def get_database_status(self) -> Dict[str, Any]:
        """Return status, track count, lock state, and backup count for Rekordbox DB."""
        if not self.is_available():
            return {
                "available": False,
                "db_path": str(self.db_path) if self.db_path else None,
                "is_running": False,
                "track_count": 0,
                "cue_count": 0,
                "backup_count": len(self.safety.list_backups()),
            }

        is_running = self.safety.is_rekordbox_running()
        track_count = 0
        cue_count = 0

        try:
            db = Rekordbox6Database(str(self.db_path))
            track_count = db.session.query(DjmdContent).count()
            cue_count = db.session.query(DjmdCue).count()
            db.close()
        except Exception:
            pass

        return {
            "available": True,
            "db_path": str(self.db_path),
            "is_running": is_running,
            "track_count": track_count,
            "cue_count": cue_count,
            "backup_count": len(self.safety.list_backups()),
            "last_backup": str(self.safety.list_backups()[0]) if self.safety.list_backups() else None,
        }

    def sync_analyses_to_rekordbox(self, analyses: List[TrackAnalysis]) -> Dict[str, Any]:
        """
        Directly sync analyzed tracks and hot cues into Rekordbox master.db.
        Automatically creates a safety backup before writing.
        """
        if not self.is_available():
            return {
                "success": False,
                "reason": "db_not_available",
                "message": "Rekordbox master.db not found on this system.",
                "updated_count": 0,
            }

        if self.safety.is_rekordbox_running():
            return {
                "success": False,
                "reason": "rekordbox_running",
                "message": "Rekordbox is currently running. Please close Rekordbox to allow direct database sync.",
                "updated_count": 0,
            }

        # 1. Create safety backup snapshot
        backup_file = self.safety.create_snapshot_backup()

        updated_tracks = 0
        total_cues_added = 0

        try:
            db = Rekordbox6Database(str(self.db_path))
            session = db.session

            for analysis in analyses:
                file_path = Path(analysis.metadata.file_path).resolve()
                file_name = file_path.name
                posix_path = file_path.as_posix()

                # Find track in Rekordbox Collection by file path or filename
                content = (
                    session.query(DjmdContent)
                    .filter((DjmdContent.FolderPath == posix_path) | (DjmdContent.FileNameL == file_name.lower()) | (DjmdContent.FolderPath.ilike(f"%{file_name}%")))
                    .first()
                )

                if not content:
                    continue

                # Update Track BPM and Key
                content.BPM = int(round(analysis.beat_grid.bpm * 100))
                content.updated_at = datetime.utcnow()

                # Remove previous cues for this content to prevent duplication
                session.query(DjmdCue).filter(DjmdCue.ContentID == content.ID).delete()

                # Add new high-conviction DJ Cue Points
                for cue_idx, cue in enumerate(analysis.cue_points, start=1):
                    in_msec = int(round(cue.timestamp * 1000))
                    cue_entry = DjmdCue(
                        ID=str(abs(hash(f"{content.ID}_{cue.timestamp}_{cue_idx}")) % (2**31 - 1)),
                        ContentID=content.ID,
                        InMsec=in_msec,
                        InFrame=int(in_msec * 0.15),
                        InMpegFrame=int(in_msec * 0.075),
                        InMpegAbs=in_msec * 15,
                        OutMsec=-1,
                        OutFrame=0,
                        OutMpegFrame=0,
                        OutMpegAbs=0,
                        Kind=1,
                        Color=255 if "DROP" in cue.cue_type.value else (16711680 if "MIX_IN" in cue.cue_type.value else -1),
                        Comment=f"{cue.label}: {cue.reasoning[:30]}",
                        ContentUUID=content.UUID if hasattr(content, "UUID") else str(uuid.uuid4()),
                        UUID=str(uuid.uuid4()),
                        rb_data_status=0,
                        rb_local_data_status=0,
                        rb_local_deleted=0,
                        rb_local_synced=0,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(cue_entry)
                    total_cues_added += 1

                updated_tracks += 1

            session.commit()
            db.close()

            return {
                "success": True,
                "reason": "synced_successfully",
                "message": f"Successfully updated {updated_tracks} tracks and {total_cues_added} cues directly in Rekordbox Master DB.",
                "updated_count": updated_tracks,
                "cues_added": total_cues_added,
                "backup_path": str(backup_file) if backup_file else None,
            }
        except Exception as e:
            return {
                "success": False,
                "reason": "db_write_error",
                "message": f"Error updating Rekordbox database: {str(e)}",
                "updated_count": 0,
            }
