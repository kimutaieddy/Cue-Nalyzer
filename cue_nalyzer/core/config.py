"""Global configuration and audio MIR parameters for Cue Nalyzer."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class Config:
    """System-wide configuration parameters."""

    # Audio Loading Parameters
    SAMPLE_RATE: int = 22050  # Optimal for MIR tasks (speed + frequency resolution up to 11 kHz)
    MONO: bool = True
    HOP_LENGTH: int = 512
    N_FFT: int = 2048

    # Frequency Band Definitions for 3-Band & 5-Band DJ Decompositions (in Hz)
    BAND_SUB_BASS: Tuple[float, float] = (20.0, 90.0)
    BAND_BASS: Tuple[float, float] = (90.0, 250.0)
    BAND_LOW_MID: Tuple[float, float] = (250.0, 800.0)
    BAND_MID_HIGH: Tuple[float, float] = (800.0, 4000.0)
    BAND_HIGH: Tuple[float, float] = (4000.0, 11000.0)

    # 3-Band DJ Visualizer Bands (Low = Bass/Sub, Mid = Vocals/Synths, High = Hi-Hats/Air)
    THREE_BAND_LOW: Tuple[float, float] = (20.0, 250.0)
    THREE_BAND_MID: Tuple[float, float] = (250.0, 3500.0)
    THREE_BAND_HIGH: Tuple[float, float] = (3500.0, 11000.0)

    # Phrasing & Structural Defaults
    BEATS_PER_BAR: int = 4
    STANDARD_PHRASE_BARS: List[int] = field(default_factory=lambda: [4, 8, 16, 32, 64])

    # Vocal Detection Range
    VOCAL_FORMANT_RANGE: Tuple[float, float] = (300.0, 3500.0)
    VOCAL_PRESENCE_THRESHOLD: float = 0.42

    # Energy & Tension thresholds
    BUILD_TENSION_MIN_DURATION_SEC: float = 4.0
    DROP_ENERGY_INCREASE_MIN_RATIO: float = 1.35

    # Storage and Caching
    CACHE_DIR: Path = Path(".cache")
    DB_PATH: Path = Path(".cache/cue_nalyzer.db")

    # Camelot Wheel Mappings (Pitch Class Major/Minor to Camelot)
    CAMELOT_MAP: Dict[str, str] = field(
        default_factory=lambda: {
            "C Major": "8B",
            "A Minor": "8A",
            "G Major": "9B",
            "E Minor": "9A",
            "D Major": "10B",
            "B Minor": "10A",
            "A Major": "11B",
            "F# Minor": "11A",
            "E Major": "12B",
            "C# Minor": "12A",
            "B Major": "1B",
            "G# Minor": "1A",
            "F# Major": "2B",
            "D# Minor": "2A",
            "C# Major": "3B",
            "A# Minor": "3A",
            "G# Major": "4B",
            "F Minor": "4A",
            "D# Major": "5B",
            "C Minor": "5A",
            "A# Major": "6B",
            "G Minor": "6A",
            "F Major": "7B",
            "D Minor": "7A",
        }
    )

    # OpenKey Mappings
    OPENKEY_MAP: Dict[str, str] = field(
        default_factory=lambda: {
            "C Major": "1d",
            "A Minor": "1m",
            "G Major": "2d",
            "E Minor": "2m",
            "D Major": "3d",
            "B Minor": "3m",
            "A Major": "4d",
            "F# Minor": "4m",
            "E Major": "5d",
            "C# Minor": "5m",
            "B Major": "6d",
            "G# Minor": "6m",
            "F# Major": "7d",
            "D# Minor": "7m",
            "C# Major": "8d",
            "A# Minor": "8m",
            "G# Major": "9d",
            "F Minor": "9m",
            "D# Major": "10d",
            "C Minor": "10m",
            "A# Major": "11d",
            "G Minor": "11m",
            "F Major": "12d",
            "D Minor": "12m",
        }
    )

