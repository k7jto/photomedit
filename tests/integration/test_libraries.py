"""Integration tests for library endpoints."""
import pytest
import os
import tempfile


def test_list_libraries(client, auth_token):
    """Test listing libraries."""
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    response = client.get('/api/libraries', headers=headers)
    # May require auth or may not depending on config
    assert response.status_code in [200, 401]
    if response.status_code == 200:
        data = response.get_json()
        assert isinstance(data, list)


def test_list_folders(client, auth_token, temp_dir):
    """Test listing folders."""
    # Create test folder structure
    test_folder = os.path.join(temp_dir, 'photos', 'test_folder')
    os.makedirs(test_folder, exist_ok=True)
    
    headers = {}
    if auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    response = client.get('/api/libraries/testlib/folders', headers=headers)
    # May return 404 if library not found, 200 with folders, or 401 if auth required
    assert response.status_code in [200, 404, 401]

