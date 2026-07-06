"""Tests for the hosted-demo smoke-check script (scripts/smoke_deploy.py).

The script's transport is one injectable `fetch` callable, so these tests
run a fake in-memory "deployment" through the real check logic — no
network, no sockets, no mocks of anything but the HTTP boundary itself.
"""
import json
import urllib.error

import pytest

from scripts.smoke_deploy import fetch, main, normalize_base_url, run_checks

BASE = "https://demo.example.test"

GOOD_METADATA = {
    "id": 1,
    "pack_id": "cytofish_synthetic",
    "pack_name": "CytoFISH Navigator Synthetic Pack",
    "pack_version": "0.6.0",
    "pack_description": "A synthetic education pack.",
    "domain_type": "synthetic_biomedical_education",
    "synthetic_only": True,
    "intended_use": "Educational and portfolio demonstration only.",
}

GOOD_REPORT_HTML = (
    "<!DOCTYPE html><html><body><h1>NavigatorEdu quiz report</h1>"
    "<p>Generated locally from submitted answers; not stored.</p>"
    "</body></html>"
)


def make_fake_fetch(overrides=None):
    """A fake deployment: every endpoint healthy unless overridden.

    `overrides` maps a path to either a (status, content_type, body_bytes)
    tuple or an Exception instance to raise (simulating network failure).
    """
    overrides = overrides or {}

    def json_response(payload):
        return 200, "application/json", json.dumps(payload).encode()

    routes = {
        "/": (200, "text/html",
              b"<html><title>NavigatorEdu</title><body>demo</body></html>"),
        "/api/v1/pack-metadata": json_response(GOOD_METADATA),
        "/api/v1/categories": json_response([{"id": "cat-1"}]),
        "/api/v1/items": json_response([{"id": "item-1"}]),
        "/openapi.json": json_response(
            {"paths": {"/api/v1/quiz/report": {}, "/api/v1/items": {}}}),
        "/api/v1/quiz/report": (200, "text/html; charset=utf-8",
                                GOOD_REPORT_HTML.encode()),
    }
    calls = []

    def fake_fetch(url, method="GET", body=None, content_type=None):
        assert url.startswith(BASE), f"unexpected URL {url}"
        path = url[len(BASE):]
        calls.append((method, path, body))
        result = overrides.get(path, routes[path])
        if isinstance(result, Exception):
            raise result
        return result

    fake_fetch.calls = calls
    return fake_fetch


def by_name(results):
    return {name: (ok, detail) for name, ok, detail in results}


class TestNormalizeBaseUrl:
    def test_strips_single_trailing_slash(self):
        assert normalize_base_url("https://x.test/") == "https://x.test"

    def test_strips_multiple_trailing_slashes(self):
        assert normalize_base_url("https://x.test///") == "https://x.test"

    def test_leaves_clean_url_alone(self):
        assert normalize_base_url("https://x.test") == "https://x.test"

    def test_keeps_path_component(self):
        assert normalize_base_url("https://x.test/app/") == "https://x.test/app"


class TestHealthyDeployment:
    def test_all_checks_pass(self):
        results = run_checks(BASE, fetch_fn=make_fake_fetch())
        failed = [(n, d) for n, ok, d in results if not ok]
        assert not failed
        assert len(results) == 8  # no expected-pack check when not requested

    def test_expected_pack_id_adds_a_passing_check(self):
        results = run_checks(BASE, expected_pack_id="cytofish_synthetic",
                             fetch_fn=make_fake_fetch())
        checks = by_name(results)
        assert len(results) == 9
        assert checks["active pack is 'cytofish_synthetic'"][0] is True

    def test_report_check_posts_empty_answers(self):
        fake = make_fake_fetch()
        run_checks(BASE, fetch_fn=fake)
        posts = [c for c in fake.calls if c[0] == "POST"]
        assert posts == [("POST", "/api/v1/quiz/report",
                          json.dumps({"answers": {}}).encode("utf-8"))]


