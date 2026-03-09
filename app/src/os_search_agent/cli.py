"""cli.py -- Conversational CLI entrypoint for the OpenSearch agent (Strands).

Commands available during a session:
    /help               - Show available commands
    /reset              - Clear conversation history
    /summarize          - Print a summary of the current session from memory
    /recall <sessionId> - Load a previous session from AgentCore Memory
    /export             - Export the current investigation bundle to disk
    /raw <method> <path> [body] - Direct OpenSearch API call via MCP (bypasses LLM)
    /quit, /exit, /q    - Exit the agent

Usage:
    os-search-agent [OPTIONS]
    python -m os_search_agent [OPTIONS]
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from typing import Optional
from urllib.parse import parse_qs, urlparse

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from os_search_agent import __version__
from os_search_agent.agent import build_system_prompt, create_opensearch_agent
from os_search_agent.config import load_config
from os_search_agent.export import BundleBuilder, export_bundle
from os_search_agent.logging import AgentLogger, LogContext
from os_search_agent.memory import AgentMemory

console = Console()

# -- Slash-command registry ---------------------------------------------------

_HELP_TEXT = """
## Available commands

| Command              | Description                                        |
|----------------------|----------------------------------------------------|
| `/help`              | Show this message                                  |
| `/reset`             | Clear conversation history                         |
| `/summarize`         | Session summary from memory                        |
| `/recall <sessionId>`| Load a previous session by session_id              |
| `/export`            | Export investigation bundle to disk                 |
| `/raw <method> <path> [body]` | Direct OpenSearch API call (bypasses LLM) |
| `/quit` / `/exit`    | Exit the agent                                     |

### /raw examples

```
/raw GET /_cat/indices?expand_wildcards=all&format=json
/raw GET /_cluster/health
/raw GET /my-index/_count
/raw POST /my-index/_search {"query":{"match_all":{}},"size":5}
```

