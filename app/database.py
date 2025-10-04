from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import url as sa_url
from .config import settings
import sys

def initialize_database():
    """
    Initializes the database. Creates the database if it doesn't exist,
    then returns the engine connected to that database.
    """
    if not settings.DATABASE_URL:
        print("FATAL: DATABASE_URL is not set. Please configure it in your .env file.", file=sys.stderr)
        sys.exit(1)
    
    if "mysql" not in settings.DATABASE_URL:
        print(f"FATAL: The configured DATABASE_URL does not seem to be for MySQL: {settings.DATABASE_URL}", file=sys.stderr)
        sys.exit(1)

    try:
        full_db_url = sa_url.make_url(settings.DATABASE_URL)
        db_name = full_db_url.database

        # Connect to the server without the specific database to check/create it
        server_url = full_db_url.set(database="")
        server_engine = create_engine(server_url, echo=False)

        with server_engine.connect() as conn:
            print(f"--- Checking/creating database: '{db_name}' ---")
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
            conn.commit()
        print(f"--- Database '{db_name}' is ready. ---")

    except Exception as e:
        print(f"--- FATAL: Could not connect to MySQL server or create database. Error: {e}", file=sys.stderr)
        print("--- Please ensure your MySQL server is running and the DATABASE_URL in your .env file is correct.", file=sys.stderr)
        sys.exit(1)

    # Return the engine that connects to the specific database
    return create_engine(full_db_url)

# The engine is now created by our robust initialization function
engine = initialize_database()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
