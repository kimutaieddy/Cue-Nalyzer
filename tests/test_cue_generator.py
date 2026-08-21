"""Unit tests for Refined DJ Cue Generator, True Musical Start, and Non-Redundancy."""

from cue_nalyzer.core.models import (
    BeatGrid,
    EnergyProfile,
    GenrePrediction,
    SectionType,
    StructureSegment,
    VocalActivity,
    VocalSegment,
)
from cue_nalyzer.intelligence.cue_generator import CueGenerator


def test_cue_generator_cue_a_start_and_no_duplicates():
    generator = CueGenerator()

    # 124 BPM, 64 bars total
    bar_duration = 60.0 / 124.0 * 4.0
    downbeats = [round(i * bar_duration, 3) for i in range(64)]

    beat_grid = BeatGrid(
        bpm=124.0,
        confidence=0.95,
        beat_times=[round(i * (bar_duration / 4), 3) for i in range(256)],
        downbeat_times=downbeats,
        bar_indices=list(range(64)),
        beats_per_bar=4,
    )
    energy = EnergyProfile()
    vocals = VocalActivity(
        vocal_ratio=0.35,
        vocal_segments=[
            VocalSegment(
                start_time=downbeats[16],
                end_time=downbeats[32],
                start_bar=17,
                end_bar=32,
                intensity=0.8,
                label="Vocal Verse",
            )
        ],
    )
    structure = [
        StructureSegment(
            section_id=1,
            label=SectionType.INTRO,
            start_time=downbeats[0],
            end_time=downbeats[16],
            start_bar=1,
            end_bar=16,
            num_bars=16,
            confidence=0.9,
            energy_level=0.4,
            vocal_presence=0.0,
            bass_presence=0.3,
            description="Intro",
        ),
        StructureSegment(
            section_id=2,
            label=SectionType.DROP,
            start_time=downbeats[32],
            end_time=downbeats[48],
            start_bar=33,
            end_bar=48,
            num_bars=16,
            confidence=0.95,
            energy_level=0.9,
            vocal_presence=0.5,
            bass_presence=0.9,
            description="Main Drop",
        ),
        StructureSegment(
            section_id=3,
            label=SectionType.OUTRO,
            start_time=downbeats[48],
            end_time=downbeats[63],
            start_bar=49,
            end_bar=64,
            num_bars=16,
            confidence=0.9,
            energy_level=0.4,
            vocal_presence=0.0,
            bass_presence=0.4,
            description="Outro",
        ),
    ]
    genre = GenrePrediction(
        primary_genre="Tech House / Techno",
        primary_confidence=0.85,
        probabilities={"Tech House / Techno": 0.85},
        reasoning="Test reasoning",
    )

    cues = generator.generate_cues(beat_grid, energy, vocals, structure, genre)

    # 1. Ensure at least 3 high-conviction cues are generated
    assert len(cues) >= 3

    # 2. Assert Cue A (Pad 1) is strictly the Track Start at Bar 1
    assert cues[0].label == "Start"
    assert cues[0].bar_number == 1
    assert cues[0].hot_cue_index == 1
    assert cues[0].timestamp == downbeats[0]

    # 3. Assert Cue B is strictly non-redundant (at least 8 bars away from Cue A)
    if len(cues) > 1:
        assert cues[1].bar_number >= 9
        assert cues[1].timestamp > cues[0].timestamp + 10.0

    # 4. Check chronological ordering and unique Hot Cue indices
    for i in range(len(cues) - 1):
        assert cues[i + 1].timestamp > cues[i].timestamp
        assert cues[i + 1].bar_number > cues[i].bar_number
        assert cues[i].hot_cue_index == i + 1


def test_amapiano_log_drum_cue_label():
    generator = CueGenerator()
    bar_duration = 60.0 / 112.0 * 4.0
    downbeats = [round(i * bar_duration, 3) for i in range(64)]

    beat_grid = BeatGrid(bpm=112.0, confidence=0.95, downbeat_times=downbeats, beats_per_bar=4)
    energy = EnergyProfile()
    vocals = VocalActivity()
    structure = [
        StructureSegment(
            section_id=1,
            label=SectionType.DROP,
            start_time=downbeats[16],
            end_time=downbeats[32],
            start_bar=17,
            end_bar=32,
            num_bars=16,
            confidence=0.9,
            energy_level=0.8,
            vocal_presence=0.2,
            bass_presence=0.9,
            description="Log drum drop",
        )
    ]
    genre = GenrePrediction(
        primary_genre="Amapiano",
        primary_confidence=0.9,
        probabilities={"Amapiano": 0.9},
        reasoning="Log drum basslines",
    )

    cues = generator.generate_cues(beat_grid, energy, vocals, structure, genre)
    cue_labels = [c.label for c in cues]
    assert "Start" in cue_labels
    assert "Log-Drum Drop" in cue_labels
