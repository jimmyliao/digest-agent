.PHONY: install dev test lint build run deploy deploy-workshop shell clean adk-web adk-run setup-data-bucket deploy-web test-local test-local-e2e test-local-api-real onboard-cloudshell

ENV_FILE ?= .env
WORKSPACE_ENV ?= $(HOME)/workspace/.env

# Load GEMINI_API_KEY from ~/workspace/.env if not already set
GEMINI_API_KEY ?= $(shell grep -m1 '^GEMINI_API_KEY=' $(WORKSPACE_ENV) 2>/dev/null | cut -d= -f2-)

install:
	uv sync --all-extras

dev:
	set -a && . $(ENV_FILE) && set +a && \
	uv run streamlit run src/app.py --server.port=8080

# Cloud Shell / CI: reads .env if present, falls back to shell env vars
# Flags required for Cloud Shell Web Preview proxy (WebSocket + XSRF)
dev-shell:
	mkdir -p data
	if [ -f .env ]; then set -a && . .env && set +a; fi && \
	uv run streamlit run src/app.py --server.port=8080 --server.address=0.0.0.0 \
		--server.enableCORS=false --server.enableXsrfProtection=false

run: dev

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/

build:
	docker build -t digest-agent .

deploy:
	gcloud run deploy digest-agent \
	  --source . \
	  --region asia-east1 \
	  --platform managed \
	  --allow-unauthenticated \
	  --port 8080 \
	  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest" \
	  --set-secrets "DATABASE_URL=supabase-db-url:latest"

# Dry-run: build Docker image locally + echo the gcloud command (no actual deploy)
# Usage: GEMINI_API_KEY=xxx make deploy-dry-run
deploy-dry-run:
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
	  echo "❌ GEMINI_API_KEY is not set. Usage: GEMINI_API_KEY=xxx make deploy-dry-run"; \
	  exit 1; \
	fi
	@echo "🔨 Building Docker image locally to validate Dockerfile..."
	docker build -t digest-agent-workshop-test .
	@echo ""
	@echo "✅ Image build OK. Would run:"
	@echo ""
	@echo "  gcloud run deploy digest-agent-workshop \\"
	@echo "    --source . \\"
	@echo "    --region asia-east1 \\"
	@echo "    --platform managed \\"
	@echo "    --allow-unauthenticated \\"
	@echo "    --port 8080 \\"
	@echo "    --set-env-vars GEMINI_API_KEY=*** \\"
	@echo "    --set-env-vars DATABASE_URL=sqlite:////tmp/digest.db"
	@echo ""
	@echo "👉 Run 'GEMINI_API_KEY=xxx make deploy-workshop' to actually deploy."

# Workshop / quick demo: no Secret Manager needed, SQLite in container
# Usage: GEMINI_API_KEY=xxx make deploy-workshop
deploy-workshop:
	@if [ -z "$(GEMINI_API_KEY)" ]; then \
	  echo "❌ GEMINI_API_KEY is not set. Usage: GEMINI_API_KEY=xxx make deploy-workshop"; \
	  exit 1; \
	fi
	gcloud run deploy digest-agent-workshop \
	  --source . \
	  --region asia-east1 \
	  --platform managed \
	  --allow-unauthenticated \
	  --port 8080 \
	  --set-env-vars "GEMINI_API_KEY=$(GEMINI_API_KEY)" \
	  --set-env-vars "DATABASE_URL=sqlite:////tmp/digest.db"

# GEAP / Vertex AI Agent Engine: deploy agents/stock SequentialAgent as managed agent
# Usage: GCP_PROJECT=xxx STAGING_BUCKET=gs://xxx GEMINI_API_KEY=xxx make deploy-agent-engine
# See GEAP_DEPLOY.md for prerequisites (gcloud auth, IAM, APIs, bucket).
deploy-agent-engine:
	@if [ -z "$(GCP_PROJECT)" ] || [ -z "$(STAGING_BUCKET)" ] || [ -z "$(GEMINI_API_KEY)" ]; then \
	  echo "❌ Missing env vars. Usage:"; \
	  echo "   GCP_PROJECT=xxx STAGING_BUCKET=gs://xxx GEMINI_API_KEY=xxx make deploy-agent-engine"; \
	  exit 1; \
	fi
	uv sync --extra geap
	uv run python -m agents.stock.deploy_to_agent_engine

