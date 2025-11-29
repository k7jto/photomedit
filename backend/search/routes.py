"""Search routes."""
from flask import Blueprint, request, jsonify, current_app
from backend.config.loader import Config
from backend.libraries.filesystem import scan_media_files
from backend.media.metadata_reader import MetadataReader
from backend.media.preview_generator import PreviewGenerator
from backend.security.sanitizer import PathSanitizer
from backend.validation.schemas import SearchQuery
from pydantic import ValidationError
import os


search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET'])
def search():
    """Search for media files."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    # Validate query parameters
    try:
        query = SearchQuery(**request.args)
    except ValidationError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    
    library = config.get_library(query.libraryId)
    if not library:
        return jsonify({'error': 'not_found', 'message': 'Library not found'}), 404
    
    # Get folder path
    folder_path = query.folder or ""
    is_valid, resolved_path, error = PathSanitizer.sanitize_path(library['rootPath'], folder_path)
    if not is_valid:
        return jsonify({'error': 'validation_error', 'message': error}), 400
    
    # Scan media files
    media_files = scan_media_files(library['rootPath'], folder_path)
    
    # Generate preview generator
    preview_gen = PreviewGenerator(config.thumbnail_cache_root)
    
    # Filter results
    results = []
    for mf in media_files:
        # Read metadata
        metadata = MetadataReader.read_logical_metadata(mf['path'])
        
        # Apply filters
        if query.reviewStatus != 'all':
            file_review_status = metadata.get('reviewStatus', 'unreviewed')
            if file_review_status != query.reviewStatus:
                continue
        
        if query.hasSubject is not None:
            has_subject = bool(metadata.get('subject'))
            if has_subject != query.hasSubject:
                continue
        
        if query.hasNotes is not None:
            has_notes = bool(metadata.get('notes'))
            if has_notes != query.hasNotes:
                continue
        
        if query.hasPeople is not None:
            has_people = bool(metadata.get('people'))
            if has_people != query.hasPeople:
                continue
        
        # Determine media type
        ext = mf['extension'].lower()
        image_exts = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
        is_image = ext in image_exts
        
        # Generate thumbnail URL
        thumbnail_path = None
        if is_image:
            thumbnail_path = preview_gen.generate_image_thumbnail(mf['path'])
        else:
            thumbnail_path = preview_gen.generate_video_thumbnail(mf['path'])
        
        thumbnail_url = None
        if thumbnail_path:
            media_id = f"{query.libraryId}|{mf['relativePath']}"
            thumbnail_url = f"/api/media/{media_id}/thumbnail"
        
        # Build media ID
        media_id = f"{query.libraryId}|{mf['relativePath']}"
        
        results.append({
            'id': media_id,
            'filename': mf['filename'],
            'relativePath': mf['relativePath'],
            'mediaType': 'image' if is_image else 'video',
            'thumbnailUrl': thumbnail_url,
            'eventDate': metadata.get('eventDate'),
            'hasSubject': bool(metadata.get('subject')),
            'hasNotes': bool(metadata.get('notes')),
            'hasPeople': bool(metadata.get('people')),
            'reviewStatus': metadata.get('reviewStatus', 'unreviewed')
        })
    
    return jsonify(results), 200

