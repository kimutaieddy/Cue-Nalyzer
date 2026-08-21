/**
 * Cue Nalyzer — DJ Music Intelligence Studio Frontend Engine
 */

let currentAnalysis = null;
let libraryTracks = [];
let audio = new Audio();
let isPlaying = false;
let animationFrameId = null;

// DOM Elements
const trackPathInput = document.getElementById("trackPathInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const exportRekordboxBtn = document.getElementById("exportRekordboxBtn");
const openLibraryModalBtn = document.getElementById("openLibraryModalBtn");
const closeLibraryModalBtn = document.getElementById("closeLibraryModalBtn");
const libraryModal = document.getElementById("libraryModal");
const libraryTableBody = document.getElementById("libraryTableBody");
const libCountBadge = document.getElementById("libCountBadge");

// Display Elements
const displayTitle = document.getElementById("displayTitle");
const displayArtist = document.getElementById("displayArtist");
const displayDuration = document.getElementById("displayDuration");
const displayBitrate = document.getElementById("displayBitrate");
const displayBpm = document.getElementById("displayBpm");
const displayGroove = document.getElementById("displayGroove");
const displaySwing = document.getElementById("displaySwing");
const displayCamelot = document.getElementById("displayCamelot");
const displayKeyName = document.getElementById("displayKeyName");
const displayOpenKey = document.getElementById("displayOpenKey");
const displayHarmStability = document.getElementById("displayHarmStability");
const displayPrimaryGenre = document.getElementById("displayPrimaryGenre");
const displayGenreConfidence = document.getElementById("displayGenreConfidence");
const displayVocalRatio = document.getElementById("displayVocalRatio");
const genreProbBar = document.getElementById("genreProbBar");

// Waveform & Canvas
const waveformCanvas = document.getElementById("waveformCanvas");
const overlayCanvas = document.getElementById("overlayCanvas");
const playheadNeedle = document.getElementById("playheadNeedle");
const cuePinsContainer = document.getElementById("cuePinsContainer");
const sectionBannerStrip = document.getElementById("sectionBannerStrip");
const currentPlayTime = document.getElementById("currentPlayTime");
const totalPlayTime = document.getElementById("totalPlayTime");

// Controls
const playPauseBtn = document.getElementById("playPauseBtn");
const playIcon = document.getElementById("playIcon");
const stopBtn = document.getElementById("stopBtn");
const hotCuePadsGrid = document.getElementById("hotCuePadsGrid");
const djSummaryText = document.getElementById("djSummaryText");
const cueEvidenceList = document.getElementById("cueEvidenceList");

// Matcher Elements
const matchTrackBSelect = document.getElementById("matchTrackBSelect");
const runMatchBtn = document.getElementById("runMatchBtn");
const transitionResultBox = document.getElementById("transitionResultBox");
const transScore = document.getElementById("transScore");
const transHarm = document.getElementById("transHarm");
const transBpm = document.getElementById("transBpm");
const transExplanation = document.getElementById("transExplanation");

// Initialize
window.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  fetchLibrary();
  resizeCanvas();
  window.addEventListener("resize", () => {
    resizeCanvas();
    if (currentAnalysis) drawWaveform(currentAnalysis);
  });
});

function setupEventListeners() {
  analyzeBtn.addEventListener("click", () => {
    const path = trackPathInput.value.trim();
    if (path) analyzeTrack(path);
  });

  trackPathInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const path = trackPathInput.value.trim();
      if (path) analyzeTrack(path);
    }
  });

  playPauseBtn.addEventListener("click", togglePlayPause);
  stopBtn.addEventListener("click", stopPlayback);

  document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && e.target.tagName !== "INPUT") {
      e.preventDefault();
      togglePlayPause();
    }
  });

  waveformCanvas.parentElement.addEventListener("click", (e) => {
    if (!currentAnalysis || !audio.duration) return;
    const rect = waveformCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const fraction = Math.max(0, Math.min(1, clickX / rect.width));
    seekTo(fraction * audio.duration);
  });

  exportRekordboxBtn.addEventListener("click", () => {
    if (currentAnalysis) {
      window.open(`/api/export/rekordbox?track_hash=${currentAnalysis.metadata.file_hash}`, "_blank");
    } else {
      window.open("/api/export/rekordbox", "_blank");
    }
  });

  openLibraryModalBtn.addEventListener("click", () => libraryModal.classList.remove("hidden"));
  closeLibraryModalBtn.addEventListener("click", () => libraryModal.classList.add("hidden"));

  runMatchBtn.addEventListener("click", runTransitionMatch);

  audio.addEventListener("timeupdate", updatePlayhead);
  audio.addEventListener("ended", () => {
    isPlaying = false;
    playIcon.textContent = "▶ PLAY";
  });
}

