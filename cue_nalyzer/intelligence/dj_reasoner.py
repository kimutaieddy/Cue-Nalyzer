"""Contextual DJ reasoning engine and natural-language explainability generator."""

from typing import List, Optional
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import (
    BeatGrid,
    DJCuePoint,
    EnergyProfile,
    GenrePrediction,
    KeyInfo,
    MusicalEvidence,
    RhythmProfile,
    StructureSegment,
    VocalActivity,
)


class DJReasoner:
    """Provides high-level DJ mixing insights, clash risk assessments, and explainability narratives."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def generate_dj_summary(
        self,
        beat_grid: BeatGrid,
        key_info: KeyInfo,
        genre: GenrePrediction,
        rhythm: RhythmProfile,
        energy: EnergyProfile,
        vocals: VocalActivity,
        structure: List[StructureSegment],
        cues: List[DJCuePoint],
    ) -> str:
        """
        Synthesize a comprehensive DJ briefing for the track covering mixing strategy,
        energy flow, vocal clash warnings, and genre nuances.
        """
        lines = []

        # 1. Overview
        lines.append(f"🎧 **DJ INTELLIGENCE SUMMARY: {genre.primary_genre} ({beat_grid.bpm:.1f} BPM | Key: {key_info.camelot} - {key_info.key_name})**")
        lines.append("")

        # 2. Energy & Arrangement flow
        num_drops = sum(1 for s in structure if "DROP" in s.label.value)
        lines.append(
            f"• **Arrangement & Dynamics:** {len(structure)} structural sections with {num_drops} detected peak release moments. "
            f"Dynamic range is {energy.dynamic_range_db:.1f} dB with an average loudness of {energy.average_lufs:.1f} LUFS."
        )

        # 3. Vocal Presence & Clash Safety
        if vocals.vocal_ratio > 0.40:
            lines.append(
                f"• **Vocal Profile:** Heavy vocal presence ({int(vocals.vocal_ratio * 100)}% of track). "
                "High vocal clash risk if layered with another vocal-heavy track. Use instrumental intros/outros for blends."
            )
        elif vocals.vocal_ratio > 0.15:
            lines.append(
                f"• **Vocal Profile:** Moderate vocal hooks ({int(vocals.vocal_ratio * 100)}% of track). "
                f"Instrumental intro ({'Available' if vocals.has_extended_instrumental_intro else 'Short'}) and outro ({'Available' if vocals.has_extended_instrumental_outro else 'Short'})."
            )
        else:
            lines.append(
                "• **Vocal Profile:** Primarily instrumental (<15% vocal activity). Very safe for extended harmonic layering and long blends."
            )

        # 4. Genre Specific DJ Advice
        if genre.primary_genre == "Amapiano":
            lines.append(
                "• **Amapiano Mixing Advice:** Distinct log-drum transient baseline. Recommended to swap basslines cleanly at 16-bar phrase boundaries rather than layering sub frequencies to prevent low-end mud."
            )
        elif genre.primary_genre == "Afro House":
            lines.append(
                "• **Afro House Mixing Advice:** Rich polyrhythmic groove. Excellent for long 32-bar percussion blends. Maintain high-pass filters on the incoming track until phrase drops."
            )
        elif "House" in genre.primary_genre:
            lines.append(
                "• **House Mixing Advice:** Standard 16/32-bar phrase structure. Match downbeats cleanly on Bar 1. The main breakdown provides an ideal window for teasing incoming vocal stems."
            )

        # 5. Cue Highlights
        mix_in = next((c for c in cues if "MIX_IN" in c.cue_type.value), None)
        main_drop = next((c for c in cues if c.cue_type.value == "DROP"), None)
        mix_out = next((c for c in cues if "MIX_OUT" in c.cue_type.value), None)

        cue_points_summary = []
        if mix_in:
            cue_points_summary.append(f"Mix-In at {self._format_time(mix_in.timestamp)} (Bar {mix_in.bar_number})")
        if main_drop:
            cue_points_summary.append(f"Main Drop at {self._format_time(main_drop.timestamp)} (Bar {main_drop.bar_number})")
        if mix_out:
            cue_points_summary.append(f"Mix-Out at {self._format_time(mix_out.timestamp)} (Bar {mix_out.bar_number})")

        if cue_points_summary:
            lines.append(f"• **Key Cue Targets:** {' | '.join(cue_points_summary)}")

        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """Format seconds into MM:SS.S timestamp."""
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:04.1f}"

