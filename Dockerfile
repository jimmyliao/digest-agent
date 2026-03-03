FROM python:3.11-slim
WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

COPY src/ ./src/
COPY config/ ./config/

RUN mkdir -p /app/data

ENV PYTHONPATH=/app
EXPOSE 8080

ENV PORT=8080
CMD ["sh", "-c", "uv run streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true"]
