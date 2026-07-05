"""Tests for the Content Pack Browser (GET /packs, POST /packs/select).

Each test builds its own isolated in-memory database (never the shared
session-scoped conftest engine) because selecting a pack mutates the DB —
these tests must not leak state into other modules.
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from backend.app.db import get_session
from backend.app.main import app
from backend.app.pack_registry import REGISTRY, seed_path_for
from backend.app.seed import DEFAULT_SEED_PATH, seed

STALE_TIDEWATCH = ["Instruments", "Sky References", "Procedures"]
STALE_ARCHIVE = ["Materials & Handling", "Cataloguing", "Provenance & Appraisal"]


@pytest.fixture()
def pack_client():
    """Isolated client seeded with the default (Tidewatch) pack."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session, seed_path=DEFAULT_SEED_PATH)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _category_names(client):
    return {c["name"] for c in client.get("/api/v1/categories").json()}


def _pack_category_ids(slug):
    data = json.loads(seed_path_for(slug).read_text(encoding="utf-8"))
    return {c["id"] for c in data["categories"]}


class TestListPacks:
    def test_returns_all_allowlisted_packs(self, pack_client):
        body = pack_client.get("/api/v1/packs").json()
        assert {p["slug"] for p in body["packs"]} == set(REGISTRY)
        assert len(body["packs"]) == 3

    def test_reports_active_pack(self, pack_client):
        body = pack_client.get("/api/v1/packs").json()
        assert body["active_pack_id"] == "tidewatch"

    def test_each_pack_carries_governance_metadata(self, pack_client):
        for p in pack_client.get("/api/v1/packs").json()["packs"]:
            for field in (
                "pack_id", "pack_name", "pack_description", "domain_type",
                "synthetic_only", "intended_use", "safety_notes",
            ):
                assert p[field] not in ("", None), f"{p['slug']} missing {field}"
            assert p["synthetic_only"] is True

    def test_no_filesystem_paths_in_response(self, pack_client):
        raw = pack_client.get("/api/v1/packs").text
        assert "data/" not in raw
        assert ".json" not in raw
        assert "/" not in json.dumps(
            [p["slug"] for p in pack_client.get("/api/v1/packs").json()["packs"]]
        ).strip('[]"')


class TestSelectPack:
    def test_select_loads_a_valid_pack(self, pack_client):
        r = pack_client.post("/api/v1/packs/select", json={"slug": "archiveguild"})
        assert r.status_code == 200
        body = r.json()
        assert body["active_pack_id"] == "archiveguild"
        assert body["loaded"]["slug"] == "archiveguild"
        assert body["counts"]["categories"] > 0
        # The metadata endpoint agrees.
        meta = pack_client.get("/api/v1/pack-metadata").json()
        assert meta["pack_id"] == "archiveguild"

    def test_invalid_slug_is_rejected_cleanly(self, pack_client):
        r = pack_client.post("/api/v1/packs/select", json={"slug": "nope"})
        assert r.status_code == 404
        assert "Unknown pack" in r.json()["detail"]
        # And nothing about the filesystem leaks in the error.
        assert "data/" not in r.text and ".json" not in r.text

    def test_path_like_slug_is_rejected(self, pack_client):
        for evil in ("../../etc/passwd", "data/seed.json", "seed.json"):
            r = pack_client.post("/api/v1/packs/select", json={"slug": evil})
            assert r.status_code == 404, f"slug {evil!r} should be rejected"
            # The error must not reflect the submitted string or any path.
            assert evil not in r.text
            assert "data/" not in r.text and ".json" not in r.text

    def test_selecting_cytofish_shows_only_cytofish_categories(self, pack_client):
        pack_client.post("/api/v1/packs/select", json={"slug": "cytofish"})
        api_ids = {c["id"] for c in pack_client.get("/api/v1/categories").json()}
        assert api_ids == _pack_category_ids("cytofish")
        names = _category_names(pack_client)
        for stale in STALE_TIDEWATCH + STALE_ARCHIVE:
            assert stale not in names

    def test_switching_away_from_cytofish_leaves_no_stale_categories(self, pack_client):
        pack_client.post("/api/v1/packs/select", json={"slug": "cytofish"})
        cyto_names = _category_names(pack_client)

        pack_client.post("/api/v1/packs/select", json={"slug": "tidewatch"})
        names = _category_names(pack_client)
        assert not names & cyto_names, "CytoFISH categories survived the switch"
        assert {c["id"] for c in pack_client.get("/api/v1/categories").json()} \
            == _pack_category_ids("tidewatch")

        pack_client.post("/api/v1/packs/select", json={"slug": "archiveguild"})
        names = _category_names(pack_client)
        assert not names & cyto_names
        for stale in STALE_TIDEWATCH:
            assert stale not in names

    def test_full_cycle_all_three_packs(self, pack_client):
        """Walk the exact manual demo path: tidewatch -> archive -> cytofish."""
        for slug in ("tidewatch", "archiveguild", "cytofish"):
            r = pack_client.post("/api/v1/packs/select", json={"slug": slug})
            assert r.status_code == 200
            assert {c["id"] for c in pack_client.get("/api/v1/categories").json()} \
                == _pack_category_ids(slug)
            quiz = pack_client.get("/api/v1/quiz").json()
            assert quiz, f"{slug}: quiz should have questions"
            assert all("correct_index" not in q for q in quiz)
