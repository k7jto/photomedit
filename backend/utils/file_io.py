"""File I/O utilities with atomic writes."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import stat
import logging

logger = logging.getLogger(__name__)


def atomic_write(file_path: str, content: bytes) -> bool:
    """
    Atomically write content to a file.
    
    Returns True on success, False on failure.
    """
    try:
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode='wb',
            dir=file_path_obj.parent,
            delete=False,
            prefix='.tmp_',
            suffix=file_path_obj.suffix
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # Validate (basic check - file exists and is readable)
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) != len(content):
            os.unlink(tmp_path)
            return False
        
        # Atomically replace original
        shutil.move(tmp_path, file_path)
        return True
        
    except Exception:
        # Clean up temp file if it exists
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return False


def read_file_safe(file_path: str) -> Optional[bytes]:
    """Safely read a file, returning None on error."""
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception:
        return None


def create_directory_with_permissions(dir_path: str, mode: int = 0o755) -> bool:
    """
    Create a directory with proper permissions, inheriting ownership from parent.
    
    Args:
        dir_path: Path to the directory to create
        mode: Permission mode (default 0o755 = rwxr-xr-x)
    
    Returns:
        True on success, False on failure
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(dir_path, exist_ok=True)
        
        # Get parent directory to inherit ownership
        parent_path = os.path.dirname(dir_path)
        if not parent_path or parent_path == dir_path:
            # If no parent (root), just set permissions
            os.chmod(dir_path, mode)
            return True
        
        try:
            # Get ownership from parent directory
            parent_stat = os.stat(parent_path)
            uid = parent_stat.st_uid
            gid = parent_stat.st_gid
            
            # Set ownership to match parent
            os.chown(dir_path, uid, gid)
        except (OSError, PermissionError) as e:
            # If we can't change ownership (e.g., not running as root), 
            # at least set permissions
            logger.warning(f"Could not set ownership for {dir_path}: {e}. Setting permissions only.")
        
        # Set permissions (readable/executable by all, writable by owner)
        os.chmod(dir_path, mode)
        
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path} with permissions: {e}")
        return False

