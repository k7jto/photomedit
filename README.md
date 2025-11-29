# PhotoMedit

Self-hosted photo and video metadata editor for family archives.

## Features

- **Metadata Editing**: Edit EXIF, IPTC, and XMP metadata for photos and videos
- **Modern UI**: Clean, dark-themed React frontend
- **Authentication**: JWT-based authentication with configurable users
- **Reject Workflow**: Move unwanted images to `.rejected` folder
- **Review Status**: Track reviewed/unreviewed images with auto-mark option
- **Geocoding**: Automatic location geocoding using Nominatim
- **Thumbnails**: Automatic thumbnail and preview generation
- **RAW Support**: Support for RAW image formats (ORF, NEF, CR2, etc.)
- **Sidecar Files**: Sidecar-first approach for video metadata

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/photomedit.git
   cd photomedit
   ```

2. **Configure**:
   - Copy `config.yaml` and update with your settings
   - Generate password hashes: `docker-compose exec -T photomedit python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode('utf-8'))"`
   - Update library paths in `config.yaml`

3. **Build and run**:
   ```bash
   docker-compose up -d
   ```

4. **Access**:
   - Open http://localhost:4750 in your browser
   - Login with credentials from `config.yaml`

## Configuration

Edit `config.yaml` to configure:
- Server port and JWT secret
- User accounts and passwords
- Library paths (mount your photo directories)
- Geocoding settings
- Logging level

## Docker Volumes

Mount your photo directories in `docker-compose.yml`:
```yaml
volumes:
  - ~/Pictures:/data/pictures:rw
```

## Development

- Backend: Python 3.11, Flask, Gunicorn
- Frontend: React, Vite
- Metadata: exiftool, Pillow, rawpy
- Video: ffmpeg

## License

[Add your license here]

