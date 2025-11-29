"""Authentication routes."""
from flask import Blueprint, request, jsonify, current_app
import bcrypt
from backend.config.loader import Config
from backend.auth.jwt import JWTManager
from backend.auth.mfa import MFAManager
from backend.auth.password_reset import PasswordResetManager
from backend.database.user_service import UserService
from backend.database.log_service import LogService


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login endpoint."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'validation_error', 'message': 'Request body required'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'validation_error', 'message': 'Username and password required'}), 400
    
    # Get config from app context
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    # Try to find user in database first
    db_user = UserService.get_user(username)
    user = None
    password_hash = None
    mfa_secret = None
    is_admin = False
    
    if db_user:
        # User found in database
        user = db_user
        password_hash = db_user.password_hash
        mfa_secret = db_user.mfa_secret
        is_admin = (db_user.role == 'admin')
    else:
        # Check config for admin user
        admin_user = config.get_admin_user()
        if admin_user and admin_user.get('username') == username:
            user = admin_user
            password_hash = admin_user.get('passwordHash')
            mfa_secret = admin_user.get('mfaSecret')
            is_admin = admin_user.get('isAdmin', False)
    
    if not user or not password_hash:
        LogService.log('WARNING', f'Failed login attempt for user: {username}', 
                      user=username, ip_address=request.remote_addr)
        return jsonify({'error': 'unauthorized', 'message': 'Invalid credentials'}), 401
    
    # Verify password
    try:
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            LogService.log('WARNING', f'Invalid password for user: {username}', 
                          user=username, ip_address=request.remote_addr)
            return jsonify({'error': 'unauthorized', 'message': 'Invalid credentials'}), 401
    except Exception:
        LogService.log('WARNING', f'Password verification error for user: {username}', 
                      user=username, ip_address=request.remote_addr)
        return jsonify({'error': 'unauthorized', 'message': 'Invalid credentials'}), 401
    
    # Check if MFA is enabled
    mfa_token = data.get('mfaToken')
    
    if mfa_secret:
        # MFA is enabled, require token
        if not mfa_token:
            return jsonify({
                'error': 'mfa_required',
                'message': 'MFA token required',
                'mfaRequired': True
            }), 200  # Return 200 to indicate MFA is needed
        
        # Verify MFA token
        if not MFAManager.verify_token(mfa_secret, mfa_token):
            LogService.log('WARNING', f'Invalid MFA token for user: {username}', 
                          user=username, ip_address=request.remote_addr)
            return jsonify({'error': 'unauthorized', 'message': 'Invalid MFA token'}), 401
    
    # Update last login (only for database users)
    if db_user:
        UserService.update_last_login(username)
    
    # Log successful login
    LogService.log('INFO', f'User logged in: {username}', 
                  user=username, ip_address=request.remote_addr)
    
    # Create JWT
    jwt_manager = JWTManager(config.jwt_secret)
    token_data = jwt_manager.create_token(username)
    
    return jsonify(token_data), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'validation_error', 'message': 'Request body required'}), 400
    
    email = data.get('email')
    if not email:
        return jsonify({'error': 'validation_error', 'message': 'Email required'}), 400
    
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    # Find user by email (database or config)
    user = None
    username = None
    
    # Check database first
    db_user = UserService.get_user(email=email)
    if db_user:
        user = db_user
        username = db_user.username
    else:
        # Check config admin user
        admin_user = config.get_admin_user()
        if admin_user and admin_user.get('email') == email:
            user = admin_user
            username = admin_user.get('username')
    
    # Always return success (security best practice - don't reveal if user exists)
    if not user:
        LogService.log('WARNING', f'Password reset requested for unknown email: {email}', 
                      ip_address=request.remote_addr)
        return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200
    
    # Generate reset token
    reset_token = PasswordResetManager.generate_reset_token(username)
    
    # In a real app, send email here
    # TODO: Implement email sending (SMTP configuration needed)
    reset_url = f"/reset-password?token={reset_token}"
    
    LogService.log('INFO', f'Password reset requested for user: {username}', 
                  user=username, ip_address=request.remote_addr)
    
    # In production, only return success message. Token should be sent via email only.
    return jsonify({
        'message': 'If the email exists, a reset link has been sent',
        # Only return token in development - remove in production
        'resetToken': reset_token if config.log_level == 'DEBUG' else None,
        'resetUrl': reset_url if config.log_level == 'DEBUG' else None
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'validation_error', 'message': 'Request body required'}), 400
    
    token = data.get('token')
    new_password = data.get('password')
    
    if not token or not new_password:
        return jsonify({'error': 'validation_error', 'message': 'Token and password required'}), 400
    
    # Verify token
    username = PasswordResetManager.consume_reset_token(token)
    if not username:
        return jsonify({'error': 'validation_error', 'message': 'Invalid or expired token'}), 400
    
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    
    # Try to find user in database first
    db_user = UserService.get_user(username)
    if db_user:
        # Update password in database
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        if not UserService.update_user(db_user, password_hash=password_hash):
            return jsonify({'error': 'internal_error', 'message': 'Failed to update password'}), 500
    else:
        # Check config admin user
        admin_user = config.get_admin_user()
        if admin_user and admin_user.get('username') == username:
            return jsonify({'error': 'validation_error', 'message': 'Cannot reset password for admin user in config. Edit config.yaml directly.'}), 400
        else:
            return jsonify({'error': 'not_found', 'message': 'User not found'}), 404
    
    LogService.log('INFO', f'Password reset for user: {username}', 
                  user=username, ip_address=request.remote_addr)
    
    return jsonify({'message': 'Password reset successfully'}), 200


