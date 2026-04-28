# GURUJEE Multi-stage Docker Image
# Build: docker build -t gurujee:latest .
# Run: docker run -p 7171:7171 -it gurujee:latest

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir \
            fastapi==0.104.1 \
            uvicorn==0.24.0 \
            httpx==0.25.0 \
            pydantic==2.4.0 \
            pyyaml==6.0.1 \
            cryptography==41.0.4 \
            psutil==5.9.5 \
            pytest==7.4.3; \
    fi

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY gurujee ./gurujee
COPY config ./config
COPY tests ./tests
COPY PHASE4-ANDROID-SETUP.md README.md* ./

# Create data directories
RUN mkdir -p /app/data/{audit,metrics,logs}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7171/api/health || exit 1

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:$PYTHONPATH \
    GURUJEE_DATA_DIR=/app/data

# Expose API port
EXPOSE 7171

# Start daemon
CMD ["python", "-m", "gurujee.daemon"]

# Metadata
LABEL maintainer="GURUJEE Development" \
      version="1.0.0" \
      description="GURUJEE AI Agent Platform - Docker Distribution" \
      org.opencontainers.image.source="https://github.com/staimoorulhassan/GURUJEE"
