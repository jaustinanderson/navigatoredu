from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Category, Disclaimer, PackMetadata, ReferenceItem

router = APIRouter(prefix="/api/v1", tags=["reference"])

LIST_FIELDS_EXCLUDE = {"body_md"}  # list view stays lightweight


@router.get("/categories")
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category)).all()


@router.get("/items")
def list_items(
    category: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(ReferenceItem)
    if category:
        stmt = stmt.where(ReferenceItem.category_id == category)
    items = session.exec(stmt).all()

    # Text search across title/summary/tags. In-Python matching is fine at
    # this scale; SQLite FTS5 is the upgrade path if the corpus grows.
    if q:
        needle = q.lower()
        items = [
            i for i in items
            if needle in i.title.lower()
            or needle in i.summary.lower()
            or any(needle in t for t in i.tags)
        ]
    return [i.model_dump(exclude=LIST_FIELDS_EXCLUDE) for i in items]


@router.get("/items/{item_id}")
def get_item(item_id: str, session: Session = Depends(get_session)):
    item = session.get(ReferenceItem, item_id)
    if not item:
        raise HTTPException(404, "Reference item not found")
    return item


@router.get("/disclaimers")
def list_disclaimers(session: Session = Depends(get_session)):
    return session.exec(select(Disclaimer)).all()


@router.get("/pack-metadata")
def get_pack_metadata(session: Session = Depends(get_session)):
    """Metadata for the content pack currently loaded in the database."""
    meta = session.get(PackMetadata, 1)
    if not meta:
        raise HTTPException(404, "No pack metadata loaded")
    return meta
