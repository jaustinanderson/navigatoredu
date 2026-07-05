from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import QuizQuestion
from ..report import build_report_html

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


@router.post("/quiz/report", response_class=HTMLResponse)
def quiz_report(
    submission: QuizSubmission, session: Session = Depends(get_session)
):
    """A self-contained, printable HTML learning report for one attempt.

    Same payload as /quiz/submit; generated statelessly from the submitted
    answers plus the loaded pack — nothing is stored (no accounts, no
    tables, no history). All pack content and submitted values are
    HTML-escaped by the builder.
    """
    try:
        html_doc = build_report_html(session, submission.answers)
    except KeyError as e:
        raise HTTPException(400, f"Unknown question id: {e.args[0]}")
    return HTMLResponse(
        content=html_doc,
        headers={
            "Content-Disposition":
                'attachment; filename="navigatoredu-quiz-report.html"'
        },
    )
