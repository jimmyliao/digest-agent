"""List Agent Engines (Reasoning Engines) deployed in a GCP project.

Usage:
    # All engines in default project/location
    python -m agents.stock.list_agent_engines

    # Filter by display_name prefix
    python -m agents.stock.list_agent_engines --filter digest-agent

    # Strict uniqueness check (exit 1 if 0 or >1 matches)
    python -m agents.stock.list_agent_engines --filter digest-agent --require-unique

Env (loaded by wrapper script):
    GCP_PROJECT       required
    GCP_LOCATION      optional (default: us-central1)
"""

from __future__ import annotations

import os
import sys


DEFAULT_FILTER = "digest-agent"


def parse_args(argv: list[str]) -> tuple[str | None, bool, bool]:
    """Returns (filter_prefix, require_unique, json_only)."""
    filter_prefix: str | None = None
    require_unique = False
    json_only = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--filter":
            i += 1
            filter_prefix = argv[i] if i < len(argv) else None
        elif a == "--require-unique":
            require_unique = True
        elif a == "--json":
            json_only = True
        elif a.startswith("--"):
            print(f"Unknown flag: {a}", file=sys.stderr)
            sys.exit(2)
        i += 1
    return filter_prefix, require_unique, json_only


def main() -> None:
    filter_prefix, require_unique, json_only = parse_args(sys.argv[1:])

    project = os.environ.get("GCP_PROJECT")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    if not project:
        print("❌ Missing GCP_PROJECT (set in .env.deploy or shell)", file=sys.stderr)
        sys.exit(1)

    try:
        import vertexai  # noqa: F401
    except ImportError:
        print("❌ vertexai SDK not installed.\n   Run: uv sync --extra geap", file=sys.stderr)
        sys.exit(1)

    import vertexai

    client = vertexai.Client(project=project, location=location)

    # SDK iterates engines lazily; collect all
    engines = list(client.agent_engines.list())

    # Filter by display_name prefix
    matches = engines
    if filter_prefix:
        matches = [e for e in engines if (e.api_resource.display_name or "").startswith(filter_prefix)]

    if json_only:
        import json
        out = [
            {
                "name": e.api_resource.name,
                "display_name": e.api_resource.display_name,
                "create_time": str(getattr(e.api_resource, "create_time", "")),
            }
            for e in matches
        ]
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"📍 {project} / {location}")
        print(f"🔍 Total engines: {len(engines)}", end="")
        if filter_prefix:
            print(f" — matching prefix '{filter_prefix}': {len(matches)}")
        else:
            print()
        print("─" * 70)
        if not matches:
            print("(none)")
        for i, e in enumerate(matches, 1):
            res = e.api_resource
            engine_id = res.name.rsplit("/", 1)[-1]
            ct = str(getattr(res, "create_time", ""))
            print(f"[{i}] {res.display_name or '(no display name)'}")
            print(f"    id         : {engine_id}")
            print(f"    full       : {res.name}")
            if ct:
                print(f"    created    : {ct}")
            print()

    # Uniqueness check
    if require_unique:
        if len(matches) == 0:
            print(f"❌ require-unique failed: 0 matches for '{filter_prefix}'", file=sys.stderr)
            sys.exit(1)
        if len(matches) > 1:
            print(
                f"❌ require-unique failed: {len(matches)} matches for '{filter_prefix}'.\n"
                f"   → Delete extras with: remote.delete(force=True)\n"
                f"   → Or invoke specific one by passing its full resource name to invoke-agent-engine.sh",
                file=sys.stderr,
            )
            sys.exit(1)
        # Exactly one — print just the resource name to stdout for easy capture
        if not json_only:
            print(f"✅ Unique match — resource name:")
            print(matches[0].api_resource.name)


if __name__ == "__main__":
    main()
