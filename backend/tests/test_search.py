"""Tests for FTS5-backed search and the tag/difficulty filters (v13).

Each client fixture builds an isolated in-memory database through the real
seed() (which is what creates the FTS index), so these tests exercise the
actual index lifecycle: build at seed, rebuild on reseed and pack switch.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from backend.app.db import get_session
from backend.app.main import app
from backend.app.search import FTS_TABLE, _fts_match_expression, search_item_ids
from backend.app.seed import DEFAULT_SEED_PATH, PROJECT_ROOT, seed

CYTOFISH_PACK = PROJECT_ROOT / "data" / "seed_cytofish_synthetic.json"
ARCHIVE_PACK = PROJECT_ROOT / "data" / "seed_archiveguild.json"


def _fresh_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def fts_client():
    """Isolated client seeded (Tidewatch) through the real seed() path."""
    engine = _fresh_engine()
    with Session(engine) as session:
        seed(session, seed_path=DEFAULT_SEED_PATH)

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _ids(client, **params):
    return {i["id"] for i in client.get("/api/v1/items", params=params).json()}


class TestFtsQueryBuilding:
    def test_tokens_are_phrase_quoted_with_trailing_prefix(self):
        assert _fts_match_expression("probe signal") == '"probe" "signal"*'

    def test_operators_in_input_are_neutralized(self):
        # OR / NEAR / - are quoted into plain phrase tokens, not operators.
        assert _fts_match_expression("a OR b") == '"a" "OR" "b"*'
        # Embedded double quotes are doubled (FTS5 literal-quote escaping).
        assert _fts_match_expression('say "hi"') == '"say" """hi"""*'

    def test_hostile_input_executes_safely(self, fts_client):
        """Quote/operator-laden input must return 200, never a 500."""
        for hostile in ('say "hi"', 'a OR b', 'NEAR(x y)', '-star', 'a*b"c'):
            r = fts_client.get("/api/v1/items", params={"q": hostile})
            assert r.status_code == 200, f"{hostile!r} -> {r.status_code}"

    def test_empty_and_whitespace_input(self):
        assert _fts_match_expression("") is None
        assert _fts_match_expression("   ") is None
        assert _fts_match_expression('"') is None


class TestFtsSearch:
    def test_search_returns_expected_items(self, fts_client):
        ids = _ids(fts_client, q="astrolabe")
        assert "ref-001" in ids

    def test_search_matches_tag_words(self, fts_client):
        ids = _ids(fts_client, q="star")
        assert "ref-003" in ids  # carries the "star" tag

    def test_search_is_case_insensitive(self, fts_client):
        assert _ids(fts_client, q="ASTROLABE") == _ids(fts_client, q="astrolabe")

    def test_prefix_matching_on_final_token(self, fts_client):
        assert _ids(fts_client, q="astro") >= _ids(fts_client, q="astrolabe")
        assert _ids(fts_client, q="astro")  # non-empty

    def test_body_text_is_searchable(self, fts_client):
        # FTS indexes body_md, which the old linear scan never searched.
        full = fts_client.get("/api/v1/items").json()
        assert full, "need items"
        # find a distinctive body word via the detail endpoint
        detail = fts_client.get(f"/api/v1/items/{full[0]['id']}").json()
        word = next(w for w in detail["body_md"].split() if w.isalpha() and len(w) > 6)
        assert detail["id"] in _ids(fts_client, q=word)

    def test_no_results_returns_empty_list(self, fts_client):
        assert fts_client.get("/api/v1/items", params={"q": "zzzzqqq"}).json() == []

    def test_whitespace_query_treated_as_absent(self, fts_client):
        everything = _ids(fts_client)
        assert _ids(fts_client, q="   ") == everything

    def test_response_shape_unchanged(self, fts_client):
        items = fts_client.get("/api/v1/items", params={"q": "astrolabe"}).json()
        assert items
        for i in items:
            assert "body_md" not in i          # list view stays light
            assert {"id", "title", "summary", "tags", "difficulty",
                    "category_id"} <= set(i)


class TestFilters:
    def test_tag_filter(self, fts_client):
        ids = _ids(fts_client, tag="star")
        assert ids
        for item in fts_client.get("/api/v1/items", params={"tag": "star"}).json():
            assert "star" in item["tags"]

    def test_difficulty_filter(self, fts_client):
        for diff in ("beginner", "intermediate"):
            items = fts_client.get(
                "/api/v1/items", params={"difficulty": diff}
            ).json()
            assert items
            assert all(i["difficulty"] == diff for i in items)

    def test_combined_q_tag_difficulty(self, fts_client):
        all_items = fts_client.get("/api/v1/items").json()
        target = all_items[0]
        combined = fts_client.get("/api/v1/items", params={
            "q": target["title"].split()[0],
            "tag": target["tags"][0],
            "difficulty": target["difficulty"],
        }).json()
        ids = {i["id"] for i in combined}
        assert target["id"] in ids
        for i in combined:  # every result satisfies every filter
            assert target["tags"][0] in i["tags"]
            assert i["difficulty"] == target["difficulty"]

    def test_filters_are_intersective(self, fts_client):
        base = _ids(fts_client, q="the")
        narrowed = _ids(fts_client, q="the", difficulty="beginner")
        assert narrowed <= base

    def test_unknown_filter_values_match_nothing(self, fts_client):
        assert _ids(fts_client, tag="no-such-tag") == set()
        assert _ids(fts_client, difficulty="expert") == set()

    def test_category_filter_still_works(self, fts_client):
        items = fts_client.get(
            "/api/v1/items", params={"category": "cat-sky"}
        ).json()
        assert items and all(i["category_id"] == "cat-sky" for i in items)


class TestFtsLifecycle:
    def test_index_is_built_by_seed(self):
        engine = _fresh_engine()
        with Session(engine) as session:
            counts = seed(session, seed_path=DEFAULT_SEED_PATH)
            indexed = session.execute(
                text(f"SELECT count(*) FROM {FTS_TABLE}")
            ).scalar()
        assert counts["fts_indexed"] == counts["reference_items"] == indexed

    def test_index_rebuilds_on_reseed(self):
        engine = _fresh_engine()
        with Session(engine) as session:
            seed(session, seed_path=DEFAULT_SEED_PATH)
            seed(session, seed_path=DEFAULT_SEED_PATH)  # again
            indexed = session.execute(
                text(f"SELECT count(*) FROM {FTS_TABLE}")
            ).scalar()
            items = session.execute(
                text("SELECT count(*) FROM referenceitem")
            ).scalar()
        assert indexed == items  # no duplicate index rows

    def test_index_rebuilds_on_pack_switch(self):
        engine = _fresh_engine()
        with Session(engine) as session:
            seed(session, seed_path=DEFAULT_SEED_PATH)
            assert search_item_ids(session, "astrolabe")          # Tidewatch term
            seed(session, seed_path=CYTOFISH_PACK)
            assert search_item_ids(session, "astrolabe") == []    # gone
            assert search_item_ids(session, "probe")              # CytoFISH term

    def test_search_scoped_to_active_pack_via_api(self, fts_client):
        # Switch packs through the browser endpoint; search must follow.
        assert _ids(fts_client, q="astrolabe")
        fts_client.post("/api/v1/packs/select", json={"slug": "cytofish"})
        assert _ids(fts_client, q="astrolabe") == set()
        assert _ids(fts_client, q="probe")
        fts_client.post("/api/v1/packs/select", json={"slug": "archiveguild"})
        assert _ids(fts_client, q="probe") == set()
        assert _ids(fts_client, q="provenance")
        fts_client.post("/api/v1/packs/select", json={"slug": "tidewatch"})
        assert _ids(fts_client, q="provenance") == set()
        assert _ids(fts_client, q="astrolabe")

    def test_never_seeded_database_searches_safely(self):
        """The documented fallback: no FTS table -> no matches, no 500."""
        engine = _fresh_engine()  # tables created, never seeded

        def override():
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override
        try:
            with TestClient(app) as c:
                r = c.get("/api/v1/items", params={"q": "anything"})
                assert r.status_code == 200
                assert r.json() == []
        finally:
            app.dependency_overrides.clear()
