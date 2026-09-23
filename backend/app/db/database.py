import importlib.util

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql") and importlib.util.find_spec("psycopg2") is None:
    DATABASE_URL = "sqlite:///./app.db"

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_schema_compatibility():
    if not str(engine.url).startswith("sqlite"):
        return

    with engine.begin() as conn:
        table_exists = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'")
        ).scalar()
        if table_exists is None:
            return

        columns = conn.execute(text("PRAGMA table_info(events)")).fetchall()
        has_event_metadata = any(row[1] == "event_metadata" for row in columns)
        if not has_event_metadata:
            conn.execute(text("ALTER TABLE events ADD COLUMN event_metadata TEXT"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
