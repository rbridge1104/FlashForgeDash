# FlashForgeDash Dockerfile
# Multi-stage build for minimal image size

# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 flashforge && \
    chown -R flashforge:flashforge /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/flashforge/.local

# Copy application files
COPY --chown=flashforge:flashforge backend/ ./backend/
COPY --chown=flashforge:flashforge frontend/ ./frontend/
COPY --chown=flashforge:flashforge tests/ ./tests/
COPY --chown=flashforge:flashforge config.yaml.example ./config.yaml.example

# Create required directories
RUN mkdir -p /app/data && \
    chown -R flashforge:flashforge /app/data

# Switch to non-root user
USER flashforge

# Add local bin to PATH
ENV PATH=/home/flashforge/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/auth/status || exit 1

# Set default environment variables
ENV PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
