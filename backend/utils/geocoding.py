"""Geocoding service."""
import time
import requests
from typing import Optional, Dict, Any
from backend.config.loader import Config


class GeocodingService:
    """Geocoding service using Nominatim."""
    
    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.geocoding_enabled
        self.user_agent = config.geocoding_user_agent
        self.rate_limit = config.geocoding_rate_limit
        self.last_request_time = 0.0
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        if not self.enabled:
            return
        
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
    
    def geocode(self, location_name: str) -> Optional[Dict[str, Any]]:
        """
        Geocode a location name to coordinates.
        
        Returns:
            {'lat': float, 'lon': float} or None
        """
        if not self.enabled or not location_name:
            return None
        
        self._rate_limit()
        
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': location_name,
                'format': 'json',
                'limit': 1
            }
            headers = {
                'User-Agent': self.user_agent
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                return {
                    'lat': float(result.get('lat', 0)),
                    'lon': float(result.get('lon', 0))
                }
        except Exception:
            # Log error but don't fail the request
            pass
        
        return None

