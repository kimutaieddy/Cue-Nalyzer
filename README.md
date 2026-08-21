# 🎛️ Cue Nalyzer — Local DJ Music Intelligence System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![Pioneer Rekordbox Compatible](https://img.shields.io/badge/Rekordbox-XML%20Ready-red.svg)](https://rekordbox.com)

> **Cue Nalyzer** is a genre-aware, context-driven local DJ music intelligence and cue extraction system. Instead of simply computing raw audio numbers, Cue Nalyzer **computationally listens to music as an experienced DJ does**, understanding structural phrasing (8/16/32-bar grids), vocal placement, log-drum/bass transitions, energy trajectories, and genre conventions to generate **musically justified, confidence-rated cue points and transition strategies**.

---

## 🌟 Key Capabilities & Intelligence Layers

### 1. 🎵 Multi-Layer MIR (Music Information Retrieval) Engine
- **3-Band Frequency Energy & Spectrograms**: Low/Sub (<250Hz), Mids (250Hz–3.5kHz), Highs (>3.5kHz) designed for Pioneer/Serato-style 3-band waveforms.
- **Dynamic Beat & Phrase Gridding**: Downbeat (Bar 1, Beat 1) detection, 4/4 meter validation, swing/groove syncopation factor, and strict 8/16/32-bar DJ phrasing.
- **Camelot Wheel & Harmonic Key Detection**: Chroma CQT + HPCP correlated against 24 Major and Minor key profiles, mapped to Camelot (`1A`–`12B`) and OpenKey (`1m`–`12d`) systems with harmonic stability curves.
- **Vocal Activity Detection (VAD)**: Formant harmonic comb filtering (300–3500 Hz) to detect singing, speech, vocal entrance points, and vocal exit points to prevent vocal clashing during blends.
- **Rhythm & Groove Intelligence**:
  - **Amapiano Log-Drum Detector**: Identifies characteristic pitch-bending sub-bass transients (40–90 Hz) and syncopations around 108–118 BPM.
  - **Afro House Polyrhythm Density**: Measures 3-stroke triplets, organic shaker layering, and swing microtiming.
  - **4-on-the-Floor Regularity**: Quantifies kick drum stability for techno and house mixing.

### 2. 🧠 Genre-Aware Context Engine
Probabilistic genre classification across electronic and urban styles:
- **Amapiano** (Log-drum basslines, 112 BPM groove, vocal hooks)
- **Afro House** (Polyrhythmic percussion, 122 BPM organic builds)
- **Deep House / Melodic House** (Smooth 4/4 grooves, dynamic breakdowns)
- **Tech House / Techno** (Hypnotic rhythm textures, 126–132 BPM)
- **Drum & Bass** (170+ BPM breakbeat tempo)
- **Hip-Hop / R&B** (Verse/hook arrangement)

### 3. 🎯 Contextual DJ Cue Points (Hot Cues A–H)
Generates 8 prioritized, confidence-scored Hot Cues with natural-language reasoning:
- `Pad A (Mix-In)`: Phrase-aligned intro groove with low vocal clash risk.
- `Pad B (Loop)`: Flawless 8/16-bar instrumental loop section.
- `Pad C (Vocal In)`: First vocal entrance warning point to prevent vocal clashes.
- `Pad D (Main Drop)`: High-energy release point where full sub-bass and kicks return.
- `Pad E (Breakdown)`: Low-energy melodic space for introducing incoming tracks.
- `Pad F (Secondary Drop)`: Re-drop / secondary energy peak.
- `Pad G (Vocal Out)`: Final vocal conclusion, opening clean instrumental blend windows.
- `Pad H (Mix-Out)`: Phrase-aligned outro transition for safe fading and bass swapping.

### 4. 🎛️ Library Transition Match Advisor
- Evaluates transition compatibility between any two tracks using Camelot rules (`PERFECT_MATCH`, `ENERGY_BOOST (+1)`, `RELATIVE_SCALE`, `SUBDOMINANT (-1)`).
- Analyzes BPM pitch-fader stretch percentages.
- Recommends transition styles (`Long 32-Bar Harmonic Blend`, `Breakdown-to-Drop Cut`, `Quick 8-Bar Fade`).

### 5. 💿 Pioneer Rekordbox XML Export
- Direct export to standard Pioneer Rekordbox XML format.
- Imports seamless Beatgrid markers (`<TEMPO Inizio="..." Bpm="..." />`), Hot Cues (A–H) with color coding, and Memory Cues with detailed DJ comments into Rekordbox and Pioneer CDJs.

