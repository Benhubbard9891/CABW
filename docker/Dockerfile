# CABW Enterprise - Production Dockerfile
FROM python:3.12-slim as builder

# Build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build

# Build wheel
RUN python -m build --wheel

# Production stage
FROM python:3.12-slim as production

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r cabw && useradd -r -g cabw cabw

# Set working directory
WORKDIR /app

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install package
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Copy application code
COPY --chown=cabw:cabw src/ ./src/

# Switch to non-root user
USER cabw

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "cabw.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM production as development

USER root

# Install development dependencies
COPY --from=builder /build/dist/*.whl /tmp/
RUN set -euo pipefail; \
    wheel_path=$(ls /tmp/*.whl | head -n 1); \
    pip install --no-cache-dir "$wheel_path" && \
    pip install --no-cache-dir "${wheel_path}[dev]" && \
    rm /tmp/*.whl

USER cabw

# Enable reload for development
CMD ["uvicorn", "cabw.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
