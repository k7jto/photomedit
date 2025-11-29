PhotoMedit – Requirements

Companion documents:

API Specification (api-spec.md)

Architecture & Implementation Guide (architecture.md)

1. Overview

PhotoMedit is a self-hosted photo and video metadata editor built for family archives, especially scanned historical photographs, RAW images, and digitized home movies (8mm, Super8, VHS captures). It focuses on lightweight metadata management, accurate genealogical tagging, and a simple review workflow.

The system includes:

A REST API backend (Python + Flask).

A responsive web UI.

Multiple NAS-backed libraries (root directories).

Support for images and videos.

Editing of essential metadata fields.

Sidecar-first metadata handling.

Secure-by-default design (OWASP aligned).

Multiple users defined in YAML config.

It is intentionally minimal — not a replacement for PhotoPrism or Lightroom — but a highly efficient tool for cleaning, enriching, and preparing archives for long-term preservation and sharing.

2. Goals & Non-Goals
Goals

Browse one or more NAS-based libraries via the web UI.

View images (JPEG/RAW) and videos (MP4/MOV/M4V).

Edit: event date, subject, notes, people, location, and review status.

Store metadata in sidecars and embedded fields (images only).

Store metadata safely for videos (sidecar-first).

Maintain genealogically accurate date handling.

Provide a workflow: unreviewed → reviewed, with optional re-check.

Implement strong validation, safe writes, and OWASP security.

Support multiple users with equal permissions.

Non-Goals (v1)

No AI tagging or facial recognition.

No batch metadata editing.

No image or video editing.

No per-user permissions or ACLs.

No media versioning (writes overwrite in-place).

No indexing/DB requirement (lazy folder scans).

Android app planned for v2.

3. Libraries (NAS Directories)

Libraries are defined in YAML:

id

name

rootPath

All media browsing and access is constrained inside these root directories.

Folder trees are generated recursively.

Media browsing is lazy-loaded (no global scanning on startup).

4. Supported Media Types
Images:

JPEG

Common RAW formats (ORF, NEF, CR2, CR3, RAF, etc.)

Videos:

MP4

MOV

M4V

Every uploaded or discovered file must be validated using binary signatures (magic bytes), not extensions or MIME types.

5. Metadata Fields

Editable fields:

eventDate

eventDateDisplay

eventDatePrecision (YEAR, MONTH, DAY, UNKNOWN)

eventDateApproximate (true/false)

subject

notes

people[]

locationName

locationCoords { lat, lon }

reviewStatus (unreviewed or reviewed)

Read-only fields:

filename, relative path

media type (image or video)

image EXIF info

video duration, resolution, frame rate, codec

embedded capture/scan timestamps, if present

6. Metadata Semantics
Event Date (critical for genealogy)

Represents when the original event occurred.

Not derived from scan timestamps.

For scanned/digitized media, this overrides any device/scan dates.

Written to image metadata as:

EXIF DateTimeOriginal

EXIF DateTimeDigitized

IPTC DateCreated and TimeCreated

XMP photoshop:DateCreated and xmp:CreateDate

Precision and approximate fields stored in custom XMP tags:

xmp:PhotoMeditEventDateDisplay

xmp:PhotoMeditEventDatePrecision

xmp:PhotoMeditEventDateApproximate

Subject (Title)

IPTC ObjectName

XMP dc:title

EXIF XPTitle (images)

Notes (Description)

IPTC Caption-Abstract

XMP dc:description

EXIF ImageDescription, XPComment (images)

People

XMP dc:subject

IPTC Keywords[]

Location

locationName mapped to Iptc4xmpCore:Location and structured fields when possible

locationCoords mapped to EXIF GPS tags

Coordinates derived automatically when the place name is recognizable by the geocoder

Review Status

Stored under:

xmp:PhotoMeditReviewStatus = unreviewed or reviewed

7. File Handling
Thumbnails & Previews

Images: use embedded previews where available or generate from RAW.

Videos: generate thumbnail using ffmpeg or equivalent.

Cache stored under thumbnailCacheRoot/YYYYMMDD/.

Lazy Folder Scanning

No pre-indexing; folders scanned per request.

Atomic Writes

Write to temporary file

Validate

Atomically replace original

Remove temporary file

Never partially overwrite or corrupt originals

8. Authentication & Security
Multiple Users via Config

Users defined with bcrypt password hashes

All users have full access

Disabling auth is allowed for trusted LAN-local deployments

JWT-Based Authentication

Login endpoint issues signed JWT

All other endpoints require Authorization: Bearer <token> when auth enabled

OWASP Alignment

Input validation (pydantic or marshmallow)

Strict path sanitization

Secure headers:

Content-Security-Policy

X-Content-Type-Options: nosniff

X-Frame-Options: DENY or SAMEORIGIN

Referrer-Policy

Logging

No passwords, no secrets, no JWTs in logs.
Debug mode includes extra metadata diff logs.

9. REST API Summary

(Full details in api-spec.md)

POST /auth/login

GET /libraries

GET /libraries/{id}/folders

GET /libraries/{id}/folders/{folderId}/media

GET /media/{id}

GET /media/{id}/preview

PATCH /media/{id}

GET /media/{id}/navigate

GET /search

POST /libraries/{id}/upload (optional v1)

10. Web UI
Views

Library & folder browser

Media grid with reviewStatus filter

Media detail view (image or video)

Editing

Immediate editing (no separate Edit mode)

Save with clear success/error messaging

Previous/Next navigation respects current reviewStatus filter

Keyboard Shortcuts

S / Ctrl+S / Cmd+S = Save

← → = Navigate

Esc = Back to grid

Ctrl+F / Cmd+F = Focus search/filter

11. Deployment & Configuration
YAML Config

Includes:

libraries[]

thumbnailCacheRoot

auth settings

geocoding settings

logging.level

server.port

server.jwtSecret

Deployment Target

Docker container or Linux host

Reverse proxy recommended for HTTPS

12. Performance & Scalability

Designed for thousands of media assets per library

Lazy scanning + caching avoids need for DB

Future upgrade path includes optional SQLite index for fast search

13. Tech Stack Summary

Backend: Python + Flask

Validation: marshmallow or pydantic

Metadata: exiftool wrapper or equivalent

Video thumbs: ffmpeg or similar

Frontend: React or equivalent SPA