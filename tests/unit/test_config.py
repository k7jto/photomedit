"""Unit tests for configuration loader."""
import pytest
import tempfile
import os
from backend.config.loader import Config


def test_config_loading():
    """Test basic configuration loading."""
    config_content = """
server:
  port: 4750
  jwtSecret: "test-secret"

auth:
  enabled: true
  users: []

libraries:
  - id: "lib1"
    name: "Library 1"
    rootPath: "/tmp/test"

thumbnailCacheRoot: "/tmp/thumbnails"

logging:
  level: "INFO"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_path = f.name
    
    try:
        config = Config(config_path)
        assert config.port == 4750
        assert config.jwt_secret == "test-secret"
        assert config.auth_enabled is True
        assert len(config.libraries) == 1
        assert config.get_library("lib1") is not None
        assert config.get_library("nonexistent") is None
    finally:
        os.unlink(config_path)


def test_config_missing_libraries():
    """Test that missing libraries raises error."""
    config_content = """
server:
  port: 4750
  jwtSecret: "test"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_path = f.name
    
    try:
        with pytest.raises(ValueError, match="library"):
            Config(config_path)
    finally:
        os.unlink(config_path)

