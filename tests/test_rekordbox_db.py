"""Unit tests for Rekordbox Master Database Safety, Backups, and Direct Integration."""

import os
from pathlib import Path
import pytest
from cue_nalyzer.core.models import (
    BeatGrid,
    EnergyProfile,
    GenrePrediction,
    SectionType,
    StructureSegment,
    TrackAnalysis,
    TrackMetadata,
    VocalActivity,
    VocalSegment,
)
from cue_nalyzer.intelligence.cue_generator import CueGenerator
from cue_nalyzer.rekordbox.db_integrator import RekordboxDBIntegrator
from cue_nalyzer.rekordbox.safety import RekordboxSafetyManager


def test_rekordbox_safety_manager_backup(tmp_path):
    # Create fake master.db
    fake_db = tmp_path / "master.db"
    fake_db.write_bytes(b"SQLCipher_Header_Test_Data" * 50)

    safety = RekordboxSafetyManager(str(fake_db))
    assert safety.db_path == fake_db

    # Create backup snapshot
    backup = safety.create_snapshot_backup()
    assert backup is not None
    assert backup.exists()
    assert backup.read_bytes() == fake_db.read_bytes()

    backups = safety.list_backups()
    assert len(backups) == 1
    assert backups[0] == backup


def test_cue_generator_produces_5_plus_cues():
    generator = CueGenerator()

    # 124 BPM, 128 bars track (approx 4 minutes)
    bar_duration = 60.0 / 124.0 * 4.0
    downbeats = [round(i * bar_duration, 3) for i in range(128)]

    beat_grid = BeatGrid(
        bpm=124.0,
        confidence=0.95,
        beat_times=[round(i * (bar_duration / 4), 3) for i in range(512)],
        downbeat_times=downbeats,
        bar_indices=list(range(128)),
        beats_per_bar=4,
    )
    energy = EnergyProfile()
    vocals = VocalActivity(
        vocal_ratio=0.45,
        vocal_segments=[
            VocalSegment(
                start_time=downbeats[32],
                end_time=downbeats[96],
                start_bar=33,
                end_bar=96,
                intensity=0.85,
                label="Vocal Verse & Chorus",
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
            energy_level=0.3,
            vocal_presence=0.0,
            bass_presence=0.3,
            description="Atmospheric Intro",
        ),
        StructureSegment(
            section_id=2,
            label=SectionType.GROOVE,
            start_time=downbeats[16],
            end_time=downbeats[32],
            start_bar=17,
            end_bar=32,
            num_bars=16,
            confidence=0.92,
            energy_level=0.6,
            vocal_presence=0.1,
            bass_presence=0.8,
            description="Main Beat Groove Entry",
        ),
        StructureSegment(
            section_id=3,
            label=SectionType.BREAKDOWN,
            start_time=downbeats[48],
            end_time=downbeats[64],
            start_bar=49,
            end_bar=64,
            num_bars=16,
            confidence=0.9,
            energy_level=0.3,
            vocal_presence=0.5,
            bass_presence=0.1,
            description="Breakdown exposing melody",
        ),
        StructureSegment(
            section_id=4,
            label=SectionType.DROP,
            start_time=downbeats[64],
            end_time=downbeats[96],
            start_bar=65,
            end_bar=96,
            num_bars=32,
            confidence=0.96,
            energy_level=0.95,
            vocal_presence=0.6,
            bass_presence=0.95,
            description="Main Peak Drop Climax",
        ),
        StructureSegment(
            section_id=5,
            label=SectionType.OUTRO,
            start_time=downbeats[112],
            end_time=downbeats[127],
            start_bar=113,
            end_bar=128,
            num_bars=16,
            confidence=0.94,
            energy_level=0.4,
            vocal_presence=0.0,
            bass_presence=0.4,
            description="Outro safe mix-out",
        ),
    ]
    genre = GenrePrediction(
        primary_genre="House / Tech House",
        primary_confidence=0.9,
        probabilities={"House / Tech House": 0.9},
        reasoning="Four on the floor drive",
    )

    cues = generator.generate_cues(beat_grid, energy, vocals, structure, genre)

    # Assert that at least 5 meaningful cues are produced
    assert len(cues) >= 5

    # Check that Cue A is Start at Bar 1
    assert cues[0].label == "Start"
    assert cues[0].bar_number == 1
    assert cues[0].hot_cue_index == 1

    # Check that subsequent cues are non-redundant and strictly increasing
    for i in range(len(cues) - 1):
        assert cues[i + 1].timestamp > cues[i].timestamp
        assert cues[i + 1].bar_number > cues[i].bar_number
        assert cues[i].hot_cue_index == i + 1
