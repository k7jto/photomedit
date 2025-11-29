PhotoMedit – File Transfer & Import Specification

(Upload, Download, and Metadata Import)

This document defines how PhotoMedit:

Imports existing metadata from files and sidecars

Uploads new photos/videos into the system

Downloads media and metadata out of the system

It is the single source of truth for:

How files are validated and stored

How existing EXIF/IPTC/XMP metadata is read and surfaced

How bulk downloads are packaged for end users

How sidecar XMP files are treated

Companion docs (conceptual, not required to read this):

- requirements.md
- api-spec.md
- architecture.md

All located in the `specs/` directory.

1. Scope & Goals

Import / Discovery

When PhotoMedit sees a file (via upload or library scan), it must:

Read existing EXIF/IPTC/XMP metadata.

Map that into PhotoMedit’s logical fields (eventDate, subject, notes, people, location, etc.).

Display that metadata in the UI without overwriting anything by default.

Upload

Let users add new media into an app-controlled area.

Require a batch name.

Validate each file by binary type detection before writing.

Preserve filenames where possible, with safe sanitization.

Download

Let users download “all” or “reviewed” media from folders or whole libraries.

Always include XMP sidecars along with their media.

Preserve folder structure.

Provide a simple “contents.txt” listing at the root of the ZIP.

The design must be friendly enough for Aunt Edna, but robust enough for long-term archive workflows.

2. Core Concepts
2.1 Media Item

A “media item” in PhotoMedit is:

A file under a library root (image or video), with:

Relative path (within the library)

Logical metadata (eventDate, subject, notes, people, location, reviewStatus, etc.)

Optional associated XMP sidecar file

Sidecars are not separate items in the UI; they are attached to their base file.

2.2 Sidecar

XMP sidecar file:

Same directory as the base file

Same basename, .xmp extension

For example:

photos/1950s/img001.nef

photos/1950s/img001.xmp

Sidecars are:

Primary source for metadata when present.

Always included in downloads alongside their media.

Never independently listed or reviewed.

2.3 Libraries & Upload Root

Libraries:

Configured in YAML, each with id, name, rootPath.

Read-only or read/write depending on deployment.

Upload Root:

A separate path where new upload batches are stored.

Example: /mnt/data/photomedit-uploads.

Each upload creates a new subdirectory.

3. Import / Discovery & Existing Metadata

Whenever PhotoMedit encounters a media file (through upload or scan), it must:

Discover Available Metadata

Look for a sidecar XMP file (same basename + .xmp).

If found:

Use sidecar fields as the primary source.

If not found:

Read embedded EXIF/IPTC/XMP from the media file.

Map to Logical Fields
For each media item, initialize PhotoMedit’s logical fields:

eventDate

eventDateDisplay / eventDatePrecision / eventDateApproximate

subject

notes

people[]

locationName / locationCoords

reviewStatus (default “unreviewed” if not found)

The mapping uses the rules already defined elsewhere (EXIF/IPTC/XMP mapping). On first import/discovery:

If a field exists in metadata (e.g., IPTC Caption), populate the corresponding logical field (e.g., notes).

If a field is missing, leave the logical field blank or set a sane default:

reviewStatus → unreviewed by default unless an XMP custom value is present.

Do Not Overwrite Unrelated Fields

Import is read-only on first discovery:

It does not write or “normalize” metadata.

It simply reads what’s already there and presents it.

Only when the user saves changes in the UI does PhotoMedit write back to sidecar/embedded metadata.

Subsequent Reads

On subsequent loads of the same media item:

The system should re-read metadata from disk or use an internal cache that was populated from the file.

If metadata was changed outside PhotoMedit, an eventual metadata refresh strategy may be added later.

v1 can assume that PhotoMedit is the primary editor for that archive while it’s in use.

Summary:
On import, PhotoMedit displays and respects existing metadata. Users see their pre-existing dates, subjects, notes, locations, etc., not blank fields.

4. Upload Specification
4.1 Upload Goal