function resizeCanvas() {
  const container = waveformCanvas.parentElement;
  const dpr = window.devicePixelRatio || 1;
  const w = container.clientWidth;
  const h = container.clientHeight;

  waveformCanvas.width = w * dpr;
  waveformCanvas.height = h * dpr;
  overlayCanvas.width = w * dpr;
  overlayCanvas.height = h * dpr;

  const ctx1 = waveformCanvas.getContext("2d");
  const ctx2 = overlayCanvas.getContext("2d");
  ctx1.scale(dpr, dpr);
  ctx2.scale(dpr, dpr);
}

// API Calls
async function fetchLibrary() {
  try {
    const res = await fetch("/api/tracks");
    if (res.ok) {
      libraryTracks = await res.json();
      libCountBadge.textContent = libraryTracks.length;
      renderLibraryTable();
      updateMatchSelect();
      if (!currentAnalysis && libraryTracks.length > 0) {
        loadAnalysisData(libraryTracks[0]);
      }
    }
  } catch (err) {
    console.error("Failed fetching library:", err);
  }
}

async function analyzeTrack(path) {
  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = `<span>Analyzing...</span>`;

  try {
    const res = await fetch("/api/analyze/path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_path: path }),
    });

    if (!res.ok) {
      const errData = await res.json();
      alert(`Analysis error: ${errData.detail || "Unknown error"}`);
      return;
    }

    const data = await res.json();
    loadAnalysisData(data);
    fetchLibrary();
  } catch (err) {
    alert(`Failed to analyze track: ${err.message}`);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = `<span>Analyze</span>`;
  }
}

function loadAnalysisData(analysis) {
  currentAnalysis = analysis;
  const meta = analysis.metadata;
  const grid = analysis.beat_grid;
  const key = analysis.key_info;
  const genre = analysis.genre;
  const rhythm = analysis.rhythm;
  const energy = analysis.energy;

  // Set Audio Source
  audio.src = `/api/audio/${meta.file_hash}`;
  audio.load();

  // Populate Meta
  displayTitle.textContent = meta.title || meta.file_name;
  displayArtist.textContent = meta.artist || "Unknown Artist";
  displayDuration.textContent = formatTime(meta.duration_sec);
  displayBitrate.textContent = meta.bitrate_kbps ? `${meta.bitrate_kbps} kbps` : "320 kbps";
  totalPlayTime.textContent = formatTime(meta.duration_sec);

  // BPM & Groove
  displayBpm.textContent = grid.bpm.toFixed(1);
  displayGroove.textContent = rhythm.groove_type;
  displaySwing.textContent = `Swing: ${Math.round(grid.swing_factor * 100)}%`;

  // Key
  displayCamelot.textContent = key.camelot;
  displayKeyName.textContent = key.key_name;
  displayOpenKey.textContent = `OpenKey: ${key.openkey}`;
  displayHarmStability.textContent = `${Math.round(key.harmonic_stability * 100)}%`;

  // Genre
  displayPrimaryGenre.textContent = genre.primary_genre;
  displayGenreConfidence.textContent = `${Math.round(genre.primary_confidence * 100)}%`;
  displayVocalRatio.textContent = `${Math.round(analysis.vocals.vocal_ratio * 100)}%`;

  // Genre Probs
  genreProbBar.innerHTML = "";
  const colors = ["bg-cyan-400", "bg-indigo-400", "bg-pink-400", "bg-amber-400"];
  let cIdx = 0;
  for (const [g, p] of Object.entries(genre.probabilities)) {
    if (p > 0.05) {
      const seg = document.createElement("div");
      seg.className = `h-full ${colors[cIdx % colors.length]}`;
      seg.style.width = `${p * 100}%`;
      seg.title = `${g}: ${Math.round(p * 100)}%`;
      genreProbBar.appendChild(seg);
      cIdx++;
    }
  }

  // Summary & Evidence
  djSummaryText.textContent = analysis.dj_summary;
  renderCueEvidence(analysis.cue_points);
  renderHotCuePads(analysis.cue_points);
  renderSectionBanners(analysis.structure, meta.duration_sec);

  // Draw Waveform & Markers
  resizeCanvas();
  drawWaveform(analysis);
  drawBeatGrid(analysis);
  renderCuePins(analysis.cue_points, meta.duration_sec);
}

