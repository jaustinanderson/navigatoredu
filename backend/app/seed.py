"""Seed the SQLite database from a JSON content pack.

The seed file is the content source of truth. Which file to load is
controlled by the SEED_PATH environment variable, defaulting to
data/seed.json (the Tidewatch Guild pack). Swapping packs requires zero
code changes:

    SEED_PATH=data/seed_archiveguild.json python -m backend.app.seed

Upsert semantics: existing rows are updated, new rows inserted, so the
script is safe to re-run after editing a seed file.
"""
import json
import os
from pathlib import Path

from sqlmodel import Session, SQLModel

from .db import create_tables, engine
from .models import (
    Category,
    Disclaimer,
    PackMetadata,
    PracticeCase,
    QuizQuestion,
    ReferenceItem,
    TrainingNote,
)

METADATA_KEY = "metadata"
METADATA_FIELDS = [
    "pack_id", "pack_name", "pack_version", "pack_description",
    "domain_type", "synthetic_only", "intended_use", "safety_notes",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_PATH = PROJECT_ROOT / "data" / "seed.json"

# seed file key -> model, in insert order (FK parents first)
COLLECTIONS: list[tuple[str, type[SQLModel]]] = [
    ("disclaimers", Disclaimer),
    ("categories", Category),
    ("reference_items", ReferenceItem),
    ("training_notes", TrainingNote),
    ("practice_cases", PracticeCase),
    ("quiz_questions", QuizQuestion),
]


def get_seed_path() -> Path:
    """Resolve the active seed file from SEED_PATH (read at call time so
    tests and containers can set it without re-importing the module).
    Relative paths are resolved against the project root."""
    raw = os.environ.get("SEED_PATH")
    if not raw:
        return DEFAULT_SEED_PATH
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def seed(session: Session, seed_path: Path | None = None) -> dict[str, int]:
    """Load a seed file into the given session. Returns row counts per table."""
    path = seed_path or get_seed_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for key, model in COLLECTIONS:
        rows = data.get(key, [])
        for row in rows:
            session.merge(model(**row))  # merge = upsert by primary key
        counts[key] = len(rows)

    # Upsert the single metadata row (id=1) describing this pack.
    meta = data.get(METADATA_KEY, {})
    if meta:
        session.merge(PackMetadata(id=1, **{f: meta[f] for f in METADATA_FIELDS}))
        counts[METADATA_KEY] = 1

    session.commit()
    return counts


def main() -> None:
    path = get_seed_path()
    create_tables()
    with Session(engine) as session:
        counts = seed(session, path)
    total = sum(counts.values())
    print(f"Seeded {total} rows from {path.name} into {engine.url.database}:")
    for key, n in counts.items():
        print(f"  {key:<16} {n}")


if __name__ == "__main__":
    main()
