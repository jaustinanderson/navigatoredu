from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from .db import create_tables, engine
from .models import Category
from .routers import cases, packs, quiz, reference, training
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and auto-seed an empty database for first-run UX.

    Re-seed after editing seed.json with: python -m backend.app.seed
    """
    create_tables()
    with Session(engine) as session:
        if not session.exec(select(Category)).first():
            seed(session)
    yield


app = FastAPI(
    title="NavigatorEdu API",
    version="0.3.0",
    description="Fictional-domain reference and training demo. All content is synthetic.",
    lifespan=lifespan,
)

app.include_router(reference.router)
app.include_router(cases.router)
app.include_router(quiz.router)
app.include_router(packs.router)
app.include_router(training.router)

# Serve the single-page frontend at the root (mounted last so /api wins).
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
