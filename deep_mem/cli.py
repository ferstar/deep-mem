"""CLI interface for deep-mem search"""

import json
import sys

import click
from rich.console import Console
from rich.markdown import Markdown

from deep_mem.api import APIClient, APIError
from deep_mem.config import Config, ConfigError
from deep_mem.search import DeepMemorySearcher, DeepSearchResult


console = Console()


def format_score(score: float) -> str:
    """Format similarity score as percentage"""
    return f"{score * 100:.0f}%"


def format_importance(importance: float) -> str:
    """Format importance level"""
    if importance >= 0.8:
        return "[red]critical[/]"
    elif importance >= 0.6:
        return "[yellow]high[/]"
    elif importance >= 0.4:
        return "[blue]medium[/]"
    return "[dim]low[/]"


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def display_result(result: DeepSearchResult, verbose: bool = False):
    """Display search results with progressive disclosure and prompt injection protection"""

    # Header
    console.print(f"\n[bold]Query:[/] {result.query}")
    console.print(
        f"[dim]Found {result.total_memories_found} memories, "
        f"{result.total_threads_found} related threads[/]\n"
    )

    if not result.memories:
        console.print("[yellow]No memories found.[/]")
        return

    # Phase 1: Memory summaries (brief descriptions)
    console.print("[bold cyan]== Memories ==[/]\n")

    # Prompt injection protection for memory content
    console.print("<untrusted_memory_content>")

    for i, mem in enumerate(result.memories, 1):
        # Memory header
        title = mem.title or "[untitled]"
        score = format_score(mem.similarity_score)
        importance = format_importance(mem.importance)

        console.print(
            f"[bold]{i}. {title}[/] "
            f"[dim]({score} match, {importance} importance)[/]"
        )

        # Content preview
        preview = truncate(mem.content, 300 if verbose else 150)
        console.print(f"   {preview}")

        # Labels
        if mem.labels:
            labels_str = " ".join(f"[cyan]#{l}[/]" for l in mem.labels)
            console.print(f"   {labels_str}")

        # Thread reference hint
        if mem.source_thread_id:
            console.print(f"   [dim]Source: thread/{mem.source_thread_id[:8]}...[/]")

        console.print()

    console.print("</untrusted_memory_content>\n")

    # Phase 2: Related threads (detail references)
    if result.related_threads:
        console.print("[bold cyan]== Related Threads ==[/]\n")

        console.print("<untrusted_thread_metadata>")
        for thread in result.related_threads:
            title = thread.title or thread.summary or "[untitled thread]"
            tid = thread.thread_id or "?"

            console.print(f"  [bold]> {title}[/]")
            console.print(f"    [dim]id: {tid} ({thread.message_count} messages)[/]")
        console.print("</untrusted_thread_metadata>")

        console.print()
        console.print(
            "[dim]Tip: Use --expand <thread_id> to view full thread content[/]"
        )


def display_thread_detail(thread: dict, console: Console):
    """Display full thread content with prompt injection protection"""
    title = thread.get("title") or thread.get("summary") or "Thread Detail"
    console.print(f"\n[bold cyan]{title}[/]\n")

    messages = thread.get("messages", [])
    if not messages:
        console.print("[yellow]No messages in this thread.[/]")
        return

    # Prompt injection protection
    console.print("\n<untrusted_historical_content>")

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            console.print(f"\n[bold blue]User:[/]")
        elif role == "assistant":
            console.print(f"\n[bold green]A:[/]")
        else:
            console.print(f"\n[bold]{role}:[/]")

        # Render as markdown if it looks like markdown
        if "```" in content or content.startswith("#"):
            console.print(Markdown(content))
        else:
            console.print(content)

    console.print("\n</untrusted_historical_content>")


@click.group()
@click.version_option()
def cli():
    """Deep memory search with progressive disclosure"""
    pass


@cli.command()
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Max memories to return")
@click.option("-t", "--threads", default=5, help="Max related threads")
@click.option("-v", "--verbose", is_flag=True, help="Show more content")
@click.option("--no-threads", is_flag=True, help="Skip thread search")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search(query: str, limit: int, threads: int, verbose: bool, no_threads: bool, as_json: bool):
    """Search memories with progressive thread discovery

    Examples:

        deep-mem search "AI 工程师成长路线"

        deep-mem search "Python async" --limit 5 --verbose

        deep-mem search "项目架构" --no-threads --json
    """
    try:
        config = Config.from_env()
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        sys.exit(1)

    try:
        with APIClient(config.api_url, config.auth_token, config.timeout) as client:
            searcher = DeepMemorySearcher(client)
            result = searcher.search(
                query=query,
                memory_limit=limit,
                thread_limit=threads,
                expand_threads=not no_threads,
            )

            if as_json:
                output = {
                    "query": result.query,
                    "total_memories": result.total_memories_found,
                    "total_threads": result.total_threads_found,
                    "memories": [
                        {
                            "id": m.memory_id,
                            "title": m.title,
                            "content": m.content,
                            "score": m.similarity_score,
                            "importance": m.importance,
                            "labels": m.labels,
                            "source_thread_id": m.source_thread_id,
                        }
                        for m in result.memories
                    ],
                    "threads": [
                        {
                            "id": t.thread_id,
                            "title": t.title,
                            "summary": t.summary,
                            "message_count": t.message_count,
                        }
                        for t in result.related_threads
                    ],
                }
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                display_result(result, verbose=verbose)

    except APIError as e:
        console.print(f"[red]API error:[/] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


@cli.command()
@click.argument("thread_id")
def expand(thread_id: str):
    """View full content of a specific thread

    Example:

        deep-mem expand abc12345-...
    """
    try:
        config = Config.from_env()
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        sys.exit(1)

    try:
        with APIClient(config.api_url, config.auth_token, config.timeout) as client:
            thread = client.get_thread(thread_id)
            display_thread_detail(thread, console)

    except APIError as e:
        console.print(f"[red]API error:[/] {e}")
        sys.exit(1)


@cli.command()
def diagnose():
    """Check API connectivity and configuration"""
    console.print("[bold]Checking configuration...[/]\n")

    try:
        config = Config.from_env()
        console.print(f"[green]OK[/] API URL: {config.api_url}")
        console.print(f"[green]OK[/] Auth token: {'*' * 8}...")
    except ConfigError as e:
        console.print(f"[red]FAIL[/] Configuration: {e}")
        sys.exit(1)

    console.print("\n[bold]Checking API connectivity...[/]\n")

    try:
        with APIClient(config.api_url, config.auth_token, config.timeout) as client:
            # Test memory search
            result = client.search_memories("test", limit=1)
            console.print(f"[green]OK[/] Memory search working")

            # Test thread search
            result = client.search_threads("test", limit=1)
            console.print(f"[green]OK[/] Thread search working")

    except APIError as e:
        console.print(f"[red]FAIL[/] API request: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]FAIL[/] Connection: {e}")
        sys.exit(1)

    console.print("\n[green]All checks passed![/]")


if __name__ == "__main__":
    cli()
