"""API tests for NavigatorEdu Phase 2 (SQLite/SQLModel data layer)."""


class TestCategories:
    def test_lists_all_categories(self, client):
        r = client.get("/api/v1/categories")
        assert r.status_code == 200
        cats = r.json()
        assert len(cats) == 3
        assert {c["slug"] for c in cats} == {
            "instruments", "sky-references", "procedures",
        }


class TestReferenceItems:
    def test_detail_returns_full_item(self, client):
        r = client.get("/api/v1/items/ref-001")
        assert r.status_code == 200
        item = r.json()
        assert item["title"] == "Meridian Astrolabe Mk. II"
        assert "body_md" in item
        assert item["is_synthetic"] is True

    def test_detail_404_for_unknown_id(self, client):
        assert client.get("/api/v1/items/nope").status_code == 404

    def test_list_view_omits_body(self, client):
        items = client.get("/api/v1/items").json()
        assert items and all("body_md" not in i for i in items)


class TestSearch:
    def test_search_matches_title_and_tags(self, client):
        items = client.get("/api/v1/items", params={"q": "star"}).json()
        ids = {i["id"] for i in items}
        assert "ref-003" in ids  # "Lodestar Vela" title + "star" tag

    def test_search_is_case_insensitive(self, client):
        items = client.get("/api/v1/items", params={"q": "ASTROLABE"}).json()
        assert any(i["id"] == "ref-001" for i in items)

    def test_category_filter(self, client):
        items = client.get(
            "/api/v1/items", params={"category": "cat-sky"}
        ).json()
        assert items
        assert all(i["category_id"] == "cat-sky" for i in items)

    def test_no_results_returns_empty_list(self, client):
        assert client.get("/api/v1/items", params={"q": "zzzz"}).json() == []


class TestPracticeCases:
    def test_list_hides_answer_material(self, client):
        cases = client.get("/api/v1/cases").json()
        assert cases
        for c in cases:
            assert "guided_steps" not in c
            assert "expected_outcome_md" not in c

    def test_detail_includes_answer_material(self, client):
        c = client.get("/api/v1/cases/case-001").json()
        assert c["guided_steps"]
        assert "Latitude" in c["expected_outcome_md"]


class TestQuiz:
    def test_questions_do_not_leak_answers(self, client):
        questions = client.get("/api/v1/quiz").json()
        assert questions
        for q in questions:
            assert "correct_index" not in q
            assert "explanation" not in q

    def test_scoring_counts_correct_answers(self, client):
        # q-001 correct answer is index 1; q-002 correct answer is index 1.
        r = client.post(
            "/api/v1/quiz/submit",
            json={"answers": {"q-001": 1, "q-002": 0}},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 1
        assert body["total"] == 2
        by_id = {x["question_id"]: x for x in body["results"]}
        assert by_id["q-001"]["correct"] is True
        assert by_id["q-002"]["correct"] is False
        assert by_id["q-002"]["explanation"]  # feedback comes with the result

    def test_perfect_score(self, client):
        questions = client.get("/api/v1/quiz").json()
        answers = {"q-001": 1, "q-002": 1, "q-003": 0, "q-004": 1, "q-005": 1}
        r = client.post("/api/v1/quiz/submit", json={"answers": answers})
        assert r.json()["score"] == len(questions)

    def test_unknown_question_id_rejected(self, client):
        r = client.post("/api/v1/quiz/submit", json={"answers": {"bogus": 0}})
        assert r.status_code == 400


class TestTraining:
    def test_returns_all_notes(self, client):
        r = client.get("/api/v1/training")
        assert r.status_code == 200
        notes = r.json()
        assert len(notes) == 3

    def test_notes_are_ordered_by_module_then_order(self, client):
        notes = client.get("/api/v1/training").json()
        keys = [(n["module"], n["order"]) for n in notes]
        assert keys == sorted(keys)

    def test_notes_link_to_existing_reference_items(self, client):
        notes = client.get("/api/v1/training").json()
        item_ids = {i["id"] for i in client.get("/api/v1/items").json()}
        for n in notes:
            assert n["related_item_ids"]
            assert set(n["related_item_ids"]) <= item_ids
