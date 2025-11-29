"""Authentication routes."""
from flask import Blueprint, request, jsonify, current_app
import bcrypt
from backend.config.loader import Config
from backend.auth.jwt import JWTManager


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
    
    # Find user
    user = config.get_user(username)
    if not user:
        return jsonify({'error': 'unauthorized', 'message': 'Invalid credentials'}), 401
    
    # Verify password
    password_hash = user.get('passwordHash')
    if not password_hash:
        return jsonify({'error': 'unauthorized', 'message': 'Invalid credentials'}), 401
    
    try:
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return jsonify({'error': 'unauthorized', 'message': 'Invalid credentials'}), 401
    except Exception:
        return jsonify({'error': 'unauthorized', 'message': 'Invalid credentials'}), 401
    
    # Create JWT
    jwt_manager = JWTManager(config.jwt_secret)
    token_data = jwt_manager.create_token(username)
    
    return jsonify(token_data), 200

