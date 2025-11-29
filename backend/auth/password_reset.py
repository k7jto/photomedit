"""Password reset token management."""
import secrets
import time
from typing import Optional, Dict
from datetime import datetime, timedelta


class PasswordResetManager:
    """Manage password reset tokens."""
    
    # In-memory store for reset tokens (in production, use Redis or database)
    _reset_tokens: Dict[str, Dict] = {}
    
    @classmethod
    def generate_reset_token(cls, username: str, expiry_minutes: int = 60) -> str:
        """Generate a password reset token."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=expiry_minutes)
        
        cls._reset_tokens[token] = {
            'username': username,
            'expires_at': expires_at.timestamp()
        }
        
        return token
    
    @classmethod
    def verify_reset_token(cls, token: str) -> Optional[str]:
        """Verify a reset token and return username if valid."""
        if token not in cls._reset_tokens:
            return None
        
        token_data = cls._reset_tokens[token]
        if datetime.now().timestamp() > token_data['expires_at']:
            # Token expired, remove it
            del cls._reset_tokens[token]
            return None
        
        return token_data['username']
    
    @classmethod
    def consume_reset_token(cls, token: str) -> Optional[str]:
        """Verify and consume (delete) a reset token."""
        username = cls.verify_reset_token(token)
        if username:
            del cls._reset_tokens[token]
        return username

