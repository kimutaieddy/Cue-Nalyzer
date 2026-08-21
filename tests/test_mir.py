"""Unit tests for MIR components: BeatTracker, KeyDetector, EnergyAnalyzer, VocalDetector, RhythmAnalyzer."""

import numpy as np
import pytest
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import BeatGrid, EnergyProfile
from cue_nalyzer.mir.beat_tracker import BeatTracker
from cue_nalyzer.mir.energy_analyzer import EnergyAnalyzer
from cue_nalyzer.mir.key_detector import KeyDetector
from cue_nalyzer.mir.rhythm_analyzer import RhythmAnalyzer
from cue_nalyzer.mir.vocal_detector import VocalDetector


@pytest.fixture
def synthetic_audio():
    """Generate 10 seconds of synthetic 120 BPM 4/4 audio with 440 Hz (A) tone and kick pulses."""
    sr = 22050
    duration = 10.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # 440 Hz Tone (A major / minor fundamental)
    tone = 0.5 * np.sin(2 * np.pi * 440.0 * t)

    # 120 BPM Kick pulses (every 0.5s)
    kicks = np.zeros_like(t)
    beat_interval = int(0.5 * sr)
    for b in range(0, len(t), beat_interval):
        # 60 Hz decaying sub kick
        kick_len = min(int(0.1 * sr), len(t) - b)
        kick_t = np.linspace(0, 0.1, kick_len)
        kicks[b : b + kick_len] += np.sin(2 * np.pi * 60.0 * kick_t) * np.exp(-kick_t * 30.0)

    y = tone + kicks
    # Normalize
    y = y / np.max(np.abs(y))
    return y.astype(np.float32), sr


def test_beat_tracker(synthetic_audio):
    y, sr = synthetic_audio
    tracker = BeatTracker()
    grid = tracker.analyze(y, sr)

    assert isinstance(grid, BeatGrid)
    assert 115.0 <= grid.bpm <= 125.0
    assert len(grid.beat_times) > 10
    assert len(grid.downbeat_times) > 2
    assert grid.beats_per_bar == 4


def test_key_detector(synthetic_audio):
    y, sr = synthetic_audio
    detector = KeyDetector()
    key_info = detector.analyze(y, sr)

    assert key_info.root_key in ["A", "D", "E"]
    assert key_info.camelot is not None
    assert key_info.confidence > 0.4


def test_energy_analyzer(synthetic_audio):
    y, sr = synthetic_audio
    analyzer = EnergyAnalyzer()
    energy, waveform = analyzer.analyze(y, sr)

    assert isinstance(energy, EnergyProfile)
    assert len(energy.overall_rms) > 0
    assert len(energy.low_band_energy) > 0
    assert waveform.num_samples == 1200
    assert len(waveform.low_peaks) == 1200


def test_vocal_detector(synthetic_audio):
    y, sr = synthetic_audio
    tracker = BeatTracker()
    grid = tracker.analyze(y, sr)

    detector = VocalDetector()
    vocals = detector.analyze(y, sr, grid)

    assert 0.0 <= vocals.vocal_ratio <= 1.0
    assert len(vocals.vocal_presence_curve) > 0


def test_rhythm_analyzer(synthetic_audio):
    y, sr = synthetic_audio
    tracker = BeatTracker()
    grid = tracker.analyze(y, sr)

    analyzer = RhythmAnalyzer()
    rhythm = analyzer.analyze(y, sr, grid)

    assert 0.0 <= rhythm.syncopation_index <= 1.0
    assert 0.0 <= rhythm.kick_regularity <= 1.0
    assert rhythm.groove_type in ["Four-On-The-Floor", "Syncopated-Groove", "Amapiano Log-Drum Groove", "Afro Polyrhythmic Groove", "High-Speed Breakbeat", "Syncopated Broken Beat"]

