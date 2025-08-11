# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY pyproject.toml README.md ./
COPY api ./api
COPY configs ./configs
COPY src ./src

# Runtime image
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Copy from build stage
COPY --from=base /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=base /usr/local/bin /usr/local/bin
COPY --from=base /app /app

EXPOSE 8080
ENV BOLCD_API_KEYS="" \
    BOLCD_SPLUNK_URL="" \
    BOLCD_SPLUNK_TOKEN="" \
    BOLCD_SENTINEL_WORKSPACE_ID="" \
    BOLCD_AZURE_TOKEN="" \
    BOLCD_AZURE_SUBSCRIPTION_ID="" \
    BOLCD_AZURE_RESOURCE_GROUP="" \
    BOLCD_AZURE_WORKSPACE_NAME="" \
    BOLCD_OPENSEARCH_ENDPOINT="" \
    BOLCD_OPENSEARCH_BASIC=""
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python - <<'PY' || exit 1
import json,sys,urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3) as r:
        sys.exit(0 if r.status==200 else 1)
except Exception:
    sys.exit(1)
PY
CMD ["uvicorn", "bolcd.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
