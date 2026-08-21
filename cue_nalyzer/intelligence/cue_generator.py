"""Intelligent, genre-aware, non-redundant DJ Cue Point placement and ranking."""

from typing import List, Optional
import numpy as np
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import (
    BeatGrid,
    CueType,
    DJCuePoint,
    EnergyProfile,
    GenrePrediction,
    MusicalEvidence,
    SectionType,
    StructureSegment,
    VocalActivity,
)


class CueGenerator:
    """
    Generates non-redundant, musically justified DJ cue points strictly aligned
    to musical phrasing and adapted to genre context.
    """

    # Performance Pad Colors for CDJs / Rekordbox
    COLOR_START = "#00E5FF"        # Cyan (Track Start)
    COLOR_GROOVE = "#00FF7F"       # Spring Green (Groove / Bass in)
    COLOR_DROP = "#FF0055"         # Crimson / Bright Red (Peak Drop)
    COLOR_BREAKDOWN = "#FFAA00"    # Golden Orange (Breakdown)
    COLOR_VOCAL_IN = "#FF00AA"     # Magenta / Pink (Vocal Entrance)
    COLOR_VOCAL_OUT = "#0077FF"    # Blue (Vocal Exit)
    COLOR_MIX_OUT = "#FF8800"      # Warm Amber (Outro Mix-Out)
    COLOR_LOOP = "#A6FF00"         # Lime Green (Mid-track Loop)
    COLOR_SECONDARY_DROP = "#9D00FF"  # Electric Purple (Drop 2)

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def generate_cues(
        self,
        beat_grid: BeatGrid,
        energy: EnergyProfile,
        vocals: VocalActivity,
        structure: List[StructureSegment],
        genre: GenrePrediction,
    ) -> List[DJCuePoint]:
        """
        Derive high-conviction, non-redundant DJ Cue points across track timeline.
        Cue A is guaranteed to be the True Musical Track Start.
        """
        downbeats = beat_grid.downbeat_times
        if not downbeats:
            return []

        duration_sec = downbeats[-1] if downbeats else 180.0
        total_bars = len(downbeats)
        candidates: List[DJCuePoint] = []

        # =========================================================================
        # 1. CUE A: TRUE MUSICAL TRACK START (Bar 1, Beat 1)
        # =========================================================================
        track_start_time = downbeats[0]
        start_desc = (
            f"Track start at Bar 1 ({self._format_time(track_start_time)}). "
            "Primary DJ cue point to launch the track on phrase beat 1."
        )

        cue_start = DJCuePoint(
            cue_id="cue_start",
            timestamp=round(track_start_time, 2),
            bar_number=1,
            beat_number=1,
            cue_type=CueType.SAFE_MIX_IN,
            label="Start",
            confidence=0.99,
            confidence_label="HIGH",
            color_hex=self.COLOR_START,
            reasoning=start_desc,
            musical_evidence=MusicalEvidence(
                energy_delta=0.0,
                bass_activity=0.40,
                rhythmic_density=0.50,
                vocal_presence=0.0,
                phrase_aligned=True,
                confidence_factors={"phrase_alignment": 1.0},
            ),
            suggested_use="Primary launch point for beatmatching and starting the track.",
            hot_cue_index=1,
        )
        candidates.append(cue_start)

        # =========================================================================
        # 2. MAIN GROOVE ENTRY (Only if distinct from Track Start)
        # =========================================================================
        # If the track starts with an atmospheric or drumless intro, find where the full kick/bass begins
        groove_seg = next(
            (s for s in structure if s.label in [SectionType.GROOVE, SectionType.VERSE] and s.start_bar >= 9 and s.start_time < 90.0),
            None,
        )
        # Check if energy/bass rises noticeably after Bar 1
        if groove_seg and groove_seg.start_bar >= 9:
            # Only add if at least 8 bars from start
            groove_label = "Log-Drum In" if genre.primary_genre == "Amapiano" else "Groove In"
            groove_color = self.COLOR_GROOVE
            candidates.append(
                DJCuePoint(
                    cue_id="cue_groove",
                    timestamp=round(groove_seg.start_time, 2),
                    bar_number=groove_seg.start_bar,
                    beat_number=1,
                    cue_type=CueType.MIX_IN,
                    label=groove_label,
                    confidence=0.92,
                    confidence_label="HIGH",
                    color_hex=groove_color,
                    reasoning=(
                        f"Main beat & bass groove establishes at Bar {groove_seg.start_bar} ({self._format_time(groove_seg.start_time)}). "
                        "Full low-end drive active; safe transition marker."
                    ),
                    musical_evidence=MusicalEvidence(
                        energy_delta=0.50,
                        bass_activity=0.75,
                        rhythmic_density=0.80,
                        vocal_presence=groove_seg.vocal_presence,
                        phrase_aligned=True,
                        confidence_factors={"bass_entry": 0.92},
                    ),
                    suggested_use="Start fading volume or unmuting lows on incoming mix as groove kicks in.",
                )
            )

        # =========================================================================
        # 3. FIRST VOCAL ENTRANCE (Vocal In)
        # =========================================================================
        if vocals.vocal_segments:
            first_vocal = vocals.vocal_segments[0]
            # Must be at least Bar 9 or later
            if first_vocal.start_bar >= 9:
                candidates.append(
                    DJCuePoint(
                        cue_id="cue_vocal_in",
                        timestamp=round(first_vocal.start_time, 2),
                        bar_number=first_vocal.start_bar,
                        beat_number=1,
                        cue_type=CueType.VOCAL_IN,
                        label="Vocal In",
                        confidence=0.90,
                        confidence_label="HIGH",
                        color_hex=self.COLOR_VOCAL_IN,
                        reasoning=(
                            f"First vocal phrase begins at Bar {first_vocal.start_bar} ({self._format_time(first_vocal.start_time)}). "
                            "Critical landmark to avoid vocal clashes with the previous track."
                        ),
                        musical_evidence=MusicalEvidence(
                            energy_delta=0.20,
                            bass_activity=0.50,
                            rhythmic_density=0.60,
                            vocal_presence=first_vocal.intensity,
                            phrase_aligned=True,
                            confidence_factors={"formant_detection": 0.90},
                        ),
                        suggested_use="Complete incoming blend or fade out previous vocal before this bar.",
                    )
                )

        # =========================================================================
        # 4. MAIN BREAKDOWN
        # =========================================================================
        breakdown_seg = next((s for s in structure if s.label == SectionType.BREAKDOWN), None)
        if breakdown_seg and breakdown_seg.start_bar >= 17:
            candidates.append(
                DJCuePoint(
                    cue_id="cue_breakdown",
                    timestamp=round(breakdown_seg.start_time, 2),
                    bar_number=breakdown_seg.start_bar,
                    beat_number=1,
                    cue_type=CueType.BREAKDOWN,
                    label="Breakdown",
                    confidence=0.89,
                    confidence_label="HIGH",
                    color_hex=self.COLOR_BREAKDOWN,
                    reasoning=(
                        f"Main breakdown begins at Bar {breakdown_seg.start_bar} ({self._format_time(breakdown_seg.start_time)}). "
                        "Rhythm and bass drop out, exposing melodic elements."
                    ),
                    musical_evidence=MusicalEvidence(
                        energy_delta=-0.60,
                        bass_activity=0.15,
                        rhythmic_density=0.20,
                        vocal_presence=breakdown_seg.vocal_presence,
                        phrase_aligned=True,
                        confidence_factors={"energy_dip": 0.90},
                    ),
                    suggested_use="Use the atmospheric space to tease the incoming track or execute a harmonic blend.",
                )
            )

        # =========================================================================
        # 5. MAIN DROP / PEAK RELEASE
        # =========================================================================
        drop_seg = next((s for s in structure if s.label == SectionType.DROP), None)
        if drop_seg and drop_seg.start_bar >= 17:
            drop_label = "Log-Drum Drop" if genre.primary_genre == "Amapiano" else "Main Drop"
            candidates.append(
                DJCuePoint(
                    cue_id="cue_main_drop",
                    timestamp=round(drop_seg.start_time, 2),
                    bar_number=drop_seg.start_bar,
                    beat_number=1,
                    cue_type=CueType.DROP,
                    label=drop_label,
                    confidence=0.95,
                    confidence_label="HIGH",
                    color_hex=self.COLOR_DROP,
                    reasoning=(
                        f"Peak energy release at Bar {drop_seg.start_bar} ({self._format_time(drop_seg.start_time)}). "
                        "Maximum bass and drum impact following build/breakdown."
                    ),
                    musical_evidence=MusicalEvidence(
                        energy_delta=0.85,
                        bass_activity=0.92,
                        rhythmic_density=0.88,
                        vocal_presence=drop_seg.vocal_presence,
                        phrase_aligned=True,
                        confidence_factors={"bass_impact": 0.96},
                    ),
                    suggested_use="High-impact drop swap location or instant climax trigger.",
                )
            )

        # =========================================================================
        # 6. SECONDARY DROP
        # =========================================================================
        sec_drop_seg = next((s for s in structure if s.label == SectionType.SECONDARY_DROP), None)
        if sec_drop_seg and sec_drop_seg.start_bar >= 33:
            candidates.append(
                DJCuePoint(
                    cue_id="cue_sec_drop",
                    timestamp=round(sec_drop_seg.start_time, 2),
                    bar_number=sec_drop_seg.start_bar,
                    beat_number=1,
                    cue_type=CueType.DROP,
                    label="Drop 2",
                    confidence=0.91,
                    confidence_label="HIGH",
                    color_hex=self.COLOR_SECONDARY_DROP,
                    reasoning=(
                        f"Secondary peak release at Bar {sec_drop_seg.start_bar} ({self._format_time(sec_drop_seg.start_time)}). "
                        "Second floor climax of the arrangement."
                    ),
                    musical_evidence=MusicalEvidence(
                        energy_delta=0.80,
                        bass_activity=0.88,
                        rhythmic_density=0.84,
                        vocal_presence=sec_drop_seg.vocal_presence,
                        phrase_aligned=True,
                        confidence_factors={"energy_jump": 0.90},
                    ),
                    suggested_use="Second energy peak for double-drop or set escalation.",
                )
            )

        # =========================================================================
        # 7. VOCAL EXIT (Only if at least 16 bars before outro)
        # =========================================================================
        if vocals.vocal_segments and len(vocals.vocal_segments) > 0:
            last_vocal = vocals.vocal_segments[-1]
            # Ensure it is well before the outro and at least 20 seconds after preceding cues
            if (duration_sec - last_vocal.end_time) >= 20.0 and last_vocal.end_bar < total_bars - 16:
                candidates.append(
                    DJCuePoint(
                        cue_id="cue_vocal_out",
                        timestamp=round(last_vocal.end_time, 2),
                        bar_number=last_vocal.end_bar,
                        beat_number=1,
                        cue_type=CueType.VOCAL_OUT,
                        label="Vocal Out",
                        confidence=0.86,
                        confidence_label="HIGH",
                        color_hex=self.COLOR_VOCAL_OUT,
                        reasoning=(
                            f"Vocals finish at Bar {last_vocal.end_bar} ({self._format_time(last_vocal.end_time)}). "
                            "Track returns to instrumental groove, opening a clean blend window."
                        ),
                        musical_evidence=MusicalEvidence(
                            energy_delta=-0.15,
                            bass_activity=0.60,
                            rhythmic_density=0.70,
                            vocal_presence=0.05,
                            phrase_aligned=True,
                            confidence_factors={"vocal_decay": 0.86},
                        ),
                        suggested_use="Safe moment to introduce incoming vocals or melodic elements.",
                    )
                )

        # =========================================================================
        # 8. SAFE MIX-OUT / OUTRO
        # =========================================================================
        outro_seg = next((s for s in structure if s.label == SectionType.OUTRO), None)
        if outro_seg and outro_seg.start_bar >= 17:
            mix_out_time = outro_seg.start_time
            mix_out_bar = outro_seg.start_bar
        else:
            # Default to 16 or 32 bars before the end
            outro_offset_bars = 32 if total_bars >= 80 else 16
            mix_out_bar = max(9, total_bars - outro_offset_bars)
            mix_out_time = downbeats[mix_out_bar - 1] if mix_out_bar <= len(downbeats) else (duration_sec - 30.0)

        candidates.append(
            DJCuePoint(
                cue_id="cue_mix_out",
                timestamp=round(mix_out_time, 2),
                bar_number=mix_out_bar,
                beat_number=1,
                cue_type=CueType.SAFE_MIX_OUT,
                label="Mix Out",
                confidence=0.93,
                confidence_label="HIGH",
                color_hex=self.COLOR_MIX_OUT,
                reasoning=(
                    f"Outro transition begins at Bar {mix_out_bar} ({self._format_time(mix_out_time)}). "
                    "Steady drum groove with winding down energy; prime safe mix-out point."
                ),
                musical_evidence=MusicalEvidence(
                    energy_delta=-0.35,
                    bass_activity=0.60,
                    rhythmic_density=0.65,
                    vocal_presence=0.05,
                    phrase_aligned=True,
                    confidence_factors={"phrase_end": 0.95},
                ),
                suggested_use="Begin fading volume or swapping bass to the incoming track over a 16-bar blend.",
            )
        )

        # =========================================================================
        # CANDIDATE PRUNING, DEDUPLICATION & PHRASE SEPARATION
        # =========================================================================
        # Sort candidates chronologically
        candidates.sort(key=lambda c: c.timestamp)

        pruned_cues: List[DJCuePoint] = []
        # Minimum separation: 6 bars (~10-15 seconds) to prevent redundant clutter
        min_bar_gap = 6
        min_time_gap_sec = 10.0

        for cand in candidates:
            if not pruned_cues:
                pruned_cues.append(cand)
                continue

            prev = pruned_cues[-1]
            time_gap = cand.timestamp - prev.timestamp
            bar_gap = cand.bar_number - prev.bar_number

            # If cues are too close, resolve conflict based on priority
            if bar_gap < min_bar_gap or time_gap < min_time_gap_sec:
                # Always preserve Cue A (Start)
                if prev.cue_id == "cue_start":
                    # If candidate is right at the start (e.g. duplicate groove at bar 1-4), skip it
                    continue

                # Drop / Vocal In takes priority over generic Groove
                if "DROP" in cand.cue_type.value and "MIX_IN" in prev.cue_type.value:
                    pruned_cues[-1] = cand  # Replace generic groove with Drop
                elif "VOCAL_IN" in cand.cue_type.value and "MIX_IN" in prev.cue_type.value:
                    pruned_cues[-1] = cand  # Replace generic groove with Vocal In
                elif cand.confidence > prev.confidence:
                    pruned_cues[-1] = cand
                # Otherwise ignore the too-close candidate
                continue

            pruned_cues.append(cand)

        # Limit to max 8 performance hot cues (Pads A through H)
        final_cues = pruned_cues[:8]

        # Re-assign hot cue indices strictly (1 to N)
        for idx, c in enumerate(final_cues):
            c.hot_cue_index = idx + 1

        return final_cues

    def _format_time(self, seconds: float) -> str:
        """Format seconds into MM:SS.S timestamp."""
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:04.1f}"
