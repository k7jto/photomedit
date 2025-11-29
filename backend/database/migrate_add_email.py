"""Migration script to add email column to users table."""
import os
import sys
from sqlalchemy import text
from backend.database.models import get_engine

def migrate():
    """Add email column to users table if it doesn't exist."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check if email column exists
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'users'
            AND COLUMN_NAME = 'email'
        """))
        
        count = result.fetchone()[0]
        
        if count == 0:
            print("Adding email column to users table...")
            # Add email column
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN email VARCHAR(255) NOT NULL DEFAULT '' AFTER username,
                ADD INDEX idx_email (email)
            """))
            conn.commit()
            print("✅ Email column added successfully")
            
            # Update existing users with placeholder emails if needed
            conn.execute(text("""
                UPDATE users
                SET email = CONCAT(username, '@example.com')
                WHERE email = '' OR email IS NULL
            """))
            conn.commit()
            print("✅ Updated existing users with placeholder emails")
        else:
            print("Email column already exists")
    
    print("Migration complete!")

if __name__ == '__main__':
    migrate()

