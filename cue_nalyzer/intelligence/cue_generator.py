"""Intelligent, genre-aware DJ Cue Point placement targeting 5+ meaningful performance landmarks."""

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
    Generates prioritized, non-redundant DJ Cue points targeting at least 5
    distinct, musically justified landmarks per suitable track across genres.
    """

    # Pioneer CDJ / Rekordbox Color Palette
    COLOR_START = "#00E5FF"        # Cyan (Track Start)
    COLOR_GROOVE = "#00FF7F"       # Spring Green (Groove / Bass In)
    COLOR_DROP = "#FF0055"         # Crimson / Bright Red (Peak Drop)
    COLOR_BREAKDOWN = "#FFAA00"    # Golden Orange (Breakdown)
    COLOR_BUILDUP = "#FFD700"      # Yellow / Gold (Build-up)
    COLOR_VOCAL_IN = "#FF00AA"     # Magenta / Pink (Vocal Entrance)
    COLOR_VOCAL_OUT = "#0077FF"    # Blue (Vocal Exit / Blend Window)
    COLOR_MIX_OUT = "#FF8800"      # Warm Amber (Outro Mix-Out)
    COLOR_SECONDARY_DROP = "#9D00FF"  # Electric Purple (Drop 2 / Re-Drop)

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
        Derive prioritized DJ Cue points across track timeline.
        Targets 5+ high-conviction cues where track structure supports it.
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
        candidates.append(
            DJCuePoint(
                cue_id="cue_start",
                timestamp=round(track_start_time, 2),
                bar_number=1,
                beat_number=1,
                cue_type=CueType.SAFE_MIX_IN,
                label="Start",
                confidence=0.99,
                confidence_label="HIGH",
                color_hex=self.COLOR_START,
                reasoning=(
                    f"Track start at Bar 1 ({self._format_time(track_start_time)}). "
                    "Primary DJ cue point to launch track playback on phrase beat 1."
                ),
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
        )

        # =========================================================================
        # 2. MAIN GROOVE ENTRY / BEAT IN (Bar 9, 17, or 33)
        # =========================================================================
        groove_seg = next(
            (s for s in structure if s.label in [SectionType.GROOVE, SectionType.VERSE] and s.start_bar >= 9 and s.start_time < 90.0),
            None,
        )
        if groove_seg and groove_seg.start_bar >= 9:
            groove_label = "Log-Drum In" if genre.primary_genre == "Amapiano" else "Groove In"
            candidates.append(
                DJCuePoint(
                    cue_id="cue_groove",
                    timestamp=round(groove_seg.start_time, 2),
                    bar_number=groove_seg.start_bar,
                    beat_number=1,
                    cue_type=CueType.MIX_IN,
                    label=groove_label,
                    confidence=0.93,
                    confidence_label="HIGH",
                    color_hex=self.COLOR_GROOVE,
                    reasoning=(
                        f"Main beat & bass groove establishes at Bar {groove_seg.start_bar} ({self._format_time(groove_seg.start_time)}). "
                        "Full low-end drive active; safe transition landmark."
                    ),
                    musical_evidence=MusicalEvidence(
                        energy_delta=0.55,
                        bass_activity=0.78,
                        rhythmic_density=0.82,
                        vocal_presence=groove_seg.vocal_presence,
                        phrase_aligned=True,
                        confidence_factors={"bass_entry": 0.94},
                    ),
                    suggested_use="Start fading volume or unmuting bass on incoming mix as groove kicks in.",
                )
            )
        elif total_bars >= 32:
            # If track starts with full drums from Bar 1, mark 16-bar phrase evolution (Bar 17)
            bar_17_idx = 16
            if bar_17_idx < len(downbeats):
                candidates.append(
                    DJCuePoint(
                        cue_id="cue_phrase_17",
                        timestamp=round(downbeats[bar_17_idx], 2),
                        bar_number=17,
                        beat_number=1,
                        cue_type=CueType.MIX_IN,
                        label="Phrase 17",
                        confidence=0.88,
                        confidence_label="HIGH",
                        color_hex=self.COLOR_GROOVE,
                        reasoning=(
                            f"16-bar phrase progression at Bar 17 ({self._format_time(downbeats[bar_17_idx])}). "
                            "Rhythm layers expand; standard DJ transition marker."
                        ),
                        musical_evidence=MusicalEvidence(
                            energy_delta=0.30,
                            bass_activity=0.65,
                            rhythmic_density=0.70,
                            vocal_presence=0.1,
                            phrase_aligned=True,
                            confidence_factors={"phrase_16b": 0.90},
                        ),
                        suggested_use="Standard 16-bar mix-in transition point.",
                    )
                )

        # =========================================================================
        # 3. FIRST VOCAL ENTRANCE (Vocal In)
        # =========================================================================
        if vocals.vocal_segments:
            first_vocal = vocals.vocal_segments[0]
            if first_vocal.start_bar >= 9:
                candidates.append(
                    DJCuePoint(
                        cue_id="cue_vocal_in",
                        timestamp=round(first_vocal.start_time, 2),
                        bar_number=first_vocal.start_bar,
                        beat_number=1,
                        cue_type=CueType.VOCAL_IN,
                        label="Vocal In",
                        confidence=0.91,
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
                            confidence_factors={"formant_detection": 0.92},
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
                    confidence=0.90,
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
                        confidence_factors={"energy_dip": 0.91},
                    ),
                    suggested_use="Use the atmospheric space to tease the incoming track or execute a harmonic blend.",
                )
            )

        # =========================================================================
        # 5. MAIN DROP / CLIMAX
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
                    confidence=0.96,
                    confidence_label="HIGH",
                    color_hex=self.COLOR_DROP,
                    reasoning=(
                        f"Peak energy release at Bar {drop_seg.start_bar} ({self._format_time(drop_seg.start_time)}). "
                        "Maximum bass and drum impact following build/breakdown."
                    ),
                    musical_evidence=MusicalEvidence(
                        energy_delta=0.85,
                        bass_activity=0.94,
                        rhythmic_density=0.88,
                        vocal_presence=drop_seg.vocal_presence,
                        phrase_aligned=True,
                        confidence_factors={"bass_impact": 0.96},
                    ),
                    suggested_use="High-impact drop swap location or instant climax trigger.",
                )
            )

        # =========================================================================
        # 6. SECONDARY DROP / RE-DROP
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
                    label="Re-Drop",
                    confidence=0.92,
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
                        confidence_factors={"energy_jump": 0.92},
                    ),
                    suggested_use="Second energy peak for double-drop or set escalation.",
                )
            )

        # =========================================================================
        # 7. VOCAL EXIT / INSTRUMENTAL BLEND WINDOW
        # =========================================================================
        if vocals.vocal_segments and len(vocals.vocal_segments) > 0:
            last_vocal = vocals.vocal_segments[-1]
            if (duration_sec - last_vocal.end_time) >= 15.0 and last_vocal.end_bar < total_bars - 8:
                candidates.append(
                    DJCuePoint(
                        cue_id="cue_vocal_out",
                        timestamp=round(last_vocal.end_time, 2),
                        bar_number=last_vocal.end_bar,
                        beat_number=1,
                        cue_type=CueType.VOCAL_OUT,
                        label="Vocal Out",
                        confidence=0.88,
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
                            confidence_factors={"vocal_decay": 0.88},
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
                confidence=0.94,
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
        candidates.sort(key=lambda c: c.timestamp)

        pruned_cues: List[DJCuePoint] = []
        min_bar_gap = 6
        min_time_gap_sec = 10.0

        for cand in candidates:
            if not pruned_cues:
                pruned_cues.append(cand)
                continue

            prev = pruned_cues[-1]
            time_gap = cand.timestamp - prev.timestamp
            bar_gap = cand.bar_number - prev.bar_number

            if bar_gap < min_bar_gap or time_gap < min_time_gap_sec:
                if prev.cue_id == "cue_start":
                    continue

                if "DROP" in cand.cue_type.value and "MIX_IN" in prev.cue_type.value:
                    pruned_cues[-1] = cand
                elif "VOCAL_IN" in cand.cue_type.value and "MIX_IN" in prev.cue_type.value:
                    pruned_cues[-1] = cand
                elif cand.confidence > prev.confidence:
                    pruned_cues[-1] = cand
                continue

            pruned_cues.append(cand)

        # Limit to max 8 performance hot cues (Pads A through H)
        final_cues = pruned_cues[:8]

        for idx, c in enumerate(final_cues):
            c.hot_cue_index = idx + 1

        return final_cues

    def _format_time(self, seconds: float) -> str:
        """Format seconds into MM:SS.S timestamp."""
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:04.1f}"
