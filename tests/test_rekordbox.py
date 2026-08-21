"""Unit tests for Rekordbox XML exporter."""

import xml.etree.ElementTree as ET
from cue_nalyzer.core.models import (
    BeatGrid,
    CueType,
    DJCuePoint,
    EnergyProfile,
    GenrePrediction,
    KeyInfo,
    MusicalEvidence,
    TrackAnalysis,
    TrackMetadata,
    VocalActivity,
    WaveformSummary,
)
from cue_nalyzer.export.rekordbox_xml import RekordboxXMLExporter


def test_rekordbox_xml_generation():
    exporter = RekordboxXMLExporter()

    cue = DJCuePoint(
        cue_id="cue_1",
        timestamp=15.5,
        bar_number=8,
        beat_number=1,
        cue_type=CueType.SAFE_MIX_IN,
        label="Mix In",
        confidence=0.95,
        confidence_label="HIGH",
        color_hex="#00FF7F",
        reasoning="Clean phrase entry",
        musical_evidence=MusicalEvidence(),
        suggested_use="Start blend",
        hot_cue_index=1,
    )

    analysis = TrackAnalysis(
        metadata=TrackMetadata(
            file_path="D:/test/song.mp3",
            file_name="song.mp3",
            file_hash="test12345",
            duration_sec=180.0,
            sample_rate=44100,
            channels=2,
            title="Test Song",
            artist="DJ Master",
        ),
        beat_grid=BeatGrid(
            bpm=124.0,
            confidence=0.98,
            beat_times=[0.0, 0.5, 1.0],
            downbeat_times=[0.0, 2.0],
            bar_indices=[0, 1],
            beats_per_bar=4,
        ),
        key_info=KeyInfo(
            root_key="A",
            scale="Minor",
            key_name="A Minor",
            camelot="8A",
            openkey="1m",
            confidence=0.9,
        ),
        energy=EnergyProfile(),
        vocals=VocalActivity(),
        rhythm=None,  # Optional in models or defaults
        structure=[],
        genre=GenrePrediction(
            primary_genre="Afro House",
            primary_confidence=0.85,
            probabilities={"Afro House": 0.85},
            reasoning="Polyrhythmic groove",
        ),
        cue_points=[cue],
        waveform=WaveformSummary(num_samples=100),
        dj_summary="Test summary",
        analysis_timestamp="2026-08-21T00:00:00",
    )

    xml_str = exporter.generate_xml([analysis])

    # Validate that it parses as valid XML
    root = ET.fromstring(xml_str)
    assert root.tag == "DJ_PLAYLISTS"

    track = root.find(".//TRACK")
    assert track is not None
    assert track.attrib["Name"] == "Test Song"
    assert track.attrib["AverageBpm"] == "124.00"
    assert track.attrib["Tonality"] == "8A"

    # Check Hot Cue mark
    pos_mark = track.find(".//POSITION_MARK[@Num='0']")
    assert pos_mark is not None
    assert pos_mark.attrib["Name"] == "Mix In"

