"""Database setup: engine, table creation, and the FastAPI session dependency.

Tests override `get_session` with their own in-memory engine.
"""
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "navigatoredu.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
)


def create_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
