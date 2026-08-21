"""Command-Line Interface (CLI) for Cue Nalyzer with rich formatting and Rekordbox sync."""

import argparse
import sys
from pathlib import Path

# Ensure Windows UTF-8 stdout handling
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from cue_nalyzer.analyzer import AnalyzerEngine
from cue_nalyzer.batch.batch_processor import BatchProcessor
from cue_nalyzer.core.cache import AnalysisCache
from cue_nalyzer.core.config import Config
from cue_nalyzer.export.json_exporter import JSONExporter
from cue_nalyzer.export.rekordbox_xml import RekordboxXMLExporter

console = Console(highlight=False)


def format_time(seconds: float) -> str:
    """Format seconds into MM:SS.S timestamp."""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:04.1f}"


def cmd_analyze(args):
    """Analyze a single track and display intelligent DJ cue points."""
    file_path = args.file
    engine = AnalyzerEngine()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Listening & Analyzing track with MIR intelligence...[/bold cyan]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("analyze", total=None)
        analysis = engine.analyze_track(file_path, force_recompute=args.force)

    meta = analysis.metadata
    grid = analysis.beat_grid
    key = analysis.key_info
    genre = analysis.genre
    rhythm = analysis.rhythm or type("R", (), {"groove_type": "Four-On-The-Floor"})()
    energy = analysis.energy

    # 1. Header Overview Panel
    overview_table = Table(show_header=False, box=None, padding=(0, 2))
    overview_table.add_row("[bold]Title:[/bold]", f"[cyan]{meta.title}[/cyan]", "[bold]BPM:[/bold]", f"[yellow]{grid.bpm:.1f}[/yellow]")
    overview_table.add_row("[bold]Artist:[/bold]", f"[cyan]{meta.artist}[/cyan]", "[bold]Key:[/bold]", f"[green]{key.camelot} ({key.key_name})[/green]")
    overview_table.add_row("[bold]Duration:[/bold]", format_time(meta.duration_sec), "[bold]Genre:[/bold]", f"[magenta]{genre.primary_genre} ({int(genre.primary_confidence * 100)}%)[/magenta]")
    overview_table.add_row("[bold]Groove:[/bold]", rhythm.groove_type, "[bold]Loudness:[/bold]", f"{energy.average_lufs:.1f} LUFS (Dyn: {energy.dynamic_range_db:.1f} dB)")
    overview_table.add_row("[bold]Vocals:[/bold]", f"{int(analysis.vocals.vocal_ratio * 100)}% Vocal Presence", "[bold]Total Cues:[/bold]", f"[bold green]{len(analysis.cue_points)} Hot Cues[/bold green]")

    console.print(Panel(overview_table, title=f"🎧 [bold white]Cue Nalyzer — {meta.file_name}[/bold white]", border_style="cyan"))

    # 2. Structural Arrangement Table
    struct_table = Table(title="🎼 Phrased Structural Arrangement", header_style="bold magenta", border_style="dim")
    struct_table.add_column("Sec", justify="right", style="dim")
    struct_table.add_column("Time Range", justify="center")
    struct_table.add_column("Bars", justify="center")
    struct_table.add_column("Section Type", justify="left")
    struct_table.add_column("Energy", justify="center")
    struct_table.add_column("Musical Context & DJ Description", justify="left")

    for s in analysis.structure:
        color = "green" if "DROP" in s.label.value else ("yellow" if "BUILD" in s.label.value or "BREAK" in s.label.value else "white")
        energy_bar = "█" * int(s.energy_level * 6) + "░" * (6 - int(s.energy_level * 6))
        struct_table.add_row(
            str(s.section_id),
            f"{format_time(s.start_time)} - {format_time(s.end_time)}",
            f"Bar {s.start_bar}-{s.end_bar} ({s.num_bars}b)",
            f"[{color}]{s.label.value}[/{color}]",
            energy_bar,
            s.description,
        )

    console.print(struct_table)
    console.print()

    # 3. Recommended DJ Cue Points Table
    cue_table = Table(title="🎯 Pioneer Rekordbox Hot Cues (Performance Pads A–H)", header_style="bold cyan", border_style="cyan")
    cue_table.add_column("Hot Cue", justify="center", style="bold")
    cue_table.add_column("Time", justify="center", style="yellow")
    cue_table.add_column("Bar", justify="center")
    cue_table.add_column("Type / Label", justify="left")
    cue_table.add_column("Conf", justify="center", style="green")
    cue_table.add_column("DJ Reasoning & Actionable Advice", justify="left")

    hot_cue_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for cue in analysis.cue_points:
        letter = hot_cue_labels[cue.hot_cue_index - 1] if cue.hot_cue_index and cue.hot_cue_index <= 8 else "-"
        cue_table.add_row(
            f"[{cue.color_hex}]Pad {letter}[/{cue.color_hex}]",
            format_time(cue.timestamp),
            f"Bar {cue.bar_number}",
            f"[{cue.color_hex}]{cue.label}[/{cue.color_hex}]",
            f"{int(cue.confidence * 100)}%",
            f"[bold]{cue.reasoning}[/bold]\n[dim]👉 Action: {cue.suggested_use}[/dim]",
        )

    console.print(cue_table)
    console.print()

    # Exports if requested
    if args.json:
        JSONExporter().export_track(analysis, args.json)
        console.print(f"[green]✓ Analysis exported to JSON: {args.json}[/green]")

    if args.rekordbox:
        RekordboxXMLExporter().export_to_file([analysis], args.rekordbox)
        console.print(f"[green]✓ Rekordbox XML exported: {args.rekordbox}[/green]")


