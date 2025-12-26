#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# PhotoMedit - Synology Build Script
# ═══════════════════════════════════════════════════════════════════════════════
# Creates a build-synology folder with:
#   - photomedit-image.tar.gz  (Docker image for Container Manager)
#   - config.yaml              (Application configuration)
#   - docker-compose.synology.yml (Docker Compose for Synology)

set -e

# Parse command line arguments
NO_CACHE=""
if [[ "$1" == "--no-cache" ]] || [[ "$1" == "-n" ]]; then
    NO_CACHE="--no-cache"
    echo "🔨 Building with --no-cache flag"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build-synology"

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  PhotoMedit - Building for Synology                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Create build directory
mkdir -p "${BUILD_DIR}"

# Build Docker image
echo "🔨 Building Docker image (PUID=1024, PGID=100 for Synology)..."
docker build ${NO_CACHE} --build-arg PUID=1024 --build-arg PGID=100 -t photomedit:latest .

# Save Docker image
echo ""
echo "💾 Saving Docker image to tar.gz..."
docker save photomedit:latest | gzip > "${BUILD_DIR}/photomedit-image.tar.gz"
IMAGE_SIZE=$(du -h "${BUILD_DIR}/photomedit-image.tar.gz" | cut -f1)
echo "   Image size: ${IMAGE_SIZE}"

echo ""
echo "✅ Build complete!"
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║  Build Output: ${BUILD_DIR}"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Files created:                                                           ║"
echo "║    • photomedit-image.tar.gz  - Docker image (${IMAGE_SIZE})              "
echo "║    • config.yaml              - Application configuration                 ║"
echo "║    • docker-compose.synology.yml - Docker Compose file                    ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────────┐"
echo "│  DEPLOYMENT STEPS                                                           │"
echo "├─────────────────────────────────────────────────────────────────────────────┤"
echo "│  1. Copy build-synology/ folder to your Synology                            │"
echo "│     Example: /volume1/docker/photomedit/                                    │"
echo "│                                                                             │"
echo "│  2. Import the Docker image:                                                │"
echo "│     Container Manager → Image → Add → Import from file                     │"
echo "│     Select: photomedit-image.tar.gz                                         │"
echo "│                                                                             │"
echo "│  3. Edit config.yaml:                                                       │"
echo "│     • Set jwtSecret to a random string                                      │"
echo "│     • Set admin email                                                       │"
echo "│     • Set DAM URL (e.g., http://nas-ip:2283 for Immich)                    │"
echo "│                                                                             │"
echo "│  4. Edit docker-compose.synology.yml:                                       │"
echo "│     • Set volume paths (left side only):                                    │"
echo "│       /volume1/Memories → your photo library                                │"
echo "│       /volume1/PhotoMedit/thumbnails → thumbnail cache                      │"
echo "│       /volume1/PhotoMedit/uploads → upload staging                          │"
echo "│       /volume1/Immich → DAM import folder                                   │"
echo "│     • Set database passwords (must match in two places)                     │"
echo "│     • Set PUID/PGID to match your Synology user                            │"
echo "│                                                                             │"
echo "│  5. Create required folders on Synology:                                    │"
echo "│     mkdir -p /volume1/PhotoMedit/{thumbnails,uploads}                       │"
echo "│     mkdir -p /volume1/docker/photomedit/data/database                       │"
echo "│                                                                             │"
echo "│  6. Start the containers:                                                   │"
echo "│     cd /volume1/docker/photomedit                                           │"
echo "│     docker-compose -f docker-compose.synology.yml up -d                     │"
echo "│                                                                             │"
echo "│  7. Access PhotoMedit:                                                      │"
echo "│     http://your-nas-ip:4750                                                 │"
echo "│     Login: admin / admin (change password immediately!)                     │"
echo "└─────────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────────┐"
echo "│  FIND YOUR SYNOLOGY USER IDs                                                │"
echo "├─────────────────────────────────────────────────────────────────────────────┤"
echo "│  SSH into Synology and run:                                                 │"
echo "│    id -u yourusername    # Returns PUID (typically 1024)                    │"
echo "│    id -g yourusername    # Returns PGID (typically 100)                     │"
echo "└─────────────────────────────────────────────────────────────────────────────┘"
echo ""
