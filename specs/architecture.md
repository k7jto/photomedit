PhotoMedit – Architecture & Implementation Guide

Companion documents:

- Requirements (requirements.md)
- API Specification (api-spec.md)
- Upload/Download Specification (upload-download.md)

All located in the `specs/` directory.

## 1. High-Level Architecture

PhotoMedit consists of:

- Python/Flask backend
- React SPA frontend
- MariaDB database for users and logs
- NAS-backed filesystem libraries
- Thumbnail/preview cache
- Upload root for new batches
- YAML configuration loader
- exiftool wrapper for metadata
- ffmpeg for video thumbnails
- pydantic for validation
- JWT-based authentication with MFA support
- Admin user management
- Password reset functionality

Database is used for:
- User management (except admin user in config)
- Application logging
- User last login tracking

Media metadata and library structure remain file-backed + in-memory scan results.

## 2. Database

### MariaDB Setup
- Database runs in separate Docker container
- Data stored in `/data/database` directory (mounted volume)
- Database: `photomedit`
- User: `photomedit` (configurable via environment variables)

### Database Tables

**users:**
- id (primary key)
- username (unique, indexed)
- password_hash (bcrypt)
- role ('user' or 'admin')
- mfa_secret (TOTP secret, nullable)
- created_at (timestamp)
- last_login (timestamp, nullable)

**logs:**
- id (primary key)
- timestamp (indexed)
- level (DEBUG, INFO, WARNING, ERROR, indexed)
- logger (string, nullable)
- message (text)
- user (string, nullable, indexed)
- ip_address (string, nullable)
- details (JSON text, nullable)

### Admin User in Config
- Admin user credentials stored in `config.yaml` for initial access
- Admin user cannot be modified via UI (must edit config.yaml)
- Other users managed via database

## 3. Backend Structure

Directory layout:

```
backend/
├── app.py
├── config/
│   └── loader.py
├── database/
│   ├── models.py
│   ├── connection.py
│   ├── user_service.py
│   └── log_service.py
├── auth/
│   ├── routes.py
│   ├── jwt.py
│   ├── mfa.py
│   └── password_reset.py
├── admin/
│   └── routes.py
├── libraries/
│   ├── routes.py
│   └── filesystem.py
├── media/
│   ├── routes.py
│   ├── metadata_reader.py
│   ├── metadata_writer.py
│   ├── preview_generator.py
│   └── navigation.py
├── upload/
│   └── routes.py
├── download/
│   └── routes.py
├── search/
│   └── routes.py
├── validation/
│   └── schemas.py
├── security/
│   ├── headers.py
│   └── sanitizer.py
└── utils/
    ├── file_io.py
    ├── sidecar.py
    ├── timestamp.py
    └── geocoding.py
```

## 3. Flask Application

- Use Blueprints for modular routing
- Apply secure headers globally
- JSON-only API
- Validate all request bodies and parameters using Pydantic schemas
- Enforce shared error-handling for consistent responses
- Resolve media IDs of form: libraryId|relative/path.ext
- Support token authentication via query parameter for image endpoints

## 4. Path Handling & Safety

All paths must be resolved as:
rootPath + relativePath

Reject:
- ".." components
- absolute paths
- symlinks that escape root
- .rejected folders (hidden from browsing)

Normalize and re-check resolved path against rootPath.

## 5. Authentication

### User Management
- Admin user stored in `config.yaml` for initial access
- Other users stored in MariaDB database
- Users have `role` field: 'user' or 'admin'
- Store passwordHash as bcrypt
- Compare provided password using bcrypt.checkpw
- Issue JWT with expiration and username
- Last login timestamp tracked in database

### Multi-Factor Authentication (MFA)
- TOTP-based using pyotp
- QR code generation for setup
- MFA secret stored in user config
- Login flow: password → MFA token (if enabled)
- Users can enable/disable MFA via UI

### Password Reset
- Token-based reset flow
- Reset tokens stored in-memory (60-minute expiry)
- Future: email integration for token delivery

### JWT Validation
- Validate JWT on every request (except login, password reset) when auth.enabled
- Support token in query parameter for image endpoints (for <img> tags)
- Store username in request.current_user for route handlers

## 6. Admin Features

### User Management
- Admin-only endpoints for CRUD operations on users
- Cannot delete own account
- Admin status can be toggled
- MFA status visible in user list

