"""Vocal Activity Detection (VAD), vocal formant analysis, and vocal boundary extraction."""

from typing import List, Optional, Tuple
import librosa
import numpy as np
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import BeatGrid, VocalActivity, VocalSegment


class VocalDetector:
    """Detects singing and vocal speech presence to prevent vocal clashes during DJ mixing."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def analyze(self, y: np.ndarray, sr: int, beat_grid: BeatGrid) -> VocalActivity:
        """
        Compute vocal presence curve and segment boundaries across the track.
        """
        hop_length = self.config.HOP_LENGTH
        n_fft = self.config.N_FFT
        duration = len(y) / sr

        # 1. Harmonic extraction to isolate tonal vocals from percussive kicks/hi-hats
        y_harmonic = librosa.effects.harmonic(y, margin=3.0)

        # 2. STFT of harmonic signal
        stft = np.abs(librosa.stft(y_harmonic, n_fft=n_fft, hop_length=hop_length))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        # 3. Vocal formant frequency mask (300 Hz to 3500 Hz)
        vocal_mask = (freqs >= self.config.VOCAL_FORMANT_RANGE[0]) & (freqs <= self.config.VOCAL_FORMANT_RANGE[1])
        vocal_band_energy = np.sum(stft[vocal_mask, :], axis=0)
        total_harmonic_energy = np.sum(stft, axis=0) + 1e-6

        # Ratio of vocal band energy to overall harmonic energy
        vocal_ratio_raw = vocal_band_energy / total_harmonic_energy

        # 4. Spectral Centroid and Flatness in vocal region
        # Vocals typically have moderate spectral flatness and dynamic formant peaks
        flatness = librosa.feature.spectral_flatness(y=y_harmonic, n_fft=n_fft, hop_length=hop_length)[0]
        # Low flatness indicates tonal/formant peaks (typical of singing)
        tonality = 1.0 - np.clip(flatness * 5.0, 0.0, 1.0)

        # Combined vocal presence index
        raw_vocal_curve = vocal_ratio_raw * (0.6 + 0.4 * tonality)

        # 5. Temporal smoothing (moving average over ~1.5 seconds)
        window_size = max(3, int(1.5 * sr / hop_length))
        if len(raw_vocal_curve) >= window_size:
            kernel = np.ones(window_size) / window_size
            smoothed_curve = np.convolve(raw_vocal_curve, kernel, mode="same")
        else:
            smoothed_curve = raw_vocal_curve

        # Normalize curve to 0.0 - 1.0
        p95 = np.percentile(smoothed_curve, 95) if len(smoothed_curve) > 20 else np.max(smoothed_curve)
        if p95 <= 1e-6:
            p95 = np.max(smoothed_curve) + 1e-6
        vocal_curve_norm = np.clip(smoothed_curve / p95, 0.0, 1.0)

        # 6. Resample vocal presence curve to 0.5s resolution
        time_step = 0.5
        target_len = max(1, int(np.ceil(duration / time_step)))
        times = np.linspace(0, duration, target_len)
        orig_indices = np.linspace(0, 1, len(vocal_curve_norm))
        target_indices = np.linspace(0, 1, target_len)
        vocal_presence_curve = np.interp(target_indices, orig_indices, vocal_curve_norm)

        # 7. Extract discrete Vocal Segments
        vocal_segments = self._extract_vocal_segments(vocal_presence_curve, times, beat_grid)

        # 8. Overall metrics
        threshold = self.config.VOCAL_PRESENCE_THRESHOLD
        vocal_frames_count = np.sum(vocal_presence_curve > threshold)
        overall_vocal_ratio = float(vocal_frames_count / len(vocal_presence_curve))

        # Check for extended instrumental intro/outro (at least 16 bars of low vocal activity)
        has_extended_intro = True
        has_extended_outro = True

        if len(vocal_segments) > 0:
            first_vocal_time = vocal_segments[0].start_time
            last_vocal_time = vocal_segments[-1].end_time
            # An intro > 25 seconds without vocals is an extended instrumental intro
            has_extended_intro = first_vocal_time >= 25.0
            # An outro > 25 seconds after last vocal is an extended instrumental outro
            has_extended_outro = (duration - last_vocal_time) >= 25.0

        return VocalActivity(
            vocal_ratio=round(overall_vocal_ratio, 3),
            vocal_presence_curve=[round(float(v), 4) for v in vocal_presence_curve],
            vocal_segments=vocal_segments,
            has_extended_instrumental_intro=has_extended_intro,
            has_extended_instrumental_outro=has_extended_outro,
        )

    def _extract_vocal_segments(
        self, presence_curve: np.ndarray, times: np.ndarray, beat_grid: BeatGrid
    ) -> List[VocalSegment]:
        """Group consecutive high-vocal frames into musical vocal sections."""
        segments: List[VocalSegment] = []
        threshold = self.config.VOCAL_PRESENCE_THRESHOLD
        is_in_vocal = False
        start_idx = 0

        # Minimum vocal duration: 4 seconds
        min_frames = 8

        for i, val in enumerate(presence_curve):
            if val >= threshold and not is_in_vocal:
                is_in_vocal = True
                start_idx = i
            elif val < threshold and is_in_vocal:
                is_in_vocal = False
                if (i - start_idx) >= min_frames:
                    st_time = float(times[start_idx])
                    end_time = float(times[i])
                    st_bar = self._time_to_bar(st_time, beat_grid)
                    end_bar = self._time_to_bar(end_time, beat_grid)
                    mean_intensity = float(np.mean(presence_curve[start_idx:i]))

                    # Determine label
                    if st_time < 45.0:
                        label = "Vocal Intro"
                    elif (times[-1] - end_time) < 45.0:
                        label = "Vocal Outro"
                    else:
                        label = "Main Vocal Hook / Verse"

                    segments.append(
                        VocalSegment(
                            start_time=round(st_time, 2),
                            end_time=round(end_time, 2),
                            start_bar=st_bar,
                            end_bar=end_bar,
                            intensity=round(mean_intensity, 3),
                            label=label,
                        )
                    )

        # Handle ending segment
        if is_in_vocal and (len(presence_curve) - start_idx) >= min_frames:
            st_time = float(times[start_idx])
            end_time = float(times[-1])
            segments.append(
                VocalSegment(
                    start_time=round(st_time, 2),
                    end_time=round(end_time, 2),
                    start_bar=self._time_to_bar(st_time, beat_grid),
                    end_bar=self._time_to_bar(end_time, beat_grid),
                    intensity=round(float(np.mean(presence_curve[start_idx:])), 3),
                    label="Vocal Outro",
                )
            )

        return segments

    def _time_to_bar(self, time_sec: float, beat_grid: BeatGrid) -> int:
        """Convert timestamp to closest bar number."""
        if not beat_grid.downbeat_times:
            return int(time_sec * (beat_grid.bpm / 240.0)) + 1

        downbeats = np.array(beat_grid.downbeat_times)
        diffs = np.abs(downbeats - time_sec)
        closest_idx = int(np.argmin(diffs))
        return closest_idx + 1