# Invoke the latest deployed Agent Engine (reads deployed-agent-engines.txt last line)
# Direct: ./scripts/invoke-agent-engine.sh "<message>"
invoke-agent-engine:
	./scripts/invoke-agent-engine.sh

# List Agent Engines deployed to GCP project (filter by display_name prefix)
list-agent-engines:
	./scripts/list-agent-engines.sh --filter digest-agent

# Set up monthly billing budget alert (default $5 USD)
# Usage: make setup-billing-alert            # $5
#        AMOUNT=10 make setup-billing-alert  # $10
setup-billing-alert:
	./scripts/setup-billing-alert.sh $(AMOUNT)

# ADK: launch web UI to test stock analysis agents interactively
adk-web:
	uv run adk web agents

# ADK: run stock agent in CLI mode
adk-run:
	uv run adk run agents/stock

shell:
	set -a && . $(ENV_FILE) && set +a && \
	uv run python -c "from src.models.database import init_db; init_db(); print('DB initialized')"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type f -name "*.pyc" -delete; \
	rm -rf .pytest_cache dist .ruff_cache

debug:
	set -a && . $(ENV_FILE) && set +a && \
	uv run python -c "\
from src.models.database import init_db; \
from src.orchestrator import DigestOrchestrator; \
import asyncio; \
init_db(); \
orch = DigestOrchestrator(); \
result = asyncio.run(orch.run_fetch_pipeline()); \
print(result)"

# Set up GCS bucket (gs://${GCP_PROJECT}-data) for Litestream-backed
# Next.js apps/web/ SQLite persistence. Idempotent.
# Usage: make setup-data-bucket
setup-data-bucket:
	@bash scripts/setup-data-bucket.sh

# Deploy apps/web/ (Next.js + Litestream) to Cloud Run with GCS-backed
# /data/digest.db. Reads LITESTREAM_GCS_BUCKET from .env.deploy.
# Usage: make deploy-web
deploy-web:
	@bash scripts/deploy-web-to-cloud-run.sh

# Run unit tests + bash lint locally (vitest + pytest + bash -n).
# Usage: make test-local
test-local:
	@echo "🧪 Running unit tests + bash lint..."
	cd apps/web && npm test
	uv run pytest tests/ -v --no-header 2>&1 | tail -20
	bash -n scripts/setup-data-bucket.sh scripts/deploy-web-to-cloud-run.sh infra/entrypoint.sh
	@echo "✅ All local tests passed"

# End-to-end local smoke (boots Next.js dev, hits API, exercises agent
# HTTP/SQLite/fallback modes; auto-cleans the dev server on exit).
# No GCS, no Cloud Run, no LLM key needed.
# Usage: make test-local-e2e
test-local-e2e:
	@bash scripts/test-local-e2e.sh

# Real-API smoke against an already-running dev server. Hits every
# /api/* endpoint with REAL data (real RSS, real LLM call). Requires
# GEMINI_API_KEY. Skips publish by default — pass --with-publish to
# include real channel sends.
# Usage:
#   make test-local-api-real
#   make test-local-api-real ARGS=--with-publish
test-local-api-real:
	@bash scripts/test-local-api-real.sh $(ARGS)

# One-shot onboarding for Cloud Shell / fresh dev machines.
# Installs bun + uv, runs bun install + uv sync, scaffolds .env files.
# Idempotent — re-runnable, skips anything already installed.
# Usage: make onboard-cloudshell
onboard-cloudshell:
	@bash scripts/onboard-cloudshell.sh