## 7. Metadata Processing

### Reader
For sidecar files:
- Read XMP first (sidecar-first approach)

For images:
- Use exiftool wrapper
- Read EXIF, IPTC, XMP

For videos:
- Use exiftool (sidecar-first)
- Avoid risky embedded writes

### Writer
Merge logical metadata fields into:
- sidecar XMP (always)
- embedded EXIF/IPTC (images only)

Metadata writing follows the final metadata strategy:

**For Date:**
- XMP-exif:DateTimeOriginal
- EXIF:DateTimeOriginal
- EXIF:CreateDate
- EXIF:ModifyDate

**For Title:**
- XMP-dc:title
- IPTC:ObjectName

**For Notes/Description:**
- XMP-dc:description
- IPTC:Caption-Abstract

**For People/Keywords:**
- XMP-dc:subject[] (array)
- IPTC:Keywords[] (array)

**For Location:**
- XMP-photoshop:City
- XMP-photoshop:Country
- IPTC:City
- IPTC:Country-PrimaryLocationName

Apply atomic write strategy:
- Write to temporary file
- Validate
- Atomically replace original

For videos:
- Prefer sidecar-only writes

## 8. Thumbnails & Previews

### Images
- For JPEGs < 5MB: serve directly without thumbnail generation
- For RAW and larger JPEGs: generate thumbnails/previews
- Prefer embedded JPEG previews for RAW where available
- Otherwise, generate using Pillow + rawpy
- Store in thumbnailCacheRoot with hashed filenames organized by date

### Videos
- Use ffmpeg:
  - Extract frame at 10% of duration
  - Cache thumbnails exactly like images

## 9. Upload & Download

### Upload
- Files stored in uploadRoot with batch directories
- Binary validation using magic bytes
- Atomic writes with temp files
- Filename conflict resolution
- Post-upload metadata import

### Download
- ZIP generation with folder structure preservation
- Automatic sidecar inclusion
- contents.txt generation with metadata
- Size and count limits enforced

See upload-download.md for full specification.

## 10. Media Workflow

### Reject Functionality
- Images can be moved to .rejected folder
- Preserves folder structure in .rejected
- Sidecars moved with media files
- .rejected folders excluded from browsing

### Review Status
- Default: "unreviewed"
- Can be set to "reviewed" manually or via "Mark reviewed when saving" checkbox
- Used for filtering in grid view and navigation

## 11. Folder Management

### Folder Creation
- Users can create new folders via UI
- Folder names validated (no path separators)
- Created within library root or specified parent folder

## 12. Searching & Filtering

v1 search is implemented via:
- folder scan
- filtering in memory
- no persistent index

Future index (SQLite) is possible without structural changes.

## 13. Error Handling

Return consistent JSON errors:
- 400 validation_error
- 401 unauthorized
- 403 forbidden (admin-only endpoints)
- 404 not_found
- 500 internal_error or metadata_write_failed

Never expose internal exceptions to client.

## 14. Configuration

YAML config includes:
- server (port, host, jwtSecret)
- auth (enabled, users with isAdmin, passwordHash, mfaSecret)
- libraries (id, name, rootPath)
- thumbnailCacheRoot
- uploadRoot
- limits (upload/download limits)
- geocoding (provider, enabled, userAgent, rateLimit)
- logging (level)

Config can be saved back to YAML (for user management).

## 15. Deployment

### Docker
Recommended Dockerfile includes:
- Python 3.11 base
- Node.js for frontend build
- exiftool installation
- ffmpeg installation
- Gunicorn for production
- Single container deployment (Flask serves React build)

### Reverse Proxy
Use Nginx/Caddy/Traefik for:
- HTTPS
- Compression
- Caching headers
- Static file serving (optional, Flask can serve)

## 16. Frontend Structure

React SPA with:
- Library selector
- Folder browser with creation
- Media grid with review status filter
- Media detail view with editing
- Upload page
- Admin page (admin users only)
- MFA setup page
- Forgot password flow

Uses:
- React Router for navigation
- Axios for API calls
- JWT stored in sessionStorage
- Token appended to image URLs for authentication

## 17. Future Enhancements

- Email integration for password reset
- Batch editing
- Bulk upload with uniform metadata presets
- SQLite metadata index
- OCR or AI enhancements (optional)
- Face detection + region tags
- Android app (v2)
