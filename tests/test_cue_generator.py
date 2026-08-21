"""Unit tests for DJ Cue Generator, Explainability Reasoning, and Camelot Set Planner."""

from cue_nalyzer.core.models import (
    BeatGrid,
    EnergyProfile,
    GenrePrediction,
    KeyInfo,
    SectionType,
    StructureSegment,
    TrackAnalysis,
    TrackMetadata,
    VocalActivity,
    VocalSegment,
    WaveformSummary,
)
from cue_nalyzer.intelligence.cue_generator import CueGenerator
from cue_nalyzer.intelligence.dj_reasoner import DJReasoner
from cue_nalyzer.intelligence.set_planner import SetPlanner


def test_cue_generator():
    generator = CueGenerator()

    beat_grid = BeatGrid(
        bpm=124.0,
        confidence=0.95,
        beat_times=[i * 0.4838 for i in range(128)],
        downbeat_times=[i * 1.935 for i in range(32)],
        bar_indices=list(range(32)),
        beats_per_bar=4,
    )
    energy = EnergyProfile()
    vocals = VocalActivity(
        vocal_ratio=0.3,
        vocal_segments=[
            VocalSegment(start_time=30.0, end_time=60.0, start_bar=16, end_bar=31, intensity=0.7, label="Main Hook")
        ],
    )
    structure = [
        StructureSegment(
            section_id=1,
            label=SectionType.INTRO,
            start_time=0.0,
            end_time=30.0,
            start_bar=1,
            end_bar=16,
            num_bars=16,
            confidence=0.9,
            energy_level=0.4,
            vocal_presence=0.1,
            bass_presence=0.3,
            description="Intro",
        ),
        StructureSegment(
            section_id=2,
            label=SectionType.DROP,
            start_time=30.0,
            end_time=60.0,
            start_bar=17,
            end_bar=32,
            num_bars=16,
            confidence=0.9,
            energy_level=0.9,
            vocal_presence=0.6,
            bass_presence=0.9,
            description="Drop",
        ),
    ]
    genre = GenrePrediction(
        primary_genre="Tech House / Techno",
        primary_confidence=0.8,
        probabilities={"Tech House / Techno": 0.8},
        reasoning="Test reasoning",
    )

    cues = generator.generate_cues(beat_grid, energy, vocals, structure, genre)

    assert len(cues) >= 3
    # Check that Hot Cue indices A-H (1-8) are assigned
    indices = [c.hot_cue_index for c in cues if c.hot_cue_index is not None]
    assert len(indices) == len(set(indices))  # All distinct


def test_set_planner_camelot_matching():
    planner = SetPlanner()

    advice = planner._evaluate_camelot("8A", "8A")
    assert advice[0].startswith("PERFECT_MATCH")
    assert advice[1] == 100.0

    advice_boost = planner._evaluate_camelot("8A", "9A")
    assert advice_boost[0].startswith("ENERGY_BOOST")
    assert advice_boost[1] == 95.0

    advice_rel = planner._evaluate_camelot("8A", "8B")
    assert advice_rel[0].startswith("RELATIVE_SCALE")
    assert advice_rel[1] == 92.0