Type anything else to query your OpenSearch cluster.
"""


# -- /raw helper --------------------------------------------------------------


def _handle_raw(args_str: str, mcp_client) -> None:
    """Parse a /raw command and call OpenSearch directly via the MCP client.

    Syntax:  /raw METHOD /path[?query_params] [JSON body]
    Examples:
        /raw GET /_cat/indices?expand_wildcards=all&format=json
        /raw POST /my-index/_search {"query":{"match_all":{}},"size":5}
    """
    tokens = args_str.split(maxsplit=2)
    if len(tokens) < 2:
        console.print("[red]Usage: /raw METHOD /path [body][/red]")
        return

    method = tokens[0].upper()
    raw_path = tokens[1]
    body_str = tokens[2] if len(tokens) > 2 else None

    # Split path and query string
    parsed = urlparse(raw_path if raw_path.startswith("/") else f"/{raw_path}")
    path = parsed.path
    query_params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()} if parsed.query else None

    # Parse body if provided
    body = None
    if body_str:
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError as exc:
            console.print(f"[red]Invalid JSON body:[/red] {exc}")
            return

    tool_args = {"method": method, "path": path}
    if query_params:
        tool_args["query_params"] = query_params
    if body is not None:
        tool_args["body"] = body

    console.print(f"[dim]→ MCP call: GenericOpenSearchApiTool {method} {raw_path}[/dim]")

    try:
        result = mcp_client.call_tool_sync(
            tool_use_id=str(uuid.uuid4()),
            name="GenericOpenSearchApiTool",
            arguments=tool_args,
        )

        # Extract text from the result content
        for item in result.get("content", []):
            text = item.get("text", "")
            # Try to pretty-print JSON
            try:
                parsed_json = json.loads(text.split("\n", 1)[-1])
                pretty = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                console.print(Syntax(pretty, "json", theme="monokai", word_wrap=True))
            except (json.JSONDecodeError, IndexError):
                console.print(text)

        status = result.get("status", "unknown")
        if status == "error":
            console.print(f"[red]Tool returned error status[/red]")

    except Exception as exc:
        console.print(f"[red]MCP call failed:[/red] {exc}")


# -- Async core ---------------------------------------------------------------

async def _run_session(
    config,
    export_dir: str,
) -> None:
    """Run the full interactive session loop using Strands Agent."""

    session_id = str(uuid.uuid4())

    # -- Bootstrap context + logging --
    log_ctx = LogContext(session_id=session_id)
    logger = AgentLogger(
        context=log_ctx,
        aws_region=config.aws_region,
        log_group=config.agent_log_group,
        debug_mode=config.debug_mode,
        max_result_chars=config.max_result_chars,
    )

    logger.info(
        "session_start",
        version=__version__,
        model=config.effective_model_id,
        region=config.aws_region,
        opensearch_url=config.opensearch_url,
    )

    console.print(
        Panel.fit(
            f"[bold cyan]OpenSearch Agent[/bold cyan]  v{__version__}\n"
            f"[dim]Model: {config.effective_model_id}  |  "
            f"Region: {config.aws_region}  |  "
            f"Cluster: {config.opensearch_url}[/dim]",
            border_style="cyan",
        )
    )

    # -- Memory --
    memory = AgentMemory(
        memory_id=config.memory_id,
        actor_id=config.memory_actor_id,
        region=config.aws_region,
        logger=logger,
    )

    # -- Bundle builder --
    bundle = BundleBuilder(
        session_id=session_id,
        model_id=config.effective_model_id,
        aws_region=config.aws_region,
    )

    # -- Strands Agent --
    agent, mcp_client = create_opensearch_agent(config)

    console.print(
        f"\n[green]Session started[/green]  |  session_id: [bold]{session_id}[/bold]"
    )
    console.print("[dim]Type /help to see available commands.[/dim]\n")

    # -- REPL --
    try:
        while True:
            try:
                raw = console.input("[bold cyan]OS>[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Exiting...[/dim]")
                break

            if not raw:
                continue

            # -- Slash commands --
            if raw.startswith("/"):
                parts = raw.split(maxsplit=1)
                cmd = parts[0].lower()

                if cmd in ("/quit", "/exit", "/q"):
                    console.print("[dim]Goodbye.[/dim]")
                    break

                elif cmd == "/help":
                    console.print(Markdown(_HELP_TEXT))

                elif cmd == "/reset":
                    console.print("[yellow]Conversation cleared.[/yellow]")
                    session_id = str(uuid.uuid4())
                    log_ctx.session_id = session_id
                    bundle = BundleBuilder(
                        session_id=session_id,
                        model_id=config.effective_model_id,
                        aws_region=config.aws_region,
                    )
                    try:
                        mcp_client.stop()
                    except Exception:
                        pass
                    agent, mcp_client = create_opensearch_agent(config)
                    console.print(
                        f"[green]New session:[/green] {session_id}\n"
                    )

                elif cmd == "/summarize":
                    summary = memory.summarize_session(session_id)
                    console.print(Panel(summary, title="Memory Summary", border_style="blue"))

                elif cmd == "/recall":
                    if len(parts) < 2:
                        console.print("[red]/recall requires a session_id.[/red]")
                        continue
                    recall_id = parts[1].strip()
                    records = memory.recall_session(recall_id)
                    if not records:
                        console.print(f"[yellow]No records found for {recall_id}[/yellow]")
                    else:
                        console.print(
                            Panel(
                                memory.summarize_session(recall_id),
                                title=f"Recall - {recall_id}",
                                border_style="blue",
                            )
                        )

                elif cmd == "/export":
                    path = export_bundle(bundle.build(), output_dir=export_dir, logger=logger)
                    console.print(f"[green]Bundle exported:[/green] {path}")

                elif cmd == "/raw":
                    if len(parts) < 2:
                        console.print(
                            "[red]/raw requires at least: METHOD PATH[/red]\n"
                            "[dim]Example: /raw GET /_cat/indices?expand_wildcards=all&format=json[/dim]"
                        )
                        continue
                    _handle_raw(parts[1], mcp_client)

                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]  Use /help")

                continue

            # -- Normal chat turn --
            console.print("[dim]Thinking...[/dim]")
            try:
                result = agent(raw)
                answer = str(result)
                bundle.add_turn("user", raw, correlation_id=log_ctx.correlation_id)
                bundle.add_turn("assistant", answer, correlation_id=log_ctx.correlation_id)
            except Exception as exc:
                logger.error("repl_error", exc=exc)
                console.print(f"[red]Error:[/red] {exc}")
                continue

            console.print(Panel(Markdown(answer), title="OpenSearch Agent", border_style="green"))

    finally:
        try:
            mcp_client.stop()
        except Exception:
            pass

    # Final export
    final_path = export_bundle(bundle.build(), output_dir=export_dir, logger=logger)
    console.print(f"[dim]Final bundle saved to: {final_path}[/dim]")
    logger.info("session_end", bundle_path=final_path)


# -- Click entrypoint ---------------------------------------------------------

@click.command()
@click.option(
    "--model",
    default=None,
    help="Override MODEL_ID env var (local development only).",
    show_default=False,
)
@click.option(
    "--export-dir",
    default="./exports",
    show_default=True,
    help="Directory for exported investigation bundles.",
)
@click.version_option(__version__, prog_name="os-search-agent")
def main(
    model: Optional[str],
    export_dir: str,
) -> None:
    """OpenSearch Agent -- Data exploration via Strands + OpenSearch MCP."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    config = load_config(model_id_override=model)

    console.print(
        f"[dim]Selected model: [bold]{config.effective_model_id}[/bold][/dim]"
    )

    asyncio.run(
        _run_session(
            config=config,
            export_dir=export_dir,
        )
    )


if __name__ == "__main__":
    main()
