"""Unit tests for Structural Segmenter and Phrase Alignment."""

import numpy as np
from cue_nalyzer.core.models import BeatGrid, EnergyProfile, VocalActivity
from cue_nalyzer.mir.segmenter import StructuralSegmenter


def test_structural_segmenter():
    segmenter = StructuralSegmenter()
    sr = 22050
    duration = 60.0
    y = np.random.randn(int(sr * duration)).astype(np.float32)

    # 120 BPM: 0.5s per beat, 2.0s per bar = 30 bars
    downbeats = list(np.arange(0.0, duration, 2.0))
    beat_times = list(np.arange(0.0, duration, 0.5))

    beat_grid = BeatGrid(
        bpm=120.0,
        confidence=0.95,
        beat_times=beat_times,
        downbeat_times=downbeats,
        bar_indices=list(range(len(downbeats))),
        beats_per_bar=4,
    )

    energy = EnergyProfile(
        time_step_sec=0.5,
        overall_rms=[0.4] * 30 + [0.8] * 60 + [0.3] * 30,
        low_band_energy=[0.4] * 30 + [0.9] * 60 + [0.2] * 30,
        mid_band_energy=[0.5] * 120,
        high_band_energy=[0.4] * 120,
        tension_curve=[0.3] * 120,
    )

    vocals = VocalActivity(
        vocal_ratio=0.2,
        vocal_presence_curve=[0.1] * 40 + [0.6] * 40 + [0.1] * 40,
        vocal_segments=[],
    )

    segments = segmenter.analyze(y, sr, beat_grid, energy, vocals)

    assert len(segments) >= 2
    # Ensure segments are phrase-aligned and cover track duration
    assert segments[0].start_time == 0.0
    assert segments[-1].end_time >= 55.0