The upload feature lets users place new media files into an app-controlled area, with:

A mandatory batch name.

Binary-type validation for each file.

File name preservation with sanitization.

Immediate metadata import (as described above), so existing tags and dates show up.

4.2 Upload Root & Batch Directories

Configuration:

uploadRoot: absolute path where upload batches are stored.

Each upload request creates:

A new directory under uploadRoot:

<sanitizedUploadName>-<timestamp>

Example:

uploadName: “Grandma Box 1”

Sanitized: grandma-box-1

Timestamp: 20251129-153010

Batch path:
/mnt/data/photomedit-uploads/grandma-box-1-20251129-153010/

All uploaded files from that request go into that directory.

Later, PhotoMedit can:

Treat uploadRoot as a library, or

Offer a way to move/copy batches into existing libraries.

4.3 Allowed File Types

Allowed types:

Images:

JPEG

Common RAW formats (ORF, NEF, CR2, CR3, RAF, etc.)

Videos:

MP4

MOV

M4V

Type detection is based on binary signature (magic bytes), not filename or MIME header.

4.4 Endpoint & Request

Endpoint:

POST /upload

Request:

Content-Type: multipart/form-data

Fields:

uploadName (required string)

files[] (one or more files)

Validation:

uploadName:

Required, non-empty.

Max length (e.g., 100 characters).

Sanitized into a directory name:

Lowercase

Spaces → -

Remove unsafe characters.

files[]:

At least one file required.

Enforce max file count.

Enforce max per-file size.

Enforce max total size.

4.5 Filename Handling

For each file:

Take client-provided filename.

Strip directory components (no ../, no slashes).

Remove or replace characters invalid for the host filesystem or problematic in Docker:

