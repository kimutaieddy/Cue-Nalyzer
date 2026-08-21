"""Unit tests for Genre Classifier and Probabilistic Context Engine."""

from cue_nalyzer.core.models import BeatGrid, EnergyProfile, RhythmProfile, VocalActivity
from cue_nalyzer.intelligence.genre_classifier import GenreClassifier


def test_genre_amapiano_detection():
    classifier = GenreClassifier()

    beat_grid = BeatGrid(bpm=113.0, confidence=0.9, beats_per_bar=4)
    rhythm = RhythmProfile(
        syncopation_index=0.65,
        log_drum_activity=0.85,
        polyrhythm_density=0.3,
        kick_regularity=0.6,
        groove_type="Amapiano Log-Drum Groove",
    )
    energy = EnergyProfile(dynamic_range_db=12.0)
    vocals = VocalActivity(vocal_ratio=0.3)

    pred = classifier.classify(beat_grid, rhythm, energy, vocals)

    assert pred.primary_genre == "Amapiano"
    assert pred.primary_confidence > 0.5
    assert "Amapiano" in pred.probabilities


def test_genre_afro_house_detection():
    classifier = GenreClassifier()

    beat_grid = BeatGrid(bpm=122.0, confidence=0.9, swing_factor=0.25, beats_per_bar=4)
    rhythm = RhythmProfile(
        syncopation_index=0.5,
        log_drum_activity=0.1,
        polyrhythm_density=0.8,
        kick_regularity=0.8,
        groove_type="Afro Polyrhythmic Groove",
    )
    energy = EnergyProfile(dynamic_range_db=15.0)
    vocals = VocalActivity(vocal_ratio=0.35)

    pred = classifier.classify(beat_grid, rhythm, energy, vocals)

    assert pred.primary_genre == "Afro House"
    assert pred.primary_confidence > 0.4

