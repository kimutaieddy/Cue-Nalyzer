"""Harmonic analysis, Key detection, and Camelot/OpenKey notation mapping."""

from typing import Dict, List, Optional, Tuple
import librosa
import numpy as np
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import KeyInfo


class KeyDetector:
    """Estimates musical key using Chroma CQT and Krumhansl-Schmuckler profiles."""

    PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    # Krumhansl-Schmuckler key profiles
    MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    # Temperley alternative profiles (empirically tuned for electronic/pop)
    TEMPERLEY_MAJOR = np.array([5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0])
    TEMPERLEY_MINOR = np.array([5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0])

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def analyze(self, y: np.ndarray, sr: int) -> KeyInfo:
        """
        Extract chroma vector and determine best-matching Major or Minor key.
        """
        # 1. Harmonic-percussive separation to isolate tonal content for cleaner chroma
        y_harmonic = librosa.effects.harmonic(y, margin=3.0)

        # 2. Compute Constant-Q Chroma
        chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, hop_length=self.config.HOP_LENGTH, n_chroma=12)

        # Mean chroma vector across time
        chroma_mean = np.mean(chroma, axis=1)
        chroma_norm = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-6)

        # 3. Correlate with all 24 key profiles (12 Major, 12 Minor)
        correlations: Dict[str, float] = {}

        for i, root in enumerate(self.PITCH_CLASSES):
            # Shift profiles to align with root note
            maj_prof = np.roll(self.MAJOR_PROFILE, i)
            maj_prof_norm = maj_prof / np.linalg.norm(maj_prof)
            maj_corr = np.corrcoef(chroma_norm, maj_prof_norm)[0, 1]
            correlations[f"{root} Major"] = float(maj_corr)

            min_prof = np.roll(self.MINOR_PROFILE, i)
            min_prof_norm = min_prof / np.linalg.norm(min_prof)
            min_corr = np.corrcoef(chroma_norm, min_prof_norm)[0, 1]
            correlations[f"{root} Minor"] = float(min_corr)

        # Sort keys by correlation score
        sorted_keys = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
        best_key, best_score = sorted_keys[0]
        second_key, second_score = sorted_keys[1]

        root_key, scale = best_key.split(" ")

        # 4. Measure harmonic stability across time chunks (10-second windows)
        chunk_size = sr * 10
        num_chunks = max(1, len(y_harmonic) // chunk_size)
        chunk_keys = []
        for c in range(num_chunks):
            chunk = y_harmonic[c * chunk_size : (c + 1) * chunk_size]
            if len(chunk) > sr * 2:
                c_chroma = np.mean(librosa.feature.chroma_cqt(y=chunk, sr=sr, hop_length=self.config.HOP_LENGTH), axis=1)
                c_norm = c_chroma / (np.linalg.norm(c_chroma) + 1e-6)
                # Quick best match
                c_best = max(
                    [(k, np.corrcoef(c_norm, np.roll(self.MAJOR_PROFILE, i) / np.linalg.norm(self.MAJOR_PROFILE))[0, 1]) for i, k in enumerate(self.PITCH_CLASSES)],
                    key=lambda x: x[1],
                )[0]
                chunk_keys.append(c_best)

        # Fraction of chunks matching root key
        harmonic_stability = chunk_keys.count(root_key) / len(chunk_keys) if chunk_keys else 0.9

        # Map to Camelot and OpenKey notation
        camelot = self.config.CAMELOT_MAP.get(best_key, "8A")
        openkey = self.config.OPENKEY_MAP.get(best_key, "1m")

        # Normalize confidence to 0.0 - 1.0 range
        confidence = float(np.clip((best_score - 0.2) / 0.6, 0.45, 0.98))

        return KeyInfo(
            root_key=root_key,
            scale=scale,
            key_name=best_key,
            camelot=camelot,
            openkey=openkey,
            confidence=round(confidence, 3),
            second_choice=second_key,
            harmonic_stability=round(harmonic_stability, 3),
        )

