/**
 * Cue Nalyzer — Zero-Manual-Step DJ Studio Frontend Engine
 */

let currentAnalysis = null;
let libraryTracks = [];
let audio = new Audio();
let isPlaying = false;

// DOM Elements
const pickFilesBtn = document.getElementById("pickFilesBtn");
const pickFolderBtn = document.getElementById("pickFolderBtn");
const dropOverlay = document.getElementById("dropOverlay");
const batchProgressBanner = document.getElementById("batchProgressBanner");
const batchProgressTitle = document.getElementById("batchProgressTitle");
const batchCurrentTrack = document.getElementById("batchCurrentTrack");
const batchProgressFraction = document.getElementById("batchProgressFraction");
const batchProgressFill = document.getElementById("batchProgressFill");

const rekordboxStatusBadge = document.getElementById("rekordboxStatusBadge");
const rekordboxStatusText = document.getElementById("rekordboxStatusText");

// Library Modal
const openLibraryModalBtn = document.getElementById("openLibraryModalBtn");
const closeLibraryModalBtn = document.getElementById("closeLibraryModalBtn");
const libraryModal = document.getElementById("libraryModal");
const libraryTableBody = document.getElementById("libraryTableBody");
const libCountBadge = document.getElementById("libCountBadge");
const modalLibCount = document.getElementById("modalLibCount");

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
const cueEvidenceList = document.getElementById("cueEvidenceList");

// Initialize
window.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  setupDragAndDrop();
  fetchLibrary();
  checkRekordboxDbStatus();
  resizeCanvas();
  window.addEventListener("resize", () => {
    resizeCanvas();
    if (currentAnalysis) drawWaveform(currentAnalysis);
  });
});

function setupEventListeners() {
  // Native Windows Explorer Dialog Triggers
  pickFilesBtn.addEventListener("click", openNativeFilesDialog);
  pickFolderBtn.addEventListener("click", openNativeFolderDialog);

  playPauseBtn.addEventListener("click", togglePlayPause);
  stopBtn.addEventListener("click", stopPlayback);

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

    if (e.code === "Space") {
      e.preventDefault();
      togglePlayPause();
      return;
    }

    // Number keys 1-8 or letters A-H trigger Hot Cues
    const key = e.key.toUpperCase();
    const numMap = { "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8 };
    const letterMap = { "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8 };
    const padIdx = numMap[key] || letterMap[key];

    if (padIdx && currentAnalysis) {
      const cue = currentAnalysis.cue_points.find((c) => c.hot_cue_index === padIdx);
      if (cue) {
        seekTo(cue.timestamp);
        if (!isPlaying) togglePlayPause();
      }
    }
  });

  waveformCanvas.parentElement.addEventListener("click", (e) => {
    if (!currentAnalysis || !audio.duration) return;
    const rect = waveformCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const fraction = Math.max(0, Math.min(1, clickX / rect.width));
    seekTo(fraction * audio.duration);
  });

  openLibraryModalBtn.addEventListener("click", () => libraryModal.classList.remove("hidden"));
  closeLibraryModalBtn.addEventListener("click", () => libraryModal.classList.add("hidden"));

  audio.addEventListener("timeupdate", updatePlayhead);
  audio.addEventListener("ended", () => {
    isPlaying = false;
    playIcon.textContent = "▶ PLAY";
  });
}

function setupDragAndDrop() {
  window.addEventListener("dragenter", (e) => {
    e.preventDefault();
    dropOverlay.classList.remove("hidden");
  });

  window.addEventListener("dragover", (e) => {
    e.preventDefault();
  });

  window.addEventListener("dragleave", (e) => {
    if (e.clientX <= 0 || e.clientY <= 0 || e.clientX >= window.innerWidth || e.clientY >= window.innerHeight) {
      dropOverlay.classList.add("hidden");
    }
  });

  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    dropOverlay.classList.add("hidden");

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    // Filter audio files
    const audioExts = [".mp3", ".wav", ".flac", ".m4a", ".aiff", ".ogg"];
    const audioFiles = files.filter((f) => audioExts.some((ext) => f.name.toLowerCase().endsWith(ext)));

    if (audioFiles.length > 0) {
      // In web apps, file paths may require user selecting via native picker for local absolute paths
      if (audioFiles[0].path) {
        // Electron / local shell absolute path available
        const paths = audioFiles.map((f) => f.path);
        processSelectedFilesList(paths);
      } else {
        // Fallback: prompt native file picker
        openNativeFilesDialog();
      }
    }
  });
}

