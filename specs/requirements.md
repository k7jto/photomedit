PhotoMedit – Requirements

Companion documents:

- API Specification (api-spec.md)
- Architecture & Implementation Guide (architecture.md)
- Upload/Download Specification (upload-download.md)

All located in the `specs/` directory.

## 1. Overview

PhotoMedit is a self-hosted photo and video metadata editor built for family archives, especially scanned historical photographs, RAW images, and digitized home movies (8mm, Super8, VHS captures). It focuses on lightweight metadata management, accurate genealogical tagging, and a simple review workflow.

The system includes:

- A REST API backend (Python + Flask)
- A responsive web UI (React)
- Multiple NAS-backed libraries (root directories)
- Support for images and videos
- Editing of essential metadata fields
- Sidecar-first metadata handling
- Secure-by-default design (OWASP aligned)
- Multiple users with role-based access (user/admin)
- MariaDB database for user management and logging
- Multi-factor authentication (MFA)
- Password reset functionality
- Upload and download capabilities
- Folder creation and management
- Reject workflow for unwanted images

It is intentionally minimal — not a replacement for PhotoPrism or Lightroom — but a highly efficient tool for cleaning, enriching, and preparing archives for long-term preservation and sharing.

## 2. Goals & Non-Goals

### Goals

- Browse one or more NAS-based libraries via the web UI
- View images (JPEG/RAW) and videos (MP4/MOV/M4V)
- Edit: event date, subject, notes, people, location, and review status
- Store metadata in sidecars and embedded fields (images only)
- Store metadata safely for videos (sidecar-first)
- Maintain genealogically accurate date handling
- Provide a workflow: unreviewed → reviewed, with optional re-check
- Implement strong validation, safe writes, and OWASP security
- Support multiple users with admin roles
- Multi-factor authentication (TOTP)
- Password reset functionality
- Upload new media files with batch organization
- Download media with metadata preservation
- Create and manage folders
- Reject unwanted images (move to .rejected folder)

### Non-Goals (v1)

- No AI tagging or facial recognition
- No batch metadata editing (single-item editing only)
- No image or video editing
- No per-user permissions or ACLs (all users have equal access, except admin features)
- No media versioning (writes overwrite in-place)
- No indexing/DB requirement (lazy folder scans)
- No email integration (password reset tokens returned directly)
- Android app planned for v2

## 3. Libraries (NAS Directories)

Libraries are defined in YAML:

- id (string)
- name (string)
- rootPath (string, absolute path)

All media browsing and access is constrained inside these root directories.

Folder trees are generated recursively.

Media browsing is lazy-loaded (no global scanning on startup).

## 4. Supported Media Types

### Images:
- JPEG
- Common RAW formats (ORF, NEF, CR2, CR3, RAF, ARW, DNG, etc.)

### Videos:
- MP4
- MOV
- M4V

Every uploaded or discovered file must be validated using binary signatures (magic bytes), not extensions or MIME types.

## 5. Metadata Fields

### Editable fields:
- eventDate (string, ISO 8601 format)
- eventDateDisplay (string, human-readable)
- eventDatePrecision (YEAR, MONTH, DAY, UNKNOWN)
- eventDateApproximate (boolean)
- subject (string)
- notes (string)
- people (array of strings)
- locationName (string)
- locationCoords (object: {lat: number, lon: number})
- reviewStatus (unreviewed or reviewed)

### Read-only fields:
- filename, relative path
- media type (image or video)
- image EXIF info
- video duration, resolution, frame rate, codec
- embedded capture/scan timestamps, if present

## 6. Metadata Semantics

### Event Date (critical for genealogy)
Represents when the original event occurred.

Not derived from scan timestamps.

For scanned/digitized media, this overrides any device/scan dates.

Written to image metadata as:
- XMP-exif:DateTimeOriginal
- EXIF:DateTimeOriginal
- EXIF:CreateDate
- EXIF:ModifyDate

Precision and approximate fields stored in custom XMP tags:
- XMP:PhotoMeditEventDateDisplay
- XMP:PhotoMeditEventDatePrecision
- XMP:PhotoMeditEventDateApproximate

### Title (Subject)
- XMP-dc:title
- IPTC:ObjectName

### Notes (Description)
- XMP-dc:description
- IPTC:Caption-Abstract

### People (Keywords)
- XMP-dc:subject[] (array of people names)
- IPTC:Keywords[] (comma-separated or array)

### Location
- locationName parsed into:
  - XMP-photoshop:City
  - XMP-photoshop:Country
  - IPTC:City
  - IPTC:Country-PrimaryLocationName
- locationCoords mapped to EXIF GPS tags:
  - EXIF:GPSLatitude
  - EXIF:GPSLongitude
  - EXIF:GPSLatitudeRef
  - EXIF:GPSLongitudeRef
- Coordinates derived automatically when the place name is recognizable by the geocoder

### Review Status
Stored under:
- xmp:PhotoMeditReviewStatus = unreviewed or reviewed

## 7. File Handling

### Thumbnails & Previews
- Images: For JPEGs < 5MB, serve directly. For RAW and larger files, use embedded previews where available or generate from RAW.
- Videos: Generate thumbnail using ffmpeg.
- Cache stored under thumbnailCacheRoot/YYYYMMDD/.

