"""Pioneer Rekordbox XML Exporter & Bridge Sync for Hot Cues, Beatgrids, and Playlists."""

import os
from pathlib import Path
from typing import List, Optional
import urllib.parse
import xml.dom.minidom
import xml.etree.ElementTree as ET
from cue_nalyzer.core.config import Config
from cue_nalyzer.core.models import TrackAnalysis


class RekordboxXMLExporter:
    """
    Exports analyzed tracks into standard Pioneer Rekordbox XML format
    for direct integration with Rekordbox Performance Pads (Hot Cues A-H) and CDJs.
    """

    # Rekordbox RGB colors
    HEX_COLOR_MAP = {
        "#00E5FF": (0, 229, 255),    # Cyan (Start)
        "#00FF7F": (0, 255, 127),    # Green (Groove)
        "#FF0055": (255, 0, 85),     # Crimson Red (Drop)
        "#FFAA00": (255, 170, 0),    # Orange (Breakdown)
        "#FF00AA": (255, 0, 170),    # Pink/Magenta (Vocal In)
        "#0077FF": (0, 119, 255),    # Blue (Vocal Out)
        "#FF8800": (255, 136, 0),    # Amber (Mix Out)
        "#A6FF00": (166, 255, 0),    # Lime (Loop)
        "#9D00FF": (157, 0, 255),    # Purple (Drop 2)
    }

    DEFAULT_MASTER_XML_NAME = "cue_nalyzer_library.xml"

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def format_windows_location_uri(self, file_path: str) -> str:
        """
        Format Windows/POSIX path to standard Rekordbox URI.
        Example: D:\\music\\song.mp3 -> file://localhost/D:/music/song.mp3
        """
        p = Path(file_path).resolve()
        posix_path = p.as_posix()
        if not posix_path.startswith("/"):
            posix_path = "/" + posix_path
        # Encode URI with safe chars
        encoded_path = urllib.parse.quote(posix_path, safe="/:")
        return f"file://localhost{encoded_path}"

    def generate_xml(self, analyses: List[TrackAnalysis], playlist_name: str = "Cue Nalyzer Library") -> str:
        """Generate formatted Pioneer Rekordbox XML string."""
        root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        ET.SubElement(root, "PRODUCT", Name="rekordbox", Version="6.8.0", Company="Pioneer DJ")

        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(analyses)))

        for idx, analysis in enumerate(analyses, start=1):
            meta = analysis.metadata
            grid = analysis.beat_grid
            key = analysis.key_info
            genre = analysis.genre

            location_uri = self.format_windows_location_uri(meta.file_path)

            track_elem = ET.SubElement(
                collection,
                "TRACK",
                TrackID=str(idx),
                Name=meta.title or meta.file_name,
                Artist=meta.artist or "Unknown Artist",
                Album=meta.album or "",
                Genre=genre.primary_genre,
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
                Comments=f"Cue Nalyzer | {genre.primary_genre} | {key.camelot}",
                Tonality=key.camelot,
                Location=location_uri,
            )

            # Beatgrid / Tempo marker
            first_downbeat = grid.downbeat_times[0] if grid.downbeat_times else 0.0
            ET.SubElement(
                track_elem,
                "TEMPO",
                Inizio=f"{first_downbeat:.3f}",
                Bpm=f"{grid.bpm:.2f}",
                Metro="4/4",
                Battito="1",
            )

            # Hot Cues strictly assigned to Num 0 through 7 (Pads A through H)
            for cue in analysis.cue_points:
                if cue.hot_cue_index and 1 <= cue.hot_cue_index <= 8:
                    hot_num = cue.hot_cue_index - 1
                    rgb = self.HEX_COLOR_MAP.get(cue.color_hex, (0, 229, 255))
                    ET.SubElement(
                        track_elem,
                        "POSITION_MARK",
                        Name=cue.label,
                        Type="0",
                        Start=f"{cue.timestamp:.3f}",
                        Num=str(hot_num),
                        Red=str(rgb[0]),
                        Green=str(rgb[1]),
                        Blue=str(rgb[2]),
                    )

        # Build Playlists Node
        playlists = ET.SubElement(root, "PLAYLISTS")
        root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT")
        playlist_node = ET.SubElement(
            root_node, "NODE", Name=playlist_name, Type="1", KeyType="0", Entries=str(len(analyses))
        )

        for idx in range(1, len(analyses) + 1):
            ET.SubElement(playlist_node, "TRACK", Key=str(idx))

        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = xml.dom.minidom.parseString(raw_xml)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    def export_to_file(self, analyses: List[TrackAnalysis], output_path: str, playlist_name: str = "Cue Nalyzer Library"):
        """Export analyzed tracks to XML file on disk."""
        xml_content = self.generate_xml(analyses, playlist_name=playlist_name)
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(xml_content)

    def sync_master_library(self, analyses: List[TrackAnalysis], custom_path: Optional[str] = None) -> str:
        """
        Synchronize full analyzed collection to master Rekordbox XML bridge.
        Returns the saved file path.
        """
        target_path = custom_path or str(Path.cwd() / self.DEFAULT_MASTER_XML_NAME)
        self.export_to_file(analyses, target_path, playlist_name="Cue Nalyzer Master Collection")
        return target_path
