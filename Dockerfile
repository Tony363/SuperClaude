# SuperClaude Framework Docker Image
# Multi-stage build for optimized production image

# =============================================================================
# Stage 1: Builder - Install dependencies and build wheel
# =============================================================================
ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

# Build arguments for metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better layer caching
COPY pyproject.toml requirements.txt ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies in virtual environment
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy source code
COPY . .

# Build the wheel
RUN pip install build && \
    python -m build --wheel && \
    pip install dist/*.whl

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

# OCI Image Labels (https://github.com/opencontainers/image-spec/blob/main/annotations.md)
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.opencontainers.image.title="SuperClaude" \
      org.opencontainers.image.description="Config-first meta-framework for Claude Code" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/SuperClaude-Org/SuperClaude_Framework" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="SuperClaude-Org"

# Security: Run as non-root user
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    APP_USER=superclaude \
    APP_HOME=/app

# Create non-root user
RUN groupadd --gid 1000 ${APP_USER} && \
    useradd --uid 1000 --gid ${APP_USER} --shell /bin/bash --create-home ${APP_USER}

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR ${APP_HOME}

# Copy application code (minimal set for runtime)
COPY --chown=${APP_USER}:${APP_USER} SuperClaude/ ./SuperClaude/
COPY --chown=${APP_USER}:${APP_USER} core/ ./core/
COPY --chown=${APP_USER}:${APP_USER} agents/ ./agents/
COPY --chown=${APP_USER}:${APP_USER} commands/ ./commands/
COPY --chown=${APP_USER}:${APP_USER} config/ ./config/

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R ${APP_USER}:${APP_USER} /app

# Switch to non-root user
USER ${APP_USER}

# Expose application port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command - can be overridden
CMD ["python", "-m", "SuperClaude"]
