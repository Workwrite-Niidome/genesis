"""
Database configuration for STRUCT CODE Clean
Simple SQLite setup only
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL (PostgreSQL on Railway or SQLite locally)
raw_url = os.getenv("DATABASE_URL")
print(f"=== DATABASE CONFIG ===")
print(f"DATABASE_URL env: {'SET' if raw_url else 'NOT SET'}")

if raw_url:
    DATABASE_URL = raw_url
    # Railway uses postgres:// but SQLAlchemy requires postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"DATABASE: Using PostgreSQL")
else:
    DATABASE_URL = "sqlite:///./struct_code.db"
    print(f"DATABASE: Using SQLite (fallback)")

SQLALCHEMY_DATABASE_URL = DATABASE_URL
print(f"=======================")

# Create engine
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL with connection pool settings
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,  # Check connection before use
        pool_recycle=300,    # Recycle connections after 5 minutes
        pool_size=5,
        max_overflow=10
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
