"""Main Analyzer Engine: Coordinates audio decoding, MIR processing, and DJ reasoning."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from cue_nalyzer.core.audio_loader import AudioLoader
from cue_nalyzer.core.cache import AnalysisCache
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis
from cue_nalyzer.export.rekordbox_xml import RekordboxXMLExporter
from cue_nalyzer.intelligence.cue_generator import CueGenerator
from cue_nalyzer.intelligence.dj_reasoner import DJReasoner
from cue_nalyzer.intelligence.genre_classifier import GenreClassifier
from cue_nalyzer.mir.beat_tracker import BeatTracker
from cue_nalyzer.mir.energy_analyzer import EnergyAnalyzer
from cue_nalyzer.mir.key_detector import KeyDetector
from cue_nalyzer.mir.rhythm_analyzer import RhythmAnalyzer
from cue_nalyzer.mir.segmenter import StructuralSegmenter
from cue_nalyzer.mir.vocal_detector import VocalDetector
from cue_nalyzer.rekordbox.db_integrator import RekordboxDBIntegrator


class AnalyzerEngine:
    """End-to-end intelligent DJ music analysis engine."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.loader = AudioLoader(self.config)
        self.cache = AnalysisCache(self.config)
        self.beat_tracker = BeatTracker(self.config)
        self.key_detector = KeyDetector(self.config)
        self.energy_analyzer = EnergyAnalyzer(self.config)
        self.vocal_detector = VocalDetector(self.config)
        self.rhythm_analyzer = RhythmAnalyzer(self.config)
        self.segmenter = StructuralSegmenter(self.config)
        self.genre_classifier = GenreClassifier(self.config)
        self.cue_generator = CueGenerator(self.config)
        self.dj_reasoner = DJReasoner(self.config)
        self.rekordbox_exporter = RekordboxXMLExporter(self.config)
        self.rekordbox_db = RekordboxDBIntegrator(self.config)

    def analyze_track(self, file_path: str, force_recompute: bool = False) -> TrackAnalysis:
        """
        Run complete multi-layer musical intelligence analysis on an audio file.
        Uses cached results unless force_recompute is True.
        """
        p = Path(file_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Check Cache first
        file_hash = self.loader.compute_file_hash(str(p))
        if not force_recompute:
            cached = self.cache.get_analysis_by_hash(file_hash)
            if cached:
                return cached

        # 1. Load Audio & Extract Metadata
        y, sr, metadata = self.loader.load_audio(str(p))

        # 2. Beat & Bar Gridding (Downbeat phase & swing factor)
        beat_grid = self.beat_tracker.analyze(y, sr)

        # 3. Harmonic Key Analysis (Camelot Wheel & OpenKey)
        key_info = self.key_detector.analyze(y, sr)

        # 4. Multi-band Energy & 3-Band Waveform Peak Summary
        energy, waveform = self.energy_analyzer.analyze(y, sr)

        # 5. Vocal Formants & Presence Detection
        vocals = self.vocal_detector.analyze(y, sr, beat_grid)

        # 6. Rhythm, Syncopation & Log-Drum Intelligence
        rhythm = self.rhythm_analyzer.analyze(y, sr, beat_grid)

        # 7. Structural Phrase-Locked Segmentation
        structure = self.segmenter.analyze(y, sr, beat_grid, energy, vocals)

        # 8. Probabilistic Genre Context Engine
        genre = self.genre_classifier.classify(beat_grid, rhythm, energy, vocals)

        # 9. Contextual DJ Cue Generation
        cue_points = self.cue_generator.generate_cues(beat_grid, energy, vocals, structure, genre)

        # 10. Natural Language DJ Intelligence Summary
        dj_summary = self.dj_reasoner.generate_dj_summary(
            beat_grid, key_info, genre, rhythm, energy, vocals, structure, cue_points
        )

        analysis = TrackAnalysis(
            metadata=metadata,
            beat_grid=beat_grid,
            key_info=key_info,
            energy=energy,
            vocals=vocals,
            rhythm=rhythm,
            structure=structure,
            genre=genre,
            cue_points=cue_points,
            waveform=waveform,
            dj_summary=dj_summary,
            analysis_timestamp=datetime.now().isoformat(),
        )

        # Cache the computed analysis
        self.cache.save_analysis(analysis)

        # Automatically update master Rekordbox XML bridge as fallback
        try:
            all_tracks = self.cache.list_all_tracks()
            self.rekordbox_exporter.sync_master_library(all_tracks)
        except Exception:
            pass

        # Directly sync to Rekordbox Master DB (master.db) with safety snapshot
        try:
            self.rekordbox_db.sync_analyses_to_rekordbox([analysis])
        except Exception:
            pass

        return analysis

