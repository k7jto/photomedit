"""Database models for PhotoMedit."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import os

Base = declarative_base()


class User(Base):
    """User model."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='user')  # 'user' or 'admin'
    mfa_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'mfaEnabled': bool(self.mfa_secret),
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastLogin': self.last_login.isoformat() if self.last_login else None
        }


class LogEntry(Base):
    """Application log entry."""
    __tablename__ = 'logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR
    logger = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    user = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    details = Column(Text, nullable=True)  # JSON string for additional details


# Database connection setup
_engine = None
_SessionLocal = None

def get_database_url():
    """Get database URL from environment or config."""
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')
    db_name = os.getenv('DB_NAME', 'photomedit')
    db_user = os.getenv('DB_USER', 'photomedit')
    db_password = os.getenv('DB_PASSWORD', 'photomedit_password')
    
    return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        # SQLite doesn't support connect_timeout
        connect_args = {}
        if 'sqlite' not in db_url:
            connect_args = {'connect_timeout': 10}
        
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            connect_args=connect_args
        )
    return _engine


def get_session_local():
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=get_engine()))
    return _SessionLocal


# For backward compatibility
def SessionLocal():
    return get_session_local()

# For backward compatibility - but don't create at import time
db = None

