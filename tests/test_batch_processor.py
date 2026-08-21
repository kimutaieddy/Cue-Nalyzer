"""Unit tests for BatchProcessor, caching skip logic, and Rekordbox master sync."""

from pathlib import Path
from cue_nalyzer.batch.batch_processor import BatchProcessor, BatchResult


def test_batch_processor_discovery(tmp_path):
    # Create fake audio files in temp dir
    (tmp_path / "song1.mp3").write_bytes(b"\x00" * 100)
    (tmp_path / "song2.wav").write_bytes(b"\x00" * 100)
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "song3.flac").write_bytes(b"\x00" * 100)
    (tmp_path / "ignore.txt").write_text("not audio")

    batch_proc = BatchProcessor()
    files = batch_proc.discover_audio_files(str(tmp_path))

    assert len(files) == 3
    file_names = [f.name for f in files]
    assert "song1.mp3" in file_names
    assert "song2.wav" in file_names
    assert "song3.flac" in file_names
    assert "ignore.txt" not in file_names

