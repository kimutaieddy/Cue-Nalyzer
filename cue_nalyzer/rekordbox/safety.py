"""Backup, lock detection, and rollback safety manager for Rekordbox master.db."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import psutil


class RekordboxSafetyManager:
    """Manages safe access, timestamped backups, process checks, and rollbacks for Rekordbox master.db."""

    def __init__(self, custom_db_path: Optional[str] = None):
        self.db_path = self._resolve_master_db_path(custom_db_path)
        self.backup_dir = self.db_path.parent / "backups" if self.db_path else None

    def _resolve_master_db_path(self, custom_path: Optional[str] = None) -> Optional[Path]:
        """Locate Rekordbox 6 / 7 master.db on Windows / macOS."""
        if custom_path and Path(custom_path).exists():
            return Path(custom_path).resolve()

        appdata = os.environ.get("APPDATA")
        if appdata:
            pioneer_dir = Path(appdata) / "Pioneer" / "rekordbox"
            master_db = pioneer_dir / "master.db"
            if master_db.exists():
                return master_db

            # Check rekordbox6 alternate dir
            alt_db = Path(appdata) / "Pioneer" / "rekordbox6" / "master.db"
            if alt_db.exists():
                return alt_db

        return None

    def is_rekordbox_running(self) -> bool:
        """Check if rekordbox.exe is currently active on the system."""
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"]
                if name and "rekordbox" in name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def create_snapshot_backup(self) -> Optional[Path]:
        """
        Create a timestamped backup snapshot of master.db before any write operation.
        Returns the backup file path.
        """
        if not self.db_path or not self.db_path.exists():
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"master_backup_cue_nalyzer_{timestamp}.db"

        # Copy master.db and any WAL/journal files
        shutil.copy2(self.db_path, backup_file)

        # Retain last 10 backups to preserve disk space
        self._prune_old_backups(max_keep=10)
        return backup_file

    def _prune_old_backups(self, max_keep: int = 10):
        """Keep only the most recent N backup snapshots."""
        if not self.backup_dir or not self.backup_dir.exists():
            return
        backups = sorted(
            self.backup_dir.glob("master_backup_cue_nalyzer_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[max_keep:]:
            try:
                old.unlink(missing_ok=True)
            except Exception:
                pass

    def list_backups(self) -> List[Path]:
        """List all available backup snapshots."""
        if not self.backup_dir or not self.backup_dir.exists():
            return []
        return sorted(
            self.backup_dir.glob("master_backup_cue_nalyzer_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def restore_backup(self, backup_path: Optional[str] = None) -> bool:
        """Restore master.db from the latest or specified backup snapshot."""
        if not self.db_path:
            return False

        if backup_path:
            target = Path(backup_path)
        else:
            backups = self.list_backups()
            if not backups:
                return False
            target = backups[0]

        if not target.exists():
            return False

        if self.is_rekordbox_running():
            raise RuntimeError("Cannot restore database while Rekordbox is running. Please close Rekordbox first.")

        shutil.copy2(target, self.db_path)
        return True
