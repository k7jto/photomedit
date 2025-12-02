"""Filesystem utilities for library browsing."""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.security.sanitizer import PathSanitizer

logger = logging.getLogger(__name__)


def scan_folder(root_path: str, relative_path: str = "") -> List[Dict[str, Any]]:
    """
    Scan a folder and return folder tree nodes.
    
    Returns list of folder nodes with:
    - id: libraryId|relativePath
    - name: folder name
    - relativePath: relative path from library root
    - hasChildren: boolean
    """
    folders = []
    
    # Resolve full path
    is_valid, resolved_path, error = PathSanitizer.sanitize_path(root_path, relative_path)
    if not is_valid:
        logger.warning(f"Invalid path for scanning: {relative_path} - {error}")
        return folders
    
    try:
        folder_path = Path(resolved_path)
        if not folder_path.exists():
            logger.warning(f"Path does not exist: {resolved_path}")
            return folders
        if not folder_path.is_dir():
            logger.warning(f"Path is not a directory: {resolved_path}")
            return folders
        
        logger.info(f"Scanning folder: {resolved_path} (root: {root_path}, relative: {relative_path})")
        
        # Diagnostic: Check if this is a mount point
        try:
            root_stat = os.stat(root_path)
            folder_stat = os.stat(resolved_path)
            is_same_device = (root_stat.st_dev == folder_stat.st_dev)
            logger.info(f"  Device check - root dev: {root_stat.st_dev}, folder dev: {folder_stat.st_dev}, same device: {is_same_device}")
            logger.info(f"  Real path: {os.path.realpath(resolved_path)}")
        except Exception as e:
            logger.warning(f"  Could not check device info: {e}")
        
        # Scan directory
        items_list = list(folder_path.iterdir())
        logger.info(f"Found {len(items_list)} items in {resolved_path}")
        
        # Log item types
        dirs = [item for item in items_list if item.is_dir()]
        files = [item for item in items_list if item.is_file()]
        logger.info(f"  Items breakdown: {len(dirs)} directories, {len(files)} files")
        
        # Hidden/system directories to exclude
        hidden_dirs = {
            '.rejected',
            '@eaDir',  # Synology thumbnail cache
            '@Recycle',  # Synology recycle bin
            '#recycle',  # Alternative recycle bin
            '.DS_Store',  # macOS metadata (though this is usually a file)
            'Thumbs.db',  # Windows thumbnail cache (usually a file)
            '.thumbnails',  # Linux thumbnail cache
            '.Trash',  # Linux trash
            '.Trash-1000',  # Linux user trash
        }
        
        for item in items_list:
            try:
                # Skip hidden files/dirs (starting with .) and system directories
                if (item.is_dir() and 
                    not item.name.startswith('.') and 
                    item.name not in hidden_dirs and
                    not item.name.startswith('@') and  # Skip all @ directories (Synology system dirs)
                    not item.name.startswith('#')):  # Skip all # directories (system dirs)
                    item_relative = os.path.relpath(item, root_path)
                    
                    # Check if it has children (non-hidden subdirectories)
                    try:
                        has_children = any(
                            child.is_dir() and not child.name.startswith('.')
                            for child in item.iterdir()
                        )
                    except (PermissionError, OSError) as e:
                        logger.warning(f"Cannot check children for {item}: {e}")
                        has_children = False
                    
                    folders.append({
                        'id': item_relative.replace(os.sep, '/'),
                        'name': item.name,
                        'relativePath': item_relative.replace(os.sep, '/'),
                        'hasChildren': has_children
                    })
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot access item {item} in {resolved_path}: {e}")
                continue
        
        # Sort by name
        folders.sort(key=lambda x: x['name'].lower())
        logger.info(f"Found {len(folders)} folders in {resolved_path}")
        if len(folders) > 0:
            logger.info(f"Folder names: {[f['name'] for f in folders[:10]]}")
        
    except Exception as e:
        logger.error(f"Error scanning folder {resolved_path}: {e}", exc_info=True)
    
    return folders


def scan_media_files(root_path: str, relative_path: str = "") -> List[Dict[str, Any]]:
    """
    Scan a folder for media files.
    
    Returns list of media file info.
    """
    media_files = []
    
    # Resolve full path
    is_valid, resolved_path, error = PathSanitizer.sanitize_path(root_path, relative_path)
    if not is_valid:
        logger.warning(f"Invalid path for media scanning: {relative_path} - {error}")
        return media_files
    
    try:
        folder_path = Path(resolved_path)
        if not folder_path.exists():
            logger.warning(f"Path does not exist for media scanning: {resolved_path}")
            return media_files
        if not folder_path.is_dir():
            logger.warning(f"Path is not a directory for media scanning: {resolved_path}")
            return media_files
        
        logger.debug(f"Scanning media files in: {resolved_path} (root: {root_path}, relative: {relative_path})")
        
        # Supported extensions
        image_extensions = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
        video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
        
        # Hidden/system files to exclude
        hidden_files = {
            '.DS_Store',  # macOS metadata
            'Thumbs.db',  # Windows thumbnail cache
            'desktop.ini',  # Windows folder settings
        }
        
        for item in folder_path.iterdir():
            try:
                if (item.is_file() and 
                    not item.name.startswith('.') and 
                    item.name not in hidden_files):
                    ext = item.suffix.lower()
                    if ext in image_extensions or ext in video_extensions:
                        item_relative = os.path.relpath(item, root_path)
                        media_files.append({
                            'path': str(item),
                            'relativePath': item_relative.replace(os.sep, '/'),
                            'filename': item.name,
                            'extension': ext
                        })
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot access file {item} in {resolved_path}: {e}")
                continue
        
        # Sort by filename
        media_files.sort(key=lambda x: x['filename'].lower())
        logger.debug(f"Found {len(media_files)} media files in {resolved_path}")
        
    except Exception as e:
        logger.error(f"Error scanning media files in {resolved_path}: {e}", exc_info=True)
    
    return media_files

