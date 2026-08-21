"""Rhythmic groove intelligence, syncopation measurement, and Amapiano log-drum detection."""

from typing import Optional, Tuple
import librosa
import numpy as np
from scipy.signal import find_peaks
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import BeatGrid, RhythmProfile


class RhythmAnalyzer:
    """Specialized rhythm analysis: Log drums, Afro polyrhythms, syncopation, and kick regularity."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def analyze(self, y: np.ndarray, sr: int, beat_grid: BeatGrid) -> RhythmProfile:
        """
        Analyze audio for groove style, syncopation index, log drum activity, and kick regularity.
        """
        hop_length = self.config.HOP_LENGTH
        n_fft = self.config.N_FFT

        # 1. Compute spectrogram
        stft = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        # 2. Extract Sub-Bass band (30 Hz to 110 Hz) for Log Drum / Kick analysis
        sub_mask = (freqs >= 30.0) & (freqs <= 110.0)
        sub_energy = np.sum(stft[sub_mask, :], axis=0)

        # 3. High-Frequency Percussion band (4000 Hz to 10000 Hz) for shakers / congas / hi-hats
        high_mask = (freqs >= 4000.0) & (freqs <= 10000.0)
        high_energy = np.sum(stft[high_mask, :], axis=0)

        # 4. Syncopation Index: measure energy on offbeats vs onbeats
        syncopation_index = self._calculate_syncopation(sub_energy, sr, beat_grid)

        # 5. Log-Drum Activity Detection (Amapiano signature)
        log_drum_activity = self._detect_log_drum(y, sr, stft, freqs, beat_grid)

        # 6. Afro House Polyrhythmic & Percussion Density
        polyrhythm_density = self._calculate_polyrhythm_density(high_energy, sr, beat_grid)

        # 7. Kick Regularity (4-on-the-floor stability)
        kick_regularity = self._calculate_kick_regularity(sub_energy, sr, beat_grid)

        # 8. Determine Groove Type
        groove_type = self._determine_groove_type(
            syncopation_index, log_drum_activity, polyrhythm_density, kick_regularity, beat_grid.bpm
        )

        return RhythmProfile(
            syncopation_index=round(float(syncopation_index), 3),
            log_drum_activity=round(float(log_drum_activity), 3),
            polyrhythm_density=round(float(polyrhythm_density), 3),
            kick_regularity=round(float(kick_regularity), 3),
            groove_type=groove_type,
        )

    def _calculate_syncopation(self, sub_energy: np.ndarray, sr: int, beat_grid: BeatGrid) -> float:
        """Measure the proportion of sub/bass transient energy occurring on offbeats."""
        if len(beat_grid.beat_times) < 8:
            return 0.2

        hop_length = self.config.HOP_LENGTH
        beat_frames = librosa.time_to_frames(beat_grid.beat_times, sr=sr, hop_length=hop_length)

        onbeat_energies = []
        offbeat_energies = []

        for i in range(len(beat_frames) - 1):
            f_start = min(beat_frames[i], len(sub_energy) - 1)
            f_next = min(beat_frames[i + 1], len(sub_energy) - 1)
            f_mid = (f_start + f_next) // 2

            onbeat_energies.append(sub_energy[f_start])
            if f_mid < len(sub_energy):
                offbeat_energies.append(sub_energy[f_mid])

        mean_on = np.mean(onbeat_energies) if onbeat_energies else 1.0
        mean_off = np.mean(offbeat_energies) if offbeat_energies else 0.0

        ratio = mean_off / (mean_on + mean_off + 1e-6)
        # Scale to standard 0.0 - 1.0 syncopation index
        return float(np.clip(ratio * 2.0, 0.0, 1.0))

    def _detect_log_drum(
        self, y: np.ndarray, sr: int, stft: np.ndarray, freqs: np.ndarray, beat_grid: BeatGrid
    ) -> float:
        """
        Detect characteristic Amapiano log drum basslines:
        - Deep sub-bass pitch transients (40-90 Hz)
        - Short punchy decays with pitch sweeps
        - Strong offbeat syncopated placement around 110-116 BPM
        """
        # Pitch filter in log drum core zone (40-90 Hz)
        core_mask = (freqs >= 40.0) & (freqs <= 90.0)
        core_sub = np.sum(stft[core_mask, :], axis=0)

        # Onset envelope of sub-bass
        sub_diff = np.maximum(0, np.diff(core_sub))
        peaks, props = find_peaks(sub_diff, distance=int(0.15 * sr / self.config.HOP_LENGTH), prominence=np.std(sub_diff))

        if len(peaks) < 10:
            return 0.0

        # Check BPM window (Amapiano is almost universally 110 - 116 BPM)
        bpm_bonus = 0.0
        if 108.0 <= beat_grid.bpm <= 118.0:
            bpm_bonus = 0.35
        elif 105.0 <= beat_grid.bpm <= 122.0:
            bpm_bonus = 0.15

        # Measure sub transient density
        duration_sec = len(y) / sr
        transient_rate_per_sec = len(peaks) / (duration_sec + 1e-6)
        # Log drums have frequent 16th/8th note sub hits (1.5 - 4.5 hits/sec)
        rate_score = 0.0
        if 1.2 <= transient_rate_per_sec <= 5.0:
            rate_score = 0.35

        # Sub-bass energy proportion
        total_energy = np.sum(stft, axis=0) + 1e-6
        sub_ratio = float(np.mean(core_sub / total_energy))
        sub_score = float(np.clip(sub_ratio * 3.5, 0.0, 0.30))

        log_drum_score = float(np.clip(bpm_bonus + rate_score + sub_score, 0.0, 1.0))
        return log_drum_score

    def _calculate_polyrhythm_density(self, high_energy: np.ndarray, sr: int, beat_grid: BeatGrid) -> float:
        """
        Detect Afro House style 3-stroke triplets / polyrhythmic shaker layering.
        """
        high_diff = np.maximum(0, np.diff(high_energy))
        peaks, _ = find_peaks(high_diff, distance=int(0.08 * sr / self.config.HOP_LENGTH), prominence=np.std(high_diff) * 0.8)

        duration_sec = len(high_energy) * self.config.HOP_LENGTH / sr
        rate = len(peaks) / (duration_sec + 1e-6)

        # Afro House typically has high percussive event rates (> 4 per second) with swing
        base_score = float(np.clip(rate / 7.0, 0.0, 0.7))
        swing_bonus = float(beat_grid.swing_factor * 0.3)
        return float(np.clip(base_score + swing_bonus, 0.0, 1.0))

    def _calculate_kick_regularity(self, sub_energy: np.ndarray, sr: int, beat_grid: BeatGrid) -> float:
        """Measure consistency of 4-on-the-floor kick drum pattern on every beat."""
        if len(beat_grid.beat_times) < 8:
            return 0.8

        hop_length = self.config.HOP_LENGTH
        beat_frames = librosa.time_to_frames(beat_grid.beat_times, sr=sr, hop_length=hop_length)

        kick_hits = []
        for f in beat_frames:
            idx = min(f, len(sub_energy) - 1)
            # Sample small local window around beat
            w_start = max(0, idx - 2)
            w_end = min(len(sub_energy), idx + 3)
            kick_hits.append(np.max(sub_energy[w_start:w_end]))

        if not kick_hits:
            return 0.8

        kick_hits = np.array(kick_hits)
        # Coefficient of variation across kick beats (lower CV = higher regularity)
        mean_k = np.mean(kick_hits)
        std_k = np.std(kick_hits)
        cv = std_k / (mean_k + 1e-6)

        regularity = float(np.clip(1.0 - (cv * 0.6), 0.2, 1.0))
        return regularity

    def _determine_groove_type(
        self, syncopation: float, log_drum: float, polyrhythm: float, kick_reg: float, bpm: float
    ) -> str:
        """Classify groove into musically descriptive DJ terms."""
        if log_drum > 0.65 and 108.0 <= bpm <= 118.0:
            return "Amapiano Log-Drum Groove"
        elif polyrhythm > 0.60 and syncopation > 0.40:
            return "Afro Polyrhythmic Groove"
        elif kick_reg > 0.75:
            return "Four-On-The-Floor"
        elif bpm >= 165.0:
            return "High-Speed Breakbeat"
        elif syncopation > 0.55:
            return "Syncopated Broken Beat"
        else:
            return "Four-On-The-Floor"

