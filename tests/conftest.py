"""Pytest configuration and fixtures."""
import pytest
import tempfile
import os
import shutil
from backend.app import create_app
from backend.config.loader import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample configuration file."""
    config_content = f"""
server:
  port: 4750
  host: "0.0.0.0"
  jwtSecret: "test-secret-key"

auth:
  enabled: true
  users:
    - username: "testuser"
      passwordHash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y5"

libraries:
  - id: "testlib"
    name: "Test Library"
    rootPath: "{temp_dir}/photos"

thumbnailCacheRoot: "{temp_dir}/thumbnails"

geocoding:
  provider: "nominatim"
  enabled: false
  userAgent: "PhotoMedit-Test/1.0"
  rateLimit: 1.0

logging:
  level: "DEBUG"
"""
    config_path = os.path.join(temp_dir, 'config.yaml')
    with open(config_path, 'w') as f:
        f.write(config_content)
    return config_path


@pytest.fixture
def app(sample_config):
    """Create Flask app for testing."""
    app = create_app(sample_config)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_token(client):
    """Get authentication token."""
    # Note: In real tests, you'd use bcrypt to generate proper hashes
    # For now, this is a placeholder
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    if response.status_code == 200:
        return response.json.get('token')
    return None

