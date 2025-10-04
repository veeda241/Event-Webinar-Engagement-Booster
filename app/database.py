from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings # Import the centralized settings

if not settings.DATABASE_URL:
    raise RuntimeError("FATAL: DATABASE_URL is not set. Please configure it in your .env file.")
elif settings.DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "FATAL: SQLite database is not supported for this application. "
        "Please configure a MySQL DATABASE_URL in your .env file."
    )

# The engine now reads the URL directly from the settings object.
engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()