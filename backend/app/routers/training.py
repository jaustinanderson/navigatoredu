from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import TrainingNote

router = APIRouter(prefix="/api/v1", tags=["training"])


@router.get("/training")
def list_training_notes(session: Session = Depends(get_session)):
    """All training notes, ordered by module then lesson order.

    The frontend groups notes by module; keeping grouping client-side keeps
    this endpoint a plain, cacheable list.
    """
    stmt = select(TrainingNote).order_by(TrainingNote.module, TrainingNote.order)
    return session.exec(stmt).all()
