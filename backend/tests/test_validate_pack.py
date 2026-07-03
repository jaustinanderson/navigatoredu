"""Tests for the content-pack validator.

Broken-pack fixtures are built by mutating a copy of the real default pack,
so the tests stay valid even as pack content evolves.
"""
import json

import pytest

from backend.app.seed import DEFAULT_SEED_PATH, PROJECT_ROOT
from backend.app.validate_pack import main, validate_pack

ARCHIVE_PACK = PROJECT_ROOT / "data" / "seed_archiveguild.json"
CYTOFISH_PACK = PROJECT_ROOT / "data" / "seed_cytofish_synthetic.json"

# Every seed*.json pack shipped in data/ — new packs are picked up automatically.
ALL_PACKS = sorted((PROJECT_ROOT / "data").glob("seed*.json"))


def load_default() -> dict:
    return json.loads(DEFAULT_SEED_PATH.read_text(encoding="utf-8"))


def write_pack(tmp_path, data) -> str:
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


class TestShippedPacks:
    def test_at_least_three_packs_present(self):
        # Guards against a pack going missing; the milestone ships three.
        assert len(ALL_PACKS) >= 3

    @pytest.mark.parametrize("pack", ALL_PACKS, ids=lambda p: p.name)
    def test_shipped_pack_is_valid(self, pack):
        assert validate_pack(pack) == []

    def test_cytofish_pack_is_valid(self):
        assert validate_pack(CYTOFISH_PACK) == []

    def test_cli_exit_code_zero_on_valid(self, capsys):
        assert main([str(DEFAULT_SEED_PATH)]) == 0
        assert "OK" in capsys.readouterr().out


class TestBrokenPacks:
    def test_missing_file_fails(self, capsys):
        assert main(["data/does_not_exist.json"]) == 2
        assert "not found" in capsys.readouterr().out

    def test_invalid_json_fails(self, tmp_path, capsys):
        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        assert main([str(p)]) == 2
        assert "not valid JSON" in capsys.readouterr().out

    def test_missing_top_level_key_fails(self, tmp_path):
        data = load_default()
        del data["quiz_questions"]
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("missing top-level key: 'quiz_questions'" in e for e in errors)

    def test_missing_required_field_fails(self, tmp_path):
        data = load_default()
        del data["reference_items"][0]["title"]
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("missing fields" in e and "'title'" in e for e in errors)

    def test_duplicate_id_fails(self, tmp_path):
        data = load_default()
        data["categories"].append(dict(data["categories"][0]))
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("duplicate id" in e for e in errors)

    def test_bad_category_reference_fails(self, tmp_path):
        data = load_default()
        data["reference_items"][0]["category_id"] = "cat-nope"
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("'cat-nope' not found in categories" in e for e in errors)

    def test_bad_related_item_reference_fails(self, tmp_path):
        data = load_default()
        data["training_notes"][0]["related_item_ids"] = ["ref-ghost"]
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("'ref-ghost' not found in reference_items" in e for e in errors)

    def test_bad_quiz_source_item_fails(self, tmp_path):
        data = load_default()
        data["quiz_questions"][0]["source_item_id"] = "ref-ghost"
        errors = validate_pack(write_pack(tmp_path, data))
        assert any(
            "quiz_questions" in e and "'ref-ghost' not found" in e for e in errors
        )

    def test_correct_index_out_of_range_fails(self, tmp_path):
        data = load_default()
        data["quiz_questions"][0]["correct_index"] = 99
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("correct_index 99 out of range" in e for e in errors)

    def test_cli_exit_code_one_and_lists_problems(self, tmp_path, capsys):
        data = load_default()
        data["quiz_questions"][0]["correct_index"] = 99
        data["reference_items"][0]["category_id"] = "cat-nope"
        assert main([write_pack(tmp_path, data)]) == 1
        out = capsys.readouterr().out
        assert "INVALID" in out and "2 problem(s)" in out


class TestMetadataValidation:
    def test_missing_metadata_fails(self, tmp_path):
        data = load_default()
        del data["metadata"]
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("missing top-level key: 'metadata'" in e for e in errors)

    def test_missing_metadata_field_fails(self, tmp_path):
        data = load_default()
        del data["metadata"]["pack_id"]
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("metadata: missing fields" in e and "pack_id" in e for e in errors)

    def test_synthetic_only_must_be_true(self, tmp_path):
        data = load_default()
        data["metadata"]["synthetic_only"] = False
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("'synthetic_only' must be true" in e for e in errors)

    def test_blank_intended_use_fails(self, tmp_path):
        data = load_default()
        data["metadata"]["intended_use"] = "   "
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("'intended_use' must be present and non-empty" in e for e in errors)

    def test_blank_pack_name_fails(self, tmp_path):
        data = load_default()
        data["metadata"]["pack_name"] = ""
        errors = validate_pack(write_pack(tmp_path, data))
        assert any("'pack_name' must be present and non-empty" in e for e in errors)

    def test_all_shipped_packs_have_valid_metadata(self):
        # Redundant with the parametrized sweep, but states the governance
        # guarantee explicitly: every shipped pack carries valid metadata.
        for pack in ALL_PACKS:
            assert validate_pack(pack) == []
