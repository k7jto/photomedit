"""Logging service for database operations."""
from backend.database.models import LogEntry, get_session_local
from datetime import datetime
from typing import Optional, Dict, Any
import json
import logging

# Get database session
def get_db():
    return get_session_local()()

logger = logging.getLogger(__name__)


class LogService:
    """Service for application logging to database."""
    
    @staticmethod
    def log(level: str, message: str, logger_name: str = None, user: str = None, 
            ip_address: str = None, details: Dict[str, Any] = None):
        """Create a log entry."""
        db = get_db()
        try:
            log_entry = LogEntry(
                level=level.upper(),
                logger=logger_name,
                message=message,
                user=user,
                ip_address=ip_address,
                details=json.dumps(details) if details else None
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            # Don't fail if logging fails - just log to standard logger
            logger.error(f"Failed to write log entry to database: {e}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def get_logs(limit: int = 100, level: str = None, user: str = None):
        """Get recent log entries."""
        db = get_db()
        try:
            query = db.query(LogEntry)
            if level:
                query = query.filter(LogEntry.level == level.upper())
            if user:
                query = query.filter(LogEntry.user == user)
            return query.order_by(LogEntry.timestamp.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return []
        finally:
            db.close()