// Waveform & Visuals
function drawWaveform(analysis) {
  const canvas = waveformCanvas;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width / dpr;
  const h = canvas.height / dpr;
  const halfH = h / 2;

  ctx.clearRect(0, 0, w, h);

  const wf = analysis.waveform;
  const numPoints = wf.num_samples;
  if (!numPoints) return;

  const step = w / numPoints;

  // Background subtle gradient
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#09090b");
  grad.addColorStop(0.5, "#030712");
  grad.addColorStop(1, "#09090b");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  // Draw 3-Band Waveform
  for (let i = 0; i < numPoints; i++) {
    const x = i * step;
    const low = wf.low_peaks[i] || 0;
    const mid = wf.mid_peaks[i] || 0;
    const high = wf.high_peaks[i] || 0;

    // High Band (Red/Pink Air)
    const highH = high * halfH * 0.95;
    ctx.fillStyle = "rgba(255, 46, 99, 0.4)";
    ctx.fillRect(x, halfH - highH, step + 0.5, highH * 2);

    // Mid Band (Amber / Gold Mids & Vocals)
    const midH = mid * halfH * 0.85;
    ctx.fillStyle = "rgba(255, 179, 0, 0.6)";
    ctx.fillRect(x, halfH - midH, step + 0.5, midH * 2);

    // Low / Sub Band (Cyan / Blue Kick & Bass Punch)
    const lowH = low * halfH * 0.75;
    ctx.fillStyle = "rgba(0, 229, 255, 0.85)";
    ctx.fillRect(x, halfH - lowH, step + 0.5, lowH * 2);
  }

  // Center line
  ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, halfH);
  ctx.lineTo(w, halfH);
  ctx.stroke();
}

function drawBeatGrid(analysis) {
  const canvas = overlayCanvas;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width / dpr;
  const h = canvas.height / dpr;
  const duration = analysis.metadata.duration_sec;

  ctx.clearRect(0, 0, w, h);

  // Draw Downbeat lines (Bar 1 Beat 1)
  const downbeats = analysis.beat_grid.downbeat_times;
  downbeats.forEach((t, idx) => {
    const x = (t / duration) * w;
    const isPhraseBoundary = (idx % 8 === 0);

    ctx.strokeStyle = isPhraseBoundary ? "rgba(255, 255, 255, 0.4)" : "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = isPhraseBoundary ? 1.5 : 0.8;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();

    if (isPhraseBoundary && x > 20) {
      ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
      ctx.font = "9px 'JetBrains Mono', monospace";
      ctx.fillText(`B${idx + 1}`, x + 2, 12);
    }
  });
}

function renderSectionBanners(structure, duration) {
  sectionBannerStrip.innerHTML = "";
  const sectionColors = {
    INTRO: "bg-zinc-800 text-zinc-300",
    GROOVE: "bg-blue-900/60 text-blue-300 border-l border-blue-500/30",
    VERSE: "bg-indigo-900/60 text-indigo-300 border-l border-indigo-500/30",
    VOCAL_HOOK: "bg-cyan-900/60 text-cyan-200 border-l border-cyan-400/40",
    BUILDUP: "bg-amber-900/60 text-amber-200 border-l border-amber-400/40",
    BREAKDOWN: "bg-yellow-950/80 text-yellow-300 border-l border-yellow-500/40",
    DROP: "bg-rose-900/80 text-rose-200 border-l border-rose-500/50",
    SECONDARY_DROP: "bg-purple-900/80 text-purple-200 border-l border-purple-500/50",
    OUTRO: "bg-zinc-800 text-zinc-400 border-l border-zinc-700",
  };

  structure.forEach((s) => {
    const widthPct = ((s.end_time - s.start_time) / duration) * 100;
    const banner = document.createElement("div");
    banner.className = `h-full flex items-center justify-center truncate px-1 ${sectionColors[s.label] || "bg-zinc-800 text-zinc-400"}`;
    banner.style.width = `${widthPct}%`;
    banner.textContent = s.label.replace("_", " ");
    banner.title = `${s.label} (${s.num_bars} bars): ${s.description}`;
    sectionBannerStrip.appendChild(banner);
  });
}

