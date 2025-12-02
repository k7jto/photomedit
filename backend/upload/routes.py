"""Upload routes per upload-download.md specification."""
from flask import Blueprint, request, jsonify, current_app, g
from backend.config.loader import Config
from backend.security.sanitizer import PathSanitizer
from backend.media.metadata_reader import MetadataReader
from backend.database.log_service import LogService
from backend.utils.file_io import create_directory_with_permissions
from flask import request as flask_request
import os
import re
import magic
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)


def sanitize_upload_name(name: str) -> str:
    """Sanitize upload name for directory creation."""
    # Lowercase
    sanitized = name.lower()
    # Replace spaces with hyphens
    sanitized = sanitized.replace(' ', '-')
    # Remove unsafe characters (keep alphanumeric, hyphens, underscores)
    sanitized = re.sub(r'[^a-z0-9_-]', '', sanitized)
    # Remove leading/trailing hyphens and underscores
    sanitized = sanitized.strip('-_')
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    # Ensure not empty
    if not sanitized:
        sanitized = 'upload'
    return sanitized


def get_unique_filename(directory: str, filename: str) -> str:
    """Get a unique filename, appending numeric suffix if needed."""
    # Ensure directory exists
    if not os.path.exists(directory):
        raise ValueError(f"Directory does not exist: {directory}")
    if not os.path.isdir(directory):
        raise ValueError(f"Path is not a directory: {directory}")
    
    base_path = os.path.join(directory, filename)
    if not os.path.exists(base_path):
        return filename
    
    # Split name and extension
    name, ext = os.path.splitext(filename)
    counter = 1
    
    while True:
        new_filename = f"{name}-{counter}{ext}"
        new_path = os.path.join(directory, new_filename)
        if not os.path.exists(new_path):
            return new_filename
        counter += 1
        if counter > 10000:  # Safety limit
            raise ValueError("Too many filename conflicts")


def validate_file_type_binary(file_content: bytes) -> tuple:
    """Validate file type using magic bytes (binary signature)."""
    if len(file_content) < 4:
        return False, None
    
    # Use python-magic for binary detection
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file_content[:8192])  # Peek at first 8KB
    except Exception as e:
        logger.error(f"Magic detection failed: {e}")
        return False, None
    
    # Allowed image types
    image_types = {
        'image/jpeg', 'image/jpg', 'image/tiff', 'image/x-tiff',
        'image/x-canon-cr2', 'image/x-canon-cr3', 'image/x-olympus-orf',
        'image/x-nikon-nef', 'image/x-fuji-raf', 'image/x-sony-arw',
        'image/x-adobe-dng', 'image/x-panasonic-rw2'
    }
    
    # Allowed video types
    video_types = {
        'video/mp4', 'video/quicktime', 'video/x-m4v'
    }
    
    if file_type in image_types:
        return True, 'image'
    elif file_type in video_types:
        return True, 'video'
    else:
        return False, None


