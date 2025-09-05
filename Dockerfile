# Multi-stage build for BOL-CD
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r bolcd && useradd -r -g bolcd -u 1000 bolcd

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/bolcd/.local

# Copy application code
COPY --chown=bolcd:bolcd . .

# Set Python path
ENV PATH=/home/bolcd/.local/bin:$PATH
ENV PYTHONPATH=/app:src

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/.cache && \
    chown -R bolcd:bolcd /app

# Switch to non-root user
USER bolcd

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m", "uvicorn", "src.bolcd.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]