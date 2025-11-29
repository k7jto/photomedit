"""MFA (Multi-Factor Authentication) utilities."""
import pyotp
import qrcode
import io
import base64
from typing import Optional, Tuple


class MFAManager:
    """Manage MFA setup and verification."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_provisioning_uri(username: str, secret: str, issuer: str = "PhotoMedit") -> str:
        """Get provisioning URI for QR code."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)
    
    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """Generate QR code as base64 data URL."""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_token(secret: str, token: str) -> bool:
        """Verify a TOTP token."""
        if not secret or not token:
            return False
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False

