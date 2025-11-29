"""Admin routes for user management."""
from flask import Blueprint, request, jsonify, current_app
import bcrypt
from backend.config.loader import Config
from backend.auth.mfa import MFAManager
from backend.database.user_service import UserService
from backend.database.log_service import LogService


admin_bp = Blueprint('admin', __name__)


def require_admin():
    """Check if current user is admin."""
    # Get username from request context (set by auth middleware)
    username = getattr(request, 'current_user', None)
    if not username:
        return jsonify({'error': 'unauthorized', 'message': 'Authentication required'}), 401
    
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    # Check if user is admin (from database or config)
    db_user = UserService.get_user(username)
    if db_user:
        is_admin = (db_user.role == 'admin')
    else:
        # Check config admin user
        admin_user = config.get_admin_user()
        is_admin = (admin_user and admin_user.get('username') == username and admin_user.get('isAdmin', False))
    
    if not is_admin:
        return jsonify({'error': 'forbidden', 'message': 'Admin access required'}), 403
    
    return None


@admin_bp.route('/users', methods=['GET'])
def list_users():
    """List all users."""
    error = require_admin()
    if error:
        return error
    
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    users = []
    
    # Add admin user from config if exists
    admin_user = config.get_admin_user()
    if admin_user and admin_user.get('username'):
        users.append({
            'username': admin_user.get('username'),
            'email': admin_user.get('email', ''),
            'role': 'admin',
            'mfaEnabled': bool(admin_user.get('mfaSecret')),
            'createdAt': None,
            'lastLogin': None,
            'source': 'config'
        })
    
    # Add users from database
    try:
        db_users = UserService.list_users()
        for db_user in db_users:
            users.append({
                'username': db_user.username,
                'role': db_user.role,
                'mfaEnabled': bool(db_user.mfa_secret),
                'createdAt': db_user.created_at.isoformat() if db_user.created_at else None,
                'lastLogin': db_user.last_login.isoformat() if db_user.last_login else None,
                'source': 'database'
            })
    except Exception as e:
        # If database is unavailable, just return config users
        pass
    
    return jsonify(users), 200


@admin_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new user."""
    error = require_admin()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'validation_error', 'message': 'Request body required'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')  # 'user' or 'admin'
    
    if not username or not password or not email:
        return jsonify({'error': 'validation_error', 'message': 'Username, email, and password required'}), 400
    
    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[1]:
        return jsonify({'error': 'validation_error', 'message': 'Invalid email address'}), 400
    
    if role not in ['user', 'admin']:
        return jsonify({'error': 'validation_error', 'message': 'Role must be "user" or "admin"'}), 400
    
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    
    # Check if user already exists in database
    if UserService.get_user(username=username):
        return jsonify({'error': 'validation_error', 'message': 'Username already exists'}), 400
    
    # Check if email already exists
    if UserService.get_user(email=email):
        return jsonify({'error': 'validation_error', 'message': 'Email already exists'}), 400
    
    # Check if username conflicts with config admin user
    admin_user = config.get_admin_user()
    if admin_user and admin_user.get('username') == username:
        return jsonify({'error': 'validation_error', 'message': 'Username conflicts with admin user in config'}), 400
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user in database
    user = UserService.create_user(username, email, password_hash, role)
    if not user:
        return jsonify({'error': 'internal_error', 'message': 'Failed to create user'}), 500
    
    LogService.log('INFO', f'User created: {username} with role: {role}', 
                  user=getattr(request, 'current_user', None), ip_address=request.remote_addr)
    
    return jsonify({'message': 'User created successfully', 'username': username}), 201


@admin_bp.route('/users/<username>', methods=['PUT'])
def update_user(username):
    """Update a user."""
    error = require_admin()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'validation_error', 'message': 'Request body required'}), 400
    
    # Check if trying to update config admin user
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    admin_user = config.get_admin_user()
    if admin_user and admin_user.get('username') == username:
        return jsonify({'error': 'validation_error', 'message': 'Cannot update admin user from config. Edit config.yaml directly.'}), 400
    
    db_user = UserService.get_user(username=username)
    if not db_user:
        return jsonify({'error': 'not_found', 'message': 'User not found'}), 404
    
    # Update email if provided
    email = None
    if 'email' in data and data['email']:
        email = data['email']
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[1]:
            return jsonify({'error': 'validation_error', 'message': 'Invalid email address'}), 400
        # Check if email is already in use by another user
        existing_user = UserService.get_user(email=email)
        if existing_user and existing_user.id != db_user.id:
            return jsonify({'error': 'validation_error', 'message': 'Email already in use'}), 400
    
    # Update password if provided
    password_hash = None
    if 'password' in data and data['password']:
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update role if provided
    role = None
    if 'role' in data:
        if data['role'] not in ['user', 'admin']:
            return jsonify({'error': 'validation_error', 'message': 'Role must be "user" or "admin"'}), 400
        role = data['role']
    
    # Update user
    updated_user = UserService.update_user(db_user, email=email, password_hash=password_hash, role=role)
    if not updated_user:
        return jsonify({'error': 'internal_error', 'message': 'Failed to update user'}), 500
    
    LogService.log('INFO', f'User updated: {username}', 
                  user=getattr(request, 'current_user', None), ip_address=request.remote_addr)
    
    return jsonify({'message': 'User updated successfully'}), 200


@admin_bp.route('/users/<username>', methods=['DELETE'])
def delete_user(username):
    """Delete a user."""
    error = require_admin()
    if error:
        return error
    
    # Don't allow deleting yourself
    current_username = getattr(request, 'current_user', None)
    if username == current_username:
        return jsonify({'error': 'validation_error', 'message': 'Cannot delete your own account'}), 400
    
    # Check if trying to delete config admin user
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    admin_user = config.get_admin_user()
    if admin_user and admin_user.get('username') == username:
        return jsonify({'error': 'validation_error', 'message': 'Cannot delete admin user from config. Edit config.yaml directly.'}), 400
    
    db_user = UserService.get_user(username)
    if not db_user:
        return jsonify({'error': 'not_found', 'message': 'User not found'}), 404
    
    # Delete user
    if not UserService.delete_user(db_user):
        return jsonify({'error': 'internal_error', 'message': 'Failed to delete user'}), 500
    
    LogService.log('INFO', f'User deleted: {username}', 
                  user=current_username, ip_address=request.remote_addr)
    
    return jsonify({'message': 'User deleted successfully'}), 200


@admin_bp.route('/users/<username>/disable-mfa', methods=['POST'])
def disable_user_mfa(username):
    """Admin endpoint to disable MFA for a user (recovery scenario)."""
    error = require_admin()
    if error:
        return error
    
    # Check if trying to modify config admin user
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    admin_user = config.get_admin_user()
    if admin_user and admin_user.get('username') == username:
        return jsonify({'error': 'validation_error', 'message': 'Cannot modify MFA for admin user from config. Edit config.yaml directly.'}), 400
    
    db_user = UserService.get_user(username=username)
    if not db_user:
        return jsonify({'error': 'not_found', 'message': 'User not found'}), 404
    
    # Disable MFA
    updated_user = UserService.update_user(db_user, mfa_secret='')
    if not updated_user:
        return jsonify({'error': 'internal_error', 'message': 'Failed to disable MFA'}), 500
    
    LogService.log('INFO', f'Admin disabled MFA for user: {username}', 
                  user=getattr(request, 'current_user', None), ip_address=request.remote_addr)
    
    return jsonify({'message': 'MFA disabled successfully for user'}), 200
