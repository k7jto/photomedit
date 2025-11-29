"""Unit tests for JWT handling."""
import pytest
from backend.auth.jwt import JWTManager


def test_create_token():
    """Test JWT token creation."""
    manager = JWTManager("test-secret")
    token_data = manager.create_token("testuser")
    
    assert 'token' in token_data
    assert 'expiresAt' in token_data
    assert token_data['token'] is not None


def test_verify_token():
    """Test JWT token verification."""
    manager = JWTManager("test-secret")
    token_data = manager.create_token("testuser")
    
    payload = manager.verify_token(token_data['token'])
    assert payload is not None
    assert payload.get('username') == 'testuser'


def test_verify_invalid_token():
    """Test verification of invalid token."""
    manager = JWTManager("test-secret")
    payload = manager.verify_token("invalid-token")
    assert payload is None


def test_get_username_from_token():
    """Test extracting username from token."""
    manager = JWTManager("test-secret")
    token_data = manager.create_token("testuser")
    
    username = manager.get_username_from_token(token_data['token'])
    assert username == "testuser"

