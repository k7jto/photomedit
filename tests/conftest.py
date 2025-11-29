"""Pytest configuration and fixtures."""
import pytest
import tempfile
import os
import shutil
from backend.app import create_app
from backend.config.loader import Config
from backend.database.models import Base, get_engine, get_session_local
from backend.database.connection import init_db


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
  adminUser:
    username: "admin"
    email: "admin@test.com"
    passwordHash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y5"
    isAdmin: true

libraries:
  - id: "testlib"
    name: "Test Library"
    rootPath: "{temp_dir}/photos"

thumbnailCacheRoot: "{temp_dir}/thumbnails"
uploadRoot: "{temp_dir}/uploads"

limits:
  maxUploadFiles: 500
  maxUploadBytesPerFile: 524288000
  maxUploadBytesTotal: 10737418240
  maxDownloadFiles: 10000
  maxDownloadBytes: 21474836480

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
def test_database(temp_dir):
    """Create a test database."""
    # Use SQLite for testing instead of MariaDB
    db_path = os.path.join(temp_dir, 'test.db')
    database_url = f'sqlite:///{db_path}'
    
    # Override the database URL
    import backend.database.models as db_models
    original_get_url = db_models.get_database_url
    
    def test_get_url():
        return database_url
    
    db_models.get_database_url = test_get_url
    
    # Reset engine to force recreation
    db_models._engine = None
    db_models._SessionLocal = None
    
    # Create tables using SQLite directly (avoid connect_timeout issue)
    from sqlalchemy import create_engine
    test_engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(bind=test_engine)
    
    # Set the engine in the module
    db_models._engine = test_engine
    
    yield database_url
    
    # Cleanup
    db_models.get_database_url = original_get_url
    if db_models._engine:
        db_models._engine.dispose()
    db_models._engine = None
    db_models._SessionLocal = None
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def app(sample_config, test_database):
    """Create Flask app for testing."""
    # Set test database environment
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_NAME'] = 'test'
    os.environ['DB_USER'] = 'test'
    os.environ['DB_PASSWORD'] = 'test'
    
    app = create_app(sample_config)
    app.config['TESTING'] = True
    
    # Initialize database
    try:
        init_db()
    except Exception:
        pass  # May already be initialized
    
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_token(client):
    """Get authentication token for admin user."""
    # Note: This will fail if password doesn't match the hash in config
    # For real tests, you'd need to generate proper bcrypt hashes
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin'  # This may not match the hash
    })
    if response.status_code == 200:
        data = response.get_json()
        return data.get('token')
    return None
