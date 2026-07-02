"""Seed the SQLite database from data/seed.json (the content source of truth).

Upsert semantics: existing rows are updated, new rows inserted, so the script
is safe to re-run after editing seed.json.

Usage:
    python -m backend.app.seed
"""
import json
from pathlib import Path

from sqlmodel import Session, SQLModel

from .db import create_tables, engine
from .models import (
    Category,
    Disclaimer,
    PracticeCase,
    QuizQuestion,
    ReferenceItem,
    TrainingNote,
)

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "seed.json"

# seed.json key -> model, in insert order (FK parents first)
COLLECTIONS: list[tuple[str, type[SQLModel]]] = [
    ("disclaimers", Disclaimer),
    ("categories", Category),
    ("reference_items", ReferenceItem),
    ("training_notes", TrainingNote),
    ("practice_cases", PracticeCase),
    ("quiz_questions", QuizQuestion),
]


def seed(session: Session, seed_path: Path = SEED_PATH) -> dict[str, int]:
    """Load seed.json into the given session. Returns row counts per table."""
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for key, model in COLLECTIONS:
        rows = data.get(key, [])
        for row in rows:
            session.merge(model(**row))  # merge = upsert by primary key
        counts[key] = len(rows)
    session.commit()
    return counts


def main() -> None:
    create_tables()
    with Session(engine) as session:
        counts = seed(session)
    total = sum(counts.values())
    print(f"Seeded {total} rows into {engine.url.database}:")
    for key, n in counts.items():
        print(f"  {key:<16} {n}")


if __name__ == "__main__":
    main()
