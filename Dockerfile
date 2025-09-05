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
COPY scripts ./scripts
COPY src ./src

# Ensure required runtime scripts exist (build-time assertion)
RUN test -f /app/scripts/fetch_data.py && test -f /app/scripts/ab_report.py

# Runtime image
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Copy from build stage
COPY --from=base /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=base /usr/local/bin /usr/local/bin
COPY --from=base /app /app

RUN groupadd -g 10001 app || true \
 && useradd -r -u 10001 -g app app || true \
 && mkdir -p /app/logs \
 && chown -R 10001:10001 /app/logs

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
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import sys,urllib.request;\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\n\
\
\
\
\n\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\n\
\
\
\
\
\
              \n\
try:\n    r=urllib.request.urlopen('http://127.0.0.1:8080/livez', timeout=3); sys.exit(0 if r.status==200 else 1)\nexcept Exception:\n    sys.exit(1)"
USER 10001:10001
CMD ["uvicorn", "bolcd.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
