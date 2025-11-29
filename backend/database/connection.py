"""Database connection and initialization."""
from backend.database.models import Base, get_engine
import logging

logger = logging.getLogger(__name__)


def init_db():
    """Initialize database tables."""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_db_session():
    """Get a database session."""
    return SessionLocal()