class TestFailureModes:
    def test_home_page_500_fails_only_that_check(self):
        fake = make_fake_fetch({"/": (500, "text/html", b"boom")})
        checks = by_name(run_checks(BASE, fetch_fn=fake))
        assert checks["home page returns 200 and names NavigatorEdu"][0] is False
        assert checks["/api/v1/pack-metadata returns 200 JSON"][0] is True

    def test_home_page_missing_brand_fails(self):
        fake = make_fake_fetch({"/": (200, "text/html", b"<html>other app</html>")})
        checks = by_name(run_checks(BASE, fetch_fn=fake))
        assert checks["home page returns 200 and names NavigatorEdu"][0] is False

    def test_metadata_not_json_fails_dependent_checks_without_crashing(self):
        fake = make_fake_fetch(
            {"/api/v1/pack-metadata": (200, "text/html", b"<html>oops</html>")})
        checks = by_name(run_checks(BASE, expected_pack_id="cytofish_synthetic",
                                    fetch_fn=fake))
        assert checks["/api/v1/pack-metadata returns 200 JSON"][0] is False
        assert checks["metadata names the pack (id / name / version / domain)"][0] is False
        assert checks["metadata declares the synthetic-only posture"][0] is False
        assert checks["active pack is 'cytofish_synthetic'"][0] is False

    def test_missing_metadata_field_fails(self):
        meta = dict(GOOD_METADATA, pack_version="")
        fake = make_fake_fetch(
            {"/api/v1/pack-metadata":
                 (200, "application/json", json.dumps(meta).encode())})
        checks = by_name(run_checks(BASE, fetch_fn=fake))
        name = "metadata names the pack (id / name / version / domain)"
        assert checks[name][0] is False
        assert "pack_version" in checks[name][1]

    def test_synthetic_only_false_fails_the_posture_check(self):
        meta = dict(GOOD_METADATA, synthetic_only=False)
        fake = make_fake_fetch(
            {"/api/v1/pack-metadata":
                 (200, "application/json", json.dumps(meta).encode())})
        checks = by_name(run_checks(BASE, fetch_fn=fake))
        assert checks["metadata declares the synthetic-only posture"][0] is False

    def test_wrong_active_pack_fails(self):
        fake = make_fake_fetch()
        checks = by_name(run_checks(BASE, expected_pack_id="tidewatch",
                                    fetch_fn=fake))
        ok, detail = checks["active pack is 'tidewatch'"]
        assert ok is False
        assert "cytofish_synthetic" in detail

    def test_empty_categories_fails(self):
        fake = make_fake_fetch(
            {"/api/v1/categories": (200, "application/json", b"[]")})
        checks = by_name(run_checks(BASE, fetch_fn=fake))
        assert checks[
            "/api/v1/categories returns 200 with at least one category"][0] is False

    def test_openapi_missing_report_path_fails(self):
        fake = make_fake_fetch(
            {"/openapi.json": (200, "application/json",
                               json.dumps({"paths": {"/api/v1/items": {}}}).encode())})
        checks = by_name(run_checks(BASE, fetch_fn=fake))
        assert checks[
            "/openapi.json returns 200 and includes /api/v1/quiz/report"][0] is False

    def test_report_without_expected_language_fails(self):
        fake = make_fake_fetch(
            {"/api/v1/quiz/report": (200, "text/html", b"<html>hello</html>")})
        checks = by_name(run_checks(BASE, fetch_fn=fake))
        name = "POST /api/v1/quiz/report (empty answers) returns the HTML report"
        assert checks[name][0] is False

    def test_unreachable_host_fails_every_check_without_raising(self):
        boom = urllib.error.URLError("connection refused")
        fake = make_fake_fetch({p: boom for p in
                                ("/", "/api/v1/pack-metadata", "/api/v1/categories",
                                 "/api/v1/items", "/openapi.json",
                                 "/api/v1/quiz/report")})
        results = run_checks(BASE, fetch_fn=fake)
        assert results and all(ok is False for _, ok, _ in results)
        assert all("unreachable" in d for _, _, d in results
                   if "metadata response" not in d)


class TestMain:
    def _patch_fetch(self, monkeypatch, fake):
        monkeypatch.setattr("scripts.smoke_deploy.fetch", fake)

    def test_exit_zero_and_checklist_on_success(self, monkeypatch, capsys):
        self._patch_fetch(monkeypatch, make_fake_fetch())
        rc = main(["--base-url", BASE + "/"])  # trailing slash normalized
        out = capsys.readouterr().out
        assert rc == 0
        assert "[PASS]" in out and "[FAIL]" not in out
        assert "8/8 checks passed" in out

    def test_exit_nonzero_on_failure(self, monkeypatch, capsys):
        self._patch_fetch(monkeypatch,
                          make_fake_fetch({"/": (503, "text/html", b"down")}))
        rc = main(["--base-url", BASE])
        out = capsys.readouterr().out
        assert rc == 1
        assert "[FAIL]" in out
        assert "FAILED" in out

    def test_expected_pack_id_flag_wired_through(self, monkeypatch, capsys):
        self._patch_fetch(monkeypatch, make_fake_fetch())
        rc = main(["--base-url", BASE,
                   "--expected-pack-id", "cytofish_synthetic"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "active pack is 'cytofish_synthetic'" in out
        assert "9/9 checks passed" in out

    def test_base_url_is_required(self):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 2  # argparse usage error


class TestRealFetchContract:
    """Pin the shape of the real fetch() without any network use."""

    def test_http_error_statuses_are_returned_not_raised(self, monkeypatch):
        # urlopen raising HTTPError must surface as a (status, ...) tuple.
        import io

        class FakeHTTPError(urllib.error.HTTPError):
            def __init__(self):
                super().__init__("https://x.test", 404, "nf",
                                 {"Content-Type": "text/plain"},
                                 io.BytesIO(b"missing"))

        def fake_urlopen(request, timeout=None):
            raise FakeHTTPError()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        status, ctype, body = fetch("https://x.test/nope")
        assert (status, ctype, body) == (404, "text/plain", b"missing")
