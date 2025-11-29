"""Library and folder routes."""
from flask import Blueprint, request, jsonify, current_app
from backend.config.loader import Config
from backend.libraries.filesystem import scan_folder, scan_media_files
from backend.media.metadata_reader import MetadataReader
from backend.media.preview_generator import PreviewGenerator
from backend.security.sanitizer import PathSanitizer
import os


libraries_bp = Blueprint('libraries', __name__)


@libraries_bp.route('/libraries', methods=['GET'])
def list_libraries():
    """List all configured libraries."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    libraries = [
        {'id': lib['id'], 'name': lib.get('name', lib['id'])}
        for lib in config.libraries
    ]
    
    return jsonify(libraries), 200


@libraries_bp.route('/libraries/<library_id>/folders', methods=['GET'])
def list_folders(library_id: str):
    """List folders in a library."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    library = config.get_library(library_id)
    if not library:
        return jsonify({'error': 'not_found', 'message': 'Library not found'}), 404
    
    parent = request.args.get('parent', '')
    folders = scan_folder(library['rootPath'], parent)
    
    # Add library ID prefix to folder IDs
    for folder in folders:
        folder['id'] = f"{library_id}|{folder['id']}"
    
    return jsonify(folders), 200


@libraries_bp.route('/libraries/<library_id>/folders/<path:folder_id>/media', methods=['GET'])
def list_media(library_id: str, folder_id: str):
    """List media files in a folder."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    library = config.get_library(library_id)
    if not library:
        return jsonify({'error': 'not_found', 'message': 'Library not found'}), 404
    
    # Remove library ID prefix from folder_id
    relative_path = folder_id.replace(f"{library_id}|", "", 1) if folder_id.startswith(f"{library_id}|") else folder_id
    
    # Validate path
    is_valid, resolved_path, error = PathSanitizer.sanitize_path(library['rootPath'], relative_path)
    if not is_valid:
        return jsonify({'error': 'validation_error', 'message': error}), 400
    
    # Get review status filter
    review_status = request.args.get('reviewStatus', 'unreviewed')
    if review_status not in ['unreviewed', 'reviewed', 'all']:
        review_status = 'unreviewed'
    
    # Scan media files
    media_files = scan_media_files(library['rootPath'], relative_path)
    
    # Generate preview generator
    preview_gen = PreviewGenerator(config.thumbnail_cache_root)
    
    # Build response
    media_list = []
    for mf in media_files:
        # Read metadata
        metadata = MetadataReader.read_logical_metadata(mf['path'])
        
        # Apply review status filter
        file_review_status = metadata.get('reviewStatus', 'unreviewed')
        if review_status == 'reviewed':
            # Show only reviewed images
            if file_review_status != 'reviewed':
                continue
        elif review_status == 'unreviewed':
            # Show all images that are NOT reviewed (including those without status)
            if file_review_status == 'reviewed':
                continue
        # 'all' shows everything, so no filtering needed
        
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
        
        # Always provide thumbnail URL for images
        media_id = f"{library_id}|{mf['relativePath']}"
        thumbnail_url = f"/api/media/{media_id}/thumbnail"
        
        # Build media ID
        media_id = f"{library_id}|{mf['relativePath']}"
        
        media_list.append({
            'id': media_id,
            'filename': mf['filename'],
            'relativePath': mf['relativePath'],
            'mediaType': 'image' if is_image else 'video',
            'thumbnailUrl': thumbnail_url,
            'eventDate': metadata.get('eventDate'),
            'hasSubject': bool(metadata.get('subject')),
            'hasNotes': bool(metadata.get('notes')),
            'hasPeople': bool(metadata.get('people')),
            'reviewStatus': file_review_status
        })
    
    return jsonify(media_list), 200

