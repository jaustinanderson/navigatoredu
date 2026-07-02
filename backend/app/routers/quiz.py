from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import QuizQuestion

router = APIRouter(prefix="/api/v1", tags=["quiz"])

# Answers and explanations never leave the server on GET.
LIST_FIELDS_EXCLUDE = {"correct_index", "explanation"}


@router.get("/quiz")
def get_quiz(category: str | None = None, session: Session = Depends(get_session)):
    stmt = select(QuizQuestion)
    if category:
        stmt = stmt.where(QuizQuestion.category_id == category)
    questions = session.exec(stmt).all()
    return [q.model_dump(exclude=LIST_FIELDS_EXCLUDE) for q in questions]


class QuizSubmission(BaseModel):
    answers: dict[str, int]  # question_id -> selected option index


@router.post("/quiz/submit")
def submit_quiz(
    submission: QuizSubmission, session: Session = Depends(get_session)
):
    results = []
    score = 0
    for qid, selected in submission.answers.items():
        q = session.get(QuizQuestion, qid)
        if not q:
            raise HTTPException(400, f"Unknown question id: {qid}")
        correct = selected == q.correct_index
        score += correct
        results.append({
            "question_id": qid,
            "correct": correct,
            "correct_index": q.correct_index,
            "explanation": q.explanation,
        })
    return {"score": score, "total": len(results), "results": results}
