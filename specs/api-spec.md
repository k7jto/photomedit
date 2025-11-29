PhotoMedit – API Specification

Companion documents:

- Requirements (requirements.md)
- Architecture Guide (architecture.md)
- Upload/Download Specification (upload-download.md)

All located in the `specs/` directory.

Base URL: /api
Auth: JWT (unless disabled)

## 1. Authentication

### POST /auth/login
Request: 
- username (string, required)
- password (string, required)
- mfaToken (string, optional) - Required if MFA is enabled for user

Response: 
- token (string)
- expiresAt (string, ISO 8601)

Errors: 
- 401 invalid credentials
- 200 with mfaRequired: true if MFA is enabled but token not provided

### POST /auth/forgot-password
Request:
- username (string, required)

Response:
- message (string)
- resetToken (string) - In production, should be sent via email only
- resetUrl (string)

### POST /auth/reset-password
Request:
- token (string, required)
- password (string, required)

Response:
- message (string)

Errors:
- 400 invalid or expired token

### GET /auth/mfa/setup
Requires authentication.

Response:
- secret (string) - TOTP secret key
- qrCode (string) - Base64 data URL of QR code
- uri (string) - Provisioning URI

### POST /auth/mfa/verify
Requires authentication.

Request:
- token (string, required) - 6-digit TOTP code

Response:
- message (string)

### POST /auth/mfa/disable
Requires authentication.

Request:
- password (string, optional) - Password confirmation

Response:
- message (string)

## 2. Admin (Admin users only)

### GET /admin/users
Requires admin authentication.

Response: Array of user objects:
- username (string)
- role (string) - "user" or "admin"
- mfaEnabled (boolean)
- createdAt (string, optional) - ISO 8601 timestamp
- lastLogin (string, optional) - ISO 8601 timestamp
- source (string) - "database" or "config" (config users cannot be modified via UI)

### POST /admin/users
Requires admin authentication.

Request:
- username (string, required)
- password (string, required)
- role (string, optional, default: "user") - "user" or "admin"

Response:
- message (string)
- username (string)

### PUT /admin/users/{username}
Requires admin authentication.

Cannot update admin user from config (must edit config.yaml directly).

Request:
- password (string, optional) - New password (leave empty to keep current)
- role (string, optional) - "user" or "admin"

Response:
- message (string)

### DELETE /admin/users/{username}
Requires admin authentication.

Cannot delete your own account.

Response:
- message (string)

## 3. Libraries & Folders

### GET /libraries
Returns: Array of library objects with:
- id (string)
- name (string)

### GET /libraries/{libraryId}/folders
Optional query: parent=<relativePath>

Returns folder tree nodes:
- id (string) - Format: libraryId|relativePath
- name (string)
- relativePath (string)
- hasChildren (boolean)

### POST /libraries/{libraryId}/folders
Request:
- parent (string, optional) - Relative path of parent folder
- name (string, required) - Folder name (no path separators)

Response:
- id (string)
- name (string)
- relativePath (string)
- hasChildren (boolean)

### GET /libraries/{libraryId}/folders/{folderId}/media
Query parameters:
- reviewStatus = unreviewed (default), reviewed, all

Returns objects containing:
- id (string) - Format: libraryId|relativePath
- filename (string)
- relativePath (string)
- mediaType (string) - "image" or "video"
- thumbnailUrl (string)
- eventDate (string, optional)
- hasSubject (boolean)
- hasNotes (boolean)
- hasPeople (boolean)
- reviewStatus (string)

## 4. Media Detail & Navigation

### GET /media/{id}
Returns:
- libraryId (string)
- relativePath (string)
- filename (string)
- mediaType (string)
- logicalMetadata (object) - All editable fields
- technicalMetadata (object)
- previewUrl (string, optional)
- downloadUrl (string)

### GET /media/{id}/preview
Returns preview image (JPEG) or video thumbnail.

Supports token query parameter for authentication: ?token=<jwt>

### GET /media/{id}/thumbnail
Returns thumbnail image (JPEG).

Supports token query parameter for authentication: ?token=<jwt>

### GET /media/{id}/download
Downloads original media file.

Supports token query parameter for authentication: ?token=<jwt>

### PATCH /media/{id}
Body may include any editable fields:
- eventDate (string, optional)
- eventDateDisplay (string, optional)
- eventDatePrecision (string, optional) - YEAR, MONTH, DAY, UNKNOWN
- eventDateApproximate (boolean, optional)
- subject (string, optional)
- notes (string, optional)
- people (array of strings, optional)
- locationName (string, optional)
- locationCoords (object, optional) - {lat: number, lon: number}
- reviewStatus (string, optional) - "unreviewed" or "reviewed"
- markReviewed (boolean, optional) - If true, automatically sets reviewStatus to "reviewed"

Validation errors return 400.
Metadata write failures return 500.

### POST /media/{id}/reject
Moves media file to .rejected folder in library root.

Response:
- message (string)

### GET /media/{id}/navigate
Query:
- direction (string, required) - "next" or "previous"
- reviewStatus (string, optional) - unreviewed (default), reviewed, all

Returns:
- nextId (string, optional) - Media ID of adjacent item

## 5. Search

### GET /search
Query:
- libraryId (string, required)
- folder (string, optional)
- hasSubject (boolean, optional)
- hasNotes (boolean, optional)
- hasPeople (boolean, optional)
- reviewStatus (string, optional) - unreviewed, reviewed, all

Returns a list of matching media items, same structure as folder media listing.

## 6. Upload

### POST /upload
Multipart form data:
- uploadName (string, required) - Batch name (max 100 characters)
- files[] (file[], required) - One or more files

Response:
- uploadId (string) - Batch directory name
- uploadName (string) - Original upload name
- targetDirectory (string) - Batch directory name
- files (array) - Per-file results:
  - originalName (string)
  - storedName (string)
  - relativePath (string)
  - sizeBytes (number)
  - status (string) - "ok" or "error"
  - errorCode (string, optional)
  - errorMessage (string, optional)

Files are stored in uploadRoot/<sanitizedUploadName>-<timestamp>/

See upload-download.md for full specification.

## 7. Download

### POST /download
Request body:
- libraryId (string, required)
- scope (string, required) - "all" or "reviewed"
- folder (string, optional) - Relative path to restrict scope

Response: ZIP file with:
- All selected media files preserving folder structure
- XMP sidecar files for each media file
- contents.txt at root with tab-separated metadata

Content-Type: application/zip
Content-Disposition: attachment; filename="<folder>-<scope>-<timestamp>.zip"

See upload-download.md for full specification.
