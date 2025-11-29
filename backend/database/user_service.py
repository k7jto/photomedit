"""User service for database operations."""
from sqlalchemy.exc import IntegrityError
from backend.database.models import User, get_session_local
from datetime import datetime
import logging

# Get database session
def get_db():
    return get_session_local()()

logger = logging.getLogger(__name__)


class UserService:
    """Service for user database operations."""
    
    @staticmethod
    def get_user(username: str = None, email: str = None):
        """Get user by username or email."""
        db = get_db()
        try:
            if username:
                return db.query(User).filter(User.username == username).first()
            elif email:
                return db.query(User).filter(User.email == email).first()
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def get_user_by_id(user_id: int):
        """Get user by ID."""
        db = get_db()
        try:
            return db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def list_users():
        """List all users."""
        db = get_db()
        try:
            return db.query(User).order_by(User.username).all()
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def create_user(username: str, email: str, password_hash: str, role: str = 'user', mfa_secret: str = None):
        """Create a new user."""
        db = get_db()
        try:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                mfa_secret=mfa_secret
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created user: {username} with email: {email} and role: {role}")
            return user
        except IntegrityError:
            db.rollback()
            logger.warning(f"User {username} or email {email} already exists")
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user {username}: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def update_user(user: User, email: str = None, password_hash: str = None, role: str = None, mfa_secret: str = None):
        """Update user."""
        db = get_db()
        try:
            # Re-fetch user to ensure we have the latest version
            db_user = db.query(User).filter(User.id == user.id).first()
            if not db_user:
                return None
            
            if email is not None:
                db_user.email = email
            if password_hash is not None:
                db_user.password_hash = password_hash
            if role is not None:
                db_user.role = role
            if mfa_secret is not None:
                if mfa_secret == '':
                    db_user.mfa_secret = None
                else:
                    db_user.mfa_secret = mfa_secret
            db.commit()
            db.refresh(db_user)
            logger.info(f"Updated user: {db_user.username}")
            return db_user
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user {user.username}: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def delete_user(user: User):
        """Delete user."""
        db = get_db()
        try:
            username = user.username
            db_user = db.query(User).filter(User.id == user.id).first()
            if db_user:
                db.delete(db_user)
                db.commit()
                logger.info(f"Deleted user: {username}")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting user {user.username}: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def update_last_login(username: str):
        """Update user's last login timestamp."""
        db = get_db()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user:
                user.last_login = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating last login for {username}: {e}")
            return False
        finally:
            db.close()

