"""Tests for the SEED_PATH content-pack mechanism.

Covers: env-var resolution, loading the alternate ArchiveGuild pack into an
isolated database, and confirming the two packs produce different domain
content through identical routes.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from backend.app.db import get_session
from backend.app.main import app
from backend.app.seed import DEFAULT_SEED_PATH, PROJECT_ROOT, get_seed_path, seed

ARCHIVE_PACK = PROJECT_ROOT / "data" / "seed_archiveguild.json"


class TestSeedPathResolution:
    def test_defaults_to_seed_json(self, monkeypatch):
        monkeypatch.delenv("SEED_PATH", raising=False)
        assert get_seed_path() == DEFAULT_SEED_PATH

    def test_env_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv("SEED_PATH", "data/seed_archiveguild.json")
        assert get_seed_path() == ARCHIVE_PACK

    def test_absolute_paths_pass_through(self, monkeypatch):
        monkeypatch.setenv("SEED_PATH", str(ARCHIVE_PACK))
        assert get_seed_path() == ARCHIVE_PACK


@pytest.fixture()
def archive_client():
    """A test client whose database is seeded from the ArchiveGuild pack."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, seed_path=ARCHIVE_PACK)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestArchiveGuildPack:
    def test_loads_through_unchanged_routes(self, archive_client):
        assert archive_client.get("/api/v1/categories").status_code == 200
        assert archive_client.get("/api/v1/items").status_code == 200
        assert archive_client.get("/api/v1/training").status_code == 200
        assert archive_client.get("/api/v1/cases").status_code == 200
        assert archive_client.get("/api/v1/quiz").status_code == 200

    def test_produces_different_domain_content(self, archive_client):
        # Compare against the default pack's JSON directly: two live clients
        # can't coexist because both would override the same get_session
        # dependency on the shared app instance.
        import json

        default_pack = json.loads(DEFAULT_SEED_PATH.read_text(encoding="utf-8"))
        tidewatch_slugs = {c["slug"] for c in default_pack["categories"]}
        archive_slugs = {c["slug"] for c in archive_client.get("/api/v1/categories").json()}
        assert archive_slugs == {"materials-handling", "cataloguing", "provenance-appraisal"}
        assert archive_slugs.isdisjoint(tidewatch_slugs)

        titles = {i["title"] for i in archive_client.get("/api/v1/items").json()}
        assert "Foldwane Paper" in titles
        assert "Meridian Astrolabe Mk. II" not in titles

    def test_pack_has_comparable_record_counts(self, archive_client):
        assert len(archive_client.get("/api/v1/categories").json()) == 3
        assert len(archive_client.get("/api/v1/items").json()) == 5
        assert len(archive_client.get("/api/v1/training").json()) == 3
        assert len(archive_client.get("/api/v1/cases").json()) == 2
        assert len(archive_client.get("/api/v1/quiz").json()) == 5

    def test_referential_integrity(self, archive_client):
        item_ids = {i["id"] for i in archive_client.get("/api/v1/items").json()}
        for n in archive_client.get("/api/v1/training").json():
            assert set(n["related_item_ids"]) <= item_ids

    def test_quiz_answers_still_hidden(self, archive_client):
        for q in archive_client.get("/api/v1/quiz").json():
            assert "correct_index" not in q
            assert "explanation" not in q

    def test_quiz_scoring_works_on_alternate_pack(self, archive_client):
        r = archive_client.post(
            "/api/v1/quiz/submit", json={"answers": {"q-001": 1, "q-002": 0}}
        )
        assert r.status_code == 200
        assert r.json()["score"] == 1
