"""Configuration loader for PhotoMedit."""
import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = os.getenv("PHOTOMEDIT_CONFIG", "config.yaml")
        
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Server settings
        server = raw_config.get('server', {})
        self.port = server.get('port', 4750)
        self.host = server.get('host', '0.0.0.0')
        self.jwt_secret = server.get('jwtSecret', 'change-me-in-production')
        
        # Auth settings
        auth = raw_config.get('auth', {})
        self.auth_enabled = auth.get('enabled', True)
        # Admin user is kept in config for initial access
        self.admin_user = auth.get('adminUser', {})
        # Other users are stored in database
        
        # Libraries
        self.libraries = raw_config.get('libraries', [])
        
        # Thumbnail cache
        self.thumbnail_cache_root = raw_config.get('thumbnailCacheRoot', '/data/thumbnails')
        os.makedirs(self.thumbnail_cache_root, exist_ok=True)
        
        # Upload root
        self.upload_root = raw_config.get('uploadRoot', '/data/uploads')
        os.makedirs(self.upload_root, exist_ok=True)
        
        # Limits
        limits = raw_config.get('limits', {})
        upload_limits = limits.get('upload', {})
        self.max_upload_files = upload_limits.get('maxFiles', 500)
        self.max_upload_bytes_per_file = upload_limits.get('maxBytesPerFile', 500 * 1024 * 1024)
        self.max_upload_bytes_total = upload_limits.get('maxBytesTotal', 10 * 1024 * 1024 * 1024)
        
        download_limits = limits.get('download', {})
        self.max_download_files = download_limits.get('maxFiles', 10000)
        self.max_download_bytes = download_limits.get('maxBytes', 20 * 1024 * 1024 * 1024)
        
        # Geocoding
        geocoding = raw_config.get('geocoding', {})
        self.geocoding_provider = geocoding.get('provider', 'nominatim')
        self.geocoding_enabled = geocoding.get('enabled', True)
        self.geocoding_user_agent = geocoding.get('userAgent', 'PhotoMedit/1.0')
        self.geocoding_rate_limit = geocoding.get('rateLimit', 1.0)
        
        # Logging
        logging = raw_config.get('logging', {})
        self.log_level = logging.get('level', 'INFO')
        
        # Validate required fields
        if not self.libraries:
            raise ValueError("At least one library must be configured")
        
        for lib in self.libraries:
            if not lib.get('id') or not lib.get('rootPath'):
                raise ValueError("Each library must have 'id' and 'rootPath'")
    
    def get_library(self, library_id: str) -> Optional[Dict[str, Any]]:
        """Get library configuration by ID."""
        for lib in self.libraries:
            if lib.get('id') == library_id:
                return lib
        return None
    
    def get_admin_user(self) -> Optional[Dict[str, Any]]:
        """Get admin user from config."""
        return self.admin_user if self.admin_user.get('username') else None
    
    def save_config(self, config_path: Optional[str] = None):
        """Save configuration back to YAML file."""
        if config_path is None:
            config_path = os.getenv("PHOTOMEDIT_CONFIG", "config.yaml")
        
        config_dict = {
            'server': {
                'port': self.port,
                'host': self.host,
                'jwtSecret': self.jwt_secret
            },
            'auth': {
                'enabled': self.auth_enabled,
                'adminUser': self.admin_user
            },
            'libraries': self.libraries,
            'thumbnailCacheRoot': self.thumbnail_cache_root,
            'uploadRoot': self.upload_root,
            'limits': {
                'upload': {
                    'maxFiles': self.max_upload_files,
                    'maxBytesPerFile': self.max_upload_bytes_per_file,
                    'maxBytesTotal': self.max_upload_bytes_total
                },
                'download': {
                    'maxFiles': self.max_download_files,
                    'maxBytes': self.max_download_bytes
                }
            },
            'geocoding': {
                'provider': self.geocoding_provider,
                'enabled': self.geocoding_enabled,
                'userAgent': self.geocoding_user_agent,
                'rateLimit': self.geocoding_rate_limit
            },
            'logging': {
                'level': self.log_level
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

