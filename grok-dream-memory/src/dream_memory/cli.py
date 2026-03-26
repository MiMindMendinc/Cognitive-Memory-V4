"""Command-line interface for grok-dream-memory."""
from __future__ import annotations

import json
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .config import Config, LANES
from .memory import MemoryStore
from .dreamer import dream_cycle
from .scheduler import start_scheduler, stop_scheduler

app = typer.Typer(name="dream-memory", add_completion=False, help="grok-dream-memory CLI")
console = Console()

_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


@app.command()
def add(
    text: str = typer.Argument(..., help="Memory text to store"),
    lane: str = typer.Option("episodic", "--lane", "-l", help=f"Memory lane: {LANES}"),
) -> None:
    """Add a new memory."""
    mem_id = get_store().store(text, lane)
    rprint(f"[green]✓ Stored[/green] in [bold]{lane}[/bold] lane — id: {mem_id}")


@app.command()
def recall(
    query: str = typer.Argument(..., help="Query text"),
    lane: Optional[str] = typer.Option(None, "--lane", "-l", help="Filter by lane"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
) -> None:
    """Recall memories semantically similar to query."""
    results = get_store().recall(query, lane=lane, top_k=top_k)
    if not results:
        rprint("[yellow]No memories found.[/yellow]")
        return
    table = Table(title=f"Recall: '{query}'", show_lines=True)
    table.add_column("Score", style="cyan", width=6)
    table.add_column("Lane", style="magenta", width=12)
    table.add_column("Text")
    table.add_column("Importance", style="yellow", width=10)
    for r in results:
        table.add_row(
            str(r["score"]),
            r.get("lane", ""),
            r.get("text", "")[:120],
            str(r.get("importance", "")),
        )
    console.print(table)


@app.command()
def show(
    lane: Optional[str] = typer.Option(None, "--lane", "-l", help="Filter by lane"),
) -> None:
    """Show all stored memories."""
    memories = get_store().all_memories(lane=lane)
    rprint(f"[bold]Total memories:[/bold] {len(memories)}")
    for m in memories:
        rprint(f"  [cyan]{m.get('lane','?')}[/cyan] | {m.get('text','')[:80]} | imp={m.get('importance','')}")


@app.command()
def dream() -> None:
    """Run a dream cycle manually."""
    result = dream_cycle(store=get_store())
    rprint(f"[bold green]Dream cycle complete:[/bold green] {json.dumps(result, indent=2)}")


@app.command()
def stats() -> None:
    """Show memory statistics."""
    ms = get_store()
    total = ms.count()
    rprint(f"[bold]Total memories:[/bold] {total}")
    for lane in LANES:
        count = len(ms.all_memories(lane=lane))
        rprint(f"  {lane}: {count}")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    api: bool = typer.Option(False, "--api", help="Launch FastAPI server instead of CLI"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)
    if api:
        import uvicorn
        from api.server import app as fastapi_app
        uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
        return
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