@auth_bp.route('/mfa/setup', methods=['GET'])
def setup_mfa():
    """Get MFA setup QR code."""
    username = getattr(request, 'current_user', None)
    if not username:
        return jsonify({'error': 'unauthorized', 'message': 'Authentication required'}), 401
    
    config = current_app.config.get('PHOTOMEDIT_CONFIG')
    if not config:
        return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
    
    # Get user from database or config
    db_user = UserService.get_user(username)
    if not db_user:
        # Check admin user in config
        admin_user = config.get_admin_user()
        if not admin_user or admin_user.get('username') != username:
            return jsonify({'error': 'not_found', 'message': 'User not found'}), 404
        # Admin user from config - MFA setup not supported for config users
        return jsonify({'error': 'validation_error', 'message': 'MFA setup not available for admin user in config'}), 400
    
    user = db_user
    
    # Generate secret if not exists
    if not user.mfa_secret:
        secret = MFAManager.generate_secret()
        UserService.update_user(user, mfa_secret=secret)
        user = UserService.get_user(username)  # Refresh
    else:
        secret = user.mfa_secret
    
    # Generate QR code
    uri = MFAManager.get_provisioning_uri(username, secret)
    qr_code = MFAManager.generate_qr_code(uri)
    
    return jsonify({
        'secret': secret,
        'qrCode': qr_code,
        'uri': uri
    }), 200


@auth_bp.route('/mfa/verify', methods=['POST'])
def verify_mfa_setup():
    """Verify MFA setup token and enable MFA."""
    username = getattr(request, 'current_user', None)
    if not username:
        return jsonify({'error': 'unauthorized', 'message': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'validation_error', 'message': 'Request body required'}), 400
    
    token = data.get('token')
    if not token:
        return jsonify({'error': 'validation_error', 'message': 'Token required'}), 400
    
    db_user = UserService.get_user(username)
    if not db_user:
        return jsonify({'error': 'not_found', 'message': 'User not found'}), 404
    
    secret = db_user.mfa_secret
    if not secret:
        return jsonify({'error': 'validation_error', 'message': 'MFA not set up'}), 400
    
    # Verify token
    if not MFAManager.verify_token(secret, token):
        return jsonify({'error': 'validation_error', 'message': 'Invalid token'}), 400
    
    # MFA is already enabled (secret exists), just confirm
    return jsonify({'message': 'MFA verified and enabled'}), 200


@auth_bp.route('/mfa/disable', methods=['POST'])
def disable_mfa():
    """Disable MFA for current user."""
    username = getattr(request, 'current_user', None)
    if not username:
        return jsonify({'error': 'unauthorized', 'message': 'Authentication required'}), 401
    
    data = request.get_json()
    password = data.get('password') if data else None
    
    db_user = UserService.get_user(username)
    if not db_user:
        return jsonify({'error': 'not_found', 'message': 'User not found'}), 404
    
    # Verify password
    if password:
        if not bcrypt.checkpw(password.encode('utf-8'), db_user.password_hash.encode('utf-8')):
            return jsonify({'error': 'unauthorized', 'message': 'Invalid password'}), 401
    
    # Remove MFA secret
    UserService.update_user(db_user, mfa_secret='')
    
    return jsonify({'message': 'MFA disabled successfully'}), 200

