from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sa_text
from sqlmodel import Session, select

from ..db import get_session
from ..models import Category, Disclaimer, PackMetadata, ReferenceItem
from ..search import search_item_ids

router = APIRouter(prefix="/api/v1", tags=["reference"])

LIST_FIELDS_EXCLUDE = {"body_md"}  # list view stays lightweight


@router.get("/categories")
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category)).all()


@router.get("/items")
def list_items(
    category: str | None = None,
    q: str | None = None,
    tag: str | None = None,
    difficulty: str | None = None,
    session: Session = Depends(get_session),
):
    """Reference items, filterable by category, tag, difficulty, and search.

    Filters combine as AND: `q` narrows by FTS5 full-text search over
    title/summary/body/tags (token + trailing-prefix matching,
    case-insensitive), `tag` by exact tag membership, `difficulty` and
    `category` by column equality. Response shape is unchanged from the
    pre-FTS version. Unknown filter values simply match nothing; an
    empty/whitespace `q` is treated as absent.
    """
    stmt = select(ReferenceItem)
    if category:
        stmt = stmt.where(ReferenceItem.category_id == category)
    if difficulty:
        stmt = stmt.where(ReferenceItem.difficulty == difficulty)
    if tag:
        # Exact membership in the JSON tags array, evaluated in SQL.
        stmt = stmt.where(
            sa_text(
                "EXISTS (SELECT 1 FROM json_each(referenceitem.tags) je "
                "WHERE je.value = :tag)"
            ).bindparams(tag=tag)
        )
    items = session.exec(stmt).all()

    if q:
        ranked = search_item_ids(session, q)
        if ranked is not None:  # None = no usable tokens, treat as no filter
            position = {item_id: n for n, item_id in enumerate(ranked)}
            items = sorted(
                (i for i in items if i.id in position),
                key=lambda i: position[i.id],
            )
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