// Native Windows File / Folder Dialog Handlers
async function openNativeFilesDialog() {
  try {
    const res = await fetch("/api/dialog/pick-files", { method: "POST" });
    if (!res.ok) return;
    const data = await res.json();
    if (data.files && data.files.length > 0) {
      processSelectedFilesList(data.files);
    }
  } catch (err) {
    console.error("File dialog error:", err);
  }
}

async function openNativeFolderDialog() {
  try {
    const res = await fetch("/api/dialog/pick-folder", { method: "POST" });
    if (!res.ok) return;
    const data = await res.json();
    if (data.folder) {
      processFolderBatch(data.folder);
    }
  } catch (err) {
    console.error("Folder dialog error:", err);
  }
}

async function processSelectedFilesList(paths) {
  if (paths.length === 1) {
    // Single track immediate analyze
    analyzeTrack(paths[0]);
    return;
  }

  // Multi-track batch queue
  batchProgressBanner.classList.remove("hidden");
  batchProgressTitle.textContent = `Analyzing ${paths.length} Tracks...`;

  let completed = 0;
  for (let i = 0; i < paths.length; i++) {
    const p = paths[i];
    const fileName = p.split(/[\\/]/).pop();
    batchCurrentTrack.textContent = `(${i + 1}/${paths.length}) ${fileName}`;
    batchProgressFraction.textContent = `${i + 1} / ${paths.length}`;
    batchProgressFill.style.width = `${Math.round(((i + 1) / paths.length) * 100)}%`;

    try {
      const res = await fetch("/api/analyze/path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: p }),
      });
      if (res.ok) {
        const analysis = await res.json();
        completed++;
        if (i === 0 || !currentAnalysis) {
          loadAnalysisData(analysis);
        }
      }
    } catch (e) {
      console.error("Failed track analysis:", p, e);
    }
  }

  batchProgressTitle.textContent = `✓ Finished ${completed} Tracks (Auto-Synced to Rekordbox)`;
  setTimeout(() => batchProgressBanner.classList.add("hidden"), 3000);
  fetchLibrary();
  checkRekordboxDbStatus();
}

async function processFolderBatch(folderPath) {
  batchProgressBanner.classList.remove("hidden");
  batchProgressTitle.textContent = "Scanning and analyzing folder...";
  batchCurrentTrack.textContent = folderPath;
  batchProgressFraction.textContent = "Working...";
  batchProgressFill.style.width = "40%";

  try {
    const res = await fetch("/api/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: folderPath }),
    });

    if (res.ok) {
      const data = await res.json();
      batchProgressFill.style.width = "100%";
      batchProgressTitle.textContent = `✓ Batch Complete: ${data.analyzed_count} analyzed, ${data.skipped_count} cached`;
      batchProgressFraction.textContent = `${data.total_found} tracks`;
      batchCurrentTrack.textContent = data.rekordbox_db_synced
        ? "✓ Master Rekordbox Collection Synced!"
        : "Rekordbox XML Updated";
      
      setTimeout(() => batchProgressBanner.classList.add("hidden"), 3500);
      fetchLibrary();
      checkRekordboxDbStatus();
    }
  } catch (err) {
    batchProgressTitle.textContent = `Batch Error: ${err.message}`;
    console.error("Batch error:", err);
  }
}

async function checkRekordboxDbStatus() {
  try {
    const res = await fetch("/api/rekordbox/db-status");
    if (res.ok) {
      const data = await res.json();
      if (data.available) {
        rekordboxStatusBadge.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-xs font-mono";
        rekordboxStatusText.textContent = `Rekordbox DB: ${data.track_count} Tracks (Auto-Sync Active)`;
      } else {
        rekordboxStatusBadge.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-mono";
        rekordboxStatusText.textContent = "Rekordbox XML Bridge Active";
      }
    }
  } catch (err) {
    console.error("DB status check failed:", err);
  }
}

async function analyzeTrack(path) {
  pickFilesBtn.disabled = true;
  pickFilesBtn.innerHTML = `<span>Analyzing...</span>`;

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
    checkRekordboxDbStatus();
  } catch (err) {
    alert(`Failed to analyze track: ${err.message}`);
  } finally {
    pickFilesBtn.disabled = false;
    pickFilesBtn.innerHTML = `<span>📁 Add Tracks</span>`;
  }
}

async function fetchLibrary() {
  try {
    const res = await fetch("/api/tracks");
    if (res.ok) {
      libraryTracks = await res.json();
      libCountBadge.textContent = libraryTracks.length;
      modalLibCount.textContent = libraryTracks.length;
      renderLibraryTable();
      if (!currentAnalysis && libraryTracks.length > 0) {
        loadAnalysisData(libraryTracks[0]);
      }
    }
  } catch (err) {
    console.error("Failed fetching library:", err);
  }
}

