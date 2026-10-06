"""G-07 mapping tables: provenance membership-first, record kinds, decisions, EP honesty, revisions, determinism."""
import glob
import json
import os

import pytest

import _pack_fixture as fx
from prooflab.pack import index, projector


@pytest.fixture()
def run(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    out = str(tmp_path / "out")
    res = projector.project(src, out, as_of="2026-10-06T09:00:00Z")
    return src, out, res


def _records(out):
    return [json.load(open(p)) for p in sorted(glob.glob(os.path.join(out, "records", "**", "*.json"), recursive=True))]


def test_provenance_membership_first_whatever_the_record_says():
    assert projector.provenance_of("PILOT", "x", {"x": "FM-A"}) == "ASSESSED"          # named run beats its own value
    assert projector.provenance_of("BASELINE", "y", {}) == "EXPLORATORY"
    assert projector.provenance_of("LIVE_SUBJECT", "y", {}) == "ASSESSED"
    assert projector.provenance_of("FAULT_INJECTION", "y", {}) == "EXPLORATORY"
    assert projector.provenance_of("WIRING_TEST", "y", {}) == "WIRING_TEST"
    assert projector.provenance_of("SYNTHETIC", "y", {}) is None                       # never enters the pack
    assert projector.provenance_of("SYNTHETIC", "x", {"x": "FM-A"}) == "ASSESSED"       # membership still first


def test_run_ids_parse_both_forms():
    got = projector.parse_run_ids("# c\nFM-A ifabric-run-1-aa\nifabric-run-2-bb=FM-B\nifabric-run-3-cc\n")
    assert got == {"ifabric-run-1-aa": "FM-A", "ifabric-run-2-bb": "FM-B", "ifabric-run-3-cc": "ifabric-run-3-cc"}


def test_records_projected_with_alias_cumulative_tokens_and_provenance(run):
    _, out, _ = run
    recs = _records(out)
    assert all(r["provenance"] in ("ASSESSED", "EXPLORATORY") for r in recs)
    b_calls = sorted((r for r in recs if r["run.id"] == "FM-B" and r["record_kind"] == "model-call"), key=lambda r: r["emitted.at"])
    assert [r["measured.value"] for r in b_calls] == [210, 440] and [r["measured.call"] for r in b_calls] == [210, 230]
    assert all(r["joins"]["cid"] == fx.B and r["threshold.value"] == 300 for r in b_calls)
    assert all(r["verdict"] == "NOT_ASSESSED" for r in recs)          # a record is not a verdict
    exp = [r for r in recs if r["joins"]["cid"] == fx.E]
    assert exp and all(r["provenance"] == "EXPLORATORY" for r in exp)  # unbound exploratory run still projected, labelled
    assert not any(r["joins"]["cid"] == fx.S for r in recs)             # SYNTHETIC never enters
    assert not any(r["facts"]["record_id"] == "r902" for r in recs)     # APPROVAL is an EP row, not a record


def test_inline_decision_observe_deny_is_alert_and_handoff_event(run):
    _, out, _ = run
    recs = _records(out)
    dec = [r for r in recs if r["facts"]["record_id"] == "r900"][0]
    assert dec["decision"] == "ALERT" and dec["record_kind"] == "event" or dec["record_kind"] == "decision"
    assert dec["record_kind"] == "decision"
    assert projector.decision_of({"record_kind": "decision", "verdict": "DENY", "inline.mode": "enforce"}) == "DENY"
    assert projector.decision_of({"record_kind": "decision", "verdict": "ALLOW"}) == "ALLOW"
    hand = [r for r in recs if r["facts"]["our_record_kind"] == "handoff"]
    assert hand and all(r["record_kind"] == "event" and r["facts"]["hop.via"] == "orchestrator-handoff" for r in hand)
    jud = [r for r in recs if r["facts"]["record_id"] == "r904"][0]
    assert jud["facts"]["disposition"] == "halted-by-budget" and jud["facts"]["reversible_action"] == "none"


def test_enforcement_points_ep0_to_ep16_honest(run):
    _, out, res = run
    eps = json.load(open(os.path.join(out, "pack-index.json")))["enforcement_points"]
    assert [e["id"] for e in eps] == ["EP-%d" % n for n in range(17)]
    st = dict((e["id"], e["status"]) for e in eps)
    assert st["EP-1"] == "BUILT" and st["EP-13"] == "ALERT_ONLY"       # records exist for exactly these two
    assert [k for k, v in st.items() if v in ("BUILT", "ALERT_ONLY", "EVIDENCED")] == ["EP-1", "EP-13"]
    assert all(v in ("NOT_RUN",) for k, v in st.items() if k not in ("EP-1", "EP-13"))


def test_enforcement_status_never_built_without_records_and_platform_eps_only_evidenced():
    none = dict((e["id"], e["status"]) for e in index.enforcement_points({}))
    assert set(none.values()) == {"NOT_RUN"}
    seen = dict((e["id"], e["status"]) for e in index.enforcement_points({"EP-1": ["record:a"], "EP-6": ["record:b"], "EP-13": ["record:c"]}))
    assert seen["EP-1"] == "BUILT" and seen["EP-6"] == "EVIDENCED" and seen["EP-13"] == "ALERT_ONLY"


def test_latest_revision_wins_and_finding_carried(run):
    _, out, _ = run
    files = glob.glob(os.path.join(out, "assessments", "C16", "*.json"))
    docs = [json.load(open(p)) for p in files]
    b = [d for d in docs if d["scope"]["id"] == fx.B]
    assert len(b) == 1 and b[0]["revision"] == 2 and b[0]["verdict"] == "BREACHED" and b[0]["finding"]["summary"] == "fixture breach"
    assert b[0]["scope"]["alias"] == "FM-B" and b[0]["provenance"] == "ASSESSED"
    assert b[0]["evidence_refs"] == ["gateway:run=" + fx.B, "record:ev-1"]


def test_claim_and_controls_are_derived_not_asserted(run):
    _, out, _ = run
    idx = json.load(open(os.path.join(out, "pack-index.json")))
    assert idx["claim"]["verdict"] == "NOT_SATISFIED"
    c16 = [c for c in idx["claim"]["controls"] if c["ref"] == "C16"][0]
    assert c16["verdict_overall"] == "BREACHED" and c16["completeness"]["f_query_under_2min"] is False
    assert c16["completeness"]["a_register"] and c16["completeness"]["b_bound_records"] and c16["completeness"]["e_owner_alerted"] is False
    # claim.json says PENDING, but the approval comes from the T2 files only: the fixture has none -> MISSING
    assert idx["register"]["approval"]["status"] == "MISSING" and idx["integrity"]["status"] == "UNVERIFIED"
    assert idx["cases"][0]["incident"] == "INC0000001" and len(idx["cases"][0]["sha256"]) == 64


def test_assessment_without_register_limits_is_skipped_and_reported(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    os.remove(os.path.join(src, "register", "versions", "v1-fixture.yaml"))
    res = projector.project(src, str(tmp_path / "out"), as_of="2026-10-06T09:00:00Z")
    assert res["report"]["written"]["assessments"] == 0 and res["report"]["skipped_assessments"]
    assert "limits" in res["report"]["skipped_assessments"][0]["why"]


def test_deterministic_twice_same_bytes(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    for name in ("o1", "o2"):
        projector.project(src, str(tmp_path / name), as_of="2026-10-06T09:00:00Z")
    def tree(root):
        return dict((os.path.relpath(p, root), open(p, "rb").read()) for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True))
    assert tree(str(tmp_path / "o1")) == tree(str(tmp_path / "o2"))
