"""PR-40b: the console on a PIPELINE-BUILT pack, round 2 (auditor views, window answers, raw refs, serve-time
integrity, README fill, C7's key=value limit)."""
import hashlib
import json
import os
import re
import shutil

import pytest
from urllib.parse import quote

from prooflab.console import sources as S
from prooflab.pack import build as B
from prooflab.pack import gaps as G
from prooflab.query import answer as A
from prooflab.query import engine as E

import conftest as C

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "tests", "query", "fixtures", "pack")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("built40b") / "pack")
    assert B.main(["build", "--out", out, "--src", SRC, "--strict-readme"]) == 0
    return out


def _serve(root):
    server = C.start(S.PackSource(root))
    return server, C.Client(server).login()


def test_auditor_views_and_window_answers_are_composed(built):
    idx = json.load(open(os.path.join(built, "pack-index.json")))
    assert idx["auditor"], "pack-index auditor[] empty"
    for a in idx["auditor"]:
        assert os.path.isfile(os.path.join(built, a["path"])) and a["questions"]
    keys = [a["key"] for a in idx["answers"]]
    assert any("|interval|" in k for k in keys) and any(k.startswith("C7|run|") for k in keys)
    server, c = _serve(built)
    try:
        st, doc = c.json("/api/v1/auditor/" + quote(idx["auditor"][0]["id"]))
        assert st == 200 and set(doc["data"]["questions"]) >= {"who", "what", "authorized", "approved", "integrity"}
        st, doc = c.json("/api/v1/ask?q=" + quote("auditor " + idx["auditor"][0]["id"]))
        assert st == 200 and doc["meta"]["route"].startswith("#/auditor/")
    finally:
        server.shutdown(); server.server_close()


def test_every_record_raw_ref_resolves_to_the_line_its_sha_names(built):
    server, c = _serve(built)
    try:
        st, recs = c.json("/api/v1/records")
        assert st == 200 and recs["data"]
        for rec in recs["data"]:
            st, raw = c.json("/api/v1/raw?ref=" + quote(rec["source"]["raw_ref"]))
            assert st == 200, rec["source"]["raw_ref"]
            assert hashlib.sha256(raw["data"]["line"].encode("utf-8")).hexdigest() == rec["source"]["sha256"]
    finally:
        server.shutdown(); server.server_close()


def test_raw_ref_without_a_line_defaults_to_line_1():
    assert S.parse_raw_ref("raw:raw/x/spans.jsonl") == ("raw/x/spans.jsonl", 1)
    assert S.parse_raw_ref("raw:raw/x/spans.jsonl#L3") == ("raw/x/spans.jsonl", 3)
    assert S.parse_raw_ref("raw:raw/x#L0") is None


def test_answers_carry_live_integrity_when_served(built):
    stored = [json.load(open(os.path.join(built, "answers", n))) for n in os.listdir(os.path.join(built, "answers"))]
    assert all(d["source"]["manifest_status"] == "UNVERIFIED" for d in stored)     # composed before MANIFEST.json
    server, c = _serve(built)
    try:
        st, pk = c.json("/api/v1/pack")
        key = [a["key"] for a in pk["data"]["answers"] if "|run|" in a["key"]][0]
        st, ans = c.json("/api/v1/answer?key=" + quote(key))
        d = ans["data"]
        assert d["source"]["manifest_status"] == "VERIFIED" and "serve time" in d["source"]["integrity_checked"]
        assert d["audit_question"]["unchanged_since"]["flag"] == "OK"
        assert "MISSING" not in set(r["manifest"] for r in d["records"])
    finally:
        server.shutdown(); server.server_close()


def test_readme_filled_and_strict_refuses_when_the_fill_fails(built, tmp_path, monkeypatch):
    text = open(os.path.join(built, "README.md")).read()
    assert B.readme_placeholders(os.path.join(built, "README.md")) == []
    assert "Delete this note" not in text and "env -i" in text and "one-time URL" in text
    from prooflab.pack import readme as R

    def boom(root):
        raise RuntimeError("fill failed")
    monkeypatch.setattr(R, "fill", boom)
    assert B.main(["build", "--out", str(tmp_path / "p"), "--src", SRC, "--strict-readme"]) == 2


def test_gap_list_parses_into_pack_index_gaps():
    md = ("# Gap list\n\n## A. ServiceNow\n\n**A1. AICT discovery scope**\n- **What:** partial inventory.\n"
          "- **Why:** connector design.\n- **Affects:** L2 observability.\n- **Impact:** partial.\n- **Next:** extend.\n\n"
          "## B. AWS\n\n### 2. WHO acted: agents look alike\n\n**What's missing:** per-agent identity for C16.\n\n"
          "**Impact:** WHO is partial.\n\n**If you had one more day:** sign records.\n")
    g = G.parse(md)
    assert [x["gap_id"] for x in g] == ["A1", "B2"]
    assert g[0]["affects"]["levels"] == ["L2"] and g[0]["status"] == "OPEN"
    assert g[1]["what"].startswith("per-agent") and g[1]["next"] == "sign records." and "WHO" in g[1]["affects"]["auditor_questions"]
    assert g[1]["why"] == G.NOT_STATED


def test_c7_key_value_limit_is_a_coverage_floor(tmp_path):
    src = str(tmp_path / "src")
    shutil.copytree(SRC, src)
    reg = os.path.join(src, "register", "versions", "v1.yaml")
    text = open(reg).read()
    lines = text.split("\n")
    i = [n for n, l in enumerate(lines) if "control_ref: C7" in l][0]
    j = max(n for n in range(i) if "observation_limit" in lines[n])
    lines[j] = re.sub(r"observation_limit:.*", 'observation_limit: "coverage_min_pct=100;gap_max_ms=30000;violating_gap_share_max_pct=0"', lines[j])
    open(reg, "w").write("\n".join(lines))
    path = os.path.join(src, "assessments", "C7", sorted(os.listdir(os.path.join(src, "assessments", "C7")))[0])
    doc = json.load(open(path))
    doc.pop("limit", None)
    doc["measured"] = {"coverage_pct": 92.0, "coverage": "23/25"}     # the C7 evaluator's own keys, no limit stored
    json.dump(doc, open(path, "w"))
    cid = E.normalize_assessment(doc)["scope_id"]
    pack = E.Pack(src)
    res = A.ask(pack, "control 7 for run %s" % cid)
    assert res["kind"] == "answer", res["doc"]
    rule = res["doc"]["rule"]
    assert rule["observation_limit"]["operator"] == ">=" and rule["observation_limit"]["value"] == 100
    assert rule["other_limits"]["gap_max_ms"] == 30000
    assert res["doc"]["comparison"]["operator"] == ">=" and res["doc"]["comparison"]["within_limit"] is False