No control chars, no reserved characters (: * ? " < > | etc.).

Normalize whitespace.

If a file with sanitizedFileName already exists in the target batch directory:

Append a numeric suffix before the extension:

img001.jpg → img001-1.jpg, img001-2.jpg, etc.

4.6 Binary Peek Validation

For each file:

Peek at the first N bytes (e.g., 4–8 KB).

Determine type from magic bytes.

If type is not recognized as a supported image/video:

Reject this file.

Do not write it to disk.

4.7 Write Process

For each accepted file:

Ensure batch directory exists.

Write to temporary file:
<uniqueSanitizedFileName>.tmp

Flush and close.

Optionally confirm size and basic integrity.

Atomically rename to <uniqueSanitizedFileName>.

If any error occurs:

Delete the temp file.

Mark file as failed in the response.

4.8 Post-Upload Import

After each successful file write:

Treat the new file as newly discovered media.

Immediately perform the import/discovery step (section 3):

Locate sidecar (if any).

Read EXIF/IPTC/XMP metadata.

Initialize logical fields from existing metadata.

This ensures that existing dates, captions, keywords, etc. are visible in the UI as soon as the upload completes.

4.9 Response

Return JSON summarizing the upload:

uploadId: e.g., grandma-box-1-20251129-153010

uploadName: original name

targetDirectory: batch directory name (relative to uploadRoot)

files: array, one entry per uploaded file

Per file:

originalName

storedName

relativePath (from uploadRoot)

sizeBytes

status: "ok" or "error"

errorCode (if any)

errorMessage (if any)

5. Download Specification
5.1 Download Goals

Downloads must:

Let users get:

All media in a folder (and below).

Only reviewed media in a folder (and below).

Optionally all/reviewed media in a library.

Preserve folder structure.

Always include XMP sidecars.

Include a simple contents.txt file at the root with human-friendly info.

5.2 Download Scope Options (UI)

At folder level:

Download all in this folder

Download reviewed in this folder

At library root (optional):

Download all in this library

Download reviewed in this library

Each action corresponds to:

A set of media items (images + videos) filtered by:

libraryId

optional folder subtree

reviewStatus (all vs reviewed)

5.3 Archive Format

Always deliver a single ZIP file:

No per-file downloads.

No multiple browser prompts.

Example filenames:

family-reviewed-20251129-143000.zip

family-all-20251129-143000.zip

5.4 Preserving Folder Structure

Within the ZIP, each media file is stored at its relative path under the library root:

photos/1950s/img001.nef

photos/1950s/img001.xmp

videos/8mm/reel01.mp4

videos/8mm/reel01.xmp

5.5 Including Sidecars

For each media file selected for download:

Add the media file under its relative path.

Compute sidecar name:

Same directory, same basename, .xmp extension.

If the sidecar exists:

Add it under the same relative path.

This is always done. No setting to skip XMP.

Orphan sidecars (without matching media) are ignored.

If both RAW and JPEG share the same basename .xmp (rare), that single sidecar will serve both.

5.6 contents.txt

At the root of every ZIP, PhotoMedit includes a file:

contents.txt

This is a plain text file with one line per media file (not counting sidecars).

5.6.1 Format

First line: header row with simple names.

Columns separated by a tab (\t) for clarity.

Columns:

Path (folder path relative to library root, no leading slash)

FileName

Reviewed (Yes or No)

EventDate (YYYY-MM-DD or empty)

Subject

People (semicolon-separated)

Location (locationName)

Notes

Header line:

Path\tFileName\tReviewed\tEventDate\tSubject\tPeople\tLocation\tNotes

Example data line:

photos/1950s\timg001.jpg\tYes\t1950-06-01\tGrandma in the backyard\tMary Smith; John Smith\tTallahassee, FL\tTaken at the old family home.

Sidecars are not listed individually; they are implied by the presence of their media files.

5.6.2 Data Source

Each line in contents.txt is generated from the logical metadata for that media item:

reviewStatus → Reviewed = Yes if reviewed, otherwise No.

eventDate → EventDate.

subject → Subject.

notes → Notes.

people → semicolon-separated.

locationName → Location.

This ensures that both existing metadata (imported) and PhotoMedit edits are reflected.

5.7 Download Endpoint

Endpoint example:

POST /download

Request body:

libraryId (required)

scope (required): "all" or "reviewed"

folder (optional): relative path to restrict the scope to a subtree

Behavior:

Validate request and auth.

Build media set based on scope.

Enforce size/count limits.

Build a ZIP (temp file or streaming) that includes:

All selected media files.

Their sidecars.

contents.txt at the root.

Respond with the ZIP as:

Content-Type: application/zip

Content-Disposition: attachment; filename="<something>.zip"

6. Limits & Safeguards

Both upload and download operations must enforce configurable limits:

Upload limits

maxUploadFiles (e.g., 500 per request)

maxUploadBytesPerFile (e.g., 500 MB)

maxUploadBytesTotal (e.g., 5–10 GB)

Download limits

maxDownloadFiles (e.g., 10,000 per request)

maxDownloadBytes (estimated or actual; e.g., 20 GB)

If a limit is exceeded:

Return a 400-level error with a clear message.

No partial ZIP created.

7. Frontend UX Summary
Upload UX

Fields:

“Name this upload” (maps to uploadName).

“Choose photos and videos” (files[]).

Messaging:

Explain that only photos/videos are accepted.

Explain that files will be placed into a new folder named after the upload.

After upload:

Show a summary of how many files succeeded and how many were skipped.

Show simple explanations for rejections (unsupported type, too big, etc.).

New batch appears in the “Uploads” area or in a dedicated library.

Import UX

Once uploaded, any existing metadata (dates, captions, etc.) should appear in:

Grid (e.g., small indicators: hasSubject, hasNotes).

Detail view (fields pre-populated).

Download UX

Buttons for “Download all in this folder” and “Download reviewed in this folder.”

Optional library-level equivalents.

Short note when they click:

“We’ll bundle your photos and their details into a ZIP file for you.”

On completion, the user gets a single ZIP file with:

Folders and filenames as they expect.

Sidecars included automatically.

contents.txt for an at-a-glance listing.