"""High-performance batch and playlist analyzer with intelligent caching and multi-worker execution."""

import concurrent.futures
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional
from cue_nalyzer.analyzer import AnalyzerEngine
from cue_nalyzer.core.audio_loader import AudioLoader
from cue_nalyzer.core.cache import AnalysisCache
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis
from cue_nalyzer.export.rekordbox_xml import RekordboxXMLExporter
from cue_nalyzer.rekordbox.db_integrator import RekordboxDBIntegrator


@dataclass
class BatchResult:
    """Summary of batch folder / playlist analysis."""
    total_found: int = 0
    analyzed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    analyses: List[TrackAnalysis] = field(default_factory=list)
    failed_files: List[str] = field(default_factory=list)
    rekordbox_xml_path: Optional[str] = None
    rekordbox_db_synced: bool = False
    rekordbox_db_message: Optional[str] = None


class BatchProcessor:
    """Processes folders and playlists with worker pools, instant caching, and Rekordbox auto-sync."""

    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aiff", ".ogg"}

    def __init__(self, config: Optional[Config] = None, max_workers: Optional[int] = None):
        self.config = config or Config()
        self.cache = AnalysisCache(self.config)
        self.loader = AudioLoader(self.config)
        self.rekordbox_exporter = RekordboxXMLExporter(self.config)
        self.rekordbox_db = RekordboxDBIntegrator(self.config)
        # Default workers: half of CPU count or min 2 to keep system responsive
        cpu = os.cpu_count() or 4
        self.max_workers = max_workers or max(1, min(4, cpu // 2))

    def discover_audio_files(self, folder_path: str, recursive: bool = True) -> List[Path]:
        """Scan directory for supported audio formats."""
        p = Path(folder_path).resolve()
        if not p.is_dir():
            raise NotADirectoryError(f"Provided path is not a directory: {folder_path}")

        files = []
        iterator = p.rglob("*") if recursive else p.glob("*")
        for item in iterator:
            if item.is_file() and item.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                files.append(item)

        return sorted(files)

    def process_folder(
        self,
        folder_path: str,
        force_recompute: bool = False,
        progress_callback: Optional[Callable[[int, int, str, str, Optional[TrackAnalysis]], None]] = None,
        auto_sync_rekordbox: bool = True,
    ) -> BatchResult:
        """
        Process a playlist folder with parallel worker pool and instant caching.
        
        progress_callback signature: (current_idx, total_count, filename, status_label, analysis_or_none)
        """
        audio_files = self.discover_audio_files(folder_path)
        total = len(audio_files)

        result = BatchResult(total_found=total)
        if total == 0:
            return result

        to_analyze: List[Path] = []

        # 1. Instant Cache Pre-Scan (< 1ms per file)
        for idx, file_p in enumerate(audio_files, start=1):
            if not force_recompute:
                cached = self.cache.get_analysis_by_path(str(file_p))
                if cached:
                    result.skipped_count += 1
                    result.analyses.append(cached)
                    if progress_callback:
                        progress_callback(idx, total, file_p.name, "SKIPPED (Cached)", cached)
                    continue

            to_analyze.append(file_p)

        # 2. Process remaining tracks with concurrent worker pool
        if to_analyze:
            engine = AnalyzerEngine(self.config)
            completed_so_far = result.skipped_count

            def _analyze_single(fp: Path):
                return fp, engine.analyze_track(str(fp), force_recompute=force_recompute)

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {executor.submit(_analyze_single, fp): fp for fp in to_analyze}

                for future in concurrent.futures.as_completed(future_to_file):
                    fp = future_to_file[future]
                    completed_so_far += 1
                    try:
                        _, analysis = future.result()
                        result.analyzed_count += 1
                        result.analyses.append(analysis)
                        if progress_callback:
                            progress_callback(completed_so_far, total, fp.name, "COMPLETED", analysis)
                    except Exception as e:
                        result.failed_count += 1
                        result.failed_files.append(f"{fp.name}: {str(e)}")
                        if progress_callback:
                            progress_callback(completed_so_far, total, fp.name, f"FAILED ({str(e)})", None)

        # 3. Synchronize Rekordbox XML bridge
        if auto_sync_rekordbox and result.analyses:
            folder_name = Path(folder_path).name
            xml_path = str(Path(folder_path) / f"{folder_name}_rekordbox.xml")
            self.rekordbox_exporter.export_to_file(result.analyses, xml_path, playlist_name=folder_name)
            result.rekordbox_xml_path = xml_path
            
            # Also update global master library XML
            self.rekordbox_exporter.sync_master_library(self.cache.list_all_tracks())

        # 4. Directly synchronize with Rekordbox Master DB (master.db)
        if result.analyses:
            db_res = self.rekordbox_db.sync_analyses_to_rekordbox(result.analyses)
            result.rekordbox_db_synced = db_res.get("success", False)
            result.rekordbox_db_message = db_res.get("message", "")

        return result

