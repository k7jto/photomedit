"""Download routes per upload-download.md specification."""
from flask import Blueprint, request, jsonify, send_file, current_app
from backend.config.loader import Config
from backend.libraries.filesystem import scan_media_files
from backend.media.metadata_reader import MetadataReader
from backend.utils.sidecar import get_sidecar_path, sidecar_exists
from backend.security.sanitizer import PathSanitizer
import os
import zipfile
import tempfile
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

download_bp = Blueprint('download', __name__)


def generate_contents_txt(media_items: list, library_root: str) -> str:
    """Generate contents.txt file content."""
    lines = ['Path\tFileName\tReviewed\tEventDate\tSubject\tPeople\tLocation\tNotes']
    
    for item in media_items:
        metadata = item.get('metadata', {})
        relative_path = item['relativePath']
        
        # Extract folder path and filename
        path_parts = relative_path.split('/')
        filename = path_parts[-1]
        folder_path = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ''
        
        # Get metadata fields
        reviewed = 'Yes' if metadata.get('reviewStatus') == 'reviewed' else 'No'
        event_date = metadata.get('eventDate', '')
        if event_date:
            # Format date as YYYY-MM-DD if possible
            try:
                from datetime import datetime
                if isinstance(event_date, str):
                    # Try to parse and format
                    dt = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                    event_date = dt.strftime('%Y-%m-%d')
            except:
                pass  # Use as-is if parsing fails
        
        subject = metadata.get('subject', '')
        people = '; '.join(metadata.get('people', [])) if metadata.get('people') else ''
        location = metadata.get('locationName', '')
        notes = metadata.get('notes', '')
        
        # Escape tabs in text fields
        subject = subject.replace('\t', ' ')
        people = people.replace('\t', ' ')
        location = location.replace('\t', ' ')
        notes = notes.replace('\t', ' ')
        
        line = f"{folder_path}\t{filename}\t{reviewed}\t{event_date}\t{subject}\t{people}\t{location}\t{notes}"
        lines.append(line)
    
    return '\n'.join(lines)


@download_bp.route('/download', methods=['POST'])
def download_media():
    """Download media files as ZIP with sidecars and contents.txt."""
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'validation_error', 'message': 'Request body required'}), 400
    
    library_id = data.get('libraryId')
    scope = data.get('scope')  # 'all' or 'reviewed'
    folder = data.get('folder', '')  # Optional folder path
    
    if not library_id:
        return jsonify({'error': 'validation_error', 'message': 'libraryId is required'}), 400
    
    if scope not in ['all', 'reviewed']:
        return jsonify({'error': 'validation_error', 'message': 'scope must be "all" or "reviewed"'}), 400
    
    # Get library
    library = config.get_library(library_id)
    if not library:
        return jsonify({'error': 'not_found', 'message': 'Library not found'}), 404
    
    # Validate folder path if provided
    if folder:
        is_valid, resolved_folder, error = PathSanitizer.sanitize_path(library['rootPath'], folder)
        if not is_valid:
            return jsonify({'error': 'validation_error', 'message': error}), 400
        search_path = folder
    else:
        search_path = ''
    
    # Scan media files
    try:
        media_files = scan_media_files(library['rootPath'], search_path)
    except Exception as e:
        logger.error(f"Failed to scan media files: {e}")
        return jsonify({'error': 'internal_error', 'message': 'Failed to scan media files'}), 500
    
    # Filter by review status and collect metadata
    media_items = []
    total_size = 0
    
    for mf in media_files:
        file_path = mf['path']
        
        # Read metadata
        try:
            metadata = MetadataReader.read_logical_metadata(file_path)
        except Exception as e:
            logger.warning(f"Failed to read metadata for {file_path}: {e}")
            metadata = {}
        
        # Apply review status filter
        review_status = metadata.get('reviewStatus', 'unreviewed')
        if scope == 'reviewed' and review_status != 'reviewed':
            continue
        
        # Get file size
        try:
            file_size = os.path.getsize(file_path)
            total_size += file_size
            
            # Add sidecar size if it exists
            sidecar_path = get_sidecar_path(file_path)
            if os.path.exists(sidecar_path):
                total_size += os.path.getsize(sidecar_path)
        except Exception as e:
            logger.warning(f"Failed to get size for {file_path}: {e}")
            continue
        
        media_items.append({
            'path': file_path,
            'relativePath': mf['relativePath'],
            'metadata': metadata
        })
    
    # Check limits
    if len(media_items) > config.max_download_files:
        return jsonify({
            'error': 'validation_error',
            'message': f'Too many files (max {config.max_download_files})'
        }), 400
    
    if total_size > config.max_download_bytes:
        return jsonify({
            'error': 'validation_error',
            'message': f'Total size exceeds limit ({config.max_download_bytes / (1024*1024*1024):.1f} GB)'
        }), 400
    
    if len(media_items) == 0:
        return jsonify({'error': 'validation_error', 'message': 'No files found matching criteria'}), 400
    
    # Create ZIP file
    try:
        # Create temp file for ZIP
        zip_fd, zip_path = tempfile.mkstemp(suffix='.zip')
        os.close(zip_fd)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add media files and sidecars
            for item in media_items:
                file_path = item['path']
                relative_path = item['relativePath']
                
                # Add media file
                zipf.write(file_path, relative_path)
                
                # Add sidecar if it exists
                sidecar_path = get_sidecar_path(file_path)
                if os.path.exists(sidecar_path):
                    sidecar_relative = get_sidecar_path(relative_path)
                    zipf.write(sidecar_path, sidecar_relative)
            
            # Generate and add contents.txt
            contents_text = generate_contents_txt(media_items, library['rootPath'])
            zipf.writestr('contents.txt', contents_text)
        
        # Generate download filename
        scope_str = 'reviewed' if scope == 'reviewed' else 'all'
        folder_str = os.path.basename(folder) if folder else library_id
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        zip_filename = f"{folder_str}-{scope_str}-{timestamp}.zip"
        
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
        
    except Exception as e:
        logger.error(f"Failed to create ZIP: {e}")
        # Clean up temp file if it exists
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except:
                pass
        return jsonify({'error': 'internal_error', 'message': 'Failed to create download archive'}), 500

