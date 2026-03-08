"""invoke_agent.py -- Invoke the AgentCore runtime remotely from a local machine.

## How it resolves AGENT_RUNTIME_ARN (in priority order):
    1. ``AGENT_RUNTIME_ARN`` environment variable
    2. ``.env`` file in the current directory
    3. ``terraform output -json`` in the ``../terraform`` directory

## Usage examples:

    # Single prompt
    python invoke_agent.py --prompt "List all indices in the cluster"

    # Interactive mode
    python invoke_agent.py --interactive

    # Save bundle to disk
    python invoke_agent.py --prompt "investigate" --export
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

try:
    import boto3
    import click
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
except ImportError as _e:
    print(
        f"\nMissing dependency: {_e}\n\n"
        "Run the following to set up the local environment:\n\n"
        "    cd app/\n"
        "    uv venv .venv && source .venv/bin/activate\n"
        "    uv pip install -e .\n\n"
        "Then re-run with the venv active:\n\n"
        "    python invoke_agent.py --interactive\n"
    )
    sys.exit(1)

console = Console()

# -- ARN resolution -----------------------------------------------------------

def _load_dotenv(path: str = ".env") -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file."""
    env: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _tf_output(tf_dir: str) -> dict:
    """Run ``terraform output -json`` and return parsed dict."""
    tf_path = Path(tf_dir).expanduser().resolve()
    if not tf_path.is_dir():
        return {}
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=str(tf_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            console.print(f"[dim yellow]terraform output failed: {result.stderr.strip()}[/dim yellow]")
            return {}
        return json.loads(result.stdout)
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        console.print(f"[dim yellow]terraform output error: {exc}[/dim yellow]")
        return {}


def resolve_agent_runtime_arn(tf_dir: str = "../terraform") -> Optional[str]:
    """Resolve AGENT_RUNTIME_ARN from env, .env, or terraform output."""
    # 1. Environment variable
    arn = os.environ.get("AGENT_RUNTIME_ARN", "").strip()
    if arn:
        console.print("[dim]ARN from env var[/dim]")
        return arn

    # 2. .env file
    dot_env = _load_dotenv(".env")
    arn = dot_env.get("AGENT_RUNTIME_ARN", "").strip()
    if arn:
        console.print("[dim]ARN from .env file[/dim]")
        return arn

    # 3. Terraform output
    console.print(f"[dim]Querying terraform output in {tf_dir}...[/dim]")
    tf = _tf_output(tf_dir)
    for candidate in ("agent_runtime_arn", "runtime_arn", "agentcore_runtime_arn"):
        obj = tf.get(candidate)
        if obj:
            value = obj.get("value") if isinstance(obj, dict) else obj
            if value:
                console.print(f"[dim]ARN from terraform output (key: {candidate})[/dim]")
                return str(value)

    return None


# -- AgentCore runtime invocation ---------------------------------------------

def invoke_runtime(
    agent_runtime_arn: str,
    session_id: str,
    prompt: str,
    region: str,
) -> str:
    """Invoke the AgentCore runtime and return the response text."""
    client = boto3.client("bedrock-agentcore", region_name=region)

    body = json.dumps({"inputText": prompt, "sessionId": session_id})

    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        runtimeSessionId=session_id,
        payload=body.encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )

    raw_body = response.get("response") or response.get("body") or response.get("responseStream")

    if raw_body is None:
        return str(response)

    raw_bytes: bytes = raw_body.read() if hasattr(raw_body, "read") else (
        raw_body if isinstance(raw_body, bytes) else str(raw_body).encode()
    )
    raw_str = raw_bytes.decode("utf-8", errors="replace")

    try:
        data = json.loads(raw_str)
        return (
            data.get("outputText")
            or data.get("response")
            or data.get("message")
            or str(data)
        )
    except json.JSONDecodeError:
        return raw_str


# -- Interactive REPL ---------------------------------------------------------

