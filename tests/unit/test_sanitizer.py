"""Unit tests for path sanitization."""
import pytest
import tempfile
import os
from backend.security.sanitizer import PathSanitizer


def test_sanitize_valid_path():
    """Test sanitization of valid paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        is_valid, resolved, error = PathSanitizer.sanitize_path(tmpdir, "subfolder/file.jpg")
        assert is_valid is True
        assert resolved is not None
        assert error is None
        assert tmpdir in resolved


def test_sanitize_absolute_path():
    """Test that absolute paths are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        is_valid, resolved, error = PathSanitizer.sanitize_path(tmpdir, "/absolute/path")
        assert is_valid is False
        assert resolved is None
        assert error is not None


def test_sanitize_path_traversal():
    """Test that path traversal is rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        is_valid, resolved, error = PathSanitizer.sanitize_path(tmpdir, "../../etc/passwd")
        assert is_valid is False
        assert resolved is None
        assert error is not None


def test_sanitize_filename():
    """Test filename sanitization."""
    # Test dangerous characters
    assert PathSanitizer.sanitize_filename("file/name.jpg") == "file_name.jpg"
    assert PathSanitizer.sanitize_filename("file\\name.jpg") == "file_name.jpg"
    assert PathSanitizer.sanitize_filename("file..name.jpg") == "file__name.jpg"
    
    # Test normal filename
    assert PathSanitizer.sanitize_filename("normal_file.jpg") == "normal_file.jpg"

