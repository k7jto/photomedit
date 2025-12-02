# Multi-stage build for PhotoMedit

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --production=false

COPY frontend/ .
RUN npm run build

# Clean up node_modules to reduce size
RUN rm -rf node_modules

# Stage 2: Python backend with dependencies
FROM python:3.11-slim

# Install system dependencies and clean up in same layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    exiftool \
    ffmpeg \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt \
    && find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -type f -name "*.pyc" -delete 2>/dev/null || true

# Copy backend code
COPY backend/ ./backend/
COPY wsgi.py ./
COPY config.yaml ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Create directories for data (these will be volumes, but create for safety)
RUN mkdir -p /data/photos /data/archive /data/thumbnails /data/uploads /data/database

# Create a non-root user for running the application
# Default to UID 1000 (common for first user on Linux systems)
# Set RUN_AS_ROOT=1 to skip user creation and run as root
ARG PUID=1000
ARG PGID=1000
ARG RUN_AS_ROOT=0

RUN if [ "${RUN_AS_ROOT}" != "1" ]; then \
        groupadd -g ${PGID} photomedit 2>/dev/null || true && \
        useradd -u ${PUID} -g ${PGID} -s /bin/bash -m photomedit 2>/dev/null || true && \
        chown -R photomedit:photomedit /app /data 2>/dev/null || true && \
        echo "Created photomedit user (UID ${PUID}, GID ${PGID})"; \
    else \
        echo "Running as root (RUN_AS_ROOT=1)"; \
    fi

# Switch to non-root user only if not running as root
# Dockerfile USER doesn't support variables, so we'll handle this in entrypoint
# For now, default to root to avoid breaking existing deployments
# USER photomedit

# Expose port
EXPOSE 4750

# Set environment variables
ENV PHOTOMEDIT_CONFIG=/app/config.yaml
ENV PYTHONUNBUFFERED=1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:4750", "--workers", "4", "--timeout", "120", "wsgi:application"]

