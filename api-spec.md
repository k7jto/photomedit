PhotoMedit – API Specification

Companion documents:

Requirements (requirements.md)

Architecture Guide (architecture.md)

Base URL: /api
Auth: JWT (unless disabled)

1. Auth

POST /auth/login
Request: username, password
Response: token, expiresAt
Errors: invalid credentials (401)

Auth is required for all other endpoints if enabled.

2. Libraries & Folders

GET /libraries
Returns: id, name for each configured library.

GET /libraries/{libraryId}/folders
Optional query: parent=<relativePath>
Returns folder tree nodes:

id

name

relativePath

hasChildren

GET /libraries/{libraryId}/folders/{folderId}/media
Query parameters:

reviewStatus = unreviewed (default), reviewed, all

Returns objects containing:

id

filename

relativePath

mediaType (image or video)

thumbnailUrl

eventDate

hasSubject

hasNotes

hasPeople

reviewStatus

3. Media Detail & Navigation

GET /media/{id}
Returns:

libraryId

relativePath

filename

mediaType

logicalMetadata (all editable fields)

technicalMetadata

previewUrl

downloadUrl

GET /media/{id}/preview
Returns either:

preview image (for images), or

thumbnail or playable video stream (for videos)

PATCH /media/{id}
Body may include any editable fields:

eventDate

eventDateDisplay

eventDatePrecision

eventDateApproximate

subject

notes

people[]

locationName

reviewStatus

Validation errors return 400.
Metadata write failures return 500.

GET /media/{id}/navigate
Query:

direction = next or previous

reviewStatus = unreviewed (default), reviewed, all

Returns:

currentId

direction

nextId (may be null)

4. Search

GET /search
Query:

libraryId

folder (optional)

hasSubject (bool)

hasNotes (bool)

hasPeople (bool)

reviewStatus (unreviewed, reviewed, all)

Returns a list of matching media items, same structure as folder media listing.

5. Upload (optional v1)

POST /libraries/{libraryId}/upload
Multipart form:

files[]

targetFolder

batchName

Behavior:

Validate JWT

Enforce size limits

Perform binary magic-number type validation

Sanitize filenames

Ensure writes occur inside library root

Save files to disk

Returns:

uploaded list (filename, relativePath, mediaId)

errors (if any)