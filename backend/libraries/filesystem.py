"""Filesystem utilities for library browsing."""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.security.sanitizer import PathSanitizer


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
        return folders
    
    try:
        folder_path = Path(resolved_path)
        if not folder_path.exists() or not folder_path.is_dir():
            return folders
        
        # Scan directory
        for item in folder_path.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != '.rejected':
                item_relative = os.path.relpath(item, root_path)
                
                # Check if it has children (non-hidden subdirectories)
                has_children = any(
                    child.is_dir() and not child.name.startswith('.')
                    for child in item.iterdir()
                )
                
                folders.append({
                    'id': item_relative.replace(os.sep, '/'),
                    'name': item.name,
                    'relativePath': item_relative.replace(os.sep, '/'),
                    'hasChildren': has_children
                })
        
        # Sort by name
        folders.sort(key=lambda x: x['name'].lower())
        
    except Exception:
        pass
    
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
        return media_files
    
    try:
        folder_path = Path(resolved_path)
        if not folder_path.exists() or not folder_path.is_dir():
            return media_files
        
        # Supported extensions
        image_extensions = {'.jpg', '.jpeg', '.orf', '.nef', '.cr2', '.cr3', '.raf', '.arw', '.dng', '.tif', '.tiff'}
        video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
        
        for item in folder_path.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                ext = item.suffix.lower()
                if ext in image_extensions or ext in video_extensions:
                    item_relative = os.path.relpath(item, root_path)
                    media_files.append({
                        'path': str(item),
                        'relativePath': item_relative.replace(os.sep, '/'),
                        'filename': item.name,
                        'extension': ext
                    })
        
        # Sort by filename
        media_files.sort(key=lambda x: x['filename'].lower())
        
    except Exception:
        pass
    
    return media_files

