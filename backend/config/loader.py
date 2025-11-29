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
        self.users = auth.get('users', [])
        
        # Libraries
        self.libraries = raw_config.get('libraries', [])
        
        # Thumbnail cache
        self.thumbnail_cache_root = raw_config.get('thumbnailCacheRoot', '/data/thumbnails')
        os.makedirs(self.thumbnail_cache_root, exist_ok=True)
        
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
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user configuration by username."""
        for user in self.users:
            if user.get('username') == username:
                return user
        return None

