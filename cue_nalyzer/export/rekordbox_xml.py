"""Pioneer Rekordbox XML Exporter for Hot Cues, Memory Cues, Beatgrid and Metadata."""

import html
import urllib.parse
from pathlib import Path
from typing import List, Optional
import xml.etree.ElementTree as ET
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis


class RekordboxXMLExporter:
    """Exports analyzed tracks into valid Pioneer Rekordbox XML for import to CDJs/Rekordbox."""

    # Map hex colors to Rekordbox RGB integers (0-255)
    HEX_COLOR_MAP = {
        "#00FF7F": (0, 255, 127),    # Safe Mix In (Green)
        "#FF0055": (255, 0, 85),     # Drop (Red)
        "#FFAA00": (255, 170, 0),    # Breakdown (Orange)
        "#9D00FF": (157, 0, 255),    # Drop 2 (Purple)
        "#00E5FF": (0, 229, 255),    # Vocal In (Cyan)
        "#0077FF": (0, 119, 255),    # Vocal Out (Blue)
        "#FF8800": (255, 136, 0),    # Mix Out (Amber)
        "#A6FF00": (166, 255, 0),    # Loop (Lime)
    }

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def generate_xml(self, analyses: List[TrackAnalysis]) -> str:
        """Generate formatted Rekordbox XML string for a collection of analyzed tracks."""
        root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        ET.SubElement(root, "PRODUCT", Name="Cue Nalyzer", Version="1.0.0", Company="Local DJ Music Intelligence")

        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(analyses)))

        for idx, analysis in enumerate(analyses, start=1):
            meta = analysis.metadata
            grid = analysis.beat_grid
            key = analysis.key_info

            # File location URI format (e.g. file://localhost/D:/path/to/song.mp3)
            clean_path = str(Path(meta.file_path).resolve()).replace("\\", "/")
            if not clean_path.startswith("/"):
                clean_path = "/" + clean_path
            location_uri = f"file://localhost{urllib.parse.quote(clean_path, safe='/:')}"

            track_elem = ET.SubElement(
                collection,
                "TRACK",
                TrackID=str(idx),
                Name=meta.title or meta.file_name,
                Artist=meta.artist or "Unknown Artist",
                Album=meta.album or "",
                Genre=analysis.genre.primary_genre,
                Kind="MP3 File",
                Size=str(1024 * 1024 * 5),
                TotalTime=str(int(meta.duration_sec)),
                DiscNumber="1",
                TrackNumber="1",
                Year=str(meta.year or 2026),
                AverageBpm=f"{grid.bpm:.2f}",
                DateAdded="2026-08-21",
                BitRate=str(meta.bitrate_kbps or 320),
                SampleRate=str(meta.sample_rate),
                Comments=f"Cue Nalyzer | {analysis.genre.primary_genre} | Camelot: {key.camelot}",
                Tonality=key.camelot,
                Location=location_uri,
            )

            # 1. Beatgrid / Tempo marker
            first_downbeat = grid.downbeat_times[0] if grid.downbeat_times else 0.0
            ET.SubElement(
                track_elem,
                "TEMPO",
                Inizio=f"{first_downbeat:.3f}",
                Bpm=f"{grid.bpm:.2f}",
                Metro="4/4",
                Battito="1",
            )

            # 2. Hot Cues (A through H, Num 0 to 7) & Memory Cues (Num -1)
            for cue in analysis.cue_points:
                hot_cue_num = (cue.hot_cue_index - 1) if cue.hot_cue_index and cue.hot_cue_index <= 8 else -1
                rgb = self.HEX_COLOR_MAP.get(cue.color_hex, (0, 255, 127))

                # Add Hot Cue
                if hot_cue_num >= 0:
                    ET.SubElement(
                        track_elem,
                        "POSITION_MARK",
                        Name=cue.label,
                        Type="0",
                        Start=f"{cue.timestamp:.3f}",
                        Num=str(hot_cue_num),
                        Red=str(rgb[0]),
                        Green=str(rgb[1]),
                        Blue=str(rgb[2]),
                    )

                # Add detailed Memory Cue with DJ explanation comment
                ET.SubElement(
                    track_elem,
                    "POSITION_MARK",
                    Name=f"Bar {cue.bar_number}: {cue.label} - {cue.reasoning[:60]}",
                    Type="0",
                    Start=f"{cue.timestamp:.3f}",
                    Num="-1",
                )

        # Build Playlists Node
        playlists = ET.SubElement(root, "PLAYLISTS")
        root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT")
        playlist_node = ET.SubElement(
            root_node, "NODE", Name="Cue Nalyzer Cues", Type="1", KeyType="0", Entries=str(len(analyses))
        )

        for idx in range(1, len(analyses) + 1):
            ET.SubElement(playlist_node, "TRACK", Key=str(idx))

        # Format XML output
        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        return xml_bytes.decode("utf-8")

    def export_to_file(self, analyses: List[TrackAnalysis], output_path: str):
        """Export analyzed tracks directly to an XML file."""
        xml_content = self.generate_xml(analyses)
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(xml_content)

