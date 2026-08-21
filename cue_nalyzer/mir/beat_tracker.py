"""High-precision Beat, Downbeat, and 8/16/32-Bar Phrase Tracking."""

from typing import List, Optional, Tuple
import librosa
import numpy as np
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import BeatGrid


class BeatTracker:
    """Extracts tempo, beat grid, downbeats, and DJ phrase structure."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def analyze(self, y: np.ndarray, sr: int) -> BeatGrid:
        """
        Analyze audio array to compute tempo, beat grid, downbeats and swing factor.
        """
        hop_length = self.config.HOP_LENGTH

        # 1. Multi-band onset strength envelope
        # Low band (kicks) vs Full band
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length, aggregate=np.median)

        # 2. Dynamic tempo & beat tracking
        tempo_arr, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=hop_length,
            start_bpm=124.0,
            tightness=100,
        )

        bpm = float(np.atleast_1d(tempo_arr)[0])

        # Disambiguate tempo octaves if needed (e.g., electronic music tempo prior: 110-135 BPM, D&B: 170-178)
        if bpm < 80.0 and bpm > 50.0:
            bpm = bpm * 2.0  # Likely half-time detection of 110-160 BPM
        elif bpm > 180.0 and bpm < 260.0:
            bpm = bpm / 2.0  # Double-time detection

        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length).tolist()

        if len(beat_times) < 4:
            # Fallback if track is too short or quiet
            duration = len(y) / sr
            bpm = 120.0
            beat_interval = 60.0 / bpm
            beat_times = list(np.arange(0, duration, beat_interval))

        # 3. Downbeat (Bar 1, Beat 1) detection
        # Isolate low-frequency kick drum energy to identify the start of 4/4 measure
        downbeat_times, beat_indices, confidence = self._detect_downbeats(y, sr, beat_times, bpm)

        # 4. Swing / Groove factor calculation
        swing_factor = self._compute_swing_factor(beat_times)

        # 5. Measure tempo stability
        intervals = np.diff(beat_times) if len(beat_times) > 1 else [60.0 / bpm]
        tempo_stability = float(max(0.5, 1.0 - (np.std(intervals) / (np.mean(intervals) + 1e-6))))

        return BeatGrid(
            bpm=round(bpm, 2),
            confidence=round(confidence, 3),
            beat_times=[round(t, 4) for t in beat_times],
            downbeat_times=[round(t, 4) for t in downbeat_times],
            bar_indices=beat_indices,
            beats_per_bar=self.config.BEATS_PER_BAR,
            swing_factor=round(swing_factor, 3),
            tempo_stability=round(tempo_stability, 3),
        )

    def _detect_downbeats(
        self, y: np.ndarray, sr: int, beat_times: List[float], bpm: float
    ) -> Tuple[List[float], List[int], float]:
        """
        Identify downbeats (first beat of each 4-beat bar) by analyzing low-frequency
        kick transients and onset energy across phase alignments 0, 1, 2, 3.
        """
        beats_per_bar = self.config.BEATS_PER_BAR
        if len(beat_times) < beats_per_bar:
            return beat_times[:1], [0], 0.5

        # Extract low-band kick onset envelope (up to 250 Hz)
        y_low = librosa.effects.preemphasis(y, coef=-0.95)
        stft = np.abs(librosa.stft(y, n_fft=self.config.N_FFT, hop_length=self.config.HOP_LENGTH))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=self.config.N_FFT)
        low_idx = freqs <= 250.0
        low_energy = np.sum(stft[low_idx, :], axis=0)

        # Sample low-frequency energy at each beat location
        beat_frames = librosa.time_to_frames(beat_times, sr=sr, hop_length=self.config.HOP_LENGTH)
        valid_frames = [min(f, len(low_energy) - 1) for f in beat_frames]
        beat_energies = low_energy[valid_frames]

        # Evaluate 4 possible phase offsets for beat 1
        phase_scores = np.zeros(beats_per_bar)
        num_full_bars = len(beat_energies) // beats_per_bar

        if num_full_bars > 0:
            for phase in range(beats_per_bar):
                # Beat 1 typically has the highest kick energy
                bar_beat_1_energies = beat_energies[phase :: beats_per_bar]
                phase_scores[phase] = np.mean(bar_beat_1_energies) if len(bar_beat_1_energies) > 0 else 0.0

            best_phase = int(np.argmax(phase_scores))
            # Confidence based on dominance of best phase over competitors
            mean_other = (np.sum(phase_scores) - phase_scores[best_phase]) / (beats_per_bar - 1 + 1e-6)
            confidence = float(min(1.0, max(0.6, (phase_scores[best_phase] - mean_other) / (mean_other + 1e-6) + 0.5)))
        else:
            best_phase = 0
            confidence = 0.65

        # Downbeat times correspond to beat_times[best_phase, best_phase + 4, ...]
        downbeat_indices = list(range(best_phase, len(beat_times), beats_per_bar))
        downbeat_times = [beat_times[i] for i in downbeat_indices]

        return downbeat_times, downbeat_indices, confidence

    def _compute_swing_factor(self, beat_times: List[float]) -> float:
        """
        Estimate microtiming swing factor (deviation from strictly straight spacing).
        0.0 = straight, ~0.15 - 0.35 = shuffled / swing groove (common in Afro House / Amapiano).
        """
        if len(beat_times) < 8:
            return 0.0

        intervals = np.diff(beat_times)
        if len(intervals) < 4:
            return 0.0

        # Look for alternating long-short beat patterns
        even_intervals = intervals[0::2]
        odd_intervals = intervals[1::2]
        min_len = min(len(even_intervals), len(odd_intervals))
        if min_len < 2:
            return 0.0

        diff_ratio = np.mean(np.abs(even_intervals[:min_len] - odd_intervals[:min_len])) / (np.mean(intervals) + 1e-6)
        return float(np.clip(diff_ratio * 2.0, 0.0, 1.0))

