"""PR-40: the console on a PIPELINE-BUILT pack (pack build -> pack-index.json, answers/, records/), not only on fixtures."""
import json
import os
import subprocess
import sys

import pytest
from urllib.parse import quote

from prooflab.console import sources as S
from prooflab.pack import build as B
from prooflab.query import engine as E

import conftest as C

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "tests", "query", "fixtures", "pack")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("built") / "pack")
    rc = B.main(["build", "--out", out, "--src", SRC])
    assert rc == 0
    return out


def test_pack_build_writes_the_console_entry_point(built):          # D1
    assert os.path.isfile(os.path.join(built, "pack-index.json"))
    man = json.load(open(os.path.join(built, "MANIFEST.json")))
    listed = set(e["path"] for e in man["files"])
    assert "pack-index.json" in listed and any(p.startswith("answers/") for p in listed)
    assert any(p.startswith("records/") for p in listed)
    # projected assessments live apart from the native ones the query engine reads
    assert any(p.startswith("projected-assessments/") for p in listed)
    assert not any(p.startswith("assessments/") and "schema" in open(os.path.join(built, p)).read()[:80] for p in listed)


def test_console_serves_a_stored_answer_from_the_built_pack(built):   # D2 / AT-P0 on the staged pack
    src = S.PackSource(built)
    server = C.start(src)
    try:
        c = C.Client(server).login()
        st, pk = c.json("/api/v1/pack")
        assert st == 200 and pk["data"]["answers"], "pack-index answers[] empty"
        a0 = pk["data"]["answers"][0]
        # the live integrity check overrides the build-time UNVERIFIED stamp (the index is written before the MANIFEST)
        assert pk["data"]["integrity"]["status"] == "VERIFIED" and pk["data"]["integrity"]["files"] > 0
        assert [x for x in pk["data"]["artefacts"] if x["path"] == "MANIFEST.json"][0]["present"] is True
        st, ans = c.json("/api/v1/ask?q=" + quote("control 16 for run " + a0["scope"]))
        assert st == 200 and ans["data"]["verdict"]["value"] == a0["verdict"]
        st, rec = c.json("/api/v1/records")
        assert st == 200 and rec["meta"]["total"] > 0
    finally:
        server.shutdown(); server.server_close()


def test_run_catalogue_keeps_honesty_fields_and_window(built):       # D5
    src = S.PackSource(built)
    rows = src.run_catalogue()
    assert rows and all(r["provenance"] and r["provenance"] != "unknown" for r in rows)
    assert all(r["source"] and r["in_window"] in (True, False) for r in rows)
    assert src.declared_window()["start"]
    cli = E.runs_list(E.Pack(built))["rows"]
    assert sorted((r["cid"], r["provenance"]) for r in rows) == sorted((r["cid"], r["provenance"]) for r in cli)


def test_cases_route_flags_closure_without_retest(pack):             # D6 / AT-10 on /cases
    case_path = [p for p in os.listdir(os.path.join(pack, "servicenow", "cases"))][0]
    full = os.path.join(pack, "servicenow", "cases", case_path)
    doc = json.load(open(full))
    doc["closure"] = {"state": "CLOSED_BY_RETEST", "retest_ref": None}
    src = S.PackSource(pack)
    src._case_docs = [doc]
    server = C.start(src)
    try:
        c = C.Client(server).login()
        st, cases = c.json("/api/v1/cases")
        assert st == 200 and cases["data"][0]["closure"]["flag"] == "CLOSED WITHOUT RE-TEST"
    finally:
        server.shutdown(); server.server_close()


def test_native_measured_keys_reach_the_renderer():                  # D4
    doc = {"assessment_id": "C16:C16-v1:run:r1:r1", "control_ref": "C16", "scope_id": "r1", "scope_kind": "run",
           "threshold_version": "C16-v1", "verdict": "BREACHED",
           "measured": {"total_tokens": 78800, "cap": 40000, "overshoot": 38800}}
    a = E.normalize_assessment(doc)
    assert a["measured"]["value"] == 78800 and a["measured"]["unit"] == "tokens" and a["limit"] == 40000
    c7 = E.normalize_assessment({"assessment_id": "C7:C7-v1:run:r1:r1", "measured": {"coverage_pct": 80.0}})
    assert c7["measured"]["value"] == 80.0 and c7["limit"] is None
    kept = E.normalize_assessment({"measured": {"value": 5, "unit": "x", "total_tokens": 9}, "limit": 7})
    assert kept["measured"]["value"] == 5 and kept["limit"] == 7


def test_strict_readme_refuses_an_unfilled_template(tmp_path):       # D3
    out = str(tmp_path / "p")
    assert B.main(["build", "--out", out, "--src", SRC, "--strict-readme"]) == 2
    assert "Open the console" in open(os.path.join(REPO, "evidence-templates", "README.md")).read()


def test_at06_scoped_to_data(built):                                  # D7: the pattern, assembled from parts, over the DATA dirs
    pat = "|".join(["AK" + "IA", "AS" + "IA", "bearer [a-z0-9]", "tkn" + "[=]", "AUDIT_WRITE_TOKEN" + "=", "client_" + "secret"])
    data = [d for d in ("store", "raw", "derived", "assessments", "answers", "records", "projected-assessments", "pack-index.json")
            if os.path.exists(os.path.join(built, d))]
    p = subprocess.run(["grep", "-rEil", pat] + data, cwd=built, stdout=subprocess.PIPE, universal_newlines=True)
    assert p.stdout.strip() == ""