function renderCuePins(cues, duration) {
  cuePinsContainer.innerHTML = "";
  const hotLabels = ["A", "B", "C", "D", "E", "F", "G", "H"];

  cues.forEach((cue) => {
    const leftPct = (cue.timestamp / duration) * 100;
    const letter = (cue.hot_cue_index && cue.hot_cue_index <= 8) ? hotLabels[cue.hot_cue_index - 1] : "•";

    const pin = document.createElement("div");
    pin.className = "absolute top-0 bottom-0 flex flex-col items-center pointer-events-auto cursor-pointer group";
    pin.style.left = `${leftPct}%`;

    pin.innerHTML = `
      <div class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold shadow-md transform -translate-x-1/2 transition group-hover:scale-110"
           style="background-color: ${cue.color_hex}; color: #000;">
        ${letter}
      </div>
      <div class="w-[1.5px] flex-1 opacity-70 group-hover:opacity-100" style="background-color: ${cue.color_hex}"></div>
    `;

    pin.title = `[Pad ${letter}] ${cue.label} at ${formatTime(cue.timestamp)}: ${cue.reasoning}`;
    pin.addEventListener("click", (e) => {
      e.stopPropagation();
      seekTo(cue.timestamp);
      if (!isPlaying) togglePlayPause();
    });

    cuePinsContainer.appendChild(pin);
  });
}

function renderHotCuePads(cues) {
  hotCuePadsGrid.innerHTML = "";
  const hotLabels = ["A", "B", "C", "D", "E", "F", "G", "H"];

  for (let i = 0; i < 8; i++) {
    const cue = cues.find((c) => c.hot_cue_index === i + 1);
    const pad = document.createElement("button");
    const letter = hotLabels[i];

    if (cue) {
      pad.className = "bg-zinc-900 border border-zinc-700/80 hover:border-cyan-400 rounded-xl p-3 flex flex-col justify-between text-left transition transform active:scale-95 shadow-md group relative overflow-hidden";
      pad.style.borderBottom = `3px solid ${cue.color_hex}`;

      pad.innerHTML = `
        <div class="flex items-center justify-between w-full">
          <span class="w-6 h-6 rounded-md flex items-center justify-center font-black text-xs text-black font-mono shadow"
                style="background-color: ${cue.color_hex}">
            ${letter}
          </span>
          <span class="text-[10px] font-mono font-bold text-zinc-400">${formatTime(cue.timestamp)}</span>
        </div>
        <div class="mt-2">
          <div class="text-xs font-bold text-white truncate">${cue.label}</div>
          <div class="text-[10px] font-mono text-zinc-500">Bar ${cue.bar_number}</div>
        </div>
      `;

      pad.addEventListener("click", () => {
        seekTo(cue.timestamp);
        if (!isPlaying) togglePlayPause();
      });
    } else {
      pad.className = "bg-zinc-950 border border-zinc-800/60 rounded-xl p-3 flex flex-col justify-between text-left opacity-40 cursor-not-allowed";
      pad.innerHTML = `
        <span class="w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs bg-zinc-800 text-zinc-500 font-mono">
          ${letter}
        </span>
        <div class="mt-2 text-[10px] font-mono text-zinc-600">Unassigned</div>
      `;
    }

    hotCuePadsGrid.appendChild(pad);
  }
}