### Lazy Folder Scanning
No pre-indexing; folders scanned per request.

### Atomic Writes
- Write to temporary file
- Validate
- Atomically replace original
- Remove temporary file
- Never partially overwrite or corrupt originals

### Reject Workflow
- Images can be rejected, moving them to .rejected folder in library root
- Preserves folder structure within .rejected
- Sidecars moved with media files
- .rejected folders excluded from browsing

## 8. Authentication & Security

### Multiple Users via Database
- Admin user stored in `config.yaml` for initial access (cannot be modified via UI)
- Other users stored in MariaDB database
- Users have `role` field: 'user' or 'admin'
- Admin users can manage other users via admin UI
- All users (user and admin roles) have full access to media
- Last login timestamp tracked for each user
- Disabling auth is allowed for trusted LAN-local deployments

### JWT-Based Authentication
- Login endpoint issues signed JWT
- All other endpoints require Authorization: Bearer <token> when auth enabled
- Image endpoints support token in query parameter for <img> tag compatibility

### Multi-Factor Authentication (MFA)
- TOTP-based using pyotp
- QR code generation for setup
- MFA secret stored in user config
- Two-step login: password → MFA token (if enabled)
- Users can enable/disable MFA via UI

### Password Reset
- Token-based reset flow
- Reset tokens stored in-memory (60-minute expiry)
- Future: email integration for token delivery

### OWASP Alignment
- Input validation (pydantic)
- Strict path sanitization
- Secure headers:
  - Content-Security-Policy
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY or SAMEORIGIN
  - Referrer-Policy

### Logging
- No passwords, no secrets, no JWTs in logs
- Debug mode includes extra metadata diff logs

## 9. Admin Features

### User Management
- Admin-only endpoints for:
  - List users
  - Create users
  - Update users (password, admin status)
  - Delete users (cannot delete self)
- MFA status visible in user list

## 10. Upload & Download

### Upload
- Files uploaded to uploadRoot with batch directories
- Batch naming: <sanitizedUploadName>-<timestamp>
- Binary validation using magic bytes
- Atomic writes with temp files
- Filename conflict resolution
- Post-upload metadata import
- Configurable limits (file count, size)

### Download
- ZIP generation with folder structure preservation
- Automatic sidecar inclusion
- contents.txt with tab-separated metadata
- Scope filtering (all or reviewed)
- Configurable limits (file count, size)

See upload-download.md for full specification.

## 11. REST API Summary

(Full details in api-spec.md)

### Authentication
- POST /auth/login
- POST /auth/forgot-password
- POST /auth/reset-password
- GET /auth/mfa/setup
- POST /auth/mfa/verify
- POST /auth/mfa/disable

### Admin (Admin users only)
- GET /admin/users
- POST /admin/users
- PUT /admin/users/{username}
- DELETE /admin/users/{username}

### Libraries & Folders
- GET /libraries
- GET /libraries/{id}/folders
- POST /libraries/{id}/folders
- GET /libraries/{id}/folders/{folderId}/media

### Media
- GET /media/{id}
- GET /media/{id}/preview
- GET /media/{id}/thumbnail
- GET /media/{id}/download
- PATCH /media/{id}
- POST /media/{id}/reject
- GET /media/{id}/navigate

### Search
- GET /search

### Upload
- POST /upload

### Download
- POST /download

## 12. Web UI

### Views
- Library & folder browser with folder creation
- Media grid with reviewStatus filter
- Media detail view (image or video)
- Upload page
- Admin page (admin users only)
- MFA setup page
- Forgot password page

### Editing
- Immediate editing (no separate Edit mode)
- Save with clear success/error messaging
- "Mark reviewed when saving" checkbox
- Previous/Next navigation respects current reviewStatus filter
- Reject button to move images to .rejected folder

### Keyboard Shortcuts
- S / Ctrl+S / Cmd+S = Save
- ← → = Navigate
- Esc = Back to grid
- Ctrl+F / Cmd+F = Focus search/filter

## 13. Deployment & Configuration

### YAML Config
Includes:
- libraries[]
- thumbnailCacheRoot
- uploadRoot
- limits (upload/download)
- auth settings (users with isAdmin, passwordHash, mfaSecret)
- geocoding settings
- logging.level
- server.port
- server.jwtSecret

### Deployment Target
- Docker container (single container with Flask serving React build)
- Linux host
- Reverse proxy recommended for HTTPS

## 14. Performance & Scalability

Designed for thousands of media assets per library.

Lazy scanning + caching avoids need for DB.

Future upgrade path includes optional SQLite index for fast search.

## 15. Tech Stack Summary

- Backend: Python 3.11 + Flask 3.0.0
- Database: MariaDB 10.11 + SQLAlchemy 2.0.23 + pymysql 1.1.0
- Validation: pydantic 2.5.2
- Metadata: exiftool wrapper
- Video thumbs: ffmpeg
- Frontend: React + Vite
- Authentication: PyJWT 2.8.0, bcrypt 4.1.1
- MFA: pyotp 2.9.0, qrcode[pil] 7.4.2
- Image processing: Pillow 10.1.0, rawpy 0.20.0
- Production server: Gunicorn 21.2.0
