# Backend: the LangGraph agent served by `langgraph dev` on port 2025.
# (2024 is the upstream default; this project standardizes on 2025 everywhere.)
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Docling (PDF/DOCX -> markdown with tables) is heavy (PyTorch); opt in with
#   docker compose build --build-arg INSTALL_DOCLING=true
# It needs a few shared libraries that the slim image lacks.
ARG INSTALL_DOCLING=false
RUN if [ "$INSTALL_DOCLING" = "true" ]; then apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*; fi

# Dependencies first, from a stub package, so editing code does not reinstall them.
COPY pyproject.toml README.md ./
RUN mkdir -p src/research_assistant && touch src/research_assistant/__init__.py     && uv pip install --system --no-cache -e . "langgraph-cli[inmem]"     && if [ "$INSTALL_DOCLING" = "true" ]; then uv pip install --system --no-cache docling; fi

COPY src ./src
COPY langgraph.json ./
# langgraph.json points at ./.env; secrets are NOT baked in (see .dockerignore),
# configuration arrives as container environment variables instead.
RUN touch .env

# Defaults for a container talking to Ollama on the Docker host.
ENV OLLAMA_BASE_URL="http://host.docker.internal:11434"     VAULT_PATH="/vault"     DOCS_PATH="/docs"     NOTIFY_ON_COMPLETE="False"

VOLUME ["/vault", "/docs"]
EXPOSE 2025

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5     CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:2025/ok', timeout=4)"

CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2025", "--no-browser", "--no-reload"]
