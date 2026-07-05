"""Allowlisted registry of the demo content packs bundled with the repo.

This exists for the local-demo Content Pack Browser (GET /api/v1/packs and
POST /api/v1/packs/select). It is deliberately a hard-coded allowlist:

- Only packs named here can be listed or loaded. There is no filesystem
  scanning and no user-supplied path handling anywhere in the feature, so a
  request can never cause the server to read an arbitrary file.
- Seed file paths stay server-side. API responses expose the slug and the
  pack's own governance metadata, never a filesystem path.
- This is a portfolio/local-demo convenience only — it is what lets a
  reviewer flip between domains from the UI. It is intentionally not an
  upload or admin feature; a real multi-tenant content system would need
  authentication, audit, and storage design that is out of scope here.

The registry stores only the slug -> seed-file mapping. Display metadata
(name, description, domain type, intended use, safety notes, synthetic flag)
is read from each pack's own governance `metadata` object, so this module
can never drift out of sync with the packs themselves.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# The allowlist. Keys are the public slugs used by the API; values are seed
# filenames inside data/ (relative on purpose — never taken from a request).
REGISTRY: dict[str, str] = {
    "tidewatch": "seed.json",
    "archiveguild": "seed_archiveguild.json",
    "cytofish": "seed_cytofish_synthetic.json",
}


def allowed_slugs() -> list[str]:
    return list(REGISTRY)


def seed_path_for(slug: str) -> Path:
    """Resolve an allowlisted slug to its bundled seed file.

    Raises KeyError for anything not in the allowlist — callers translate
    that into a 404. Slugs are dict keys, never path fragments, so no
    user-controlled string ever touches the filesystem.
    """
    return DATA_DIR / REGISTRY[slug]


def pack_summary(slug: str) -> dict:
    """Public description of one allowlisted pack, from its own metadata.

    Returns the slug plus the pack's governance metadata fields. Filesystem
    paths are intentionally not included.
    """
    data = json.loads(seed_path_for(slug).read_text(encoding="utf-8"))
    meta = data.get("metadata", {})
    return {
        "slug": slug,
        "pack_id": meta.get("pack_id", ""),
        "pack_name": meta.get("pack_name", ""),
        "pack_version": meta.get("pack_version", ""),
        "pack_description": meta.get("pack_description", ""),
        "domain_type": meta.get("domain_type", ""),
        "synthetic_only": meta.get("synthetic_only", True),
        "intended_use": meta.get("intended_use", ""),
        "safety_notes": meta.get("safety_notes", ""),
    }


def all_pack_summaries() -> list[dict]:
    return [pack_summary(slug) for slug in REGISTRY]
