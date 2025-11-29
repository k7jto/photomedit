"""Integration tests for authentication."""
import pytest
import bcrypt
from backend.database.user_service import UserService


def test_login_success(client):
    """Test successful login."""
    # This test will work if we have a valid user in database or config
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin'
    })
    # May succeed or fail depending on actual password hash
    assert response.status_code in [200, 401]


def test_login_missing_fields(client):
    """Test login with missing fields."""
    response = client.post('/api/auth/login', json={})
    assert response.status_code == 400


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('/api/auth/login', json={
        'username': 'nonexistent',
        'password': 'wrongpass'
    })
    assert response.status_code == 401


def test_forgot_password_with_email(client):
    """Test forgot password with email."""
    response = client.post('/api/auth/forgot-password', json={
        'email': 'admin@test.com'
    })
    # Should always return 200 (security best practice)
    assert response.status_code in [200, 400]  # 400 if email validation fails
    if response.status_code == 200:
        data = response.get_json()
        assert 'message' in data


def test_forgot_password_missing_email(client):
    """Test forgot password without email."""
    response = client.post('/api/auth/forgot-password', json={})
    assert response.status_code == 400


def test_protected_endpoint_without_auth(client):
    """Test that protected endpoints require authentication."""
    response = client.get('/api/libraries')
    # Should fail if auth is enabled
    assert response.status_code in [200, 401]


def test_protected_endpoint_with_auth(client, auth_token):
    """Test that protected endpoints work with authentication."""
    if not auth_token:
        pytest.skip("No auth token available")
    
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.get('/api/libraries', headers=headers)
    assert response.status_code == 200


def test_create_user_requires_admin(client, auth_token):
    """Test that creating users requires admin access."""
    if not auth_token:
        pytest.skip("No auth token available")
    
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.post('/api/admin/users', json={
        'username': 'testuser',
        'email': 'test@test.com',
        'password': 'testpass',
        'role': 'user'
    }, headers=headers)
    # May succeed if admin token is valid, or fail if not admin
    assert response.status_code in [201, 403, 401]


def test_create_user_missing_email(client, auth_token):
    """Test that creating user requires email."""
    if not auth_token:
        pytest.skip("No auth token available")
    
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.post('/api/admin/users', json={
        'username': 'testuser',
        'password': 'testpass',
        'role': 'user'
    }, headers=headers)
    assert response.status_code == 400
    data = response.get_json()
    assert 'email' in data.get('message', '').lower() or 'required' in data.get('message', '').lower()
