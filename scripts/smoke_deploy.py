"""Hosted-demo smoke check for a deployed NavigatorEdu instance.

Deployment verification, not testing: the pytest suite proves the code,
the browser suite proves the UI, and the CI docker-build job proves the
image — but none of them prove that *a URL you just deployed* is alive,
serving the expected pack, and still declaring its synthetic-only posture.
This script closes that gap with a handful of read-only requests (plus one
stateless empty-report POST) against a running instance.

Usage:

    python scripts/smoke_deploy.py --base-url https://your-demo.onrender.com
    python scripts/smoke_deploy.py --base-url https://your-demo.onrender.com \
        --expected-pack-id cytofish_synthetic

Standard library only — runnable anywhere Python is, including a bare
GitHub Actions runner (.github/workflows/hosted-smoke.yml). Exits 0 when
every check passes, 1 otherwise. The script never writes anything to the
target instance: the report endpoint it POSTs to is stateless by design.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 20
WAKE_ATTEMPTS = 3
WAKE_RETRY_DELAY_SECONDS = 5
RETRYABLE_WAKE_STATUSES = frozenset({502, 503, 504})
NETWORK_ERRORS = (urllib.error.URLError, TimeoutError)
USER_AGENT = "navigatoredu-smoke-deploy/1.0"


def normalize_base_url(base_url: str) -> str:
    """Strip trailing slashes so path joining is uniform ('' is left alone)."""
    return base_url.rstrip("/")


def fetch(url: str, method: str = "GET", body: bytes | None = None,
          content_type: str | None = None) -> tuple[int, str, bytes]:
    """Return (status, content_type_header, body) for one HTTP request.

    HTTP error statuses are returned, not raised, so checks can report the
    actual status code. Network-level failures (DNS, refused, TLS, timeout)
    raise ``urllib.error.URLError`` or ``TimeoutError`` for the caller to turn
    into a failed check.
    """
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("User-Agent", USER_AGENT)
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            return (resp.status, resp.headers.get("Content-Type", ""),
                    resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


def _network_error_reason(error: BaseException) -> str:
    """Return a stable human-readable reason for URL and socket failures."""
    return str(getattr(error, "reason", error))


def run_checks(base_url: str, expected_pack_id: str | None = None,
               fetch_fn=None, sleep_fn=None) -> list[tuple[str, bool, str]]:
    """Run every smoke check against a normalized base URL.

    Returns a list of (check name, passed, detail). Checks that depend on a
    previous response (e.g. metadata fields) are reported as failed with an
    explanatory detail when that response was unusable, so the checklist
    always has the same shape. `fetch_fn` exists so tests can inject a fake
    transport; resolved at call time so monkeypatching module `fetch` works.
    The home-page check retries only network failures and common cold-start
    gateway statuses, giving a sleeping free-tier deployment a bounded chance
    to wake before the remaining checks run. `sleep_fn` keeps that retry path
    deterministic in tests.
    """
    fetch = fetch_fn if fetch_fn is not None else globals()["fetch"]
    sleep = sleep_fn if sleep_fn is not None else time.sleep
    results: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        results.append((name, bool(passed), detail))

    def get(path: str):
        return fetch(base_url + path)

    # -- Home page / bounded cold-start wake-up ----------------------------
    for attempt in range(1, WAKE_ATTEMPTS + 1):
        try:
            status, _, body = get("/")
            text = body.decode("utf-8", errors="replace")
        except NETWORK_ERRORS as e:
            if attempt < WAKE_ATTEMPTS:
                sleep(WAKE_RETRY_DELAY_SECONDS)
                continue
            check("home page returns 200 and names NavigatorEdu", False,
                  f"unreachable after {attempt} attempts: "
                  f"{_network_error_reason(e)}")
            break

        if status in RETRYABLE_WAKE_STATUSES and attempt < WAKE_ATTEMPTS:
            sleep(WAKE_RETRY_DELAY_SECONDS)
            continue

        branded = "NavigatorEdu" in text
        detail = f"status {status}"
        if attempt > 1:
            detail += f" after {attempt} attempts"
        if not branded:
            detail += "; 'NavigatorEdu' not found"
        check("home page returns 200 and names NavigatorEdu",
              status == 200 and branded, detail)
        break

    # -- Pack metadata (governance posture) --------------------------------
    meta = None
    try:
        status, _, body = get("/api/v1/pack-metadata")
        try:
            meta = json.loads(body) if status == 200 else None
        except json.JSONDecodeError:
            meta = None
        check("/api/v1/pack-metadata returns 200 JSON",
              meta is not None,
              f"status {status}" + ("" if meta is not None else "; not JSON"))
    except NETWORK_ERRORS as e:
        check("/api/v1/pack-metadata returns 200 JSON", False,
              f"unreachable: {_network_error_reason(e)}")

    required_fields = ("pack_id", "pack_name", "pack_version", "domain_type")
    if meta is not None:
        missing = [f for f in required_fields if not meta.get(f)]
        check("metadata names the pack (id / name / version / domain)",
              not missing,
              ", ".join(f"{f}={meta.get(f)!r}" for f in required_fields)
              if not missing else f"missing/empty: {', '.join(missing)}")

        check("metadata declares the synthetic-only posture",
              meta.get("synthetic_only") is True,
              f"synthetic_only={meta.get('synthetic_only')!r}")

        if expected_pack_id is not None:
            check(f"active pack is '{expected_pack_id}'",
                  meta.get("pack_id") == expected_pack_id,
                  f"pack_id={meta.get('pack_id')!r}")
    else:
        check("metadata names the pack (id / name / version / domain)",
              False, "no metadata response to inspect")
        check("metadata declares the synthetic-only posture",
              False, "no metadata response to inspect")
        if expected_pack_id is not None:
            check(f"active pack is '{expected_pack_id}'",
                  False, "no metadata response to inspect")

    # -- Content endpoints actually serve content --------------------------
    for path, noun in (("/api/v1/categories", "category"),
                       ("/api/v1/items", "reference item")):
        name = f"{path} returns 200 with at least one {noun}"
        try:
            status, _, body = get(path)
            try:
                payload = json.loads(body) if status == 200 else None
            except json.JSONDecodeError:
                payload = None
            ok = isinstance(payload, list) and len(payload) >= 1
            check(name, ok,
                  f"status {status}, "
                  + (f"{len(payload)} returned" if isinstance(payload, list)
                     else "no JSON list"))
        except NETWORK_ERRORS as e:
            check(name, False,
                  f"unreachable: {_network_error_reason(e)}")

    # -- API schema advertises the report feature --------------------------
    try:
        status, _, body = get("/openapi.json")
        try:
            schema = json.loads(body) if status == 200 else None
        except json.JSONDecodeError:
            schema = None
        ok = (schema is not None
              and "/api/v1/quiz/report" in schema.get("paths", {}))
        check("/openapi.json returns 200 and includes /api/v1/quiz/report",
              ok,
              f"status {status}"
              + ("" if ok else "; path not advertised"))
    except NETWORK_ERRORS as e:
        check("/openapi.json returns 200 and includes /api/v1/quiz/report",
              False, f"unreachable: {_network_error_reason(e)}")

    # -- The one write-shaped call: stateless by design ---------------------
    name = "POST /api/v1/quiz/report (empty answers) returns the HTML report"
    try:
        status, ctype, body = fetch(
            base_url + "/api/v1/quiz/report", method="POST",
            body=json.dumps({"answers": {}}).encode("utf-8"),
            content_type="application/json")
        text = body.decode("utf-8", errors="replace")
        lowered = text.lower()
        ok = (status == 200 and "html" in ctype.lower()
              and ("not stored" in lowered or "quiz report" in lowered))
        check(name, ok,
              f"status {status}, content-type {ctype or '(none)'}"
              + ("" if ok else "; report language not found"))
    except NETWORK_ERRORS as e:
        check(name, False, f"unreachable: {_network_error_reason(e)}")

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-check a deployed NavigatorEdu instance.")
    parser.add_argument("--base-url", required=True,
                        help="Deployed instance, e.g. https://your-demo.onrender.com")
    parser.add_argument("--expected-pack-id", default=None,
                        help="Fail unless this pack is the active one "
                             "(e.g. cytofish_synthetic)")
    args = parser.parse_args(argv)

    base_url = normalize_base_url(args.base_url)
    print(f"Smoke-checking {base_url or '(empty base URL)'}\n")

    results = run_checks(base_url, args.expected_pack_id)
    for name, passed, detail in results:
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}")
        print(f"         {detail}")

    passed_count = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed_count}/{total} checks passed.")
    if passed_count == total:
        print("Hosted demo looks alive, synthetic-only, and serving the "
              "expected API.")
        return 0
    print("Smoke check FAILED — see the checklist above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
