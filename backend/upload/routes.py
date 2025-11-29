"""Upload routes."""
from flask import Blueprint, request, jsonify, current_app
from backend.config.loader import Config
from backend.security.sanitizer import PathSanitizer
import os
import magic
from werkzeug.utils import secure_filename


upload_bp = Blueprint('upload', __name__)

# Allowed MIME types
ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/tiff', 'image/x-tiff',
    'image/x-canon-cr2', 'image/x-canon-cr3', 'image/x-olympus-orf',
    'image/x-nikon-nef', 'image/x-fuji-raf', 'image/x-sony-arw',
    'image/x-adobe-dng'
}

ALLOWED_VIDEO_TYPES = {
    'video/mp4', 'video/quicktime', 'video/x-m4v', 'video/x-msvideo'
}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


def validate_file_type(file_content: bytes) -> tuple:
    """Validate file type using magic bytes."""
    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(file_content)
    
    if file_type in ALLOWED_IMAGE_TYPES:
        return True, 'image'
    elif file_type in ALLOWED_VIDEO_TYPES:
        return True, 'video'
    else:
        return False, None


@upload_bp.route('/libraries/<library_id>/upload', methods=['POST'])
def upload_files(library_id: str):
    """Upload media files to a library."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    library = config.get_library(library_id)
    if not library:
        return jsonify({'error': 'not_found', 'message': 'Library not found'}), 404
    
    # Get form data
    target_folder = request.form.get('targetFolder', '')
    batch_name = request.form.get('batchName', '')
    
    # Validate target folder path
    is_valid, resolved_folder, error = PathSanitizer.sanitize_path(library['rootPath'], target_folder)
    if not is_valid:
        return jsonify({'error': 'validation_error', 'message': error}), 400
    
    # Ensure target folder exists
    os.makedirs(resolved_folder, exist_ok=True)
    
    # Process uploaded files
    uploaded = []
    errors = []
    
    if 'files' not in request.files:
        return jsonify({'error': 'validation_error', 'message': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    for file in files:
        if not file.filename:
            continue
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            errors.append({
                'filename': file.filename,
                'error': 'File size exceeds maximum (500MB)'
            })
            continue
        
        # Read file content for validation
        file_content = file.read()
        file.seek(0)
        
        # Validate file type
        is_valid_type, media_type = validate_file_type(file_content)
        if not is_valid_type:
            errors.append({
                'filename': file.filename,
                'error': 'File type not supported'
            })
            continue
        
        # Sanitize filename
        sanitized_filename = PathSanitizer.sanitize_filename(file.filename)
        if not sanitized_filename:
            errors.append({
                'filename': file.filename,
                'error': 'Invalid filename'
            })
            continue
        
        # Determine target path
        target_path = os.path.join(resolved_folder, sanitized_filename)
        
        # Check if file already exists
        if os.path.exists(target_path):
            errors.append({
                'filename': file.filename,
                'error': 'File already exists'
            })
            continue
        
        # Save file
        try:
            file.save(target_path)
            
            # Get relative path
            relative_path = os.path.relpath(target_path, library['rootPath']).replace(os.sep, '/')
            media_id = f"{library_id}|{relative_path}"
            
            uploaded.append({
                'filename': sanitized_filename,
                'relativePath': relative_path,
                'mediaId': media_id
            })
        except Exception as e:
            errors.append({
                'filename': file.filename,
                'error': f'Failed to save file: {str(e)}'
            })
    
    return jsonify({
        'uploaded': uploaded,
        'errors': errors
    }), 200

