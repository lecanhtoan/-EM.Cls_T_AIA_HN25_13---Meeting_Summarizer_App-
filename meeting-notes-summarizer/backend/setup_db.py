"""
Database setup script for Meeting Notes Summarizer.
Creates all tables and initializes the database.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from app.models import Base, User


def setup_database():
    """Create all tables and initialize default data."""
    
    print("Setting up database...")
    
    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")
    
    # Create default user for MVP
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if default user exists
        existing_user = session.query(User).filter(User.id == 1).first()
        if not existing_user:
            print("Creating default user...")
            default_user = User(
                id=1,
                email="demo@example.com",
                full_name="Demo User"
            )
            session.add(default_user)
            session.commit()
            print("✓ Default user created")
        else:
            print("✓ Default user already exists")
    
    finally:
        session.close()
    
    print("\n✓ Database setup completed successfully!")
    print("\nYou can now run the application with:")
    print("  python -m uvicorn app.main:app --reload")


if __name__ == "__main__":
    try:
        setup_database()
    except Exception as e:
        print(f"\n✗ Error setting up database: {e}")
        sys.exit(1)


