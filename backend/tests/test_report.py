"""Tests for the exportable learning report (POST /quiz/report, v14).

The escaping tests inject hostile content directly into an isolated
database — a question, option, explanation, reference title, and pack
metadata all carrying script/HTML payloads — and assert none of it survives
unescaped into the report document.
"""
import html as html_mod

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from backend.app.db import get_session
from backend.app.main import app
from backend.app.models import PackMetadata, QuizQuestion, ReferenceItem
from backend.app.seed import DEFAULT_SEED_PATH, PROJECT_ROOT, seed

CYTOFISH_PACK = PROJECT_ROOT / "data" / "seed_cytofish_synthetic.json"


def _make_client(seed_path=DEFAULT_SEED_PATH, mutate=None):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, seed_path=seed_path)
        if mutate:
            mutate(session)
            session.commit()

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    return TestClient(app)


@pytest.fixture()
def report_client():
    client = _make_client()
    with client as c:
        yield c
    app.dependency_overrides.clear()


def _some_questions(client, n=3):
    qs = client.get("/api/v1/quiz").json()[:n]
    return {q["id"]: 0 for q in qs}, qs


class TestReportEndpoint:
    def test_returns_html_document(self, report_client):
        answers, _ = _some_questions(report_client)
        r = report_client.post("/api/v1/quiz/report", json={"answers": answers})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert r.text.startswith("<!DOCTYPE html>")
        assert "attachment" in r.headers.get("content-disposition", "")
        # Self-contained: no external assets.
        assert "http://" not in r.text and "https://" not in r.text
        assert "<script" not in r.text

    def test_score_summary_matches_submit(self, report_client):
        answers, _ = _some_questions(report_client)
        submit = report_client.post(
            "/api/v1/quiz/submit", json={"answers": answers}
        ).json()
        html = report_client.post(
            "/api/v1/quiz/report", json={"answers": answers}
        ).text
        percent = round(100 * submit["score"] / submit["total"])
        assert f"{submit['score']} / {submit['total']} ({percent}%)" in html

    def test_per_question_content(self, report_client):
        answers, qs = _some_questions(report_client, n=2)
        html = report_client.post(
            "/api/v1/quiz/report", json={"answers": answers}
        ).text
        for q in qs:
            # Compare escaped forms: apostrophes etc. are (correctly) escaped.
            assert html_mod.escape(q["question"], quote=True) in html
            assert html_mod.escape(q["options"][0], quote=True) in html
        assert "Your answer:" in html and "Correct answer:" in html
        assert "Explanation:" in html
        assert ("Correct" in html) or ("Incorrect" in html)

    def test_uses_submitted_answers(self, report_client):
        _, qs = _some_questions(report_client, n=1)
        q = qs[0]
        html_a = report_client.post(
            "/api/v1/quiz/report", json={"answers": {q["id"]: 0}}
        ).text
        html_b = report_client.post(
            "/api/v1/quiz/report", json={"answers": {q["id"]: 1}}
        ).text
        opt0 = html_mod.escape(q["options"][0], quote=True)
        opt1 = html_mod.escape(q["options"][1], quote=True)
        assert f"<strong>Your answer:</strong> {opt0}" in html_a.replace("\n", "")
        assert f"<strong>Your answer:</strong> {opt1}" in html_b.replace("\n", "")

    def test_related_reference_titles_included(self, report_client):
        answers, qs = _some_questions(report_client, n=1)
        item = report_client.get(
            f"/api/v1/items/{qs[0]['source_item_id']}"
        ).json()
        html = report_client.post(
            "/api/v1/quiz/report", json={"answers": answers}
        ).text
        assert html_mod.escape(item["title"], quote=True) in html
        assert "Related reference:" in html

    def test_safety_language_present(self, report_client):
        html = report_client.post(
            "/api/v1/quiz/report", json={"answers": {}}
        ).text
        assert "Generated locally from submitted answers; not stored." in html
        assert "fictional and synthetic" in html
        assert "Content pack:" in html  # active pack block

    def test_out_of_range_answer_is_safe(self, report_client):
        _, qs = _some_questions(report_client, n=1)
        r = report_client.post(
            "/api/v1/quiz/report", json={"answers": {qs[0]["id"]: 99}}
        )
        assert r.status_code == 200
        assert "not a valid choice" in r.text

    def test_unknown_question_id_400(self, report_client):
        r = report_client.post(
            "/api/v1/quiz/report", json={"answers": {"nope": 0}}
        )
        assert r.status_code == 400

    def test_empty_submission_renders(self, report_client):
        r = report_client.post("/api/v1/quiz/report", json={"answers": {}})
        assert r.status_code == 200
        assert "0 / 0 (0%)" in r.text
        assert "No answers were submitted." in r.text

    def test_submit_endpoint_unchanged(self, report_client):
        answers, _ = _some_questions(report_client)
        r = report_client.post("/api/v1/quiz/submit", json={"answers": answers})
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"score", "total", "results"}


class TestReportEscaping:
    XSS = "<script>alert('x')</script>"
    IMG = '<img src=x onerror=alert(1)>'

    def _hostile_client(self):
        def mutate(session):
            item = ReferenceItem(
                id="ref-evil", category_id="cat-instruments",
                title=f"Evil {self.XSS} title", summary="s", body_md="b",
                tags=["evil"], difficulty="beginner", disclaimer_id="d1",
            )
            session.add(item)
            session.add(QuizQuestion(
                id="q-evil", category_id="cat-instruments",
                question=f"Q {self.XSS}?",
                options=[f"opt {self.IMG}", "safe"],
                correct_index=1,
                explanation=f"Because {self.XSS}.",
                source_item_id="ref-evil",
            ))
            meta = session.exec(select(PackMetadata)).one()
            meta.pack_name = f"Pack {self.XSS}"
            meta.safety_notes = f"Notes {self.IMG}"
            session.add(meta)
        return _make_client(mutate=mutate)

    def test_all_dynamic_fields_are_escaped(self):
        client = self._hostile_client()
        try:
            with client as c:
                r = c.post(
                    "/api/v1/quiz/report",
                    json={"answers": {"q-evil": 0}},  # submitted answer = hostile option
                )
                assert r.status_code == 200
                doc = r.text
                # No live payloads anywhere: question, option (as submitted
                # answer), explanation, reference title, pack name, notes.
                assert "<script>" not in doc
                assert "<img" not in doc
                assert "&lt;script&gt;" in doc
                assert "&lt;img" in doc
                # The document's only <style> is our own static block.
                assert doc.count("<style>") == 1
        finally:
            app.dependency_overrides.clear()


class TestReportPerPack:
    def test_report_reflects_active_pack_after_seed(self):
        client = _make_client(seed_path=CYTOFISH_PACK)
        try:
            with client as c:
                answers, _ = _some_questions(c, n=2)
                doc = c.post(
                    "/api/v1/quiz/report", json={"answers": answers}
                ).text
                assert "CytoFISH Navigator Synthetic Pack" in doc
                assert "cytofish_synthetic" in doc
        finally:
            app.dependency_overrides.clear()

    def test_report_follows_pack_switch(self):
        client = _make_client()
        try:
            with client as c:
                c.post("/api/v1/packs/select", json={"slug": "archiveguild"})
                answers, _ = _some_questions(c, n=1)
                doc = c.post(
                    "/api/v1/quiz/report", json={"answers": answers}
                ).text
                assert "ArchiveGuild" in doc
                assert "Tidewatch" not in doc
        finally:
            app.dependency_overrides.clear()
