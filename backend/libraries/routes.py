"""Library and folder routes."""
from flask import Blueprint, request, jsonify, current_app
from backend.config.loader import Config
from backend.libraries.filesystem import scan_folder, scan_media_files
from backend.media.metadata_reader import MetadataReader
from backend.media.preview_generator import PreviewGenerator
from backend.security.sanitizer import PathSanitizer
import os
import logging

logger = logging.getLogger(__name__)


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
    logger.info(f"List folders request: library={library_id}, parent='{parent}', rootPath={library['rootPath']}")
    
    # Verify root path exists and is accessible
    if not os.path.exists(library['rootPath']):
        logger.error(f"Library root path does not exist: {library['rootPath']}")
        return jsonify({'error': 'internal_error', 'message': f'Library root path does not exist: {library["rootPath"]}'}), 500
    
    if not os.path.isdir(library['rootPath']):
        logger.error(f"Library root path is not a directory: {library['rootPath']}")
        return jsonify({'error': 'internal_error', 'message': f'Library root path is not a directory: {library["rootPath"]}'}), 500
    
    if not os.access(library['rootPath'], os.R_OK):
        logger.error(f"Library root path is not readable: {library['rootPath']}")
        return jsonify({'error': 'internal_error', 'message': f'Library root path is not readable: {library["rootPath"]}'}), 500
    
    logger.info(f"Scanning folders with parent='{parent}', rootPath={library['rootPath']}")
    folders = scan_folder(library['rootPath'], parent)
    logger.info(f"Scan returned {len(folders)} folders")
    if len(folders) > 0:
        logger.info(f"Sample folder paths: {[f.get('relativePath', f.get('id', '')) for f in folders[:5]]}")
    
    # Add library ID prefix to folder IDs
    for folder in folders:
        folder['id'] = f"{library_id}|{folder['id']}"
    
    logger.info(f"Returning {len(folders)} folders with IDs: {[f['id'] for f in folders[:5]]}")
    return jsonify(folders), 200


@libraries_bp.route('/libraries/<library_id>/folders/<path:folder_id>/media', methods=['GET'])
@libraries_bp.route('/libraries/<library_id>/folders/media', methods=['GET'], defaults={'folder_id': ''})
def list_media(library_id: str, folder_id: str):
    """List media files in a folder."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    library = config.get_library(library_id)
    if not library:
        return jsonify({'error': 'not_found', 'message': 'Library not found'}), 404
    
    # Remove library ID prefix from folder_id, handle empty folder_id (root)
    if not folder_id:
        relative_path = ''
    else:
        relative_path = folder_id.replace(f"{library_id}|", "", 1) if folder_id.startswith(f"{library_id}|") else folder_id
    
    logger.info(f"List media request: library={library_id}, folder_id='{folder_id}', relative_path='{relative_path}'")
    
    # Validate path
    is_valid, resolved_path, error = PathSanitizer.sanitize_path(library['rootPath'], relative_path)
    if not is_valid:
        logger.error(f"Invalid path for media listing: {relative_path} - {error}")
    else:
        logger.info(f"Resolved path for media: {resolved_path}")
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
        
        # Check if thumbnail exists (don't generate synchronously during listing)
        # Queue for background generation if it doesn't exist
        media_id = f"{library_id}|{mf['relativePath']}"
        has_thumb = False
        if is_image:
            has_thumb = preview_gen.has_thumbnail(mf['path'])
            if not has_thumb:
                # Queue for background generation
                try:
                    from backend.media.thumbnail_worker import queue_thumbnail_generation
                    queue_thumbnail_generation(mf['path'], is_image=True, thumbnail_cache_root=config.thumbnail_cache_root)
                except Exception as e:
                    logger.debug(f"Failed to queue thumbnail for {mf['path']}: {e}")
        else:
            has_thumb = preview_gen.has_thumbnail(mf['path'])
            if not has_thumb:
                # Queue for background generation
                try:
                    from backend.media.thumbnail_worker import queue_thumbnail_generation
                    queue_thumbnail_generation(mf['path'], is_image=False, thumbnail_cache_root=config.thumbnail_cache_root)
                except Exception as e:
                    logger.debug(f"Failed to queue thumbnail for {mf['path']}: {e}")
        
        # Always provide thumbnail URL (will be generated on-demand if not cached)
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
    
    # Sort media list: by eventDate if available, otherwise by filename
    def sort_key(item):
        # Primary sort: eventDate (newest first)
        event_date = item.get('eventDate')
        if event_date:
            try:
                from datetime import datetime
                # Parse ISO format date
                dt = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                # Return negative timestamp for descending order (newest first)
                return (-dt.timestamp(), item['filename'].lower())
            except Exception:
                pass
        # Fallback: sort by filename (case-insensitive)
        return (float('inf'), item['filename'].lower())
    
    media_list.sort(key=sort_key)
    
    return jsonify(media_list), 200

