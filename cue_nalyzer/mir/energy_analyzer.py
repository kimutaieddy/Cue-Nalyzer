"""Multi-band energy trajectories, tension dynamics, and 3-band waveform generation."""

from typing import Optional, Tuple
import librosa
import numpy as np
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import EnergyProfile, WaveformSummary


class EnergyAnalyzer:
    """Computes frequency-banded energy curves, buildup tension, and waveform peak data."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def analyze(self, y: np.ndarray, sr: int) -> Tuple[EnergyProfile, WaveformSummary]:
        """
        Extract multi-band energy, tension curve, and waveform display peaks.
        """
        hop_length = self.config.HOP_LENGTH
        n_fft = self.config.N_FFT

        # 1. Compute Short-Time Fourier Transform (magnitude)
        stft = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        # 2. Mask frequency bands
        low_mask = (freqs >= self.config.THREE_BAND_LOW[0]) & (freqs <= self.config.THREE_BAND_LOW[1])
        mid_mask = (freqs > self.config.THREE_BAND_MID[0]) & (freqs <= self.config.THREE_BAND_MID[1])
        high_mask = (freqs > self.config.THREE_BAND_HIGH[0]) & (freqs <= self.config.THREE_BAND_HIGH[1])

        # Sum energy across frequency bins per frame
        low_band = np.sum(stft[low_mask, :], axis=0)
        mid_band = np.sum(stft[mid_mask, :], axis=0)
        high_band = np.sum(stft[high_mask, :], axis=0)
        total_rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        # 3. Downsample to standard time grid (0.5s resolution) for profile
        duration = len(y) / sr
        time_step = 0.5
        target_len = max(1, int(np.ceil(duration / time_step)))
        frames_per_sec = sr / hop_length

        times = np.linspace(0, duration, target_len)
        low_resampled = self._resample_curve(low_band, target_len)
        mid_resampled = self._resample_curve(mid_band, target_len)
        high_resampled = self._resample_curve(high_band, target_len)
        rms_resampled = self._resample_curve(total_rms, target_len)

        # Normalize bands to 0.0 - 1.0
        low_norm = self._normalize(low_resampled)
        mid_norm = self._normalize(mid_resampled)
        high_norm = self._normalize(high_resampled)
        rms_norm = self._normalize(rms_resampled)

        # 4. Compute Tension / Buildup index:
        # High frequency accumulation + spectral flux + rising pitch/noise
        spectral_flux = np.diff(stft, axis=1)
        spectral_flux = np.pad(np.sum(np.maximum(0, spectral_flux), axis=0), (1, 0), mode="edge")
        flux_resampled = self._resample_curve(spectral_flux, target_len)
        flux_norm = self._normalize(flux_resampled)

        # Tension formula: combines high band emphasis, mid energy, and spectral movement
        tension_curve = 0.45 * high_norm + 0.35 * flux_norm + 0.20 * mid_norm
        tension_curve = np.clip(tension_curve, 0.0, 1.0).tolist()

        peak_idx = int(np.argmax(rms_norm))
        peak_time = float(times[peak_idx]) if len(times) > 0 else 0.0

        # Dynamic range (peak vs 10th percentile energy in dB)
        min_rms = max(1e-5, np.percentile(total_rms[total_rms > 0], 10) if np.any(total_rms > 0) else 1e-5)
        max_rms = max(1e-4, np.max(total_rms))
        dynamic_range_db = float(round(20 * np.log10(max_rms / min_rms), 2))

        energy_profile = EnergyProfile(
            time_step_sec=time_step,
            overall_rms=[round(float(v), 4) for v in rms_norm],
            low_band_energy=[round(float(v), 4) for v in low_norm],
            mid_band_energy=[round(float(v), 4) for v in mid_norm],
            high_band_energy=[round(float(v), 4) for v in high_norm],
            tension_curve=[round(float(v), 4) for v in tension_curve],
            peak_energy_time=round(peak_time, 2),
            dynamic_range_db=dynamic_range_db,
            average_lufs=round(-18.0 + (float(np.mean(rms_norm)) * 8.0), 1),
        )

        # 5. Generate high-resolution waveform display peaks (1000 sample points for UI)
        waveform_summary = self._generate_waveform_peaks(low_band, mid_band, high_band, total_rms, num_points=1200)

        return energy_profile, waveform_summary

    def _resample_curve(self, arr: np.ndarray, target_length: int) -> np.ndarray:
        """Resample 1D array to target length using linear interpolation."""
        if len(arr) == 0:
            return np.zeros(target_length)
        orig_indices = np.linspace(0, 1, len(arr))
        target_indices = np.linspace(0, 1, target_length)
        return np.interp(target_indices, orig_indices, arr)

    def _normalize(self, arr: np.ndarray) -> np.ndarray:
        """Normalize array to 0.0 - 1.0 with robust outlier clipping."""
        if len(arr) == 0:
            return arr
        p98 = np.percentile(arr, 98) if len(arr) > 10 else np.max(arr)
        if p98 <= 1e-6:
            p98 = np.max(arr) + 1e-6
        clipped = np.clip(arr / p98, 0.0, 1.0)
        return clipped

    def _generate_waveform_peaks(
        self, low: np.ndarray, mid: np.ndarray, high: np.ndarray, rms: np.ndarray, num_points: int = 1200
    ) -> WaveformSummary:
        """Generate 3-band peak envelopes for interactive waveform rendering."""
        low_res = self._normalize(self._resample_curve(low, num_points))
        mid_res = self._normalize(self._resample_curve(mid, num_points))
        high_res = self._normalize(self._resample_curve(high, num_points))
        rms_res = self._normalize(self._resample_curve(rms, num_points))

        return WaveformSummary(
            num_samples=num_points,
            low_peaks=[round(float(v), 4) for v in low_res],
            mid_peaks=[round(float(v), 4) for v in mid_res],
            high_peaks=[round(float(v), 4) for v in high_res],
            rms_peaks=[round(float(v), 4) for v in rms_res],
        )

