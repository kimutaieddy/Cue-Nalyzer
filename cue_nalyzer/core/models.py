"""Pydantic data models for Cue Nalyzer representing analysis results, cues, and DJ intelligence."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class CueType(str, Enum):
    """Categorization of DJ Cue Points."""
    MIX_IN = "MIX_IN"
    SAFE_MIX_IN = "SAFE_MIX_IN"
    DROP = "DROP"
    BREAKDOWN = "BREAKDOWN"
    BUILDUP = "BUILDUP"
    VOCAL_IN = "VOCAL_IN"
    VOCAL_OUT = "VOCAL_OUT"
    MIX_OUT = "MIX_OUT"
    SAFE_MIX_OUT = "SAFE_MIX_OUT"
    LOOP = "LOOP"
    QUICK_CUT = "QUICK_CUT"
    BRIDGE = "BRIDGE"


class SectionType(str, Enum):
    """Structural section types found in DJ arrangements."""
    INTRO = "INTRO"
    GROOVE = "GROOVE"
    VERSE = "VERSE"
    VOCAL_HOOK = "VOCAL_HOOK"
    BUILDUP = "BUILDUP"
    BREAKDOWN = "BREAKDOWN"
    DROP = "DROP"
    SECONDARY_DROP = "SECONDARY_DROP"
    BRIDGE = "BRIDGE"
    OUTRO = "OUTRO"
    FADEOUT = "FADEOUT"
    OTHER = "OTHER"


class TrackMetadata(BaseModel):
    """Basic file and audio tag metadata."""
    file_path: str
    file_name: str
    file_hash: str
    duration_sec: float
    sample_rate: int
    channels: int
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[int] = None
    bitrate_kbps: Optional[int] = None


class BeatGrid(BaseModel):
    """Accurate beat and bar tracking with phrase gridding."""
    bpm: float
    confidence: float
    beat_times: List[float] = Field(default_factory=list)
    downbeat_times: List[float] = Field(default_factory=list)
    bar_indices: List[int] = Field(default_factory=list)
    beats_per_bar: int = 4
    swing_factor: float = 0.0  # Deviation from rigid 16th/8th grid (0.0 = straight, >0.1 = swung)
    tempo_stability: float = 1.0  # 1.0 = rigid digital tempo, lower = live/human drift


class KeyInfo(BaseModel):
    """Harmonic analysis, Camelot wheel and OpenKey representations."""
    root_key: str  # e.g., "C", "F#", "A"
    scale: str  # "Major" or "Minor"
    key_name: str  # e.g. "A Minor"
    camelot: str  # e.g. "8A"
    openkey: str  # e.g. "1m"
    confidence: float
    second_choice: Optional[str] = None
    harmonic_stability: float = 1.0  # How consistent key remains across duration


class EnergyProfile(BaseModel):
    """Multi-band energy trajectories and tension/drop dynamics."""
    time_step_sec: float = 0.5
    overall_rms: List[float] = Field(default_factory=list)
    low_band_energy: List[float] = Field(default_factory=list)  # Sub + Bass (<250Hz)
    mid_band_energy: List[float] = Field(default_factory=list)  # Mids (250-3500Hz)
    high_band_energy: List[float] = Field(default_factory=list)  # Highs (>3500Hz)
    tension_curve: List[float] = Field(default_factory=list)  # Harmonic & rhythmic tension
    peak_energy_time: float = 0.0
    dynamic_range_db: float = 0.0
    average_lufs: float = -14.0


class VocalSegment(BaseModel):
    """Detected vocal section."""
    start_time: float
    end_time: float
    start_bar: int
    end_bar: int
    intensity: float
    label: str  # e.g. "Vocal Intro", "Main Verse", "Vocal Adlib"


class VocalActivity(BaseModel):
    """Vocal presence analysis across the track."""
    vocal_ratio: float = 0.0  # Fraction of track with active vocals (0.0 = pure instrumental)
    vocal_presence_curve: List[float] = Field(default_factory=list)
    vocal_segments: List[VocalSegment] = Field(default_factory=list)
    has_extended_instrumental_intro: bool = False
    has_extended_instrumental_outro: bool = False


class RhythmProfile(BaseModel):
    """Detailed rhythm, syncopation, and percussion pattern characteristics."""
    syncopation_index: float = 0.0  # Higher = off-beat syncopated groove
    log_drum_activity: float = 0.0  # Characteristic pitch-sliding sub transient in Amapiano (0.0 to 1.0)
    polyrhythm_density: float = 0.0  # 3-against-4 or layered percussion (Afro House indicator)
    kick_regularity: float = 1.0  # 1.0 = strict 4-on-the-floor kick, lower = breakbeat/trap
    groove_type: str = "Four-On-The-Floor"  # "Four-On-The-Floor", "Syncopated-Groove", "Breakbeat", "Log-Drum", "Acoustic"


class StructureSegment(BaseModel):
    """A structural musical section aligned to DJ phrase boundaries."""
    section_id: int
    label: SectionType
    start_time: float
    end_time: float
    start_bar: int
    end_bar: int
    num_bars: int
    confidence: float
    energy_level: float  # 0.0 to 1.0
    vocal_presence: float  # 0.0 to 1.0
    bass_presence: float  # 0.0 to 1.0
    description: str


class MusicalEvidence(BaseModel):
    """Supporting empirical audio evidence for explainability."""
    energy_delta: float = 0.0
    bass_activity: float = 0.0
    rhythmic_density: float = 0.0
    vocal_presence: float = 0.0
    phrase_aligned: bool = True
    preceding_section: Optional[str] = None
    confidence_factors: Dict[str, float] = Field(default_factory=dict)


class DJCuePoint(BaseModel):
    """An intelligent, confidence-scored DJ Cue Point."""
    cue_id: str
    timestamp: float
    bar_number: int
    beat_number: int
    cue_type: CueType
    label: str
    confidence: float
    confidence_label: str  # "HIGH", "MEDIUM", "LOW"
    color_hex: str  # Color for CDJ/Rekordbox display (e.g. "#00FF7F" green for mix-in, "#FF0055" red for drop)
    reasoning: str  # Human-readable DJ reasoning
    musical_evidence: MusicalEvidence
    suggested_use: str  # Practical DJ application guidance
    loop_length_bars: Optional[int] = None
    hot_cue_index: Optional[int] = None  # 1-8 for Rekordbox Hot Cues A-H


class GenrePrediction(BaseModel):
    """Probabilistic musical style and genre context."""
    primary_genre: str
    primary_confidence: float
    probabilities: Dict[str, float] = Field(default_factory=dict)
    subgenre: Optional[str] = None
    genre_characteristics: List[str] = Field(default_factory=list)
    reasoning: str


class WaveformSummary(BaseModel):
    """Compressed 3-band waveform visual data for high-performance UI rendering."""
    num_samples: int
    low_peaks: List[float] = Field(default_factory=list)
    mid_peaks: List[float] = Field(default_factory=list)
    high_peaks: List[float] = Field(default_factory=list)
    rms_peaks: List[float] = Field(default_factory=list)


class TrackAnalysis(BaseModel):
    """Complete, rich musical intelligence analysis of a track."""
    metadata: TrackMetadata
    beat_grid: BeatGrid
    key_info: KeyInfo
    energy: EnergyProfile
    vocals: VocalActivity
    rhythm: Optional[RhythmProfile] = None
    structure: List[StructureSegment] = Field(default_factory=list)
    genre: GenrePrediction
    cue_points: List[DJCuePoint] = Field(default_factory=list)
    waveform: WaveformSummary
    dj_summary: str
    analysis_timestamp: str


class TransitionAdvice(BaseModel):
    """Intelligent transition recommendation between two tracks in a library."""
    track_a_id: str
    track_b_id: str
    harmonic_compatibility: str  # "PERFECT", "ENERGY_BOOST (+1 Camelot)", "SUBDOMINANT (-1 Camelot)", "RELATIVE_SCALE", "CLASH"
    harmonic_score: float
    bpm_diff_pct: float
    pitch_adjustment_needed_pct: float
    recommended_mix_out_point: Optional[DJCuePoint] = None
    recommended_mix_in_point: Optional[DJCuePoint] = None
    transition_style: str  # "Long 32-Bar Blend", "Drop-to-Drop Cut", "Breakdown Vocal Swap", "Quick 8-Bar Outro"
    transition_score: float  # 0.0 to 100.0
    explanation: str
    warnings: List[str] = Field(default_factory=list)
