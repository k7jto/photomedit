#!/bin/bash
# Build script for Synology deployment
# Creates a tar archive with Docker image and configuration files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/synology-build"
TAR_NAME="photomedit-synology-$(date +%Y%m%d-%H%M%S).tar.gz"

echo "📦 Building PhotoMedit for Synology deployment..."
echo ""

# Clean up any previous build
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t photomedit:latest .

# Save Docker image to tar
echo "💾 Saving Docker image..."
docker save photomedit:latest | gzip > "${BUILD_DIR}/photomedit-image.tar.gz"

# Copy configuration files
echo "📋 Copying configuration files..."
cp docker-compose.yml "${BUILD_DIR}/"
cp config.yaml "${BUILD_DIR}/config.yaml.example"
cp README.md "${BUILD_DIR}/" 2>/dev/null || true

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

# Create deployment instructions
echo "📖 Creating deployment instructions..."
cat > "${BUILD_DIR}/DEPLOY.md" << 'EOF'
# PhotoMedit Synology Deployment Guide

## Prerequisites

- Synology NAS with Docker package installed
- SSH access to your Synology (or use File Station + Terminal)
- At least 2GB free disk space

## Deployment Steps

### 1. Extract the Archive

```bash
# On your Synology, extract the tar file
tar -xzf photomedit-synology-*.tar.gz
cd photomedit-synology-*
```

### 2. Load the Docker Image

```bash
# Load the Docker image
docker load < photomedit-image.tar.gz
```

### 3. Configure the Application

```bash
# Copy and edit the config file
cp config.yaml.example config.yaml
nano config.yaml  # or use your preferred editor
```

**Important settings to configure:**
- `server.jwtSecret`: Change to a strong random secret
- `auth.adminUser.passwordHash`: Generate a new hash for admin password
- `libraries[0].rootPath`: Set to your photo directory path (e.g., `/volume1/photos`)
- `auth.adminUser.email`: Set your admin email

**To generate a password hash:**
```bash
docker run --rm photomedit:latest python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode('utf-8'))"
```

### 4. Update docker-compose.synology.yml

Edit `docker-compose.synology.yml` and update:
- Volume paths to match your Synology directory structure
- Database passwords (change from defaults)
- Port mapping if 4750 conflicts with other services

**Default volume paths:**
- Photos: `/volume1/photos` (adjust to your actual photo location)
- Thumbnails: `./data/thumbnails` (relative to compose file)
- Uploads: `./data/uploads` (relative to compose file)
- Database: `./data/database` (relative to compose file)

### 5. Create Data Directories

```bash
mkdir -p data/thumbnails data/uploads data/database
```

### 6. Start the Services

```bash
# Start using the Synology docker-compose file
docker-compose -f docker-compose.synology.yml up -d
```

### 7. Verify Deployment

```bash
# Check container status
docker ps

# Check logs
docker-compose -f docker-compose.synology.yml logs -f
```

Access the application at: `http://your-synology-ip:4750`

## Updating

To update to a new version:

1. Extract the new archive
2. Load the new image: `docker load < photomedit-image.tar.gz`
3. Stop services: `docker-compose -f docker-compose.synology.yml down`
4. Start services: `docker-compose -f docker-compose.synology.yml up -d`

## Troubleshooting

**Port already in use:**
- Change the port mapping in `docker-compose.synology.yml` (e.g., `"4751:4750"`)

**Permission issues:**
- Ensure the photo directory is accessible
- Check that the container user can read/write to mounted volumes

**Database connection issues:**
- Verify database container is healthy: `docker ps`
- Check database logs: `docker logs photomedit-db`

**Can't access the web interface:**
- Check firewall settings on Synology
- Verify port 4750 is open
- Check container logs: `docker logs photomedit`
EOF

# Create a quick start script
echo "🚀 Creating quick start script..."
cat > "${BUILD_DIR}/deploy.sh" << 'EOF'
#!/bin/bash
# Quick deployment script for Synology

set -e

echo "📦 Loading Docker image..."
docker load < photomedit-image.tar.gz

echo "📁 Creating data directories..."
mkdir -p data/thumbnails data/uploads data/database

echo "⚙️  Please edit config.yaml and docker-compose.synology.yml before starting"
echo ""
echo "Then run:"
echo "  docker-compose -f docker-compose.synology.yml up -d"
EOF
chmod +x "${BUILD_DIR}/deploy.sh"

# Create the tar archive
echo "📦 Creating deployment archive..."
cd "${SCRIPT_DIR}"
tar -czf "${TAR_NAME}" -C "${BUILD_DIR}" .

# Clean up build directory
rm -rf "${BUILD_DIR}"

echo ""
echo "✅ Build complete!"
echo ""
echo "📦 Deployment package: ${TAR_NAME}"
echo ""
echo "To deploy on Synology:"
echo "  1. Copy ${TAR_NAME} to your Synology"
echo "  2. Extract: tar -xzf ${TAR_NAME}"
echo "  3. Follow instructions in DEPLOY.md"
echo ""
echo "Package size: $(du -h "${TAR_NAME}" | cut -f1)"

