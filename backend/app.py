"""Main Flask application."""
import os
import logging
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from backend.config.loader import Config
from backend.security.headers import apply_security_headers
from backend.auth.jwt import JWTManager
from backend.auth.routes import auth_bp
from backend.libraries.routes import libraries_bp
from backend.media.routes import media_bp
from backend.search.routes import search_bp
from backend.upload.routes import upload_bp


def create_app(config_path: str = None):
    """Create and configure Flask application."""
    app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
    
    # Enable CORS
    CORS(app)
    
    # Load configuration
    try:
        config = Config(config_path)
        app.config['PHOTOMEDIT_CONFIG'] = config
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        raise
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Apply security headers
    apply_security_headers(app)
    
    # JWT manager
    jwt_manager = JWTManager(config.jwt_secret)
    app.config['JWT_MANAGER'] = jwt_manager
    
    # Authentication middleware
    @app.before_request
    def check_auth():
        """Check JWT authentication for protected routes."""
        # Skip auth check for login and static files
        if request.endpoint in ['auth.login', 'static', 'serve_frontend']:
            return
        
        if not config.auth_enabled:
            return
        
        # For image endpoints, allow token in query parameter (for <img> tags)
        is_image_endpoint = request.endpoint and (
            'thumbnail' in str(request.endpoint) or 
            'preview' in str(request.endpoint) or 
            'download' in str(request.endpoint)
        ) or '/thumbnail' in request.path or '/preview' in request.path or '/download' in request.path
        
        if is_image_endpoint:
            # Check for token in query parameter first
            token = request.args.get('token')
            if token:
                payload = jwt_manager.verify_token(token)
                if payload:
                    request.current_user = payload.get('username')
                    return
            # Fall back to header check
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                payload = jwt_manager.verify_token(token)
                if payload:
                    request.current_user = payload.get('username')
                    return
            # If no valid token found, return 401
            return jsonify({'error': 'unauthorized', 'message': 'Missing or invalid token'}), 401
        
        # For other endpoints, require Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'unauthorized', 'message': 'Missing or invalid authorization header'}), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        payload = jwt_manager.verify_token(token)
        
        if not payload:
            return jsonify({'error': 'unauthorized', 'message': 'Invalid or expired token'}), 401
        
        # Store username in request context
        request.current_user = payload.get('username')
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(libraries_bp, url_prefix='/api')
    app.register_blueprint(media_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    
    # Serve frontend
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve React frontend."""
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'not_found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'internal_error', 'message': 'Internal server error'}), 500
    
    return app


if __name__ == '__main__':
    config_path = os.getenv('PHOTOMEDIT_CONFIG', 'config.yaml')
    app = create_app(config_path)
    app.run(host='0.0.0.0', port=4750, debug=False)

