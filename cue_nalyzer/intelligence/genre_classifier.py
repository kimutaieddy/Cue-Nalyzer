"""Probabilistic genre classification and contextual musical priors."""

from typing import Dict, List, Optional, Tuple
import numpy as np
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import (
    BeatGrid,
    EnergyProfile,
    GenrePrediction,
    RhythmProfile,
    VocalActivity,
)


class GenreClassifier:
    """Classifies track into probabilistic electronic and urban DJ genres."""

    GENRES = [
        "Amapiano",
        "Afro House",
        "Deep House",
        "Tech House / Techno",
        "Progressive House",
        "Drum & Bass",
        "Hip-Hop / R&B",
        "Melodic House",
    ]

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def classify(
        self,
        beat_grid: BeatGrid,
        rhythm: RhythmProfile,
        energy: EnergyProfile,
        vocals: VocalActivity,
    ) -> GenrePrediction:
        """
        Compute probabilistic genre likelihoods using tempo, syncopation,
        log drums, polyrhythmic density, and vocal metrics.
        """
        bpm = beat_grid.bpm
        scores: Dict[str, float] = {g: 0.05 for g in self.GENRES}
        characteristics: List[str] = []

        # 1. Amapiano Scoring
        # BPM 108-118, high log drum presence, syncopated groove, moderate swing
        if 108.0 <= bpm <= 118.0:
            scores["Amapiano"] += 0.40
            if rhythm.log_drum_activity > 0.5:
                scores["Amapiano"] += 0.50
                characteristics.append("Signature pitch-bending log drum basslines")
            if rhythm.syncopation_index > 0.35:
                scores["Amapiano"] += 0.25
                characteristics.append("Syncopated South African shaker & rim patterns")
        elif 105.0 <= bpm <= 122.0 and rhythm.log_drum_activity > 0.6:
            scores["Amapiano"] += 0.45

        # 2. Afro House Scoring
        # BPM 118-124, 3-stroke polyrhythms, organic percussion, moderate vocal presence
        if 117.0 <= bpm <= 124.5:
            scores["Afro House"] += 0.35
            if rhythm.polyrhythm_density > 0.55:
                scores["Afro House"] += 0.45
                characteristics.append("Rich polyrhythmic conga/shaker layering")
            if beat_grid.swing_factor > 0.15:
                scores["Afro House"] += 0.20
                characteristics.append("Organic swing groove")
            if vocals.vocal_ratio > 0.25:
                scores["Afro House"] += 0.15

        # 3. Deep House / Melodic House
        if 120.0 <= bpm <= 126.0:
            scores["Deep House"] += 0.30
            scores["Melodic House"] += 0.25
            if rhythm.kick_regularity > 0.8:
                scores["Deep House"] += 0.25
                scores["Melodic House"] += 0.25
                characteristics.append("Steady 4-on-the-floor kick foundation")
            if energy.dynamic_range_db > 14.0:
                scores["Melodic House"] += 0.25
                characteristics.append("Dynamic melodic buildup & breakdown arcs")

        # 4. Tech House / Techno
        if 124.0 <= bpm <= 135.0:
            scores["Tech House / Techno"] += 0.40
            if rhythm.kick_regularity > 0.85:
                scores["Tech House / Techno"] += 0.35
            if vocals.vocal_ratio < 0.20:
                scores["Tech House / Techno"] += 0.25
                characteristics.append("Hypnotic, percussion-driven club texture")

        # 5. Progressive House
        if 122.0 <= bpm <= 128.0:
            scores["Progressive House"] += 0.25
            if energy.dynamic_range_db > 16.0:
                scores["Progressive House"] += 0.35
                characteristics.append("Extended atmospheric buildups and tension releases")

        # 6. Drum & Bass
        if 165.0 <= bpm <= 180.0:
            scores["Drum & Bass"] += 0.90
            characteristics.append("Fast 170+ BPM breakbeat rhythm")

        # 7. Hip-Hop / R&B
        if 70.0 <= bpm <= 104.0:
            scores["Hip-Hop / R&B"] += 0.65
            if vocals.vocal_ratio > 0.45:
                scores["Hip-Hop / R&B"] += 0.30
                characteristics.append("Vocal-centric verse and hook structure")

        # Softmax normalization across probabilities
        raw_vals = np.array(list(scores.values()))
        exp_vals = np.exp(raw_vals * 3.0)  # Temperature scaling
        probs = exp_vals / np.sum(exp_vals)

        prob_dict = {k: round(float(p), 3) for k, p in zip(scores.keys(), probs)}

        # Determine primary genre
        sorted_genres = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
        primary_genre, primary_conf = sorted_genres[0]
        subgenre = sorted_genres[1][0] if sorted_genres[1][1] > 0.20 else None

        # Build reasoning text
        reasoning = (
            f"Classified primarily as {primary_genre} ({int(primary_conf * 100)}% confidence) based on {bpm:.1f} BPM tempo, "
            f"syncopation index of {rhythm.syncopation_index:.2f}, log drum activity of {rhythm.log_drum_activity:.2f}, "
            f"and polyrhythm density of {rhythm.polyrhythm_density:.2f}."
        )

        return GenrePrediction(
            primary_genre=primary_genre,
            primary_confidence=primary_conf,
            probabilities=prob_dict,
            subgenre=subgenre,
            genre_characteristics=characteristics if characteristics else ["Standard 4/4 Electronic Arrangement"],
            reasoning=reasoning,
        )

