"""Main Flask application."""
import os
import logging
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from backend.config.loader import Config
from backend.security.headers import apply_security_headers
from backend.auth.jwt import JWTManager
from backend.database.connection import init_db
from backend.database.log_service import LogService
from backend.auth.routes import auth_bp
from backend.libraries.routes import libraries_bp
from backend.media.routes import media_bp
from backend.search.routes import search_bp
from backend.upload.routes import upload_bp
from backend.download.routes import download_bp
from backend.admin.routes import admin_bp


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
    
    # Initialize database (with retry logic)
    max_retries = 5
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            init_db()
            app.logger.info("Database initialized")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                app.logger.warning(f"Database initialization attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                import time
                time.sleep(retry_delay)
            else:
                app.logger.error(f"Failed to initialize database after {max_retries} attempts: {e}")
                # Continue anyway - database might not be available yet
    
    # JWT manager
    jwt_manager = JWTManager(config.jwt_secret)
    app.config['JWT_MANAGER'] = jwt_manager
    
    # Authentication middleware
    @app.before_request
    def check_auth():
        """Check JWT authentication for protected routes."""
        # Skip auth check for login, password reset, static files, and favicon
        skip_endpoints = ['auth.login', 'auth.forgot_password', 'auth.reset_password', 'static', 'serve_frontend', 'favicon']
        if request.endpoint in skip_endpoints or '/forgot-password' in request.path or '/reset-password' in request.path or request.path == '/favicon.ico':
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
    
    # Close database session after request
    @app.teardown_appcontext
    def close_db(error):
        from backend.database.models import get_session_local
        try:
            get_session_local().remove()
        except Exception:
            pass
    
    # Close database session after request
    @app.teardown_appcontext
    def close_db(error):
        from backend.database.models import get_session_local
        try:
            get_session_local().remove()
        except Exception:
            pass
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(libraries_bp, url_prefix='/api')
    app.register_blueprint(media_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(download_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Serve favicon
    @app.route('/favicon.ico')
    def favicon():
        favicon_path = os.path.join(app.static_folder, 'favicon.ico')
        if os.path.exists(favicon_path):
            return send_from_directory(app.static_folder, 'favicon.ico')
        else:
            # Return 204 No Content if favicon doesn't exist
            return '', 204
    
    # Serve frontend
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve React frontend."""
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
    
    # Request logging middleware
    @app.after_request
    def log_request(response):
        """Log all API requests to database."""
        # Only log API endpoints (not static files)
        if request.path.startswith('/api/'):
            user = getattr(request, 'current_user', None)
            level = 'ERROR' if response.status_code >= 400 else 'INFO'
            message = f"{request.method} {request.path} - {response.status_code}"
            
            # Include error details for error responses
            details = None
            if response.status_code >= 400:
                try:
                    # Try to get error message from response
                    if response.is_json:
                        data = response.get_json()
                        if data and 'message' in data:
                            message += f": {data['message']}"
                            details = {'error': data.get('error'), 'message': data.get('message')}
                except:
                    pass
            
            LogService.log(
                level=level,
                message=message,
                logger_name='api.request',
                user=user,
                ip_address=request.remote_addr,
                details=details
            )
        
        return response
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        user = getattr(request, 'current_user', None)
        LogService.log(
            level='WARNING',
            message=f"404 Not Found: {request.method} {request.path}",
            logger_name='api.error',
            user=user,
            ip_address=request.remote_addr,
            details={'path': request.path, 'method': request.method}
        )
        return jsonify({'error': 'not_found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        user = getattr(request, 'current_user', None)
        import traceback
        error_details = {
            'path': request.path,
            'method': request.method,
            'traceback': traceback.format_exc()
        }
        LogService.log(
            level='ERROR',
            message=f"500 Internal Server Error: {request.method} {request.path}",
            logger_name='api.error',
            user=user,
            ip_address=request.remote_addr,
            details=error_details
        )
        return jsonify({'error': 'internal_error', 'message': 'Internal server error'}), 500
    
    return app


if __name__ == '__main__':
    config_path = os.getenv('PHOTOMEDIT_CONFIG', 'config.yaml')
    app = create_app(config_path)
    app.run(host='0.0.0.0', port=4750, debug=False)

