"""Scaffold a new content pack from a valid, safe skeleton.

Hand-copying an existing pack to start a new one is error-prone: it drags along
another domain's IDs and content, and it's easy to forget a governance field.
This command instead emits a *minimal, fully-wired* pack that passes the
validator immediately, so authors start from a green baseline and only ever
add content — they never have to reconstruct the contract.

Usage:
    python -m backend.app.new_pack demo_pack
    python -m backend.app.new_pack demo_pack --force

The slug names both the output file and the pack_id:

    demo_pack  ->  data/seed_demo_pack.json   (pack_id "demo_pack")

Safety defaults are baked in, not optional: every generated pack is
synthetic_only, is labelled educational-demo-only, and carries safety_notes
stating no real records / no real cases / no operational or clinical use.

Exit codes: 0 = created, 1 = refused (file exists; re-run with --force),
2 = bad usage or invalid slug (nothing written).
"""
import json
import re
import sys
from pathlib import Path

# Slugs become filenames and pack_ids, so keep them boring and portable:
# a lowercase letter followed by lowercase letters, digits, or underscores.
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_SLUG_LEN = 40

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# Baked-in governance defaults. These are the whole point of the skeleton:
# a new pack cannot be born without them, so it cannot silently ship unsafe.
SYNTHETIC_ONLY = True
INTENDED_USE = (
    "Educational demonstration only. This pack exists to teach and to show "
    "structure in a portfolio; it is not for real-world, operational, "
    "clinical, diagnostic, or decision-making use."
)
SAFETY_NOTES = (
    "No real records, no real cases, no real identifiers. Fully synthetic and "
    "fictional. Not validated for any operational or clinical use, and must "
    "not be used to interpret real data or make real decisions."
)


class SlugError(ValueError):
    """The requested slug is not usable as a pack id / filename."""


class PackExistsError(FileExistsError):
    """Refusing to overwrite an existing pack without --force."""


def validate_slug(slug: str) -> str:
    """Return the slug if usable, else raise SlugError with a clear reason."""
    if not slug:
        raise SlugError("slug is empty")
    if len(slug) > MAX_SLUG_LEN:
        raise SlugError(f"slug too long (max {MAX_SLUG_LEN} characters): {slug!r}")
    if not SLUG_PATTERN.match(slug):
        raise SlugError(
            f"invalid slug {slug!r}: use lowercase letters, digits, and "
            "underscores only, starting with a letter (e.g. 'demo_pack')"
        )
    return slug


def _title_from_slug(slug: str) -> str:
    """demo_pack -> 'Demo Pack' (for human-facing names in the skeleton)."""
    return " ".join(word.capitalize() for word in slug.split("_"))


