"""Unit tests for database models and services."""
import pytest
import tempfile
import os
from backend.database.models import User, LogEntry, Base, get_engine, get_session_local
from backend.database.user_service import UserService
from backend.database.log_service import LogService
import bcrypt


@pytest.fixture
def test_db():
    """Create a test database."""
    # Use SQLite for testing
    db_path = tempfile.mktemp(suffix='.db')
    database_url = f'sqlite:///{db_path}'
    
    # Override database URL
    import backend.database.models as db_models
    original_get_url = db_models.get_database_url
    
    def test_get_url():
        return database_url
    
    db_models.get_database_url = test_get_url
    
    # Reset engine and session to force recreation
    db_models._engine = None
    db_models._SessionLocal = None
    
    # Create tables using a fresh engine
    from sqlalchemy import create_engine
    test_engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(bind=test_engine)
    
    # Now set the engine in the module
    db_models._engine = test_engine
    db_models._SessionLocal = None  # Will be recreated on next get_session_local call
    
    yield
    
    # Cleanup
    db_models.get_database_url = original_get_url
    if db_models._engine:
        db_models._engine.dispose()
    db_models._engine = None
    db_models._SessionLocal = None
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_create_user(test_db):
    """Test creating a user."""
    password_hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt()).decode('utf-8')
    user = UserService.create_user('testuser', 'test@test.com', password_hash, 'user')
    
    assert user is not None
    assert user.username == 'testuser'
    assert user.email == 'test@test.com'
    assert user.role == 'user'


def test_get_user_by_username(test_db):
    """Test getting user by username."""
    password_hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt()).decode('utf-8')
    UserService.create_user('testuser', 'test@test.com', password_hash, 'user')
    
    user = UserService.get_user(username='testuser')
    assert user is not None
    assert user.username == 'testuser'
    assert user.email == 'test@test.com'


def test_get_user_by_email(test_db):
    """Test getting user by email."""
    password_hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt()).decode('utf-8')
    UserService.create_user('testuser', 'test@test.com', password_hash, 'user')
    
    user = UserService.get_user(email='test@test.com')
    assert user is not None
    assert user.username == 'testuser'
    assert user.email == 'test@test.com'


def test_update_user_email(test_db):
    """Test updating user email."""
    password_hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt()).decode('utf-8')
    user = UserService.create_user('testuser', 'test@test.com', password_hash, 'user')
    
    updated = UserService.update_user(user, email='newemail@test.com')
    assert updated is not None
    assert updated.email == 'newemail@test.com'


def test_update_user_mfa_secret(test_db):
    """Test updating user MFA secret."""
    password_hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt()).decode('utf-8')
    user = UserService.create_user('testuser', 'test@test.com', password_hash, 'user')
    
    updated = UserService.update_user(user, mfa_secret='test_secret')
    assert updated is not None
    assert updated.mfa_secret == 'test_secret'
    
    # Test disabling MFA
    updated = UserService.update_user(user, mfa_secret='')
    assert updated is not None
    assert updated.mfa_secret is None


def test_list_users(test_db):
    """Test listing users."""
    password_hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt()).decode('utf-8')
    UserService.create_user('user1', 'user1@test.com', password_hash, 'user')
    UserService.create_user('user2', 'user2@test.com', password_hash, 'admin')
    
    users = UserService.list_users()
    assert len(users) == 2
    usernames = [u.username for u in users]
    assert 'user1' in usernames
    assert 'user2' in usernames


def test_log_entry(test_db):
    """Test creating log entry."""
    LogService.log('INFO', 'Test message', 'test_logger', 'testuser', '127.0.0.1')
    
    logs = LogService.get_logs(limit=10)
    assert len(logs) > 0
    assert logs[0].message == 'Test message'
    assert logs[0].level == 'INFO'
    assert logs[0].user == 'testuser'

