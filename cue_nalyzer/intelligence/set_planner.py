"""Library-level set planning, harmonic Camelot mixing rules, and transition advice."""

import re
from typing import List, Optional, Tuple
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis, TransitionAdvice


class SetPlanner:
    """Evaluates transition compatibility between tracks in a DJ library."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def evaluate_transition(self, track_a: TrackAnalysis, track_b: TrackAnalysis) -> TransitionAdvice:
        """
        Compute harmonic compatibility, BPM stretch, overlap phrasing, and clash risks
        between outgoing Track A and incoming Track B.
        """
        # 1. Harmonic Compatibility (Camelot Wheel analysis)
        harm_label, harm_score = self._evaluate_camelot(track_a.key_info.camelot, track_b.key_info.camelot)

        # 2. BPM difference
        bpm_a = track_a.beat_grid.bpm
        bpm_b = track_b.beat_grid.bpm
        bpm_diff_pct = round(((bpm_b - bpm_a) / bpm_a) * 100.0, 2)
        pitch_adj = round(-bpm_diff_pct, 2)

        # 3. Align Mix-Out of Track A with Mix-In of Track B
        mix_out = next((c for c in track_a.cue_points if "MIX_OUT" in c.cue_type.value), None)
        mix_in = next((c for c in track_b.cue_points if "MIX_IN" in c.cue_type.value), None)

        warnings: List[str] = []

        # BPM Compatibility
        if abs(bpm_diff_pct) > 6.0:
            warnings.append(f"Significant BPM difference ({bpm_diff_pct:+.1f}%). Requires substantial pitch fader adjustment.")
            bpm_score = max(0.0, 100.0 - abs(bpm_diff_pct) * 8.0)
        else:
            bpm_score = 100.0 - abs(bpm_diff_pct) * 2.5

        # Vocal Clash Risk
        vocal_risk = False
        if track_a.vocals.vocal_ratio > 0.30 and not track_b.vocals.has_extended_instrumental_intro:
            warnings.append("Vocal clash risk: Track A outro may overlap with Track B vocals. Use EQ mid cut or wait for vocal pause.")
            vocal_risk = True

        # Transition Style heuristic
        if harm_score >= 90 and abs(bpm_diff_pct) <= 3.5:
            transition_style = "Long 32-Bar Harmonic Blend"
        elif "DROP" in [c.cue_type.value for c in track_b.cue_points]:
            transition_style = "Breakdown to Drop Transition"
        elif abs(bpm_diff_pct) > 4.0:
            transition_style = "Quick 8-Bar Cut on Phrase Start"
        else:
            transition_style = "Standard 16-Bar Bass Swap"

        # Overall Score calculation (weighted: 50% Harmonic, 35% BPM, 15% Arrangement)
        vocal_penalty = 15.0 if vocal_risk else 0.0
        total_score = round(max(0.0, min(100.0, (harm_score * 0.50) + (bpm_score * 0.35) + 15.0 - vocal_penalty)), 1)

        explanation = (
            f"Transition from '{track_a.metadata.title}' to '{track_b.metadata.title}': "
            f"Harmonic relationship is {harm_label} ({track_a.key_info.camelot} → {track_b.key_info.camelot}). "
            f"BPM delta is {bpm_diff_pct:+.1f}%. Recommended approach: {transition_style}."
        )

        return TransitionAdvice(
            track_a_id=track_a.metadata.file_hash,
            track_b_id=track_b.metadata.file_hash,
            harmonic_compatibility=harm_label,
            harmonic_score=harm_score,
            bpm_diff_pct=bpm_diff_pct,
            pitch_adjustment_needed_pct=pitch_adj,
            recommended_mix_out_point=mix_out,
            recommended_mix_in_point=mix_in,
            transition_style=transition_style,
            transition_score=total_score,
            explanation=explanation,
            warnings=warnings,
        )

    def find_best_next_tracks(
        self, current_track: TrackAnalysis, library: List[TrackAnalysis], limit: int = 5
    ) -> List[Tuple[TrackAnalysis, TransitionAdvice]]:
        """Rank library tracks by transition compatibility score to follow the current track."""
        scored_tracks = []
        for candidate in library:
            if candidate.metadata.file_hash == current_track.metadata.file_hash:
                continue
            advice = self.evaluate_transition(current_track, candidate)
            scored_tracks.append((candidate, advice))

        scored_tracks.sort(key=lambda x: x[1].transition_score, reverse=True)
        return scored_tracks[:limit]

    def _evaluate_camelot(self, cam_a: str, cam_b: str) -> Tuple[str, float]:
        """
        Evaluate Camelot Wheel distance (e.g. '8A' to '9A').
        """
        match_a = re.match(r"^(\d+)([ABab])$", cam_a.strip())
        match_b = re.match(r"^(\d+)([ABab])$", cam_b.strip())

        if not match_a or not match_b:
            return "UNKNOWN", 50.0

        num_a, letter_a = int(match_a.group(1)), match_a.group(2).upper()
        num_b, letter_b = int(match_b.group(1)), match_b.group(2).upper()

        if num_a == num_b and letter_a == letter_b:
            return "PERFECT_MATCH (Same Key)", 100.0

        if letter_a == letter_b:
            # Distance on 12-hour clock
            diff = (num_b - num_a) % 12
            if diff == 1:
                return "ENERGY_BOOST (+1 Camelot)", 95.0
            elif diff == 11:
                return "SUBDOMINANT_DOWN (-1 Camelot)", 90.0
            elif diff == 2:
                return "WHOLE_TONE_RAISE (+2 Camelot)", 75.0
            elif diff == 10:
                return "WHOLE_TONE_DROP (-2 Camelot)", 70.0
            else:
                return f"HARMONIC_JUMP ({diff} steps)", 40.0

        # Relative Major/Minor (Same number, different letter)
        if num_a == num_b and letter_a != letter_b:
            return "RELATIVE_SCALE (Major/Minor Swap)", 92.0

        # Diagonal shift (e.g., 8A -> 9B)
        diff = (num_b - num_a) % 12
        if diff in [1, 11]:
            return "DIAGONAL_MODULATION (Subtle Lift)", 80.0

        return "HARMONIC_CLASH", 30.0

