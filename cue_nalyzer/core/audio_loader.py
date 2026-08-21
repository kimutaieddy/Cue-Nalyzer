"""Audio loading, decoding, resampling, and tag extraction module."""

import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple
import librosa
import mutagen
import numpy as np
import soundfile as sf
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackMetadata


class AudioLoader:
    """Handles fast, robust audio loading and metadata parsing."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of the audio file for caching and identity."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks of 64KB for speed and low memory
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def extract_metadata(self, file_path: str) -> TrackMetadata:
        """Extract metadata tags (artist, title, bitrate, etc.) using mutagen."""
        p = Path(file_path)
        file_hash = self.compute_file_hash(file_path)

        title = p.stem
        artist = "Unknown Artist"
        album = None
        year = None
        bitrate_kbps = None
        duration_sec = 0.0
        channels = 2
        sample_rate = 44100

        try:
            audio_tag = mutagen.File(file_path)
            if audio_tag is not None:
                if audio_tag.info:
                    duration_sec = getattr(audio_tag.info, "length", 0.0)
                    bitrate = getattr(audio_tag.info, "bitrate", None)
                    if bitrate:
                        bitrate_kbps = int(bitrate / 1000)
                    channels = getattr(audio_tag.info, "channels", 2)
                    sample_rate = getattr(audio_tag.info, "sample_rate", 44100)

                # Extract ID3 or Vorbis tags
                tags = audio_tag.tags
                if tags:
                    if "TIT2" in tags:
                        title = str(tags["TIT2"].text[0])
                    elif "title" in tags:
                        title = str(tags["title"][0])

                    if "TPE1" in tags:
                        artist = str(tags["TPE1"].text[0])
                    elif "artist" in tags:
                        artist = str(tags["artist"][0])

                    if "TALB" in tags:
                        album = str(tags["TALB"].text[0])
                    elif "album" in tags:
                        album = str(tags["album"][0])

                    if "TDRC" in tags:
                        try:
                            year = int(str(tags["TDRC"].text[0])[:4])
                        except Exception:
                            pass
        except Exception:
            # Fallback to filename parsing: "Artist - Title"
            if " - " in p.stem:
                parts = p.stem.split(" - ", 1)
                artist = parts[0].strip()
                title = parts[1].strip()

        return TrackMetadata(
            file_path=str(p.resolve()),
            file_name=p.name,
            file_hash=file_hash,
            duration_sec=round(duration_sec, 2),
            sample_rate=sample_rate,
            channels=channels,
            title=title,
            artist=artist,
            album=album,
            year=year,
            bitrate_kbps=bitrate_kbps,
        )

    def load_audio(
        self,
        file_path: str,
        target_sr: Optional[int] = None,
        mono: bool = True,
        duration: Optional[float] = None,
        offset: float = 0.0,
    ) -> Tuple[np.ndarray, int, TrackMetadata]:
        """
        Load audio signal as normalized float32 numpy array.
        Uses soundfile / librosa with fallback.
        """
        sr = target_sr or self.config.SAMPLE_RATE
        metadata = self.extract_metadata(file_path)

        try:
            # First attempt fast soundfile load
            y, native_sr = sf.read(file_path, start=int(offset * 44100), stop=int((offset + duration) * 44100) if duration else None, dtype="float32")
            if y.ndim > 1:
                if mono:
                    y = np.mean(y, axis=1)
                else:
                    y = y.T
            if native_sr != sr:
                y = librosa.resample(y, orig_sr=native_sr, target_sr=sr)
        except Exception:
            # Robust fallback to librosa.load
            y, sr = librosa.load(file_path, sr=sr, mono=mono, offset=offset, duration=duration)

        # Update metadata duration if not previously available
        actual_duration = len(y) / sr if mono else y.shape[1] / sr
        if metadata.duration_sec <= 0:
            metadata.duration_sec = round(actual_duration, 2)

        return y, sr, metadata

    def detect_true_musical_start(self, y: np.ndarray, sr: int, threshold_db: float = -48.0) -> float:
        """
        Detect true musical audio start timestamp (seconds), ignoring leading digital
        silence or metadata encoding delay while preserving intentional ambient intros.
        """
        hop_length = self.config.HOP_LENGTH
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        if len(rms) == 0:
            return 0.0

        max_rms = np.max(rms)
        if max_rms <= 1e-6:
            return 0.0

        # Convert RMS to dB relative to peak
        db_rms = 20 * np.log10(rms / max_rms + 1e-9)

        # Find first frame where signal is above noise threshold
        active_frames = np.where(db_rms > threshold_db)[0]
        if len(active_frames) == 0:
            return 0.0

        first_active_frame = active_frames[0]
        start_time = float(librosa.frames_to_time(first_active_frame, sr=sr, hop_length=hop_length))

        # If silence is negligible (< 0.05s), start at 0.0
        if start_time < 0.05:
            return 0.0

        return round(start_time, 3)

