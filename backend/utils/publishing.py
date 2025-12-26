"""Publishing to DAM (Digital Asset Manager) utilities."""
import csv
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

PUBLISHED_FILENAME = 'published.csv'
CSV_FIELDS = ['filename', 'username', 'published_at', 'dam_name', 'dam_path']


def get_published_file_path(folder_path: str) -> str:
    """Get the path to the published.csv file in a folder."""
    return os.path.join(folder_path, PUBLISHED_FILENAME)


def read_published(folder_path: str) -> Dict[str, Dict]:
    """
    Read all published records from a folder's published.csv file.
    
    Returns a dict mapping filename -> publish data
    """
    published = {}
    csv_path = get_published_file_path(folder_path)
    
    if not os.path.exists(csv_path):
        return published
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get('filename', '')
                if filename:
                    published[filename] = {
                        'username': row.get('username', ''),
                        'publishedAt': row.get('published_at', ''),
                        'damName': row.get('dam_name', ''),
                        'damPath': row.get('dam_path', ''),
                        'isPublished': True
                    }
    except Exception as e:
        logger.error(f"Error reading published file {csv_path}: {e}")
    
    return published


def is_published(folder_path: str, filename: str) -> bool:
    """Check if a file has been published."""
    published = read_published(folder_path)
    return filename in published


def get_publish_info(folder_path: str, filename: str) -> Optional[Dict]:
    """Get publish info for a specific file."""
    published = read_published(folder_path)
    return published.get(filename)


def publish_file(
    source_path: str,
    dam_folder_path: str,
    dam_name: str,
    username: str,
    preserve_folder_structure: bool = True
) -> Dict:
    """
    Publish a file to the DAM folder.
    
    Args:
        source_path: Full path to the source file
        dam_folder_path: Root path of the DAM folder
        dam_name: Name of the DAM (for logging)
        username: User performing the publish
        preserve_folder_structure: If True, preserve relative folder structure
        
    Returns:
        Dict with 'success', 'message', and optionally 'dam_path'
    """
    try:
        source = Path(source_path)
        if not source.exists():
            return {'success': False, 'message': 'Source file not found'}
        
        filename = source.name
        folder_path = str(source.parent)
        
        # Determine destination path
        if preserve_folder_structure:
            # Try to preserve some folder structure
            # Use the parent folder name as a subdirectory in DAM
            parent_folder = source.parent.name
            dest_folder = Path(dam_folder_path) / parent_folder
        else:
            dest_folder = Path(dam_folder_path)
        
        # Create destination folder if needed
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_folder / filename
        
        # Check if file already exists in DAM
        if dest_path.exists():
            return {'success': False, 'message': f'File already exists in {dam_name}'}
        
        # Copy file to DAM
        shutil.copy2(str(source), str(dest_path))
        
        # Also copy sidecar XMP file if it exists
        sidecar_source = source.with_suffix(source.suffix + '.xmp')
        if sidecar_source.exists():
            sidecar_dest = dest_path.with_suffix(dest_path.suffix + '.xmp')
            shutil.copy2(str(sidecar_source), str(sidecar_dest))
            logger.info(f"Copied sidecar file to {sidecar_dest}")
        
        # Record in published.csv
        record_published(folder_path, filename, username, dam_name, str(dest_path))
        
        logger.info(f"Published {filename} to {dam_name} at {dest_path}")
        
        return {
            'success': True,
            'message': f'Published to {dam_name}',
            'dam_path': str(dest_path)
        }
        
    except PermissionError as e:
        logger.error(f"Permission denied publishing {source_path}: {e}")
        return {'success': False, 'message': 'Permission denied'}
    except Exception as e:
        logger.error(f"Error publishing {source_path}: {e}")
        return {'success': False, 'message': str(e)}


def record_published(
    folder_path: str,
    filename: str,
    username: str,
    dam_name: str,
    dam_path: str
) -> bool:
    """Record a file as published in the CSV."""
    csv_path = get_published_file_path(folder_path)
    records = []
    
    # Read existing records
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip if this file is already recorded (will be re-added with new data)
                    if row.get('filename') != filename:
                        records.append(row)
        except Exception as e:
            logger.error(f"Error reading published file {csv_path}: {e}")
    
    # Add new record
    records.append({
        'filename': filename,
        'username': username,
        'published_at': datetime.utcnow().isoformat() + 'Z',
        'dam_name': dam_name,
        'dam_path': dam_path
    })
    
    # Write back
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(records)
        return True
    except Exception as e:
        logger.error(f"Error writing published file {csv_path}: {e}")
        return False


def list_published_in_folder(folder_path: str) -> List[Dict]:
    """List all published files in a folder."""
    published = read_published(folder_path)
    return [
        {'filename': filename, **data}
        for filename, data in published.items()
    ]


def publish_multiple(
    source_paths: List[str],
    dam_folder_path: str,
    dam_name: str,
    username: str
) -> Dict:
    """
    Publish multiple files to DAM.
    
    Returns summary with 'published' count, 'failed' count, and 'results' list.
    """
    results = []
    published_count = 0
    failed_count = 0
    
    for source_path in source_paths:
        result = publish_file(source_path, dam_folder_path, dam_name, username)
        result['filename'] = os.path.basename(source_path)
        results.append(result)
        
        if result['success']:
            published_count += 1
        else:
            failed_count += 1
    
    return {
        'published': published_count,
        'failed': failed_count,
        'results': results
    }



