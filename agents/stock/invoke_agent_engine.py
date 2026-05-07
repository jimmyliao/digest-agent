"""Invoke a deployed Agent Engine reasoning engine.

Usage:
    # Latest deploy from deployed-agent-engines.txt + default message
    python -m agents.stock.invoke_agent_engine

    # Custom message
    python -m agents.stock.invoke_agent_engine "鴻海營運分析"

    # Specific resource + message
    python -m agents.stock.invoke_agent_engine \\
        projects/N/locations/us-central1/reasoningEngines/NNN \\
        "聯發科展望"

Env (load order: shell > .env.deploy > .env):
    GCP_PROJECT       required
    GCP_LOCATION      optional (default: us-central1)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

REGISTRY_FILE = "deployed-agent-engines.txt"
DEFAULT_MESSAGE = "分析台積電 AI 晶片供應鏈"


def latest_resource_from_registry() -> str | None:
    p = Path(REGISTRY_FILE)
    if not p.exists():
        return None
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    # Format: "<iso-utc>\t<resource_name>"
    parts = lines[-1].split("\t")
    return parts[1] if len(parts) >= 2 else None


def parse_args(argv: list[str]) -> tuple[str | None, str]:
    """Returns (resource_or_None, message)."""
    resource: str | None = None
    message = DEFAULT_MESSAGE
    if argv:
        if argv[0].startswith("projects/") and "/reasoningEngines/" in argv[0]:
            resource = argv[0]
            if len(argv) > 1:
                message = " ".join(argv[1:])
        else:
            message = " ".join(argv)
    return resource, message


def main() -> None:
    resource, message = parse_args(sys.argv[1:])

    if resource is None:
        resource = latest_resource_from_registry()
        if resource is None:
            print(
                f"❌ No resource specified and {REGISTRY_FILE} is empty/missing.\n"
                "   Run `./scripts/deploy-to-agent-engine.sh` first, or pass resource as arg.",
                file=sys.stderr,
            )
            sys.exit(1)

    project = os.environ.get("GCP_PROJECT")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    if not project:
        print("❌ Missing GCP_PROJECT (set in .env.deploy or shell)", file=sys.stderr)
        sys.exit(1)

    try:
        import vertexai  # noqa: F401
    except ImportError:
        print(
            "❌ vertexai SDK not installed.\n   Run: uv sync --extra geap",
            file=sys.stderr,
        )
        sys.exit(1)

    import vertexai

    print(f"🎯 Resource: {resource}")
    print(f"📍 Project : {project} / {location}")
    print(f"💬 Message : {message}")
    print("─" * 60)

    client = vertexai.Client(project=project, location=location)
    remote = client.agent_engines.get(resource)

    async def run() -> None:
        n = 0
        async for event in remote.async_stream_query(user_id="demo", message=message):
            n += 1
            # Each event is a dict — print key fields if present
            if isinstance(event, dict):
                author = event.get("author") or event.get("agent_name") or "?"
                content = event.get("content") or event.get("text") or event
                print(f"[{n}] {author}: {content}")
            else:
                print(f"[{n}] {event}")
            print()
        print("─" * 60)
        print(f"✅ Stream complete — {n} event(s)")

    asyncio.run(run())


if __name__ == "__main__":
    main()
