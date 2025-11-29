# Multi-stage build for PhotoMedit

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Stage 2: Python backend with dependencies
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    exiftool \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY wsgi.py ./
COPY config.yaml ./

# Copy tests
COPY tests/ ./tests/
COPY pytest.ini ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Create directories for data
RUN mkdir -p /data/photos /data/archive /data/thumbnails

# Expose port
EXPOSE 4750

# Set environment variables
ENV PHOTOMEDIT_CONFIG=/app/config.yaml
ENV PYTHONUNBUFFERED=1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:4750", "--workers", "4", "--timeout", "120", "wsgi:application"]

