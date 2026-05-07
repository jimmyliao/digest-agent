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


def main() -> None:
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
    app = agent_engines.AdkApp(agent=root_agent)

    print("🚀 Deploying to Agent Engine Runtime (3-5 min)...")
    remote = client.agent_engines.create(
        agent=app,
        config={
            "requirements": [
                "google-cloud-aiplatform[agent_engines,adk]>=1.112",
                "google-adk>=1.0.0",
                "google-genai>=1.0.0",
            ],
            "staging_bucket": bucket,
            "display_name": "digest-agent-stock-analyzer",
            "env_vars": {
                "GOOGLE_API_KEY": api_key,  # ADK uses GOOGLE_API_KEY
            },
        },
    )
    resource_name = remote.api_resource.name
    # parse resource_name: projects/PROJECT_NUM/locations/LOCATION/reasoningEngines/ENGINE_ID
    engine_id = resource_name.rsplit("/", 1)[-1]

    print(f"\n✅ Deployed: {resource_name}\n")

    # Append to local registry (gitignored) for follow-up invoke/delete scripts
    from datetime import datetime, timezone
    registry = "deployed-agent-engines.txt"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(registry, "a", encoding="utf-8") as f:
        f.write(f"{ts}\t{resource_name}\n")
    print(f"📝 Logged to {registry} (latest line = newest deploy)")

    # Clickable Console URLs (modern terminals auto-detect)
    console_base = "https://console.cloud.google.com"
    print(
        "\n🔗 Console links:\n"
        f"  Agent detail : {console_base}/vertex-ai/agents/locations/{location}/agent-engines/{engine_id}?project={project}\n"
        f"  Cloud Build  : {console_base}/cloud-build/builds?project={project}\n"
        f"  Logs         : {console_base}/logs/query;query=resource.type%3D%22aiplatform.googleapis.com%2FReasoningEngine%22?project={project}\n"
        f"  Staging bkt  : {console_base}/storage/browser/{bucket.removeprefix('gs://')}?project={project}\n"
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
