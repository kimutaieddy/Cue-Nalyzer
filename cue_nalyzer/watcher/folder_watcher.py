"""Background auto-watch folder monitor for zero-touch DJ music intelligence."""

import os
from pathlib import Path
import threading
import time
from typing import Callable, Dict, List, Optional, Set
from cue_nalyzer.analyzer import AnalyzerEngine
from cue_nalyzer.core.cache import AnalysisCache
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis
from cue_nalyzer.rekordbox.db_integrator import RekordboxDBIntegrator


class WatchFolderManager:
    """
    Monitors music folders in the background. Automatically analyzes newly added
    tracks and syncs Hot Cues to Rekordbox master.db with zero user interaction.
    """

    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aiff", ".ogg"}

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.engine = AnalyzerEngine(self.config)
        self.cache = AnalysisCache(self.config)
        self.rekordbox_db = RekordboxDBIntegrator(self.config)

        self._watch_paths: Set[str] = set()
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._known_files: Dict[str, float] = {}  # path -> mtime
        self._callbacks: List[Callable[[TrackAnalysis], None]] = []

    def add_watch_folder(self, folder_path: str):
        """Add a directory to the active watch list."""
        p = Path(folder_path).resolve()
        if p.is_dir():
            self._watch_paths.add(str(p))
            self._scan_initial_files(p)

    def remove_watch_folder(self, folder_path: str):
        """Remove a directory from the watch list."""
        p_str = str(Path(folder_path).resolve())
        self._watch_paths.discard(p_str)

    def get_watch_folders(self) -> List[str]:
        """Return list of monitored directories."""
        return sorted(list(self._watch_paths))

    def register_callback(self, callback: Callable[[TrackAnalysis], None]):
        """Register listener for newly analyzed tracks."""
        self._callbacks.append(callback)

    def _scan_initial_files(self, folder: Path):
        """Scan directory and index known files."""
        for item in folder.rglob("*"):
            if item.is_file() and item.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    self._known_files[str(item)] = item.stat().st_mtime
                except Exception:
                    pass

    def start(self, poll_interval_sec: float = 3.0):
        """Start background watching thread."""
        if self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._watch_loop, args=(poll_interval_sec,), daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background watching thread."""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _watch_loop(self, poll_interval: float):
        """Poll watch directories for new audio files."""
        while self._is_running:
            for folder_str in list(self._watch_paths):
                folder = Path(folder_str)
                if not folder.is_dir():
                    continue

                for item in folder.rglob("*"):
                    if not self._is_running:
                        break

                    if item.is_file() and item.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        p_str = str(item)
                        try:
                            mtime = item.stat().st_mtime
                        except Exception:
                            continue

                        # Check if new file or updated file
                        if p_str not in self._known_files or mtime > self._known_files[p_str]:
                            # Wait briefly for file write completion if download in progress
                            if self._is_file_stable(item):
                                self._known_files[p_str] = mtime
                                self._process_new_file(p_str)

            time.sleep(poll_interval)

    def _is_file_stable(self, file_path: Path, wait_sec: float = 1.0) -> bool:
        """Ensure file has completed downloading or copying to disk."""
        try:
            size1 = file_path.stat().st_size
            time.sleep(wait_sec)
            size2 = file_path.stat().st_size
            return size1 == size2 and size1 > 1024
        except Exception:
            return False

    def _process_new_file(self, file_path: str):
        """Analyze new file and commit to Rekordbox master.db."""
        try:
            analysis = self.engine.analyze_track(file_path, force_recompute=False)
            for cb in self._callbacks:
                try:
                    cb(analysis)
                except Exception:
                    pass
        except Exception as e:
            print(f"[WatchFolder] Error auto-analyzing {file_path}: {e}")