function renderCueEvidence(cues) {
  cueEvidenceList.innerHTML = "";
  cues.forEach((cue) => {
    const item = document.createElement("div");
    item.className = "bg-zinc-950/70 border border-zinc-800/80 rounded-lg p-3 space-y-1 font-mono";
    item.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-bold text-white flex items-center space-x-1.5">
          <span class="w-2.5 h-2.5 rounded-full inline-block" style="background-color: ${cue.color_hex}"></span>
          <span>${cue.label} (${formatTime(cue.timestamp)} | Bar ${cue.bar_number})</span>
        </span>
        <span class="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-green-400 font-bold">${cue.confidence_label} (${Math.round(cue.confidence * 100)}%)</span>
      </div>
      <p class="text-[11px] text-zinc-300 leading-snug">${cue.reasoning}</p>
      <div class="text-[10px] text-cyan-400/90 pt-1">👉 Action: ${cue.suggested_use}</div>
    `;
    cueEvidenceList.appendChild(item);
  });
}

function renderLibraryTable() {
  libraryTableBody.innerHTML = "";
  libraryTracks.forEach((t) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-zinc-800/40 cursor-pointer transition";
    tr.innerHTML = `
      <td class="py-2.5 font-bold text-white truncate max-w-[200px]">${t.metadata.title || t.metadata.file_name}</td>
      <td class="text-zinc-400 truncate max-w-[150px]">${t.metadata.artist || "Unknown"}</td>
      <td class="text-yellow-400 font-bold">${t.beat_grid.bpm.toFixed(1)}</td>
      <td><span class="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold">${t.key_info.camelot}</span></td>
      <td class="text-pink-400">${t.genre.primary_genre}</td>
      <td class="text-zinc-500">${formatTime(t.metadata.duration_sec)}</td>
      <td>
        <button class="px-2 py-1 bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500 hover:text-black rounded text-[10px] font-bold transition">
          Load
        </button>
      </td>
    `;
    tr.addEventListener("click", () => {
      loadAnalysisData(t);
      libraryModal.classList.add("hidden");
    });
    libraryTableBody.appendChild(tr);
  });
}

function updateMatchSelect() {
  matchTrackBSelect.innerHTML = `<option value="">-- Choose Library Track --</option>`;
  libraryTracks.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.metadata.file_hash;
    opt.textContent = `${t.metadata.title} (${t.beat_grid.bpm.toFixed(0)} BPM | ${t.key_info.camelot})`;
    matchTrackBSelect.appendChild(opt);
  });
}

async function runTransitionMatch() {
  if (!currentAnalysis) {
    alert("Please analyze or load a track first.");
    return;
  }
  const trackBHash = matchTrackBSelect.value;
  if (!trackBHash) {
    alert("Please select an incoming track B.");
    return;
  }

  try {
    const res = await fetch("/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        track_a_hash: currentAnalysis.metadata.file_hash,
        track_b_hash: trackBHash,
      }),
    });

    if (res.ok) {
      const data = await res.json();
      transScore.textContent = `${data.transition_score} / 100`;
      transHarm.textContent = data.harmonic_compatibility;
      transBpm.textContent = `${data.bpm_diff_pct > 0 ? "+" : ""}${data.bpm_diff_pct.toFixed(1)}% (${data.transition_style})`;
      transExplanation.textContent = data.explanation;
      transitionResultBox.classList.remove("hidden");
    }
  } catch (err) {
    alert(`Match evaluation error: ${err.message}`);
  }
}

// Transport & Audio Playback
function togglePlayPause() {
  if (!currentAnalysis) return;
  if (isPlaying) {
    audio.pause();
    isPlaying = false;
    playIcon.textContent = "▶ PLAY";
  } else {
    audio.play();
    isPlaying = true;
    playIcon.textContent = "⏸ PAUSE";
  }
}

function stopPlayback() {
  audio.pause();
  audio.currentTime = 0;
  isPlaying = false;
  playIcon.textContent = "▶ PLAY";
  updatePlayhead();
}

function seekTo(seconds) {
  audio.currentTime = seconds;
  updatePlayhead();
}

function updatePlayhead() {
  if (!audio.duration) return;
  const cur = audio.currentTime;
  const dur = audio.duration;
  const pct = (cur / dur) * 100;

  playheadNeedle.style.left = `${pct}%`;
  currentPlayTime.textContent = formatTime(cur);
}

function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "00:00.0";
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(1);
  return `${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}`;
}

