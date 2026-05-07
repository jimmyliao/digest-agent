"""Deploy `agents/stock` SequentialAgent to Gemini Enterprise Agent Platform
(Vertex AI Agent Engine Runtime).

Usage:
    GCP_PROJECT=your-project \
    STAGING_BUCKET=gs://your-bucket \
    GEMINI_API_KEY=your-key \
    uv run python -m agents.stock.deploy_to_agent_engine

Or via Makefile:
    GCP_PROJECT=xxx STAGING_BUCKET=gs://xxx GEMINI_API_KEY=xxx make deploy-agent-engine

Prerequisites:
- gcloud auth application-default login
- IAM roles: roles/aiplatform.user + roles/storage.admin
- APIs enabled: aiplatform.googleapis.com + storage.googleapis.com
- pip install (or uv add): google-cloud-aiplatform[agent_engines,adk]>=1.112
"""

from __future__ import annotations

import os
import sys


def verify_local() -> None:
    """Quick in-process check before paying for Cloud Build.

    Catches: import errors, agent construction errors, basic AdkApp wrap.
    Does NOT catch: deploy-time packaging issues (extra_packages),
                    pip requirements completeness in deployed env.
    """
    print("🧪 Local verify mode — no GCP cost")
    try:
        from agents.stock.agent import root_agent
        print(f"  ✅ Imported root_agent: {root_agent.name} ({type(root_agent).__name__})")
    except Exception as e:
        print(f"  ❌ Import failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        from vertexai import agent_engines
        app = agent_engines.AdkApp(agent=root_agent)
        print(f"  ✅ AdkApp wrapped OK: {type(app).__name__}")
    except ImportError:
        print(
            "  ⚠️  vertexai SDK not installed (run: uv sync --extra geap)",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ AdkApp wrap failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("✅ Local verify passed — agent is structurally sound.")
    print("   Note: still need actual deploy to catch packaging / requirement gaps.")


def main() -> None:
    if "--verify-local" in sys.argv:
        verify_local()
        return

    # Always run local verify before paying for Cloud Build
    verify_local()
    print()

    project = os.environ.get("GCP_PROJECT")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    bucket = os.environ.get("STAGING_BUCKET")
    api_key = os.environ.get("GEMINI_API_KEY")

    missing = [k for k, v in {
        "GCP_PROJECT": project,
        "STAGING_BUCKET": bucket,
        "GEMINI_API_KEY": api_key,
    }.items() if not v]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    try:
        import vertexai
        from vertexai import agent_engines
    except ImportError:
        print(
            "❌ Missing Agent Engine SDK. Install with:\n"
            "    uv add 'google-cloud-aiplatform[agent_engines,adk]>=1.112'",
            file=sys.stderr,
        )
        sys.exit(1)

    from agents.stock.agent import root_agent

    print(f"📍 Project: {project} / Location: {location}")
    print(f"📦 Staging: {bucket}")
    print(f"🤖 Agent: {root_agent.name} ({type(root_agent).__name__})")

    client = vertexai.Client(project=project, location=location)

    # Uniqueness check: ensure at most one digest-agent-stock-analyzer engine
    DISPLAY_NAME = "digest-agent-stock-analyzer"
    existing = [
        e for e in client.agent_engines.list()
        if (e.api_resource.display_name or "") == DISPLAY_NAME
    ]
    if existing:
        print(f"\n⚠️  Found {len(existing)} existing '{DISPLAY_NAME}' engine(s):")
        for e in existing:
            print(f"    - {e.api_resource.name}")
        ans = input("Delete them all and proceed with fresh deploy? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted (existing engines retained).")
            sys.exit(0)
        for e in existing:
            res_name = e.api_resource.name
            print(f"🗑️  Deleting {res_name}...")
            e.delete(force=True)
        print()

    app = agent_engines.AdkApp(agent=root_agent)

    bucket_path = bucket.removeprefix("gs://")
    console_base = "https://console.cloud.google.com"
    print(
        "\n📡 Monitor progress while you wait:\n"
        f"  Staging bkt : {console_base}/storage/browser/{bucket_path}?project={project}\n"
        f"  Reasoning logs (live startup): {console_base}/logs/query;query=resource.type%3D%22aiplatform.googleapis.com%2FReasoningEngine%22?project={project}\n"
        "  Or in another terminal:\n"
        f"    gcloud logging read 'resource.type=\"aiplatform.googleapis.com/ReasoningEngine\"' --project={project} --limit=20 --freshness=10m\n"
        "  (Note: Agent Engine builds run in a Vertex-internal pipeline, NOT your Cloud Build history.)\n"
    )

    print("🚀 Deploying to Agent Engine Runtime (3-5 min)...")

    # Heartbeat ticker so user sees deploy isn't frozen
    import threading
    import time
    stop_event = threading.Event()

    def _ticker() -> None:
        start = time.time()
        # Print at 30s, 60s, 90s, ... up to ~10 min
        while not stop_event.wait(30):
            elapsed = int(time.time() - start)
            m, s = divmod(elapsed, 60)
            print(f"  ⏱  Still deploying... ({m}m {s:02d}s elapsed)", flush=True)

    ticker = threading.Thread(target=_ticker, daemon=True)
    ticker.start()

    try:
        remote = client.agent_engines.create(
            agent=app,
            config={
                "requirements": [
                    "google-cloud-aiplatform[agent_engines,adk]>=1.112",
                    "google-adk>=1.0.0",
                    "google-genai>=1.0.0",
                    "pydantic",      # ADK uses pydantic models internally
                    "cloudpickle",   # agent_engines serializes the agent via cloudpickle
                ],
                "extra_packages": ["agents"],   # include agents/ source tree so 'agents.stock.*' imports work in deployed env
                "staging_bucket": bucket,
                "display_name": "digest-agent-stock-analyzer",
                "identity_type": "AGENT_IDENTITY",  # use managed identity so engine can call internal aiplatform APIs (SessionService etc.)
                "env_vars": {
                    # GEAP auto-injects GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION
                    # (they're reserved). Setting them here triggers FAILED_PRECONDITION.
                    #
                    # Route Gemini calls through Vertex AI (uses managed service account)
                    # instead of AI Studio API key. Without this, GOOGLE_API_KEY in env
                    # can pollute the genai client into API-key auth mode, which then
                    # breaks SessionService.CreateSession with RESOURCE_PROJECT_INVALID.
                    "GOOGLE_GENAI_USE_VERTEXAI": "true",
                    # API key is no longer needed when GOOGLE_GENAI_USE_VERTEXAI=true
                    # — engine uses its managed SA for both Gemini and SessionService.
                },
            },
        )
    finally:
        stop_event.set()
        ticker.join(timeout=1)

    resource_name = remote.api_resource.name
    # parse resource_name: projects/PROJECT_NUM/locations/LOCATION/reasoningEngines/ENGINE_ID
    engine_id = resource_name.rsplit("/", 1)[-1]

    print(f"\n✅ Deployed: {resource_name}\n")

    # Append to local registry (gitignored) for follow-up invoke/delete scripts
    from agents.stock import _registry
    _registry.append(resource_name)
    print(f"📝 Logged to {_registry.REGISTRY_FILE} (latest line = newest deploy)")

    # Clickable Console URLs (modern terminals auto-detect)
    # Note: Vertex AI Console doesn't expose a deep-link to individual agent
    # engines; use the list page and find your engine_id there.
    console_base = "https://console.cloud.google.com"
    logs_query = f"resource.type%3D%22aiplatform.googleapis.com%2FReasoningEngine%22%20resource.labels.reasoning_engine_id%3D%22{engine_id}%22"
    print(
        "\n🔗 Console links:\n"
        f"  Agent Runtime list : {console_base}/agent-platform/runtimes?project={project}\n"
        f"    → engine_id to find: {engine_id}\n"
        f"  Logs (this engine) : {console_base}/logs/query;query={logs_query}?project={project}\n"
        f"  Staging bucket     : {console_base}/storage/browser/{bucket.removeprefix('gs://')}?project={project}\n"
    )

    print(
        "🐍 To invoke (Python):\n"
        "    import vertexai\n"
        f"    client = vertexai.Client(project='{project}', location='{location}')\n"
        f"    remote = client.agent_engines.get('{resource_name}')\n"
        "    async for event in remote.async_stream_query(\n"
        "        user_id='demo', message='分析台積電'):\n"
        "        print(event)\n"
    )

    print(
        "🗑️  To delete:\n"
        f"    remote.delete(force=True)\n"
    )


if __name__ == "__main__":
    main()
