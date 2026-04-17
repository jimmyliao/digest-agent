.PHONY: install dev test lint build run deploy deploy-workshop shell clean adk-web adk-run

ENV_FILE ?= .env
WORKSPACE_ENV ?= $(HOME)/workspace/.env

# Load GEMINI_API_KEY from ~/workspace/.env if not already set
GEMINI_API_KEY ?= $(shell grep -m1 '^GEMINI_API_KEY=' $(WORKSPACE_ENV) 2>/dev/null | cut -d= -f2-)

install:
	uv sync --all-extras

dev:
	set -a && source $(ENV_FILE) && set +a && \
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

# ADK: launch web UI to test stock analysis agents interactively
adk-web:
	uv run adk web agents

# ADK: run stock agent in CLI mode
adk-run:
	uv run adk run agents/stock

shell:
	set -a && source $(ENV_FILE) && set +a && \
	uv run python -c "from src.models.database import init_db; init_db(); print('DB initialized')"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type f -name "*.pyc" -delete; \
	rm -rf .pytest_cache dist .ruff_cache

debug:
	set -a && source $(ENV_FILE) && set +a && \
	uv run python -c "\
from src.models.database import init_db; \
from src.orchestrator import DigestOrchestrator; \
import asyncio; \
init_db(); \
orch = DigestOrchestrator(); \
result = asyncio.run(orch.run_fetch_pipeline()); \
print(result)"
