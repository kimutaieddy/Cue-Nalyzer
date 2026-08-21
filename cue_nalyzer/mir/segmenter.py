"""Structural segmentation and 8/16/32-bar phrase-aligned arrangement mapping."""

from typing import List, Optional, Tuple
import librosa
import numpy as np
from scipy.ndimage import gaussian_filter1d
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import (
    BeatGrid,
    EnergyProfile,
    SectionType,
    StructureSegment,
    VocalActivity,
)


class StructuralSegmenter:
    """Segments track into DJ-meaningful musical sections aligned to phrase bars."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def analyze(
        self,
        y: np.ndarray,
        sr: int,
        beat_grid: BeatGrid,
        energy: EnergyProfile,
        vocals: VocalActivity,
    ) -> List[StructureSegment]:
        """
        Produce a list of structural sections (Intro, Groove, Build, Breakdown, Drop, Outro)
        strictly quantized to musical bar and phrase boundaries.
        """
        downbeats = beat_grid.downbeat_times
        if not downbeats:
            return self._fallback_segments(len(y) / sr)

        total_bars = len(downbeats)
        duration_sec = len(y) / sr

        # 1. Extract bar-synchronous feature matrix (MFCC + Chroma + RMS)
        bar_features = self._extract_bar_features(y, sr, downbeats)

        # 2. Compute Self-Similarity Matrix (SSM)
        ssm = np.dot(bar_features, bar_features.T)
        norms = np.linalg.norm(bar_features, axis=1, keepdims=True) + 1e-6
        ssm = ssm / np.dot(norms, norms.T)

        # 3. Novelty detection along the SSM diagonal (checkerboard kernel)
        novelty = self._compute_novelty(ssm, kernel_size=8)

        # 4. Find candidate boundary bars (favoring 8, 16, 32 bar intervals)
        boundary_bars = self._find_phrase_aligned_boundaries(novelty, total_bars, energy, vocals)

        # 5. Classify each segment based on energy, vocal activity, and position
        segments = self._classify_segments(boundary_bars, downbeats, duration_sec, energy, vocals)

        return segments

    def _extract_bar_features(self, y: np.ndarray, sr: int, downbeats: List[float]) -> np.ndarray:
        """Extract average MFCC, Chroma, and RMS features per bar."""
        hop_length = self.config.HOP_LENGTH

        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)

        # Stack features
        all_feats = np.vstack([mfcc, chroma, rms])
        frames_per_sec = sr / hop_length

        num_bars = len(downbeats)
        bar_feats = np.zeros((num_bars, all_feats.shape[0]))

        for b in range(num_bars):
            start_sec = downbeats[b]
            end_sec = downbeats[b + 1] if b + 1 < num_bars else start_sec + (60.0 / 120.0 * 4)

            start_f = min(int(start_sec * frames_per_sec), all_feats.shape[1] - 1)
            end_f = min(int(end_sec * frames_per_sec), all_feats.shape[1])
            if end_f > start_f:
                bar_feats[b, :] = np.mean(all_feats[:, start_f:end_f], axis=1)
            else:
                bar_feats[b, :] = all_feats[:, start_f]

        return bar_feats

    def _compute_novelty(self, ssm: np.ndarray, kernel_size: int = 8) -> np.ndarray:
        """Compute novelty curve along diagonal of SSM using a checkerboard kernel."""
        n = ssm.shape[0]
        novelty = np.zeros(n)
        k = kernel_size // 2

        # 2D Checkerboard kernel
        checkerboard = np.kron([[1, -1], [-1, 1]], np.ones((k, k)))

        for i in range(k, n - k):
            patch = ssm[i - k : i + k, i - k : i + k]
            if patch.shape == checkerboard.shape:
                novelty[i] = np.sum(patch * checkerboard)

        # Smooth novelty
        novelty = np.maximum(0, novelty)
        if np.max(novelty) > 0:
            novelty = novelty / np.max(novelty)
        return gaussian_filter1d(novelty, sigma=1.5)

    def _find_phrase_aligned_boundaries(
        self, novelty: np.ndarray, total_bars: int, energy: EnergyProfile, vocals: VocalActivity
    ) -> List[int]:
        """Snap boundaries to strict 8-bar, 16-bar, or 32-bar phrases."""
        boundaries = [0]
        cur_bar = 0

        # DJ tracks are organized in chunks of 8, 16, or 32 bars
        valid_phrase_lengths = [8, 16, 24, 32, 64]

        while cur_bar < total_bars - 8:
            # Check 8, 16, 24, 32 bars ahead for highest novelty score
            best_candidate = cur_bar + 16  # default 16-bar phrase
            best_score = -1.0

            for plen in valid_phrase_lengths:
                target_bar = cur_bar + plen
                if target_bar >= total_bars:
                    continue

                # Local novelty around target_bar (+- 1 bar)
                window_start = max(0, target_bar - 1)
                window_end = min(total_bars, target_bar + 2)
                nov_val = np.max(novelty[window_start:window_end]) if window_start < len(novelty) else 0.0

                # Score phrase length: 16 and 32 bars get priority
                weight = 1.2 if plen in [16, 32] else 1.0
                score = nov_val * weight

                if score > best_score:
                    best_score = score
                    best_candidate = target_bar

            # If track has fewer bars remaining than next candidate, finish
            if best_candidate >= total_bars - 4:
                break

            boundaries.append(best_candidate)
            cur_bar = best_candidate

        boundaries.append(total_bars)
        return sorted(list(set(boundaries)))

    def _classify_segments(
        self,
        boundaries: List[int],
        downbeats: List[float],
        duration_sec: float,
        energy: EnergyProfile,
        vocals: VocalActivity,
    ) -> List[StructureSegment]:
        """Assign musical labels (Intro, Drop, Breakdown, etc.) with DJ descriptions."""
        segments: List[StructureSegment] = []
        num_segs = len(boundaries) - 1

        rms = np.array(energy.overall_rms) if energy.overall_rms else np.array([0.5])
        low_band = np.array(energy.low_band_energy) if energy.low_band_energy else np.array([0.5])
        voc_curve = np.array(vocals.vocal_presence_curve) if vocals.vocal_presence_curve else np.array([0.0])
        tension = np.array(energy.tension_curve) if energy.tension_curve else np.array([0.0])

        has_seen_drop = False

        for i in range(num_segs):
            st_bar = boundaries[i]
            end_bar = boundaries[i + 1]
            num_bars = end_bar - st_bar

            st_time = downbeats[st_bar] if st_bar < len(downbeats) else (st_bar * 2.0)
            end_time = downbeats[end_bar] if end_bar < len(downbeats) else duration_sec

            # Slice energy and vocal profiles for this segment
            st_frac = max(0.0, min(1.0, st_time / duration_sec))
            end_frac = max(0.0, min(1.0, end_time / duration_sec))

            idx_st = int(st_frac * len(rms))
            idx_end = max(idx_st + 1, int(end_frac * len(rms)))

            seg_rms = float(np.mean(rms[idx_st:idx_end]))
            seg_low = float(np.mean(low_band[idx_st:idx_end]))
            seg_voc = float(np.mean(voc_curve[idx_st:idx_end]))
            seg_tension = float(np.mean(tension[idx_st:idx_end]))

            # Label heuristic
            if i == 0 and st_time < 30.0:
                label = SectionType.INTRO
                desc = f"{num_bars}-bar DJ intro. Clean entry point with building groove."
            elif i == num_segs - 1 or end_time >= duration_sec - 25.0:
                label = SectionType.OUTRO
                desc = f"{num_bars}-bar DJ outro. Decreasing energy; ideal safe mix-out zone."
            elif seg_rms > 0.68 and seg_low > 0.65:
                if not has_seen_drop:
                    label = SectionType.DROP
                    desc = f"Main peak drop/release ({num_bars} bars). Full sub-bass and maximum drum energy."
                    has_seen_drop = True
                else:
                    label = SectionType.SECONDARY_DROP
                    desc = f"Secondary drop/climax ({num_bars} bars). Sustained peak floor energy."
            elif seg_low < 0.35 and seg_rms < 0.50:
                label = SectionType.BREAKDOWN
                desc = f"{num_bars}-bar breakdown. Sub/bass removed, exposing melodies and pads."
            elif seg_tension > 0.60 and seg_rms < 0.70 and i < num_segs - 1:
                label = SectionType.BUILDUP
                desc = f"{num_bars}-bar tension buildup leading into the drop."
            elif seg_voc > 0.45:
                label = SectionType.VOCAL_HOOK
                desc = f"{num_bars}-bar vocal section. High vocal presence; avoid overlapping vocals."
            else:
                label = SectionType.GROOVE
                desc = f"{num_bars}-bar steady rhythm section. Stable baseline groove."

            confidence = 0.85 if num_bars in [8, 16, 32] else 0.72

            segments.append(
                StructureSegment(
                    section_id=i + 1,
                    label=label,
                    start_time=round(st_time, 2),
                    end_time=round(end_time, 2),
                    start_bar=st_bar + 1,
                    end_bar=end_bar,
                    num_bars=num_bars,
                    confidence=round(confidence, 2),
                    energy_level=round(seg_rms, 2),
                    vocal_presence=round(seg_voc, 2),
                    bass_presence=round(seg_low, 2),
                    description=desc,
                )
            )

        return segments

    def _fallback_segments(self, duration_sec: float) -> List[StructureSegment]:
        """Simple fallback if beat tracking failed."""
        return [
            StructureSegment(
                section_id=1,
                label=SectionType.INTRO,
                start_time=0.0,
                end_time=round(duration_sec * 0.2, 2),
                start_bar=1,
                end_bar=16,
                num_bars=16,
                confidence=0.5,
                energy_level=0.4,
                vocal_presence=0.1,
                bass_presence=0.3,
                description="Intro section.",
            ),
            StructureSegment(
                section_id=2,
                label=SectionType.DROP,
                start_time=round(duration_sec * 0.2, 2),
                end_time=round(duration_sec * 0.8, 2),
                start_bar=17,
                end_bar=64,
                num_bars=48,
                confidence=0.5,
                energy_level=0.8,
                vocal_presence=0.5,
                bass_presence=0.8,
                description="Main energy section.",
            ),
            StructureSegment(
                section_id=3,
                label=SectionType.OUTRO,
                start_time=round(duration_sec * 0.8, 2),
                end_time=round(duration_sec, 2),
                start_bar=65,
                end_bar=80,
                num_bars=16,
                confidence=0.5,
                energy_level=0.3,
                vocal_presence=0.1,
                bass_presence=0.2,
                description="Outro section.",
            ),
        ]

