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
  adminUser:
    username: "admin"
    email: "admin@test.com"
    passwordHash: "$2b$12$test"
    isAdmin: true

libraries:
  - id: "lib1"
    name: "Library 1"
    rootPath: "/tmp/test"

thumbnailCacheRoot: "/tmp/thumbnails"
uploadRoot: "/tmp/uploads"

limits:
  maxUploadFiles: 500
  maxUploadBytesPerFile: 524288000
  maxUploadBytesTotal: 10737418240
  maxDownloadFiles: 10000
  maxDownloadBytes: 21474836480

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
        assert config.get_admin_user() is not None
        assert config.get_admin_user().get('username') == 'admin'
        assert config.get_admin_user().get('email') == 'admin@test.com'
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


def test_config_admin_user():
    """Test admin user configuration."""
    config_content = """
server:
  port: 4750
  jwtSecret: "test"

auth:
  enabled: true
  adminUser:
    username: "admin"
    email: "admin@test.com"
    passwordHash: "$2b$12$test"
    isAdmin: true

libraries:
  - id: "lib1"
    name: "Library 1"
    rootPath: "/tmp/test"

thumbnailCacheRoot: "/tmp/thumbnails"
uploadRoot: "/tmp/uploads"

limits:
  maxUploadFiles: 500
  maxUploadBytesPerFile: 524288000
  maxUploadBytesTotal: 10737418240
  maxDownloadFiles: 10000
  maxDownloadBytes: 21474836480

logging:
  level: "INFO"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_path = f.name
    
    try:
        config = Config(config_path)
        admin_user = config.get_admin_user()
        assert admin_user is not None
        assert admin_user.get('username') == 'admin'
        assert admin_user.get('email') == 'admin@test.com'
        assert admin_user.get('isAdmin') is True
    finally:
        os.unlink(config_path)
