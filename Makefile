.PHONY: install dev test lint build run deploy shell clean

ENV_FILE ?= ~/workspace/.env

install:
	uv sync --all-extras

dev:
	set -a && source $(ENV_FILE) && set +a && \
	uv run streamlit run src/app.py --server.port=8080

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
