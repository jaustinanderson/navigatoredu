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
CYTOFISH_PACK = PROJECT_ROOT / "data" / "seed_cytofish_synthetic.json"


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


@pytest.fixture()
def cytofish_client():
    """A test client whose database is seeded from the CytoFISH pack."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, seed_path=CYTOFISH_PACK)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestCytoFishPack:
    def test_loads_through_unchanged_routes(self, cytofish_client):
        for route in ("/categories", "/items", "/training", "/cases", "/quiz"):
            assert cytofish_client.get("/api/v1" + route).status_code == 200

    def test_has_expected_domain_categories(self, cytofish_client):
        slugs = {c["slug"] for c in cytofish_client.get("/api/v1/categories").json()}
        assert slugs == {
            "panel-foundations",
            "probe-signal-concepts",
            "quality-review-awareness",
            "synthetic-practice-cases",
        }

    def test_practice_cases_use_synthetic_names(self, cytofish_client):
        titles = [c["title"] for c in cytofish_client.get("/api/v1/cases").json()]
        assert all("SYN-FISH-" in t for t in titles)

    def test_referential_integrity(self, cytofish_client):
        item_ids = {i["id"] for i in cytofish_client.get("/api/v1/items").json()}
        for n in cytofish_client.get("/api/v1/training").json():
            assert set(n["related_item_ids"]) <= item_ids

    def test_quiz_answers_still_hidden(self, cytofish_client):
        for q in cytofish_client.get("/api/v1/quiz").json():
            assert "correct_index" not in q
            assert "explanation" not in q

    def test_quiz_scoring_works(self, cytofish_client):
        # q-003 correct index is 1; q-007 correct index is 1.
        r = cytofish_client.post(
            "/api/v1/quiz/submit", json={"answers": {"q-003": 1, "q-007": 0}}
        )
        assert r.status_code == 200
        assert r.json()["score"] == 1

    def test_metadata_endpoint_reflects_loaded_pack(self, cytofish_client):
        meta = cytofish_client.get("/api/v1/pack-metadata").json()
        assert meta["pack_id"] == "cytofish_synthetic"
        assert meta["synthetic_only"] is True
        assert meta["domain_type"] == "synthetic_biomedical_education"


class TestPackSwitchingClearsStaleContent:
    """Seeding is clear-then-load: the database always holds exactly one pack.

    Regression tests for the v10 bug where seeding CytoFISH over a database
    that already held Tidewatch left the old categories visible on the
    Reference page while the metadata endpoint named the new pack.
    """

    @staticmethod
    def _fresh_engine():
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        return engine

    @staticmethod
    def _client(engine):
        def override_get_session():
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        return TestClient(app)

    @staticmethod
    def _pack_category_ids(path):
        import json

        return {c["id"] for c in json.loads(path.read_text())["categories"]}

    def test_reseeding_another_pack_leaves_no_stale_categories(self):
        engine = self._fresh_engine()
        with Session(engine) as session:
            seed(session, seed_path=DEFAULT_SEED_PATH)   # Tidewatch first
            seed(session, seed_path=CYTOFISH_PACK)       # then CytoFISH, same DB
        try:
            client = self._client(engine)
            cats = client.get("/api/v1/categories").json()
            names = {c["name"] for c in cats}
            for stale in [
                "Instruments", "Sky References", "Procedures",
                "Materials & Handling", "Cataloguing", "Provenance & Appraisal",
            ]:
                assert stale not in names, f"stale category survived reseed: {stale}"
        finally:
            app.dependency_overrides.clear()

    def test_categories_after_cytofish_seed_are_exactly_cytofish(self):
        engine = self._fresh_engine()
        with Session(engine) as session:
            seed(session, seed_path=DEFAULT_SEED_PATH)
            seed(session, seed_path=CYTOFISH_PACK)
        try:
            client = self._client(engine)
            api_ids = {c["id"] for c in client.get("/api/v1/categories").json()}
            assert api_ids == self._pack_category_ids(CYTOFISH_PACK)
        finally:
            app.dependency_overrides.clear()

    def test_all_content_types_switch_together(self):
        """Not just categories: every content table reflects only the new pack."""
        import json

        engine = self._fresh_engine()
        with Session(engine) as session:
            seed(session, seed_path=ARCHIVE_PACK)
            counts = seed(session, seed_path=CYTOFISH_PACK)
        pack = json.loads(CYTOFISH_PACK.read_text())
        try:
            client = self._client(engine)
            for key, route in [
                ("reference_items", "/api/v1/items"),
                ("practice_cases", "/api/v1/cases"),
                ("quiz_questions", "/api/v1/quiz"),
                ("training_notes", "/api/v1/training"),
                ("disclaimers", "/api/v1/disclaimers"),
            ]:
                got = client.get(route).json()
                assert len(got) == len(pack[key]) == counts[key], (
                    f"{key}: expected only the new pack's rows"
                )
            meta = client.get("/api/v1/pack-metadata").json()
            assert meta["pack_id"] == "cytofish_synthetic"
        finally:
            app.dependency_overrides.clear()

    def test_reseeding_same_pack_is_idempotent(self):
        """Clear-then-load keeps the old guarantee: re-running converges."""
        engine = self._fresh_engine()
        with Session(engine) as session:
            first = seed(session, seed_path=DEFAULT_SEED_PATH)
            second = seed(session, seed_path=DEFAULT_SEED_PATH)
        assert first == second
        try:
            client = self._client(engine)
            cats = client.get("/api/v1/categories").json()
            assert len(cats) == first["categories"]  # no duplicates
        finally:
            app.dependency_overrides.clear()
