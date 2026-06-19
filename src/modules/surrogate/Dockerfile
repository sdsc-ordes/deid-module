FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY . /app
RUN uv sync --frozen --no-cache

CMD [".venv/bin/fastapi", "run", "src/main.py", "--port", "80", "--host", "0.0.0.0"]