### 6. 💻 Interactive DJ Web Studio & Rich CLI
- **Web Studio**: Dark neon DJ aesthetic, interactive 3-band waveform visualizer, hot cue pads with instant auditioning, playhead scrubber, and dual-deck match simulator.
- **Rich CLI**: Full terminal dashboard with colorful tables and ASCII energy progression graphs.

---

## 🚀 Quick Start

### 1. Installation

```powershell
# Clone the repository
git clone https://github.com/kimutaieddy/Cue-Nalyzer.git
cd "Cue Nalyzer"

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt
```

---

## 🛠️ CLI Usage

### Analyze a Single Track
```powershell
python -m cue_nalyzer.cli.main analyze "D:\music\track.mp3"
```
Options:
- `--rekordbox playlist.xml`: Export Rekordbox XML file.
- `--json analysis.json`: Export full structured analysis data.
- `--force`: Ignore cached analysis and recompute.

### Batch Analyze a Folder
```powershell
python -m cue_nalyzer.cli.main batch "D:\music\Afro House" --rekordbox "afro_house_set.xml"
```

### Transition Match Two Tracks
```powershell
python -m cue_nalyzer.cli.main match "D:\music\track1.mp3" "D:\music\track2.mp3"
```

### Launch Interactive Web Studio
```powershell
python -m cue_nalyzer.cli.main serve --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 🌐 Web Studio Interface

1. **3-Band Waveform Canvas**: Blue/Cyan = Sub/Bass, Amber = Mids/Vocals, Crimson = Highs/Air.
2. **Beatgrid & Downbeat Markers**: Downbeat phase alignment (Bar 1 Beat 1) and phrase boundaries (B1, B9, B17, B33).
3. **Interactive Hot Cue Pads**: Jump to and audition cue points with a single click or spacebar.
4. **Transition Advisor**: Test blend compatibility between any two tracks in your local library.

---

## 🧪 Automated Testing

Run the full pytest test suite:
```powershell
.\venv\Scripts\pytest tests/ -v
```

---

## 📂 Project Architecture

```
Cue Nalyzer/
├── cue_nalyzer/
│   ├── core/
│   │   ├── config.py           # Audio DSP parameters, frequency bands, Camelot map
│   │   ├── models.py           # Pydantic data schemas (BeatGrid, DJCuePoint, TrackAnalysis)
│   │   ├── audio_loader.py     # Multi-format audio loader & metadata extractor
│   │   └── cache.py            # SQLite + JSON local persistent cache
│   ├── mir/
│   │   ├── beat_tracker.py     # Onset envelopes, downbeats, 8/16/32-bar phrase grids
│   │   ├── key_detector.py     # Chroma CQT, HPCP, Camelot wheel & OpenKey mapper
│   │   ├── energy_analyzer.py  # 3-band energy curves, LUFS loudness, tension index
│   │   ├── vocal_detector.py   # Vocal formant detection, presence curve & vocal bounds
│   │   ├── rhythm_analyzer.py  # Syncopation, Amapiano log-drums, Afro polyrhythms
│   │   └── segmenter.py        # SSM novelty filtering & phrase-aligned segmentation
│   ├── intelligence/
│   │   ├── genre_classifier.py # Probabilistic genre reasoning engine
│   │   ├── dj_reasoner.py      # Natural language DJ briefings & clash risk analysis
│   │   ├── cue_generator.py    # Prioritized, confidence-scored Hot Cue generator
│   │   └── set_planner.py      # Camelot harmonic matching & transition evaluator
│   ├── export/
│   │   ├── rekordbox_xml.py    # Pioneer Rekordbox XML exporter
│   │   └── json_exporter.py    # Structured JSON exporter
│   ├── api/
│   │   ├── server.py           # FastAPI web server
│   │   └── routes.py           # REST endpoints
│   ├── ui/
│   │   ├── index.html          # Web Studio dashboard
│   │   ├── app.js              # Web Audio playback & 3-band waveform visualizer
│   │   └── style.css           # Modern neon DJ aesthetic styling
│   ├── cli/
│   │   └── main.py             # Rich terminal CLI dashboard
│   └── analyzer.py             # Unified end-to-end analyzer engine
├── tests/
│   ├── test_mir.py             # MIR component unit tests
│   ├── test_segmenter.py       # Structural segmenter tests
│   ├── test_genre.py           # Genre classifier tests
│   ├── test_cue_generator.py   # Cue generator & Camelot matching tests
│   └── test_rekordbox.py       # Rekordbox XML exporter tests
├── pyproject.toml              # Package configuration
├── requirements.txt            # Python dependencies
└── README.md                   # System documentation
```

---

## 📜 License
MIT License. Built for DJs and Music Information Retrieval researchers.

