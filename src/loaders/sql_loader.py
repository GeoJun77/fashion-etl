# src/loaders/sql_loader.py
# Handles the connection between Python and the database

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.settings import settings


# Create the database engine (the main connection object)
engine = create_engine(
    settings.database_url,
    echo=False,        # set to True to see every SQL query in the logs
    pool_pre_ping=True # checks the connection is alive before using it
)

# Create a session factory (used to send queries)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """
    Creates all tables by reading schema.sql.
    Safe to run multiple times — uses CREATE IF NOT EXISTS.
    """
    schema_path = "database/schema.sql"

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()

    logger.info("Database initialized successfully")


def get_session():
    """
    Returns a database session.
    Always use it with a 'with' block to ensure it closes properly.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()