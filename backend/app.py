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
    
    # Run filesystem diagnostics on startup (immediately)
    def run_startup_diagnostics():
        """Run diagnostic checks on startup and log results."""
        import os
        import stat
        
        app.logger.info("=" * 80)
        app.logger.info("FILESYSTEM DIAGNOSTICS - STARTUP")
        app.logger.info("=" * 80)
        
        config = app.config.get('PHOTOMEDIT_CONFIG')
        if not config:
            app.logger.error("Cannot run diagnostics: Configuration not available")
            return
        
        # Check each library
        for library in config.libraries:
            lib_id = library['id']
            root_path = library['rootPath']
            
            app.logger.info(f"--- Library: {lib_id} ---")
            app.logger.info(f"  Config rootPath: {root_path}")
            
            # Note: Path resolution happens in Config._resolve_library_paths()
            # Host paths like /volume1/Memories are automatically converted to /data/pictures
            app.logger.info(f"  Path exists: {os.path.exists(root_path)}")
            
            if os.path.exists(root_path):
                app.logger.info(f"  Is directory: {os.path.isdir(root_path)}")
                app.logger.info(f"  Readable: {os.access(root_path, os.R_OK)}")
                app.logger.info(f"  Writable: {os.access(root_path, os.W_OK)}")
                app.logger.info(f"  Executable: {os.access(root_path, os.X_OK)}")
                
                try:
                    root_stat = os.stat(root_path)
                    app.logger.info(f"  Device ID: {root_stat.st_dev}")
                    app.logger.info(f"  Inode: {root_stat.st_ino}")
                    app.logger.info(f"  Real path (resolved): {os.path.realpath(root_path)}")
                    
                    # Check if it's a mount point
                    parent = os.path.dirname(root_path)
                    if os.path.exists(parent):
                        parent_stat = os.stat(parent)
                        is_mount = (root_stat.st_dev != parent_stat.st_dev)
                        app.logger.info(f"  Is mount point: {is_mount} (parent device: {parent_stat.st_dev})")
                    
                    # Try to list contents
                    try:
                        items = os.listdir(root_path)
                        app.logger.info(f"  Item count: {len(items)}")
                        app.logger.info(f"  Sample items (first 20): {items[:20]}")
                        
                        # Count folders vs files
                        folders = []
                        files = []
                        for item in items:
                            item_path = os.path.join(root_path, item)
                            try:
                                if os.path.isdir(item_path):
                                    folders.append(item)
                                else:
                                    files.append(item)
                            except Exception:
                                pass
                        app.logger.info(f"  Folders: {len(folders)} - {folders[:10]}")
                        app.logger.info(f"  Files: {len(files)} - {files[:10]}")
                    except PermissionError as e:
                        app.logger.error(f"  Permission denied listing directory: {e}")
                    except Exception as e:
                        app.logger.error(f"  Error listing directory: {e}")
                        
                except Exception as e:
                    app.logger.error(f"  Error getting path info: {e}")
            else:
                app.logger.error(f"  PATH DOES NOT EXIST - This is a problem!")
                # Check if parent exists
                parent = os.path.dirname(root_path)
                if os.path.exists(parent):
                    app.logger.info(f"  Parent directory exists: {parent}")
                    app.logger.info(f"  Parent is directory: {os.path.isdir(parent)}")
                    app.logger.info(f"  Parent readable: {os.access(parent, os.R_OK)}")
                    app.logger.info(f"  Parent writable: {os.access(parent, os.W_OK)}")
                else:
                    app.logger.error(f"  Parent directory also does not exist: {parent}")
        
        app.logger.info("=" * 80)
        app.logger.info("END FILESYSTEM DIAGNOSTICS")
        app.logger.info("=" * 80)
    
    # Run diagnostics immediately after app setup
    run_startup_diagnostics()
    
    # Start thumbnail worker for async thumbnail generation
    from backend.media.thumbnail_worker import get_thumbnail_worker
    try:
        thumbnail_worker = get_thumbnail_worker(config.thumbnail_cache_root)
        app.logger.info("Thumbnail worker started")
    except Exception as e:
        app.logger.warning(f"Failed to start thumbnail worker: {e}")
    
    # JWT manager
    jwt_manager = JWTManager(config.jwt_secret)
    app.config['JWT_MANAGER'] = jwt_manager
    
    # Health check endpoint (no auth required)
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Docker healthchecks."""
        return jsonify({'status': 'ok'}), 200
    
    # Diagnostic endpoint (admin only, for troubleshooting)
    @app.route('/api/diagnostic/paths', methods=['GET'])
    def diagnostic_paths():
        """Diagnostic endpoint to check filesystem paths and mounts."""
        import os
        import stat
        from backend.config.loader import Config
        
        config = current_app.config.get('PHOTOMEDIT_CONFIG')
        if not config:
            return jsonify({'error': 'internal_error', 'message': 'Configuration not available'}), 500
        
        diagnostics = {}
        
        # Check each library
        for library in config.libraries:
            lib_id = library['id']
            root_path = library['rootPath']
            
            lib_info = {
                'rootPath': root_path,
                'exists': os.path.exists(root_path),
                'isDir': os.path.isdir(root_path) if os.path.exists(root_path) else False,
                'readable': os.access(root_path, os.R_OK) if os.path.exists(root_path) else False,
                'writable': os.access(root_path, os.W_OK) if os.path.exists(root_path) else False,
            }
            
            if os.path.exists(root_path):
                try:
                    root_stat = os.stat(root_path)
                    lib_info['device'] = root_stat.st_dev
                    lib_info['inode'] = root_stat.st_ino
                    lib_info['realpath'] = os.path.realpath(root_path)
                    
                    # Check parent to see if it's a mount
                    parent = os.path.dirname(root_path)
                    if os.path.exists(parent):
                        parent_stat = os.stat(parent)
                        lib_info['isMountPoint'] = (root_stat.st_dev != parent_stat.st_dev)
                        lib_info['parentDevice'] = parent_stat.st_dev
                    
                    # List some items
                    try:
                        items = os.listdir(root_path)
                        lib_info['itemCount'] = len(items)
                        lib_info['sampleItems'] = items[:10]
                    except Exception as e:
                        lib_info['listError'] = str(e)
                except Exception as e:
                    lib_info['statError'] = str(e)
            
            diagnostics[lib_id] = lib_info
        
        return jsonify(diagnostics), 200
    
    # Authentication middleware
    @app.before_request
    def check_auth():
        """Check JWT authentication for protected routes."""
        # Skip auth check for login, password reset, static files, favicon, health check, and frontend routes
        skip_endpoints = ['auth.login', 'auth.forgot_password', 'auth.reset_password', 'static', 'serve_frontend', 'favicon', 'health_check', 'diagnostic_paths']
        # Skip auth for non-API routes (frontend routes) - these will be handled by serve_frontend
        is_frontend_route = not request.path.startswith('/api/') and request.endpoint == 'serve_frontend'
        if request.endpoint in skip_endpoints or '/forgot-password' in request.path or '/reset-password' in request.path or request.path == '/favicon.ico' or request.path == '/health' or '/diagnostic/' in request.path or is_frontend_route:
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
        """Handle 404 errors - serve React app for frontend routes, JSON for API routes."""
        # If it's an API route, return JSON error
        if request.path.startswith('/api/'):
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
        
        # For non-API routes, check if it's a static file first
        path = request.path.lstrip('/')
        if path:
            static_file_path = os.path.join(app.static_folder, path)
            if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
                return send_from_directory(app.static_folder, path)
        
        # For all other routes (React Router routes), serve index.html
        # React Router will handle the routing on the client side
        return send_from_directory(app.static_folder, 'index.html')
    
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

