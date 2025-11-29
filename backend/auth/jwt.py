"""JWT token handling."""
import jwt
import datetime
from typing import Optional, Dict, Any


class JWTManager:
    """JWT token manager."""
    
    def __init__(self, secret: str, expiration_hours: int = 24):
        self.secret = secret
        self.expiration_hours = expiration_hours
    
    def create_token(self, username: str) -> Dict[str, Any]:
        """Create a JWT token for a user."""
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(hours=self.expiration_hours)
        
        payload = {
            'username': username,
            'iat': now,
            'exp': expires_at
        }
        
        token = jwt.encode(payload, self.secret, algorithm='HS256')
        
        return {
            'token': token,
            'expiresAt': expires_at.isoformat() + 'Z'
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_username_from_token(self, token: str) -> Optional[str]:
        """Extract username from token."""
        payload = self.verify_token(token)
        if payload:
            return payload.get('username')
        return None

