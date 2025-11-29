PhotoMedit – Architecture & Implementation Guide

Companion documents:

Requirements (requirements.md)

API Specification (api-spec.md)

1. High-Level Architecture

PhotoMedit consists of:

Python/Flask backend

React (or similar) SPA frontend

NAS-backed filesystem libraries

Thumbnail/preview cache

YAML configuration loader

exiftool wrapper for metadata

ffmpeg (or similar) for video thumbnails

pydantic or marshmallow for validation

JWT-based authentication

No database is required in v1.
Everything is file-backed + in-memory scan results.

2. Backend Structure

Recommended directory layout:

backend/

app.py

config/

loader.py

auth/

routes.py

jwt.py

libraries/

routes.py

filesystem.py

media/

routes.py

metadata_reader.py

metadata_writer.py

preview_generator.py

navigation.py

validation/

schemas.py

security/

headers.py

sanitizer.py

utils/

file_io.py

sidecar.py

timestamp.py

3. Flask Application

Use Blueprints for modular routing.

Apply secure headers globally.

JSON-only API.

Validate all request bodies and parameters using schema validators.

Enforce shared error-handling for consistent responses.

Resolve media IDs of form: libraryId|relative/path.ext.

4. Path Handling & Safety

All paths must be resolved as:
rootPath + relativePath

Reject:

".." components

absolute paths

symlinks that escape root

Normalize and re-check resolved path against rootPath.

5. Authentication

Load user list from config.

Store passwordHash as bcrypt.

Compare provided password using bcrypt.verify.

Issue JWT with:

expiration

username

Validate JWT on every request (except login) when auth.enabled.

6. Metadata Processing
Reader

For sidecar files:

Read XMP first.

For images:

Use exiftool or equivalent wrapper.

For videos:

Use exiftool (sidecar-first), avoid risky embedded writes.

Writer

Merge logical metadata fields into:

sidecar XMP

embedded EXIF/IPTC (images only)

Apply atomic write strategy:

Write to temporary

Validate

Replace original

For videos:

Prefer sidecar-only writes unless tooling fully safe.

7. Thumbnails & Previews
Images

Prefer embedded JPEG previews for RAW.

Otherwise, generate using image library + demosaic.

Store in thumbnailCacheRoot with hashed filenames.

Videos

Use ffmpeg or similar:

Extract frame at fixed timestamp (e.g., 10% duration).

Cache thumbnails exactly like images.

8. Searching & Filtering

v1 search is implemented via:

folder scan

filtering in memory

no persistent index

Future index (SQLite) is possible without structural changes.

9. Error Handling

Return consistent JSON errors:

400 validation_error

401 unauthorized

403 forbidden (if needed)

404 not_found

500 internal_error or metadata_write_failed

Never expose internal exceptions to client.

10. Deployment
Docker

Recommended Dockerfile includes:

Python base

exiftool installation

ffmpeg installation

Gunicorn/Waitress or similar for production

Reverse Proxy

Use Nginx/Caddy/Traefik for:

HTTPS

Compression

Caching headers

Static file serving (frontend build)

11. Frontend Structure

React SPA with:

Library selector

Folder browser

Media grid

Media detail view

Use fetch/axios client for REST calls.

Use React Router for navigation.

Handle JWT storage in memory (no localStorage unless secure).

Implement keyboard shortcuts at root level.

12. Future Enhancements

Android app (v2)

Batch editing

Bulk upload with uniform metadata presets

SQLite metadata index

OCR or AI enhancements (optional)

Face detection + region tags