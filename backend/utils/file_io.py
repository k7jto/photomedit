"""File I/O utilities with atomic writes."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional


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

