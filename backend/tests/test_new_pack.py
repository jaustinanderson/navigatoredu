"""Tests for the content-pack authoring command (backend.app.new_pack).

All filesystem writes go to pytest's tmp_path, and the CLI is redirected there
by monkeypatching new_pack.DATA_DIR — so running the suite never creates a real
data/seed_*.json artifact (important: CI must stay clean).
"""
import json

import pytest

from backend.app import new_pack as np
from backend.app.validate_pack import validate_pack


class TestSlugValidation:
    @pytest.mark.parametrize(
        "slug",
        ["demo_pack", "demo", "a", "pack2", "my_demo_pack_42"],
    )
    def test_good_slugs_accepted(self, slug):
        assert np.validate_slug(slug) == slug

    @pytest.mark.parametrize(
        "slug",
        [
            "",             # empty
            "Demo",         # uppercase
            "demo-pack",    # hyphen
            "demo pack",    # space
            "demo/pack",    # path separator
            "1demo",        # leading digit
            "_demo",        # leading underscore
            "démo",         # non-ascii
            "a" * 41,       # too long
        ],
    )
    def test_bad_slugs_rejected(self, slug):
        with pytest.raises(np.SlugError):
            np.validate_slug(slug)


class TestPackCreation:
    def test_creates_file(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        assert path.exists()
        assert path.name == "seed_demo_pack.json"
        assert path.parent == tmp_path

    def test_created_file_is_valid_json(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        json.loads(path.read_text(encoding="utf-8"))  # raises if not valid JSON

    def test_created_file_passes_validate_pack(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        assert validate_pack(path) == []

    def test_pack_id_matches_slug(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        meta = json.loads(path.read_text(encoding="utf-8"))["metadata"]
        assert meta["pack_id"] == "demo_pack"

    def test_all_required_sections_present(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "metadata", "disclaimers", "categories", "reference_items",
            "training_notes", "practice_cases", "quiz_questions",
        ):
            assert key in data, f"missing section {key!r}"
        # Minimal but non-empty: at least one starter record per collection.
        for key in (
            "disclaimers", "categories", "reference_items",
            "training_notes", "practice_cases", "quiz_questions",
        ):
            assert len(data[key]) >= 1

    def test_invalid_slug_creates_no_file(self, tmp_path):
        with pytest.raises(np.SlugError):
            np.new_pack("Bad-Slug", data_dir=tmp_path)
        assert list(tmp_path.iterdir()) == []


class TestSafetyDefaults:
    def test_synthetic_only_is_true(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        meta = json.loads(path.read_text(encoding="utf-8"))["metadata"]
        assert meta["synthetic_only"] is True

    def test_intended_use_says_educational_demo(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        meta = json.loads(path.read_text(encoding="utf-8"))["metadata"]
        use = meta["intended_use"].lower()
        assert "educational" in use and "demonstration" in use

    def test_safety_notes_forbid_real_and_operational_use(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        meta = json.loads(path.read_text(encoding="utf-8"))["metadata"]
        notes = meta["safety_notes"].lower()
        assert "no real records" in notes
        assert "no real cases" in notes
        assert "clinical" in notes and "operational" in notes


class TestOverwriteProtection:
    def test_duplicate_not_overwritten_without_force(self, tmp_path):
        first = np.new_pack("demo_pack", data_dir=tmp_path)
        # Mark the file so we can detect an unwanted overwrite.
        first.write_text("SENTINEL", encoding="utf-8")
        with pytest.raises(np.PackExistsError):
            np.new_pack("demo_pack", data_dir=tmp_path)
        assert first.read_text(encoding="utf-8") == "SENTINEL"

    def test_force_overwrites(self, tmp_path):
        path = np.new_pack("demo_pack", data_dir=tmp_path)
        path.write_text("SENTINEL", encoding="utf-8")
        np.new_pack("demo_pack", data_dir=tmp_path, force=True)
        # Regenerated: sentinel gone, and the file validates again.
        assert path.read_text(encoding="utf-8") != "SENTINEL"
        assert validate_pack(path) == []


class TestCli:
    """Exercise main() through its argv, redirecting DATA_DIR to tmp_path."""

    @pytest.fixture(autouse=True)
    def _redirect_data_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(np, "DATA_DIR", tmp_path)
        self.tmp_path = tmp_path

    def test_cli_creates_and_reports(self, capsys):
        assert np.main(["demo_pack"]) == 0
        out = capsys.readouterr().out
        assert "Created" in out
        created = self.tmp_path / "seed_demo_pack.json"
        assert created.exists()
        assert validate_pack(created) == []

    def test_cli_refuses_existing_without_force(self, capsys):
        assert np.main(["demo_pack"]) == 0
        assert np.main(["demo_pack"]) == 1
        assert "refused" in capsys.readouterr().out.lower()

    def test_cli_force_overwrites(self):
        assert np.main(["demo_pack"]) == 0
        assert np.main(["demo_pack", "--force"]) == 0

    def test_cli_invalid_slug_returns_2(self, capsys):
        assert np.main(["Bad-Slug"]) == 2
        assert "invalid slug" in capsys.readouterr().out.lower()
        assert list(self.tmp_path.iterdir()) == []

    def test_cli_no_args_returns_2(self, capsys):
        assert np.main([]) == 2
        assert "usage" in capsys.readouterr().out.lower()