function loadAnalysisData(analysis) {
  currentAnalysis = analysis;
  const meta = analysis.metadata;
  const grid = analysis.beat_grid;
  const key = analysis.key_info;
  const genre = analysis.genre;
  const rhythm = analysis.rhythm || { groove_type: "Straight" };

  audio.src = `/api/audio/${meta.file_hash}`;
  audio.load();

  displayTitle.textContent = meta.title || meta.file_name;
  displayArtist.textContent = meta.artist || "Unknown Artist";
  displayDuration.textContent = formatTime(meta.duration_sec);
  displayBitrate.textContent = meta.bitrate_kbps ? `${meta.bitrate_kbps} kbps` : "320 kbps";
  totalPlayTime.textContent = formatTime(meta.duration_sec);

  displayBpm.textContent = grid.bpm.toFixed(1);
  displayGroove.textContent = rhythm.groove_type;
  displaySwing.textContent = `Swing: ${Math.round(grid.swing_factor * 100)}%`;

  displayCamelot.textContent = key.camelot;
  displayKeyName.textContent = key.key_name;
  displayOpenKey.textContent = `OpenKey: ${key.openkey}`;

  displayPrimaryGenre.textContent = genre.primary_genre;
  displayGenreConfidence.textContent = `${Math.round(genre.primary_confidence * 100)}%`;
  displayVocalRatio.textContent = `${Math.round(analysis.vocals.vocal_ratio * 100)}%`;

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

  renderCueEvidence(analysis.cue_points);
  renderHotCuePads(analysis.cue_points);
  renderSectionBanners(analysis.structure, meta.duration_sec);

  resizeCanvas();
  drawWaveform(analysis);
  drawBeatGrid(analysis);
  renderCuePins(analysis.cue_points, meta.duration_sec);
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

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#09090b");
  grad.addColorStop(0.5, "#030712");
  grad.addColorStop(1, "#09090b");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  for (let i = 0; i < numPoints; i++) {
    const x = i * step;
    const low = wf.low_peaks[i] || 0;
    const mid = wf.mid_peaks[i] || 0;
    const high = wf.high_peaks[i] || 0;

    const highH = high * halfH * 0.95;
    ctx.fillStyle = "rgba(255, 46, 99, 0.4)";
    ctx.fillRect(x, halfH - highH, step + 0.5, highH * 2);

    const midH = mid * halfH * 0.85;
    ctx.fillStyle = "rgba(255, 179, 0, 0.6)";
    ctx.fillRect(x, halfH - midH, step + 0.5, midH * 2);

    const lowH = low * halfH * 0.75;
    ctx.fillStyle = "rgba(0, 229, 255, 0.85)";
    ctx.fillRect(x, halfH - lowH, step + 0.5, lowH * 2);
  }

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
      pad.className = "bg-zinc-950 border border-zinc-800/40 rounded-xl p-3 flex flex-col justify-between text-left opacity-30 cursor-not-allowed";
      pad.innerHTML = `
        <span class="w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs bg-zinc-800 text-zinc-600 font-mono">
          ${letter}
        </span>
        <div class="mt-2 text-[10px] font-mono text-zinc-700">Empty</div>
      `;
    }

    hotCuePadsGrid.appendChild(pad);
  }
}

function renderCueEvidence(cues) {
  cueEvidenceList.innerHTML = "";
  const hotLabels = ["A", "B", "C", "D", "E", "F", "G", "H"];

  cues.forEach((cue) => {
    const letter = (cue.hot_cue_index && cue.hot_cue_index <= 8) ? hotLabels[cue.hot_cue_index - 1] : "•";
    const item = document.createElement("div");
    item.className = "bg-zinc-950/70 border border-zinc-800/80 rounded-lg p-3 space-y-1 font-mono";
    item.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-bold text-white flex items-center space-x-2">
          <span class="w-5 h-5 rounded flex items-center justify-center font-black text-xs text-black" style="background-color: ${cue.color_hex}">
            ${letter}
          </span>
          <span>${cue.label} — ${formatTime(cue.timestamp)} (Bar ${cue.bar_number})</span>
        </span>
        <span class="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-green-400 font-bold">${cue.confidence_label} (${Math.round(cue.confidence * 100)}%)</span>
      </div>
      <p class="text-[11px] text-zinc-300 leading-snug">${cue.reasoning}</p>
      <div class="text-[10px] text-cyan-400/90 pt-0.5">👉 DJ Action: ${cue.suggested_use}</div>
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
      <td class="text-cyan-400 font-bold">${t.cue_points.length} Cues</td>
      <td>
        <button class="px-2.5 py-1 bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500 hover:text-black rounded text-[10px] font-bold transition">
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