def cmd_batch(args):
    """Batch analyze an entire folder/playlist with instant caching and auto-sync."""
    folder_path = Path(args.folder)
    if not folder_path.is_dir():
        console.print(f"[red]Error: {folder_path} is not a valid directory.[/red]")
        sys.exit(1)

    batch_proc = BatchProcessor()
    console.print(f"[bold cyan]Scanning directory: {folder_path}...[/bold cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing playlist...", total=100)

        def on_progress(cur, total, filename, status, _):
            progress.update(
                task,
                total=total,
                completed=cur,
                description=f"[{'yellow' if 'SKIPPED' in status else 'cyan'}]{filename[:30]}[/]: {status}",
            )

        res = batch_proc.process_folder(
            str(folder_path),
            force_recompute=args.force,
            progress_callback=on_progress,
            auto_sync_rekordbox=True,
        )

    console.print(Panel(
        f"✓ [bold green]Batch Analysis Finished![/bold green]\n\n"
        f"• Total Tracks Found: {res.total_found}\n"
        f"• Newly Analyzed: [cyan]{res.analyzed_count}[/cyan]\n"
        f"• Skipped (Pre-cached): [yellow]{res.skipped_count}[/yellow]\n"
        f"• Failed: [red]{res.failed_count}[/red]\n"
        f"• Master Rekordbox XML Bridge: [bold cyan]{res.rekordbox_xml_path}[/bold cyan]",
        title="⚡ Batch Summary",
        border_style="green",
    ))


def cmd_sync(args):
    """Sync all analyzed library tracks into master Rekordbox XML bridge."""
    cache = AnalysisCache()
    exporter = RekordboxXMLExporter()
    tracks = cache.list_all_tracks()

    if not tracks:
        console.print("[yellow]No analyzed tracks found in library. Run 'analyze' or 'batch' first.[/yellow]")
        return

    out_path = args.output or str(Path.cwd() / RekordboxXMLExporter.DEFAULT_MASTER_XML_NAME)
    exporter.sync_master_library(tracks, custom_path=out_path)
    console.print(f"[bold green]✓ Successfully synced {len(tracks)} tracks to Rekordbox XML bridge: {out_path}[/bold green]")


def cmd_serve(args):
    """Launch the FastAPI server and DJ Web Studio UI."""
    import uvicorn
    console.print(f"[bold green]🚀 Launching Cue Nalyzer DJ Studio on http://{args.host}:{args.port}[/bold green]")
    uvicorn.run("cue_nalyzer.api.server:app", host=args.host, port=args.port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(description="Cue Nalyzer — Intelligent DJ Music Intelligence System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze a single audio track")
    p_analyze.add_argument("file", help="Path to audio file")
    p_analyze.add_argument("--force", action="store_true", help="Force recomputation ignoring cache")
    p_analyze.add_argument("--json", help="Export analysis to JSON file path")
    p_analyze.add_argument("--rekordbox", help="Export to Rekordbox XML file path")

    # batch
    p_batch = subparsers.add_parser("batch", help="Batch analyze an entire folder/playlist")
    p_batch.add_argument("folder", help="Directory containing audio files")
    p_batch.add_argument("--force", action="store_true", help="Force recompute cached files")
    p_batch.add_argument("--rekordbox", help="Custom Rekordbox XML output path")

    # sync
    p_sync = subparsers.add_parser("sync", help="Synchronize all cached tracks to Rekordbox XML bridge")
    p_sync.add_argument("--output", help="Target XML path")

    # serve
    p_serve = subparsers.add_parser("serve", help="Start the Web UI & REST API server")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host address")
    p_serve.add_argument("--port", type=int, default=8000, help="Port number")
    p_serve.add_argument("--reload", action="store_true", help="Auto-reload on code change")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
