"""Seed the SQLite database from a JSON content pack.

The seed file is the content source of truth. Which file to load is
controlled by the SEED_PATH environment variable, defaulting to
data/seed.json (the Tidewatch Guild pack). Swapping packs requires zero
code changes:

    SEED_PATH=data/seed_archiveguild.json python -m backend.app.seed

Clear-then-load semantics: seeding first clears all content tables, then
loads only the selected pack. The database therefore always holds exactly
one pack — the one named by the metadata endpoint — and re-seeding (after
an edit, or to switch domains) converges to the selected pack's content.
"""
import json
import os
from pathlib import Path

from sqlmodel import Session, SQLModel, delete

from .db import create_tables, engine
from .search import rebuild_fts
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

# Deletion order: children before parents, so FK constraints can never trip.
CLEAR_ORDER: list[type[SQLModel]] = [
    QuizQuestion, PracticeCase, TrainingNote,
    ReferenceItem, Category, Disclaimer, PackMetadata,
]


def clear_content(session: Session) -> None:
    """Remove all pack content (and pack metadata) from the database.

    Packs use their own ID schemes, so upserting one pack over another would
    leave the first pack's rows behind — with the metadata endpoint then
    naming a pack whose content is mixed with a stale one. Clearing first
    guarantees the database always reflects exactly one pack.
    """
    for model in CLEAR_ORDER:
        session.exec(delete(model))


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
    """Clear existing content, then load a seed file into the given session.

    Returns row counts per table. Clearing first means the database always
    holds exactly one pack (see clear_content), and re-seeding after an edit
    still converges: the call is idempotent for a given pack file.
    """
    path = seed_path or get_seed_path()
    data = json.loads(path.read_text(encoding="utf-8"))

    clear_content(session)

    counts: dict[str, int] = {}
    for key, model in COLLECTIONS:
        rows = data.get(key, [])
        for row in rows:
            session.add(model(**row))  # tables were just cleared: plain inserts
        counts[key] = len(rows)

    # The single metadata row (id=1) describing this pack.
    meta = data.get(METADATA_KEY, {})
    if meta:
        session.add(PackMetadata(id=1, **{f: meta[f] for f in METADATA_FIELDS}))
        counts[METADATA_KEY] = 1

    # Rebuild the FTS5 search index from exactly what was just loaded. Seeding
    # is the only content write path, so this keeps search perfectly in sync
    # with the active pack across CLI seeds and pack-browser switches alike.
    counts["fts_indexed"] = rebuild_fts(session)

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