def build_skeleton(slug: str) -> dict:
    """Build a minimal, fully-wired, valid pack for the given slug.

    Every foreign key resolves, the one quiz question is answerable, and the
    metadata carries the baked-in safety defaults. The records are obvious
    placeholders ("TODO: replace") so an author knows exactly what to edit —
    but they are *valid* placeholders, so the pack is green from the first run.
    """
    title = _title_from_slug(slug)
    return {
        "metadata": {
            "pack_id": slug,
            "pack_name": f"{title} (Synthetic Starter Pack)",
            "pack_version": "0.1.0",
            "pack_description": (
                f"Starter skeleton for the '{slug}' content pack. Replace these "
                "placeholder records with your own fully synthetic content."
            ),
            "domain_type": "synthetic_education",
            "synthetic_only": SYNTHETIC_ONLY,
            "intended_use": INTENDED_USE,
            "safety_notes": SAFETY_NOTES,
        },
        # Legacy descriptive block carried by every shipped pack for uniformity.
        "meta": {
            "app": "NavigatorEdu",
            "domain": f"{title} — synthetic starter pack (fictional)",
            "is_synthetic": True,
            "version": "0.1.0",
        },
        "disclaimers": [
            {
                "id": "d1",
                "applies_to": "global",
                "text": (
                    "Educational and portfolio demonstration only. All content "
                    "in this pack is fully synthetic and fictional. It contains "
                    "no real records, no real cases, and no real identifiers, "
                    "and it is not validated for any operational or clinical "
                    "use. Do not use it to interpret real data or make real "
                    "decisions."
                ),
            }
        ],
        "categories": [
            {
                "id": "cat-getting-started",
                "name": "Getting Started",
                "slug": "getting-started",
                "description": (
                    "TODO: replace. A starter category describing one area of "
                    "this synthetic pack."
                ),
                "parent_id": None,
            }
        ],
        "reference_items": [
            {
                "id": "ref-001",
                "category_id": "cat-getting-started",
                "title": "TODO: Replace This Reference Item",
                "summary": (
                    "A one-line summary of a synthetic reference concept."
                ),
                "body_md": (
                    "# TODO: Replace\n\n"
                    "This is a **synthetic** starter reference item. Replace the "
                    "title, summary, and this body with your own fictional, "
                    "educational content.\n\n"
                    "- Keep everything invented.\n"
                    "- Use no real records, cases, or identifiers.\n"
                ),
                "tags": ["starter", "synthetic", "todo"],
                "difficulty": "beginner",
                "disclaimer_id": "d1",
            }
        ],
        "training_notes": [
            {
                "id": "tn-001",
                "module": "Foundations",
                "order": 1,
                "title": "TODO: Replace This Training Note",
                "body_md": (
                    "A short synthetic training note. Replace with your own "
                    "educational explanation, and point `related_item_ids` at "
                    "the reference items it supports."
                ),
                "related_item_ids": ["ref-001"],
            }
        ],
        "practice_cases": [
            {
                "id": "case-001",
                "category_id": "cat-getting-started",
                "title": "TODO: Replace This Practice Case",
                "scenario_md": (
                    "A fully fictional scenario for the learner to work "
                    "through. Replace with your own synthetic case."
                ),
                "guided_steps": [
                    "TODO: first guided step.",
                    "TODO: second guided step.",
                ],
                "expected_outcome_md": (
                    "**TODO:** describe the expected reasoning and outcome for "
                    "this synthetic case."
                ),
                "difficulty": "beginner",
            }
        ],
        "quiz_questions": [
            {
                "id": "q-001",
                "category_id": "cat-getting-started",
                "question": "TODO: replace — is every record in this pack synthetic?",
                "options": ["Yes", "No"],
                "correct_index": 0,
                "explanation": (
                    "Every NavigatorEdu content pack is synthetic-only by "
                    "design. Replace this placeholder with a real question "
                    "about your synthetic content."
                ),
                "source_item_id": "ref-001",
            }
        ],
    }


def output_path(slug: str, data_dir: Path | str | None = None) -> Path:
    """Where the pack for this slug will be written.

    data_dir defaults to None (not DATA_DIR directly) so the module-level
    DATA_DIR is read at call time — this keeps the CLI redirectable in tests
    that monkeypatch new_pack.DATA_DIR.
    """
    base = Path(data_dir) if data_dir is not None else DATA_DIR
    return base / f"seed_{slug}.json"


def new_pack(
    slug: str,
    data_dir: Path | str | None = None,
    force: bool = False,
) -> Path:
    """Create data/seed_<slug>.json from the skeleton. Return the written path.

    Raises SlugError for a bad slug and PackExistsError if the target exists
    and force is False. data_dir is injectable so tests write to a temp dir and
    never leave artifacts in the real data/ directory.
    """
    slug = validate_slug(slug)
    data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
    path = output_path(slug, data_dir)
    if path.exists() and not force:
        raise PackExistsError(
            f"{path} already exists; re-run with --force to overwrite"
        )
    data_dir.mkdir(parents=True, exist_ok=True)
    skeleton = build_skeleton(slug)
    path.write_text(
        json.dumps(skeleton, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _parse_args(argv: list[str]) -> tuple[str | None, bool]:
    """Tiny hand-rolled parser: <slug> with an optional --force flag."""
    force = False
    positional: list[str] = []
    for arg in argv:
        if arg in ("--force", "-f"):
            force = True
        else:
            positional.append(arg)
    slug = positional[0] if len(positional) == 1 else None
    return slug, force


def main(argv: list[str]) -> int:
    slug, force = _parse_args(argv)
    if slug is None:
        print(
            "usage: python -m backend.app.new_pack <slug> [--force]\n"
            "  <slug>: lowercase letters, digits, underscores; start with a "
            "letter (e.g. demo_pack)"
        )
        return 2
    try:
        slug = validate_slug(slug)
    except SlugError as e:
        print(f"error: {e}")
        return 2

    path = output_path(slug)
    try:
        new_pack(slug, force=force)
    except PackExistsError as e:
        print(f"refused: {e}")
        return 1

    print(f"Created {path}")
    print("Next steps:")
    print(f"  1. Edit {path} — replace the TODO placeholder records.")
    print(f"  2. Validate:  python -m backend.app.validate_pack {path}")
    print(f"  3. Seed:      SEED_PATH={path} python -m backend.app.seed")
    print("  4. Run:       uvicorn backend.app.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
