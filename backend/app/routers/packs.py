"""Content Pack Browser endpoints (local portfolio-demo feature).

GET  /api/v1/packs         — list the allowlisted bundled demo packs
POST /api/v1/packs/select  — reseed the local demo database from one of them

Scope and safety: this exists so a reviewer can flip the demo between the
bundled domains from the UI. Only slugs in the hard-coded allowlist
(pack_registry.REGISTRY) can be loaded; there is no path handling, no
upload, no scanning, and no filesystem information in any response. It is
deliberately not an admin or content-management feature — see
docs/ARCHITECTURE.md for the rationale. The SEED_PATH + `python -m
backend.app.seed` command-line workflow is unchanged and remains the
canonical way to load a pack outside the browser.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..db import get_session
from ..models import PackMetadata
from ..pack_registry import all_pack_summaries, pack_summary, seed_path_for
from ..seed import seed

router = APIRouter(prefix="/api/v1", tags=["packs"])


class PackSelection(BaseModel):
    slug: str


@router.get("/packs")
def list_packs(session: Session = Depends(get_session)):
    """All allowlisted demo packs, plus which one is currently active."""
    active = session.get(PackMetadata, 1)
    return {
        "active_pack_id": active.pack_id if active else None,
        "packs": all_pack_summaries(),
    }


@router.post("/packs/select")
def select_pack(selection: PackSelection, session: Session = Depends(get_session)):
    """Reseed the local demo database from an allowlisted pack.

    The slug is used only as a dictionary key into the allowlist — it is
    never treated as a path. Unknown slugs get a 404 listing nothing about
    the filesystem. Seeding is clear-then-load (see seed.py), so after this
    call the database holds exactly the selected pack.
    """
    try:
        path = seed_path_for(selection.slug)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Unknown pack. This demo can only load its bundled packs.",
        )
    counts = seed(session, seed_path=path)
    active = session.get(PackMetadata, 1)
    return {
        "loaded": pack_summary(selection.slug),
        "active_pack_id": active.pack_id if active else None,
        "counts": counts,
    }
