"""Media routes."""
from flask import Blueprint, request, jsonify, send_file, current_app
from backend.config.loader import Config
from backend.media.metadata_reader import MetadataReader
from backend.media.metadata_writer import MetadataWriter
from backend.media.preview_generator import PreviewGenerator
from backend.media.navigation import MediaNavigator
from backend.security.sanitizer import PathSanitizer
from backend.utils.geocoding import GeocodingService
from backend.validation.schemas import MediaUpdateRequest, NavigateQuery
from pydantic import ValidationError
import os


media_bp = Blueprint('media', __name__)


def _parse_media_id(media_id: str) -> tuple:
    """Parse media ID into library_id and relative_path."""
    if '|' not in media_id:
        return None, None
    parts = media_id.split('|', 1)
    return parts[0], parts[1]


def _get_media_path(library_id: str, relative_path: str) -> tuple:
    """Get full media path and validate."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return None, None, {'error': 'internal_error', 'message': 'Configuration not available'}, 500
    
    library = config.get_library(library_id)
    if not library:
        return None, None, {'error': 'not_found', 'message': 'Library not found'}, 404
    
    is_valid, resolved_path, error = PathSanitizer.sanitize_path(library['rootPath'], relative_path)
    if not is_valid:
        return None, None, {'error': 'validation_error', 'message': error}, 400
    
    if not os.path.exists(resolved_path) or not os.path.isfile(resolved_path):
        return None, None, {'error': 'not_found', 'message': 'Media file not found'}, 404
    
    return resolved_path, library, None, None


@media_bp.route('/media/<path:media_id>', methods=['GET'])
def get_media(media_id: str):
    """Get media detail."""
    library_id, relative_path = _parse_media_id(media_id)
    if not library_id or not relative_path:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    media_path, library, error_dict, status = _get_media_path(library_id, relative_path)
    if error_dict:
        return jsonify(error_dict), status
    
    # Determine media type
    ext = os.path.splitext(media_path)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
    is_image = ext in image_exts
    
    # Read metadata
    logical_metadata = MetadataReader.read_logical_metadata(media_path)
    technical_metadata = MetadataReader.read_technical_metadata(media_path)
    
    # Generate preview URL
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    preview_gen = PreviewGenerator(config.thumbnail_cache_root)
    preview_path = preview_gen.generate_preview(media_path, is_image)
    preview_url = f"/api/media/{media_id}/preview" if preview_path else None
    
    return jsonify({
        'libraryId': library_id,
        'relativePath': relative_path,
        'filename': os.path.basename(media_path),
        'mediaType': 'image' if is_image else 'video',
        'logicalMetadata': logical_metadata,
        'technicalMetadata': technical_metadata,
        'previewUrl': preview_url,
        'downloadUrl': f"/api/media/{media_id}/download"
    }), 200


@media_bp.route('/media/<path:media_id>/preview', methods=['GET'])
def get_preview(media_id: str):
    """Get preview image or video."""
    library_id, relative_path = _parse_media_id(media_id)
    if not library_id or not relative_path:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    media_path, library, error_dict, status = _get_media_path(library_id, relative_path)
    if error_dict:
        return jsonify(error_dict), status
    
    # Determine media type
    ext = os.path.splitext(media_path)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
    is_image = ext in image_exts
    
    # Generate preview
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    preview_gen = PreviewGenerator(config.thumbnail_cache_root)
    
    if is_image:
        ext = os.path.splitext(media_path)[1].lower()
        # For JPEGs, serve directly for preview (no need to generate)
        if ext in ['.jpg', '.jpeg']:
            return send_file(media_path, mimetype='image/jpeg')
        else:
            # For RAW files, generate preview
            preview_path = preview_gen.generate_preview(media_path, is_image=True)
            if not preview_path or not os.path.exists(preview_path):
                return jsonify({'error': 'internal_error', 'message': 'Failed to generate preview'}), 500
            return send_file(preview_path, mimetype='image/jpeg')
    else:
        # For videos, return thumbnail as preview
        preview_path = preview_gen.generate_video_thumbnail(media_path)
        if not preview_path or not os.path.exists(preview_path):
            return jsonify({'error': 'internal_error', 'message': 'Failed to generate preview'}), 500
        return send_file(preview_path, mimetype='image/jpeg')


@media_bp.route('/media/<path:media_id>/thumbnail', methods=['GET'])
def get_thumbnail(media_id: str):
    """Get thumbnail image."""
    library_id, relative_path = _parse_media_id(media_id)
    if not library_id or not relative_path:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    media_path, library, error_dict, status = _get_media_path(library_id, relative_path)
    if error_dict:
        return jsonify(error_dict), status
    
    # Determine media type
    ext = os.path.splitext(media_path)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
    is_image = ext in image_exts
    
    # Generate thumbnail
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    preview_gen = PreviewGenerator(config.thumbnail_cache_root)
    
    if is_image:
        ext = os.path.splitext(media_path)[1].lower()
        # For JPEGs, serve directly without generating thumbnail (faster)
        if ext in ['.jpg', '.jpeg']:
            # Check file size - if small enough, serve directly
            file_size = os.path.getsize(media_path)
            if file_size < 5 * 1024 * 1024:  # Less than 5MB, serve directly
                return send_file(media_path, mimetype='image/jpeg')
            # Otherwise generate thumbnail
            thumbnail_path = preview_gen.generate_image_thumbnail(media_path)
            if thumbnail_path and os.path.exists(thumbnail_path):
                return send_file(thumbnail_path, mimetype='image/jpeg')
            # Fallback to original if thumbnail generation fails
            return send_file(media_path, mimetype='image/jpeg')
        else:
            # For RAW and other formats, generate thumbnail
            thumbnail_path = preview_gen.generate_image_thumbnail(media_path)
            if not thumbnail_path or not os.path.exists(thumbnail_path):
                return jsonify({'error': 'internal_error', 'message': 'Failed to generate thumbnail'}), 500
            return send_file(thumbnail_path, mimetype='image/jpeg')
    else:
        thumbnail_path = preview_gen.generate_video_thumbnail(media_path)
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            return jsonify({'error': 'internal_error', 'message': 'Failed to generate thumbnail'}), 500
        return send_file(thumbnail_path, mimetype='image/jpeg')


@media_bp.route('/media/<path:media_id>/download', methods=['GET'])
def download_media(media_id: str):
    """Download original media file."""
    library_id, relative_path = _parse_media_id(media_id)
    if not library_id or not relative_path:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    media_path, library, error_dict, status = _get_media_path(library_id, relative_path)
    if error_dict:
        return jsonify(error_dict), status
    
    return send_file(media_path, as_attachment=True)


@media_bp.route('/media/<path:media_id>', methods=['PATCH'])
def update_media(media_id: str):
    """Update media metadata."""
    library_id, relative_path = _parse_media_id(media_id)
    if not library_id or not relative_path:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    media_path, library, error_dict, status = _get_media_path(library_id, relative_path)
    if error_dict:
        return jsonify(error_dict), status
    
    # Validate request body
    try:
        update_data = MediaUpdateRequest(**request.get_json() or {})
    except ValidationError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    
    # Determine media type
    ext = os.path.splitext(media_path)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
    is_image = ext in image_exts
    
    # Convert to dict, excluding None values
    metadata = update_data.model_dump(exclude_none=True)
    
    # Check if we should mark as reviewed when saving
    mark_reviewed = request.get_json().get('markReviewed', False) if request.get_json() else False
    if mark_reviewed:
        metadata['reviewStatus'] = 'reviewed'
    
    # Geocode location if locationName is provided and locationCoords is not
    if 'locationName' in metadata and 'locationCoords' not in metadata:
        config = current_app.config.get('PHOTOMEDIT_CONFIG')
        geocoding = GeocodingService(config)
        coords = geocoding.geocode(metadata['locationName'])
        if coords:
            metadata['locationCoords'] = coords
    
    # Write metadata
    success = MetadataWriter.write_metadata(media_path, metadata, is_image)
    if not success:
        return jsonify({'error': 'metadata_write_failed', 'message': 'Failed to write metadata'}), 500
    
    return jsonify({'message': 'Metadata updated successfully'}), 200


@media_bp.route('/media/<path:media_id>/reject', methods=['POST'])
def reject_media(media_id: str):
    """Move media file to rejected folder."""
    library_id, relative_path = _parse_media_id(media_id)
    if not library_id or not relative_path:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    media_path, library, error_dict, status = _get_media_path(library_id, relative_path)
    if error_dict:
        return jsonify(error_dict), status
    
    try:
        import shutil
        from pathlib import Path
        
        # Get the library root path
        root_path = Path(library['rootPath'])
        
        # Create .rejected folder in library root if it doesn't exist
        rejected_folder = root_path / '.rejected'
        rejected_folder.mkdir(exist_ok=True)
        
        # Get the source file path
        source_path = Path(media_path)
        
        # Determine destination path in .rejected folder
        # Preserve folder structure by including parent folder name
        parent_folder = source_path.parent.name if source_path.parent != root_path else ''
        if parent_folder:
            dest_folder = rejected_folder / parent_folder
            dest_folder.mkdir(exist_ok=True)
            dest_path = dest_folder / source_path.name
        else:
            dest_path = rejected_folder / source_path.name
        
        # Move the file
        shutil.move(str(source_path), str(dest_path))
        
        # Also move sidecar file if it exists
        sidecar_path = source_path.with_suffix(source_path.suffix + '.xmp')
        if sidecar_path.exists():
            dest_sidecar = dest_path.with_suffix(dest_path.suffix + '.xmp')
            shutil.move(str(sidecar_path), str(dest_sidecar))
        
        return jsonify({'message': 'Media file moved to rejected folder'}), 200
        
    except Exception as e:
        import logging
        logging.error(f"Failed to reject media: {e}")
        return jsonify({'error': 'internal_error', 'message': f'Failed to move file: {str(e)}'}), 500


@media_bp.route('/media/<path:media_id>/navigate', methods=['GET'])
def navigate_media(media_id: str):
    """Navigate to next/previous media."""
    library_id, relative_path = _parse_media_id(media_id)
    if not library_id or not relative_path:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    media_path, library, error_dict, status = _get_media_path(library_id, relative_path)
    if error_dict:
        return jsonify(error_dict), status
    
    # Validate query parameters
    try:
        query = NavigateQuery(**request.args)
    except ValidationError as e:
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400
    
    # Find next/previous
    next_relative_path = MediaNavigator.find_next_previous(
        library['rootPath'],
        relative_path,
        query.direction,
        query.reviewStatus
    )
    
    next_id = None
    if next_relative_path:
        next_id = f"{library_id}|{next_relative_path}"
    
    return jsonify({
        'currentId': media_id,
        'direction': query.direction,
        'nextId': next_id
    }), 200

