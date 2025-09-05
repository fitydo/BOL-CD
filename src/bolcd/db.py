"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# Ensure data directory exists
data_dir = Path("data/db")
data_dir.mkdir(parents=True, exist_ok=True)

DB_URL = os.getenv("DB_URL", f"sqlite:///{data_dir}/bolcd.db")

# Create engine with appropriate settings
if DB_URL.startswith("sqlite"):
    engine = create_engine(
        DB_URL, 
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=os.getenv("DB_ECHO", "false").lower() == "true"
    )
else:
    engine = create_engine(
        DB_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=os.getenv("DB_ECHO", "false").lower() == "true"
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from src.bolcd.models.condense import Base
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at: {DB_URL}")
