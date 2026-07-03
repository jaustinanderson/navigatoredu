"""Validate a content pack before import.

A content pack is only a real interface if something enforces its contract.
This validator checks structure, required fields, ID uniqueness, foreign
references, and quiz-answer sanity — without touching the database.

Usage:
    python -m backend.app.validate_pack data/seed.json
    python -m backend.app.validate_pack data/seed_archiveguild.json

Exit codes: 0 = valid, 1 = invalid (all problems listed), 2 = unreadable file.
"""
import json
import sys
from pathlib import Path

# Collection name -> fields every record must have.
REQUIRED_FIELDS: dict[str, set[str]] = {
    "disclaimers": {"id", "applies_to", "text"},
    "categories": {"id", "name", "slug", "description"},
    "reference_items": {
        "id", "category_id", "title", "summary", "body_md",
        "tags", "difficulty", "disclaimer_id",
    },
    "training_notes": {"id", "module", "order", "title", "body_md", "related_item_ids"},
    "practice_cases": {
        "id", "category_id", "title", "scenario_md",
        "guided_steps", "expected_outcome_md", "difficulty",
    },
    "quiz_questions": {
        "id", "category_id", "question", "options",
        "correct_index", "explanation", "source_item_id",
    },
}


def _ids(records: list[dict]) -> set[str]:
    return {r["id"] for r in records if isinstance(r, dict) and "id" in r}


def validate_pack(path: Path | str) -> list[str]:
    """Return a list of human-readable problems. Empty list = valid pack."""
    path = Path(path)
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))  # may raise; CLI handles

    # 1. Top-level structure
    for key in REQUIRED_FIELDS:
        if key not in data:
            errors.append(f"missing top-level key: '{key}'")
        elif not isinstance(data[key], list):
            errors.append(f"'{key}' must be a list")
    if errors:
        return errors  # structure is broken; deeper checks would just cascade

    # 2. Required fields + unique IDs, per collection
    for key, required in REQUIRED_FIELDS.items():
        seen: set[str] = set()
        for n, record in enumerate(data[key]):
            label = f"{key}[{n}]"
            if not isinstance(record, dict):
                errors.append(f"{label}: record must be an object")
                continue
            missing = required - record.keys()
            if missing:
                errors.append(f"{label} ({record.get('id', '?')}): missing fields {sorted(missing)}")
            rid = record.get("id")
            if rid in seen:
                errors.append(f"{label}: duplicate id '{rid}'")
            if rid:
                seen.add(rid)

    # 3. Foreign references
    category_ids = _ids(data["categories"])
    item_ids = _ids(data["reference_items"])
    disclaimer_ids = _ids(data["disclaimers"])

    for parent_key, fk_field, valid_ids, target in [
        ("reference_items", "category_id", category_ids, "categories"),
        ("reference_items", "disclaimer_id", disclaimer_ids, "disclaimers"),
        ("practice_cases", "category_id", category_ids, "categories"),
        ("quiz_questions", "category_id", category_ids, "categories"),
        ("quiz_questions", "source_item_id", item_ids, "reference_items"),
    ]:
        for record in data[parent_key]:
            value = record.get(fk_field)
            if value is not None and value not in valid_ids:
                errors.append(
                    f"{parent_key} '{record.get('id', '?')}': "
                    f"{fk_field} '{value}' not found in {target}"
                )

    for note in data["training_notes"]:
        for ref in note.get("related_item_ids", []):
            if ref not in item_ids:
                errors.append(
                    f"training_notes '{note.get('id', '?')}': "
                    f"related_item_id '{ref}' not found in reference_items"
                )

    # 4. Quiz sanity: options non-empty, correct_index in range
    for q in data["quiz_questions"]:
        options = q.get("options", [])
        idx = q.get("correct_index")
        if not options:
            errors.append(f"quiz_questions '{q.get('id', '?')}': options is empty")
        elif not isinstance(idx, int) or not (0 <= idx < len(options)):
            errors.append(
                f"quiz_questions '{q.get('id', '?')}': "
                f"correct_index {idx!r} out of range for {len(options)} options"
            )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m backend.app.validate_pack <path/to/pack.json>")
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"error: file not found: {path}")
        return 2
    try:
        errors = validate_pack(path)
    except json.JSONDecodeError as e:
        print(f"error: {path} is not valid JSON: {e}")
        return 2

    if errors:
        print(f"INVALID: {path} — {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {path} is a valid content pack.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
