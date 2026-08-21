"""Unit tests for background WatchFolderManager."""

import time
from pathlib import Path
from cue_nalyzer.watcher.folder_watcher import WatchFolderManager


def test_watch_folder_manager(tmp_path):
    watcher = WatchFolderManager()
    assert watcher.get_watch_folders() == []

    # Add watch folder
    watcher.add_watch_folder(str(tmp_path))
    assert str(tmp_path) in watcher.get_watch_folders()

    # Start and stop watcher
    watcher.start(poll_interval_sec=0.1)
    assert watcher._is_running is True

    watcher.stop()
    assert watcher._is_running is False

    # Remove watch folder
    watcher.remove_watch_folder(str(tmp_path))
    assert watcher.get_watch_folders() == []

