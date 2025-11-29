"""Sidecar file utilities."""
import os
from pathlib import Path
from typing import Optional


def get_sidecar_path(media_path: str) -> str:
    """Get the path to the XMP sidecar file for a media file."""
    base = os.path.splitext(media_path)[0]
    return f"{base}.xmp"


def sidecar_exists(media_path: str) -> bool:
    """Check if a sidecar file exists."""
    return os.path.exists(get_sidecar_path(media_path))


def read_sidecar(media_path: str) -> Optional[str]:
    """Read sidecar file content."""
    sidecar_path = get_sidecar_path(media_path)
    try:
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None


def write_sidecar(media_path: str, content: str) -> bool:
    """Write sidecar file content."""
    sidecar_path = get_sidecar_path(media_path)
    try:
        with open(sidecar_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False