def _interactive_loop(
    agent_runtime_arn: str,
    session_id: str,
    region: str,
    export_dir: Optional[str],
) -> None:
    """Run an interactive prompt loop against the remote AgentCore runtime."""
    turns: list[dict] = []

    console.print(
        Panel.fit(
            f"[bold cyan]OpenSearch Agent -- Remote Invoke[/bold cyan]\n"
            f"[dim]ARN: {agent_runtime_arn[:60]}...\n"
            f"Session: {session_id}  |  Region: {region}[/dim]",
            border_style="cyan",
        )
    )
    console.print("[dim]Type /quit to exit.[/dim]\n")

    while True:
        try:
            raw = console.input("[bold cyan]OS>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting...[/dim]")
            break

        if not raw:
            continue

        if raw.lower() in ("/quit", "/exit", "/q"):
            break

        console.print("[dim]Invoking remote runtime...[/dim]")
        try:
            answer = invoke_runtime(agent_runtime_arn, session_id, raw, region)
        except Exception as exc:
            console.print(f"[red]Invocation error:[/red] {exc}")
            continue

        console.print(Panel(Markdown(answer), title="Agent", border_style="green"))
        turns.append({"user": raw, "agent": answer})

    if export_dir and turns:
        import time

        out_dir = Path(export_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        filepath = out_dir / f"remote-session-{session_id[:8]}-{ts}.json"
        filepath.write_text(
            json.dumps(
                {"session_id": session_id, "turns": turns},
                indent=2,
                ensure_ascii=False,
            )
        )
        console.print(f"[green]Session saved:[/green] {filepath}")


# -- CLI ----------------------------------------------------------------------

@click.command()
@click.option(
    "--prompt", "-p",
    default=None,
    help="Single prompt to send to the runtime and print response.",
)
@click.option(
    "--interactive", "-i",
    is_flag=True,
    default=False,
    help="Run interactive REPL against the remote runtime.",
)
@click.option(
    "--session-id",
    default=None,
    help="Session ID (generated if not provided).",
)
@click.option(
    "--region",
    default=None,
    envvar="AWS_REGION",
    show_default=True,
    help="AWS region of the AgentCore runtime.",
)
@click.option(
    "--tf-dir",
    default="../terraform",
    show_default=True,
    help="Terraform directory used to read agent_runtime_arn output.",
)
@click.option(
    "--export",
    "do_export",
    is_flag=True,
    default=False,
    help="Save conversation bundle to --export-dir.",
)
@click.option(
    "--export-dir",
    default="./exports",
    show_default=True,
    help="Directory for exported conversation files.",
)
def main(
    prompt: Optional[str],
    interactive: bool,
    session_id: Optional[str],
    region: Optional[str],
    tf_dir: str,
    do_export: bool,
    export_dir: str,
) -> None:
    """Invoke the deployed AgentCore runtime from your local machine."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        dot_env = _load_dotenv(".env")
        os.environ.update(dot_env)

    arn = resolve_agent_runtime_arn(tf_dir=tf_dir)
    if not arn:
        console.print(
            "[red]Could not resolve AGENT_RUNTIME_ARN.[/red]\n"
            "Options:\n"
            "  1) Export: export AGENT_RUNTIME_ARN=arn:aws:...\n"
            "  2) Add AGENT_RUNTIME_ARN=... to .env\n"
            "  3) Ensure terraform output exposes 'agent_runtime_arn'"
        )
        sys.exit(1)

    if not region:
        arn_parts = arn.split(":")
        if len(arn_parts) >= 4 and arn_parts[3]:
            region = arn_parts[3]
            console.print(f"[dim]Region auto-detected from ARN: {region}[/dim]")
        else:
            region = os.environ.get("AWS_REGION", "us-east-1")

    sid = session_id or str(uuid.uuid4())
    console.print(f"[dim]Session ID: {sid}[/dim]")

    if interactive:
        _interactive_loop(
            agent_runtime_arn=arn,
            session_id=sid,
            region=region,
            export_dir=export_dir if do_export else None,
        )
    elif prompt:
        console.print("[dim]Invoking remote runtime...[/dim]")
        try:
            answer = invoke_runtime(arn, sid, prompt, region)
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            sys.exit(1)

        console.print(Panel(Markdown(answer), title="Agent Response", border_style="green"))

        if do_export:
            import json as _json
            import time

            out_dir = Path(export_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            filepath = out_dir / f"remote-single-{sid[:8]}-{ts}.json"
            filepath.write_text(
                _json.dumps(
                    {"session_id": sid, "prompt": prompt, "response": answer},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            console.print(f"[green]Response saved:[/green] {filepath}")
    else:
        console.print("[yellow]Use --prompt or --interactive.  See --help.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
