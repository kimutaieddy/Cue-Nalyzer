"""Structured JSON Exporter for Cue Nalyzer track intelligence."""

import json
from pathlib import Path
from typing import List, Optional
from cue_nalyzer.core.models import TrackAnalysis


class JSONExporter:
    """Exports structured analysis results to JSON files."""

    def export_track(self, analysis: TrackAnalysis, output_path: str):
        """Export single track analysis to formatted JSON file."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(analysis.model_dump_json(indent=2))

    def export_collection(self, analyses: List[TrackAnalysis], output_path: str):
        """Export multiple tracks to a combined collection JSON file."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = [a.model_dump() for a in analyses]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

