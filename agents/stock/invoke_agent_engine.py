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
AUTO_DISCOVER_PREFIX = "digest-agent"


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


def auto_discover(project: str, location: str, prefix: str = AUTO_DISCOVER_PREFIX) -> str | None:
    """Find a unique deployed engine matching display_name prefix. Returns None on 0 or >1 match."""
    import vertexai
    client = vertexai.Client(project=project, location=location)
    matches = [
        e for e in client.agent_engines.list()
        if (e.api_resource.display_name or "").startswith(prefix)
    ]
    if len(matches) == 1:
        return matches[0].api_resource.name
    if len(matches) > 1:
        print(
            f"⚠️  Auto-discover found {len(matches)} engines matching '{prefix}':",
            file=sys.stderr,
        )
        for e in matches:
            print(f"    - {e.api_resource.name}", file=sys.stderr)
        print(
            "    Pass the specific resource path as first arg.",
            file=sys.stderr,
        )
    return None


def verify_resource_exists(resource: str, project: str, location: str) -> bool:
    """Returns True if the engine exists, False if 404."""
    import vertexai
    try:
        client = vertexai.Client(project=project, location=location)
        client.agent_engines.get(name=resource)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "not found" in msg or "404" in msg or "does not exist" in msg:
            return False
        # Other errors: surface upward
        raise


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

    # Resolve resource via cascading fallback:
    #   1. CLI arg
    #   2. Registry file last line (verified to still exist)
    #   3. Auto-discover by display_name prefix (must be unique)
    if resource is None:
        candidate = latest_resource_from_registry()
        if candidate and verify_resource_exists(candidate, project, location):
            resource = candidate
            print(f"📒 Using registry latest: {candidate}")
        elif candidate:
            print(f"⚠️  Registry latest no longer exists (404): {candidate}")

    if resource is None:
        print(f"🔎 Auto-discovering by prefix '{AUTO_DISCOVER_PREFIX}'...")
        resource = auto_discover(project, location)
        if resource:
            print(f"📡 Auto-discovered: {resource}")

    if resource is None:
        print(
            "❌ Cannot resolve a deployed Agent Engine.\n"
            "   - Check ./scripts/list-agent-engines.sh\n"
            "   - Or run ./scripts/deploy-to-agent-engine.sh first\n"
            "   - Or pass resource path as first arg",
            file=sys.stderr,
        )
        sys.exit(1)

    import vertexai

    print(f"🎯 Resource: {resource}")
    print(f"📍 Project : {project} / {location}")
    print(f"💬 Message : {message}")
    print("─" * 60)

    client = vertexai.Client(project=project, location=location)
    remote = client.agent_engines.get(name=resource)

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
