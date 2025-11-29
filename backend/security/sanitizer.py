"""Path sanitization utilities."""
import os
from pathlib import Path
from typing import Tuple, Optional


class PathSanitizer:
    """Sanitize and validate file paths."""
    
    @staticmethod
    def sanitize_path(root_path: str, relative_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Sanitize and resolve a relative path against a root.
        
        Returns:
            (is_valid, resolved_path, error_message)
        """
        try:
            # Reject absolute paths
            if os.path.isabs(relative_path):
                return False, None, "Absolute paths are not allowed"
            
            # Reject paths with '..' components
            if '..' in relative_path:
                return False, None, "Path traversal ('..') is not allowed"
            
            # Normalize the path
            normalized = os.path.normpath(relative_path)
            
            # Check again for '..' after normalization
            if '..' in normalized or normalized.startswith('/'):
                return False, None, "Invalid path"
            
            # Resolve against root
            root = Path(root_path).resolve()
            resolved = (root / normalized).resolve()
            
            # Ensure resolved path is still within root
            try:
                resolved.relative_to(root)
            except ValueError:
                return False, None, "Path escapes library root"
            
            # Check for symlinks that escape root
            if resolved.is_symlink():
                target = resolved.readlink()
                if target.is_absolute():
                    try:
                        target.resolve().relative_to(root)
                    except ValueError:
                        return False, None, "Symlink escapes library root"
            
            return True, str(resolved), None
            
        except Exception as e:
            return False, None, f"Path validation error: {str(e)}"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize a filename by removing dangerous characters."""
        # Remove path separators and dangerous characters
        dangerous = ['/', '\\', '..', '\x00']
        sanitized = filename
        for char in dangerous:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250] + ext
        
        return sanitized

