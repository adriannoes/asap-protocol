# ASAP Protocol - Production Dockerfile
# Multi-stage build for minimal image size and security
#
# Build: docker build -t asap-protocol .
# Run:   docker run -p 8000:8000 asap-protocol
#
# Environment variables:
#   ASAP_HOST        - Host to bind (default: 0.0.0.0)
#   ASAP_PORT        - Port to bind (default: 8000)
#   ASAP_WORKERS     - Number of workers (default: 1)
#   ASAP_DEBUG       - Enable debug mode (default: false)
#   ASAP_RATE_LIMIT  - Rate limit string (default: 10/second;100/minute)

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM python:3.13-slim AS builder

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install uv for faster dependency resolution
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /build

# Copy only dependency files first (for layer caching)
COPY pyproject.toml ./
COPY README.md ./

# Copy source code
COPY src/ ./src/

# Build and install the package
RUN uv pip install --no-cache .

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.13-slim AS runtime

# Labels for container metadata
LABEL org.opencontainers.image.title="ASAP Protocol"
LABEL org.opencontainers.image.description="Async Simple Agent Protocol - Agent-to-agent communication"
LABEL org.opencontainers.image.url="https://github.com/adriannoes/asap-protocol"
LABEL org.opencontainers.image.source="https://github.com/adriannoes/asap-protocol"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1000 asap \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home asap

# Set working directory
WORKDIR /app

# Create directories for logs and data
RUN mkdir -p /app/data /app/logs && chown -R asap:asap /app

# Switch to non-root user
USER asap

# Default environment variables
ENV ASAP_HOST="0.0.0.0"
ENV ASAP_PORT="8000"
ENV ASAP_WORKERS="1"
ENV ASAP_DEBUG="false"
ENV ASAP_RATE_LIMIT="10/second;100/minute"
ENV ASAP_MAX_REQUEST_SIZE="10485760"

# Expose the default port
EXPOSE 8000

# Health check using built-in endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${ASAP_PORT}/health')" || exit 1

# Default command: run the ASAP server
# Uses uvicorn with configurable workers and host/port
CMD ["sh", "-c", "uvicorn asap.transport.server:app --host ${ASAP_HOST} --port ${ASAP_PORT} --workers ${ASAP_WORKERS}"]
