from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import PracticeCase

router = APIRouter(prefix="/api/v1", tags=["cases"])

# List view omits the answer material so the UI can reveal it on demand.
LIST_FIELDS_EXCLUDE = {"guided_steps", "expected_outcome_md"}


@router.get("/cases")
def list_cases(session: Session = Depends(get_session)):
    cases = session.exec(select(PracticeCase)).all()
    return [c.model_dump(exclude=LIST_FIELDS_EXCLUDE) for c in cases]


@router.get("/cases/{case_id}")
def get_case(case_id: str, session: Session = Depends(get_session)):
    case = session.get(PracticeCase, case_id)
    if not case:
        raise HTTPException(404, "Practice case not found")
    return case
