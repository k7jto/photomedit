"""Publish to DAM routes."""
from flask import Blueprint, request, jsonify, current_app
from backend.security.sanitizer import PathSanitizer
from backend.utils.publishing import (
    publish_file, publish_multiple, is_published, get_publish_info
)
import os

publish_bp = Blueprint('publish', __name__)


@publish_bp.route('/publish/config', methods=['GET'])
def get_publish_config():
    """Get DAM configuration for the frontend."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    return jsonify({
        'enabled': config.dam_enabled,
        'name': config.dam_name,
        'url': config.dam_url
    }), 200


@publish_bp.route('/publish', methods=['POST'])
def publish_media():
    """
    Publish one or more media files to DAM.
    
    Request body:
    {
        "mediaIds": ["library1|folder/image.jpg", ...],
        "preserveFolderStructure": true  // optional, default true
    }
    """
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    if not config.dam_enabled:
        return jsonify({'error': 'not_configured', 'message': 'DAM integration is not enabled'}), 400
    
    if not config.dam_folder_path:
        return jsonify({'error': 'not_configured', 'message': 'DAM folder path is not configured'}), 400
    
    data = request.get_json() or {}
    media_ids = data.get('mediaIds', [])
    preserve_structure = data.get('preserveFolderStructure', True)
    
    if not media_ids:
        return jsonify({'error': 'validation_error', 'message': 'No media IDs provided'}), 400
    
    # Get current user
    username = getattr(request, 'current_user', 'unknown')
    
    # Resolve media IDs to file paths
    source_paths = []
    errors = []
    
    for media_id in media_ids:
        if '|' not in media_id:
            errors.append({'mediaId': media_id, 'error': 'Invalid media ID format'})
            continue
        
        library_id, relative_path = media_id.split('|', 1)
        library = config.get_library(library_id)
        
        if not library:
            errors.append({'mediaId': media_id, 'error': 'Library not found'})
            continue
        
        is_valid, resolved_path, error = PathSanitizer.sanitize_path(library['rootPath'], relative_path)
        if not is_valid:
            errors.append({'mediaId': media_id, 'error': error})
            continue
        
        if not os.path.exists(resolved_path):
            errors.append({'mediaId': media_id, 'error': 'File not found'})
            continue
        
        source_paths.append(resolved_path)
    
    if not source_paths:
        return jsonify({
            'error': 'validation_error',
            'message': 'No valid files to publish',
            'errors': errors
        }), 400
    
    # Publish files
    result = publish_multiple(
        source_paths,
        config.dam_folder_path,
        config.dam_name,
        username
    )
    
    # Add any pre-validation errors
    if errors:
        result['errors'] = errors
    
    return jsonify(result), 200


@publish_bp.route('/publish/status/<path:media_id>', methods=['GET'])
def get_publish_status(media_id: str):
    """Check if a media file has been published."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    if '|' not in media_id:
        return jsonify({'error': 'validation_error', 'message': 'Invalid media ID format'}), 400
    
    library_id, relative_path = media_id.split('|', 1)
    library = config.get_library(library_id)
    
    if not library:
        return jsonify({'error': 'not_found', 'message': 'Library not found'}), 404
    
    is_valid, resolved_path, error = PathSanitizer.sanitize_path(library['rootPath'], relative_path)
    if not is_valid:
        return jsonify({'error': 'validation_error', 'message': error}), 400
    
    folder_path = os.path.dirname(resolved_path)
    filename = os.path.basename(resolved_path)
    
    publish_info = get_publish_info(folder_path, filename)
    
    if publish_info:
        return jsonify({
            'isPublished': True,
            'publishedAt': publish_info.get('publishedAt'),
            'publishedBy': publish_info.get('username'),
            'damName': publish_info.get('damName'),
            'damPath': publish_info.get('damPath')
        }), 200
    else:
        return jsonify({
            'isPublished': False
        }), 200



