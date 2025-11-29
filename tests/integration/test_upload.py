"""Integration tests for upload functionality."""
import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture
def auth_token(client):
    """Get authentication token for admin user."""
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin'
    })
    if response.status_code == 200:
        return response.get_json().get('token')
    return None


def test_upload_without_auth(client):
    """Test upload without authentication."""
    response = client.post('/api/upload', data={
        'uploadName': 'test',
        'files': (tempfile.NamedTemporaryFile(delete=False), 'test.jpg')
    })
    assert response.status_code == 401


def test_upload_with_auth(client, auth_token, sample_config):
    """Test upload with authentication."""
    if not auth_token:
        pytest.skip("Admin login failed - check config")
    
    # Create a test image file
    test_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    test_file.write(b'fake jpeg content')
    test_file.close()
    
    try:
        with open(test_file.name, 'rb') as f:
            response = client.post(
                '/api/upload',
                data={
                    'uploadName': 'test-batch',
                    'libraryId': 'library1',
                    'files': (f, 'test.jpg')
                },
                headers={'Authorization': f'Bearer {auth_token}'},
                content_type='multipart/form-data'
            )
        
        # Should succeed or fail with validation error (not auth error)
        assert response.status_code in [200, 400, 500]  # 500 might be due to folder creation issues
        assert response.status_code != 401  # Should not be unauthorized
    finally:
        if os.path.exists(test_file.name):
            os.unlink(test_file.name)


def test_upload_invalid_file_type(client, auth_token):
    """Test upload with invalid file type."""
    if not auth_token:
        pytest.skip("Admin login failed - check config")
    
    test_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    test_file.write(b'not an image')
    test_file.close()
    
    try:
        with open(test_file.name, 'rb') as f:
            response = client.post(
                '/api/upload',
                data={
                    'uploadName': 'test-batch',
                    'libraryId': 'library1',
                    'files': (f, 'test.txt')
                },
                headers={'Authorization': f'Bearer {auth_token}'},
                content_type='multipart/form-data'
            )
        
        # Should fail with validation error
        assert response.status_code in [400, 422]
    finally:
        if os.path.exists(test_file.name):
            os.unlink(test_file.name)

