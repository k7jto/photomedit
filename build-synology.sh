#!/bin/bash
# Build script for Synology deployment
# Creates a build-synology folder with config files and Docker image tar

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build-synology"

echo "📦 Building PhotoMedit for Synology deployment..."
echo ""

# Create build directory
mkdir -p "${BUILD_DIR}"

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t photomedit:latest .

# Save Docker image to tar (for Synology Container Manager import)
echo "💾 Saving Docker image to tar..."
docker save photomedit:latest | gzip > "${BUILD_DIR}/photomedit-image.tar.gz"

# Copy configuration files to build directory
echo "📋 Copying configuration files..."
cp config.yaml "${BUILD_DIR}/"
cp docker-compose.yml "${BUILD_DIR}/docker-compose.yml"

# Create Synology-specific docker-compose file
echo "📝 Creating Synology docker-compose.yml..."
cat > "${BUILD_DIR}/docker-compose.synology.yml" << 'EOF'
version: '3.8'

services:
  photomedit-db:
    image: mariadb:10.11
    container_name: photomedit-db
    environment:
      - MYSQL_ROOT_PASSWORD=photomedit_root_password_change_me
      - MYSQL_DATABASE=photomedit
      - MYSQL_USER=photomedit
      - MYSQL_PASSWORD=photomedit_password_change_me
    volumes:
      - ./data/database:/var/lib/mysql
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  photomedit:
    image: photomedit:latest
    container_name: photomedit
    ports:
      - "4750:4750"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - /volume1/photos:/data/pictures:rw
      - ./data/thumbnails:/data/thumbnails:rw
      - ./data/uploads:/data/uploads:rw
    environment:
      - PHOTOMEDIT_CONFIG=/app/config.yaml
      - DB_HOST=photomedit-db
      - DB_PORT=3306
      - DB_NAME=photomedit
      - DB_USER=photomedit
      - DB_PASSWORD=photomedit_password_change_me
    depends_on:
      photomedit-db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:4750/api/libraries').read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

echo ""
echo "✅ Build complete!"
echo ""
echo "📁 Build directory: ${BUILD_DIR}"
echo ""
echo "Contents:"
echo "  - photomedit-image.tar.gz (Docker image for Synology Container Manager)"
echo "  - config.yaml (application configuration)"
echo "  - docker-compose.synology.yml (Synology docker-compose file)"
echo "  - docker-compose.yml (original docker-compose file)"
echo ""
echo "📦 To deploy on Synology:"
echo "  1. Import photomedit-image.tar.gz in Container Manager"
echo "  2. Copy config.yaml and docker-compose.synology.yml to your Synology"
echo "  3. Edit config.yaml with your settings"
echo "  4. Run: docker-compose -f docker-compose.synology.yml up -d"
echo ""
echo "Image size: $(du -h "${BUILD_DIR}/photomedit-image.tar.gz" | cut -f1)"
