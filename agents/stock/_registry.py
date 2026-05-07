"""Shared helpers for the deployed-agent-engines.txt registry.

Used by:
  - deploy_to_agent_engine.py  (append on successful deploy)
  - invoke_agent_engine.py     (read latest line)
  - list_agent_engines.py      (--sync: append API-discovered engines)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

REGISTRY_FILE = "deployed-agent-engines.txt"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append(resource_name: str) -> None:
    """Append a new entry: '<UTC-iso>\t<resource_name>'."""
    with open(REGISTRY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{_now_iso()}\t{resource_name}\n")


def latest() -> str | None:
    """Return the most recently appended resource_name, or None if empty/missing."""
    p = Path(REGISTRY_FILE)
    if not p.exists():
        return None
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    parts = lines[-1].split("\t")
    return parts[1] if len(parts) >= 2 else None


def all_resources() -> set[str]:
    """Return the set of all resource_names ever appended."""
    p = Path(REGISTRY_FILE)
    if not p.exists():
        return set()
    out: set[str] = set()
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split("\t")
        if len(parts) >= 2:
            out.add(parts[1])
    return out


def sync_from_list(resource_names: list[str]) -> int:
    """Append any resource_names not already present. Returns count appended."""
    existing = all_resources()
    appended = 0
    for name in resource_names:
        if name not in existing:
            append(name)
            existing.add(name)
            appended += 1
    return appended