@upload_bp.route('/upload', methods=['POST'])
def upload_files():
    """Upload media files to uploadRoot with batch naming, or directly to a library folder."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    # Get form data
    upload_name = request.form.get('uploadName', '').strip()
    library_id = request.form.get('libraryId', '').strip()
    folder = request.form.get('folder', '').strip()
    
    logger.info(f"Upload request: uploadName={upload_name}, libraryId={library_id}, folder={folder}")
    
    # Determine target directory
    if library_id:
        # Uploading to a library
        library = config.get_library(library_id)
        if not library:
            logger.error(f"Library not found: {library_id}")
            user = getattr(g, 'current_user', None) or getattr(request, 'current_user', None)
            LogService.log(
                level='WARNING',
                message=f"Upload failed: Library not found: {library_id}",
                logger_name='upload',
                user=user,
                ip_address=flask_request.remote_addr,
                details={'libraryId': library_id, 'uploadName': upload_name}
            )
            return jsonify({'error': 'not_found', 'message': f'Library not found: {library_id}'}), 404
        
        if folder:
            # Upload directly to specified library folder
            is_valid, resolved_path, error = PathSanitizer.sanitize_path(library['rootPath'], folder)
            if not is_valid:
                return jsonify({'error': 'validation_error', 'message': error}), 400
            
            # Ensure the target folder exists
            if not os.path.exists(resolved_path):
                try:
                    if not create_directory_with_permissions(resolved_path):
                        logger.error(f"Failed to create target folder: {resolved_path}")
                        return jsonify({'error': 'internal_error', 'message': 'Failed to create target folder'}), 500
                except Exception as e:
                    logger.error(f"Failed to create target folder: {e}", exc_info=True)
                    return jsonify({'error': 'internal_error', 'message': 'Failed to create target folder'}), 500
            elif not os.path.isdir(resolved_path):
                return jsonify({'error': 'validation_error', 'message': 'Target path exists but is not a directory'}), 400
            
            batch_path = resolved_path
            target_root = library['rootPath']
        else:
            # Uploading to library root - create folder from upload name
            if not upload_name:
                return jsonify({'error': 'validation_error', 'message': 'Upload name is required to create a folder in the library root'}), 400
            
            if len(upload_name) > 100:
                return jsonify({'error': 'validation_error', 'message': 'uploadName too long (max 100 characters)'}), 400
            
            # Sanitize upload name and create folder in library root
            sanitized_name = sanitize_upload_name(upload_name)
            new_folder_path = os.path.join(library['rootPath'], sanitized_name)
            
            # Verify library root path exists and is accessible
            logger.info(f"Library root path: {library['rootPath']}")
            logger.info(f"Library root exists: {os.path.exists(library['rootPath'])}")
            logger.info(f"Library root is dir: {os.path.isdir(library['rootPath']) if os.path.exists(library['rootPath']) else 'N/A'}")
            logger.info(f"Library root readable: {os.access(library['rootPath'], os.R_OK) if os.path.exists(library['rootPath']) else 'N/A'}")
            logger.info(f"Library root writable: {os.access(library['rootPath'], os.W_OK) if os.path.exists(library['rootPath']) else 'N/A'}")
            
            # Check if it's a mount point
            try:
                import stat
                root_stat = os.stat(library['rootPath'])
                logger.info(f"Library root device: {root_stat.st_dev}")
                # Check parent to see if it's on a different device (mount point)
                parent_path = os.path.dirname(library['rootPath'])
                if os.path.exists(parent_path):
                    parent_stat = os.stat(parent_path)
                    is_mount = (root_stat.st_dev != parent_stat.st_dev)
                    logger.info(f"Library root appears to be mount point: {is_mount}")
            except Exception as e:
                logger.warning(f"Could not check mount status: {e}")
            
            logger.info(f"Creating upload folder: {new_folder_path} (library root: {library['rootPath']})")
            logger.info(f"Sanitized upload name: '{upload_name}' -> '{sanitized_name}'")
            
            try:
                if not create_directory_with_permissions(new_folder_path):
                    logger.error(f"Failed to create folder in library root: {new_folder_path}")
                    return jsonify({'error': 'internal_error', 'message': 'Failed to create folder'}), 500
                logger.info(f"Successfully created folder: {new_folder_path}")
                # Verify folder exists and get its actual location
                if os.path.exists(new_folder_path):
                    real_path = os.path.realpath(new_folder_path)
                    logger.info(f"Verified folder exists: {new_folder_path}")
                    logger.info(f"Real path (resolved symlinks): {real_path}")
                    # Check if it's actually on the mounted volume
                    try:
                        folder_stat = os.stat(new_folder_path)
                        root_stat = os.stat(library['rootPath'])
                        same_device = (folder_stat.st_dev == root_stat.st_dev)
                        logger.info(f"Folder is on same device as root: {same_device} (folder dev={folder_stat.st_dev}, root dev={root_stat.st_dev})")
                    except Exception as e:
                        logger.warning(f"Could not verify device: {e}")
                else:
                    logger.error(f"Folder creation reported success but folder does not exist: {new_folder_path}")
            except Exception as e:
                logger.error(f"Failed to create folder in library root: {e}", exc_info=True)
                return jsonify({'error': 'internal_error', 'message': 'Failed to create folder'}), 500
            
            batch_path = new_folder_path
            target_root = library['rootPath']
    else:
        # Default: upload to uploadRoot with batch naming (standalone upload page)
        if not upload_name:
            return jsonify({'error': 'validation_error', 'message': 'uploadName is required'}), 400
        
        if len(upload_name) > 100:
            return jsonify({'error': 'validation_error', 'message': 'uploadName too long (max 100 characters)'}), 400
        
        # Sanitize upload name and create batch directory
        sanitized_name = sanitize_upload_name(upload_name)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        batch_dir_name = f"{sanitized_name}-{timestamp}"
        batch_path = os.path.join(config.upload_root, batch_dir_name)
        target_root = config.upload_root
        
        try:
            if not create_directory_with_permissions(batch_path):
                logger.error(f"Failed to create batch directory: {batch_path}")
                return jsonify({'error': 'internal_error', 'message': 'Failed to create upload directory'}), 500
        except Exception as e:
            logger.error(f"Failed to create batch directory: {e}")
            return jsonify({'error': 'internal_error', 'message': 'Failed to create upload directory'}), 500
    
    # Verify batch_path exists and is a directory before processing files
    if not os.path.exists(batch_path):
        logger.error(f"Batch path does not exist: {batch_path}")
        return jsonify({'error': 'internal_error', 'message': 'Upload directory does not exist'}), 500
    
    if not os.path.isdir(batch_path):
        logger.error(f"Batch path is not a directory: {batch_path}")
        return jsonify({'error': 'internal_error', 'message': 'Upload path is not a directory'}), 500
    
    # Get files
    if 'files' not in request.files:
        return jsonify({'error': 'validation_error', 'message': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    if not files or len(files) == 0:
        return jsonify({'error': 'validation_error', 'message': 'No files provided'}), 400
    
    # Check file count limit
    if len(files) > config.max_upload_files:
        return jsonify({
            'error': 'validation_error',
            'message': f'Too many files (max {config.max_upload_files})'
        }), 400
    
    # Process files
    uploaded_files = []
    total_size = 0
    errors = []
    
    for file in files:
        if not file.filename:
            continue
        
        original_name = file.filename
        
        # Read file content for validation
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        # Check per-file size limit
        if file_size > config.max_upload_bytes_per_file:
            errors.append({
                'originalName': original_name,
                'status': 'error',
                'errorCode': 'FILE_TOO_LARGE',
                'errorMessage': f'File exceeds maximum size ({config.max_upload_bytes_per_file / (1024*1024):.0f} MB)'
            })
            continue
        
        # Check total size limit
        if total_size + file_size > config.max_upload_bytes_total:
            errors.append({
                'originalName': original_name,
                'status': 'error',
                'errorCode': 'TOTAL_SIZE_EXCEEDED',
                'errorMessage': 'Total upload size would exceed limit'
            })
            continue
        
        # Read first 8KB for binary validation
        peek_content = file.read(8192)
        file.seek(0)
        
        # Validate file type
        is_valid, media_type = validate_file_type_binary(peek_content)
        if not is_valid:
            errors.append({
                'originalName': original_name,
                'status': 'error',
                'errorCode': 'UNSUPPORTED_TYPE',
                'errorMessage': 'File type not supported (must be image or video)'
            })
            continue
        
        # Sanitize filename
        sanitized_filename = PathSanitizer.sanitize_filename(original_name)
        if not sanitized_filename:
            errors.append({
                'originalName': original_name,
                'status': 'error',
                'errorCode': 'INVALID_FILENAME',
                'errorMessage': 'Invalid filename'
            })
            continue
        
        # Get unique filename
        try:
            unique_filename = get_unique_filename(batch_path, sanitized_filename)
        except Exception as e:
            errors.append({
                'originalName': original_name,
                'status': 'error',
                'errorCode': 'FILENAME_CONFLICT',
                'errorMessage': f'Failed to resolve filename conflict: {str(e)}'
            })
            continue
        
        # Atomic write: write to temp file, then rename
        temp_filename = f"{unique_filename}.tmp"
        temp_path = os.path.join(batch_path, temp_filename)
        final_path = os.path.join(batch_path, unique_filename)
        
        try:
            # Write to temp file
            logger.debug(f"Writing file to temp path: {temp_path}")
            with open(temp_path, 'wb') as f:
                shutil.copyfileobj(file, f)
            
            # Verify file was written correctly
            if os.path.getsize(temp_path) != file_size:
                os.remove(temp_path)
                errors.append({
                    'originalName': original_name,
                    'status': 'error',
                    'errorCode': 'WRITE_FAILED',
                    'errorMessage': 'File size mismatch after write'
                })
                continue
            
            # Atomically rename
            os.rename(temp_path, final_path)
            logger.info(f"Successfully saved file '{original_name}' to '{final_path}'")
            
            # Detailed diagnostics for saved file
            if os.path.exists(final_path):
                file_size_actual = os.path.getsize(final_path)
                logger.info(f"✓ Verified file exists: {final_path} (size: {file_size_actual} bytes)")
                
                # Check device ID and mount status
                try:
                    file_stat = os.stat(final_path)
                    real_path = os.path.realpath(final_path)
                    logger.info(f"✓ File device ID: {file_stat.st_dev}, inode: {file_stat.st_ino}")
                    logger.info(f"✓ File real path (resolved): {real_path}")
                    
                    # If uploading to library, check if it's on the same device as library root
                    if library_id and library:
                        root_stat = os.stat(library['rootPath'])
                        same_device = (file_stat.st_dev == root_stat.st_dev)
                        logger.info(f"✓ File is on same device as library root: {same_device}")
                        logger.info(f"  - File device: {file_stat.st_dev}, Root device: {root_stat.st_dev}")
                        if not same_device:
                            logger.error(f"✗ WARNING: File is NOT on the same device as library root!")
                            logger.error(f"✗ This means the file is being written to a different filesystem!")
                            logger.error(f"✗ Library root: {library['rootPath']} (device {root_stat.st_dev})")
                            logger.error(f"✗ File location: {final_path} (device {file_stat.st_dev})")
                    
                    # Check parent directory device
                    parent_dir = os.path.dirname(final_path)
                    if os.path.exists(parent_dir):
                        parent_stat = os.stat(parent_dir)
                        is_mount = (file_stat.st_dev != parent_stat.st_dev)
                        logger.info(f"✓ Parent directory device: {parent_stat.st_dev}, is mount point: {is_mount}")
                except Exception as e:
                    logger.warning(f"Could not get file diagnostics: {e}")
            else:
                logger.error(f"✗ File save reported success but file does not exist: {final_path}")
            
            # Queue thumbnail generation in background
            try:
                from backend.media.thumbnail_worker import queue_thumbnail_generation
                from pathlib import Path
                config = current_app.config.get('PHOTOMEDIT_CONFIG')
                if config:
                    # Determine if it's an image or video
                    ext = Path(final_path).suffix.lower()
                    image_exts = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
                    is_image = ext in image_exts
                    queue_thumbnail_generation(final_path, is_image=is_image, thumbnail_cache_root=config.thumbnail_cache_root)
                    logger.debug(f"Queued thumbnail generation for {final_path}")
            except Exception as e:
                logger.warning(f"Failed to queue thumbnail generation: {e}")
            
            # Post-upload: import metadata
            try:
                # Read metadata (this will discover sidecar if present)
                logical_metadata = MetadataReader.read_logical_metadata(final_path)
                # Metadata is now available for the UI
            except Exception as e:
                logger.warning(f"Failed to import metadata for {final_path}: {e}")
                # Continue anyway - file is uploaded successfully
            
            # Calculate relative path from target root
            relative_path = os.path.relpath(final_path, target_root).replace(os.sep, '/')
            
            uploaded_files.append({
                'originalName': original_name,
                'storedName': unique_filename,
                'relativePath': relative_path,
                'sizeBytes': file_size,
                'status': 'ok'
            })
            
            total_size += file_size
            
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            logger.error(f"Failed to save file {original_name}: {e}")
            errors.append({
                'originalName': original_name,
                'status': 'error',
                'errorCode': 'WRITE_FAILED',
                'errorMessage': f'Failed to save file: {str(e)}'
            })
    
    # Build response
    if library_id:
        if folder:
            response = {
                'uploadId': f"{library_id}|{folder}",
                'uploadName': upload_name or 'Direct upload',
                'targetDirectory': folder,
                'libraryId': library_id,
                'files': uploaded_files + errors
            }
        else:
            # Created new folder in library root
            folder_name = sanitize_upload_name(upload_name)
            logger.info(f"Upload complete: {len(uploaded_files)} files uploaded to library root folder: {folder_name}")
            response = {
                'uploadId': f"{library_id}|{folder_name}",
                'uploadName': upload_name,
                'targetDirectory': folder_name,
                'targetPath': os.path.join(library['rootPath'], folder_name),  # Add full path for debugging
                'libraryId': library_id,
                'files': uploaded_files + errors
            }
    else:
        response = {
            'uploadId': batch_dir_name,
            'uploadName': upload_name,
            'targetDirectory': batch_dir_name,
            'files': uploaded_files + errors
        }
    
    # Log upload result
    user = getattr(g, 'current_user', None) or getattr(request, 'current_user', None)
    success_count = len(uploaded_files)
    error_count = len(errors)
    LogService.log(
        level='INFO' if error_count == 0 else 'WARNING',
        message=f"Upload completed: {success_count} successful, {error_count} failed",
        logger_name='upload',
        user=user,
        ip_address=flask_request.remote_addr,
        details={
            'uploadName': upload_name,
            'libraryId': library_id or None,
            'folder': folder or None,
            'successCount': success_count,
            'errorCount': error_count,
            'targetDirectory': response.get('targetDirectory')
        }
    )
    
    return jsonify(response), 200
