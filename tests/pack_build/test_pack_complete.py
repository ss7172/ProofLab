"""PR-47: the final Evidence Pack is complete and correct. SYNTHETIC fixture (derived shapes, no real data):
register v1 + v1.1 (text order != chain order), C16 assessed under C16-v1.1, C9 with k=v limits, approvals from the
T2 files (v1 APPROVED, v1.1 PENDING with its note on the other incident), a failed pilot, README fill under --strict-readme.
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
from prooflab.pack import history, projector  # noqa: E402

NAMED = "ifabric-run-1790100000-aaaaaa"
WARM = "ifabric-run-1790099000-wwwwww"
PILOT_FAIL = "ifabric-run-1790090000-ffffff"
PILOT_OK = "ifabric-run-1790091000-pppppp"

REG = """version: {v}
version_date: "{at}"
supersedes: {sup}
register_owner: Owner
status: FROZEN
frozen_at: "{at}"
builder: "Builder"
owner: owner@example.invalid
owner_name: "Fixture Owner"
retention: "Evidence is kept for 7 years from the submission date"
controls:
  - control_id: "16"
    name: "Per-run token spend cap"
    metric: "tokens per run"
    observation_limit: {cap}
    exception_tolerance: 0
    measurement_basis: "gateway llm lines"
    owner: owner@example.invalid
    version_date: "{at}"
    control_ref: C16
    threshold_version: {c16v}
    metric_unit: tokens
  - control_id: "9"
    name: "Drift and performance"
    metric: "latency max per runtime window"
    observation_limit: "max_relative_change_pct=75;violating_windows_max_pct=0;errors_max=0"
    exception_tolerance: 0
    measurement_basis: "AgentCore Latency Maximum"
    owner: owner@example.invalid
    version_date: "2026-10-06T12:39:29Z"
    control_ref: C9
    threshold_version: C9-v1
    limit_direction: two-sided
    metric_unit: milliseconds
"""


def _w(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text if isinstance(text, str) else json.dumps(text))


def _assessment(ctl, tv, rv, scope_kind, scope_id, measured, sha=None, start="2026-10-06T13:56:00Z", end="2026-10-06T13:57:00Z"):
    return {"assessment_id": "%s:%s:%s:%s:r1" % (ctl, tv, scope_kind, scope_id), "control_ref": ctl, "threshold_version": tv,
            "register_version": rv, "threshold_sha256": sha, "scope_kind": scope_kind, "scope_id": scope_id,
            "scope_start": start, "scope_end": end, "requirement_verdict": "SATISFIED", "measured": measured,
            "denominators": {"expected": 3, "observed": 3, "matched": 3, "missing": 0}, "exceptions": [], "gaps": [],
            "formula": "fixture", "evaluator_name": "prooflab.evaluators.%s" % ctl.lower(), "evaluator_sha256": "b" * 64,
            "as_of": "2026-10-06T14:00:00Z", "finding": None, "evidence_refs": ["gateway:run=" + scope_id]}


def _rec(rid, cid, ts, **extra):
    r = {"schema": "ifabric.evidence/1", "record_id": rid, "record_kind": "action", "correlation_id": cid, "run.id": cid,
         "verdict": "RECORDED", "ts": ts, "provenance": "LIVE_SUBJECT", "authorship": "PLATFORM", "emitted.at": ts,
         "emitted.clock": "gateway", "source.refs": ["gateway:action_id=" + rid], "emitter": "fixture-adapter",
         "tokens.in": 100, "tokens.out": 10, "model.id": "m", "call.id": "act-" + rid, "actor.id": "ifabric-it"}
    r.update(extra)
    return r


def build_src(root):
    _w(root, "FIXTURE-SYNTHETIC.txt", "synthetic test data; not evidence\n")
    v1 = REG.format(v="v1", at="2026-10-06T12:39:29Z", sup="v0-pilot4", cap=20000, c16v="C16-v1")
    v11 = REG.format(v="v1.1", at="2026-10-06T13:36:43Z", sup="v1", cap=25000, c16v="C16-v1.1")
    v0 = REG.format(v="v0-pilot4", at="2026-10-06T10:15:44Z", sup="none", cap=100000, c16v="C16-v0").replace("FROZEN", "EXPLORATORY")
    _w(root, "register/versions/v1.yaml", v1)
    _w(root, "register/versions/v1.1.yaml", v11)
    _w(root, "register/versions/v0-pilot4.yaml", v0)
    for _v, _at in (("v1", "2026-10-06T12:40:22Z"), ("v1.1", "2026-10-06T13:38:05Z"), ("v0-pilot4", "2026-10-06T10:16:20Z")):
        _w(root, "register/versions/%s.head.json" % _v, {"VersionId": "VID-" + _v, "LastModified": _at})  # PR-48: build refuses a version with no T1 proof
    import hashlib
    sha11 = hashlib.sha256(v11.encode()).hexdigest()
    _w(root, "register/experiments/rules-v1.1.json", {"post_hoc": {"declared": True, "control": "C16", "rule_replaced": "C16-cap/1",
                                                                   "rule_new": "C16-cap/2", "decided_by": "the captain"}})
    _w(root, "register/t1/t1-v1.1.json", [{"file": "v1.1.yaml", "key": "ifabric/register/v1.1.yaml",
                                           "head_object": {"VersionId": "VID-v11", "LastModified": "2026-10-06T13:38:05+00:00"}}])
    _w(root, "register/experiments/experiments.jsonl", "\n".join(json.dumps(x) for x in (
        {"pilot": "P1b", "run_id": PILOT_FAIL, "failed": True, "failure_class": "client-read-timeout (not upstream-5xx)",
         "provenance": "PILOT", "scenario": "S1", "mode": "observe", "time_utc": ["2026-10-06T11:15:50.455Z", "2026-10-06T11:31:03.860Z"],
         "measured": {"c16_tokens": 22980}},
        {"pilot": "P3", "run_id": PILOT_OK, "failed": False, "provenance": "PILOT", "scenario": "S3", "derivation_eligible": True,
         "time_utc": ["2026-10-06T11:56:45.689Z", "2026-10-06T11:57:41.945Z"], "measured": {"c16_tokens": 16052}})) + "\n")
    _w(root, "run-ids.txt", NAMED + "\n")
    _w(root, "derived/run-catalogue.jsonl", json.dumps({"run_id": WARM, "label": "OURS-ROLE-UNDECLARED", "assessed": False,
                                                        "first_seen": "2026-10-06T13:52:05Z", "last_seen": "2026-10-06T13:53:11Z",
                                                        "tokens_in": 100, "tokens_out": 10}) + "\n")
    _w(root, "store/records.jsonl", "".join(json.dumps(_rec("r%d" % i, NAMED, "2026-10-06T13:56:%02dZ" % (10 + i))) + "\n" for i in range(3)))
    _w(root, "assessments/C16/named.json", _assessment("C16", "C16-v1.1", "v1.1", "run", NAMED, {"total_tokens": 330, "unit": "tokens"}, sha11))
    _w(root, "assessments/C9/named.json", _assessment("C9", "C9-v1", "v1.1", "run", NAMED,
                                                      {"windows": [{"runtime": "ifabric-it", "change_pct": "-12.5"},
                                                                   {"runtime": "ifabric-network", "change_pct": "8.6"}]}, sha11))
    _w(root, "assessments/C9/window.json", _assessment("C9", "C9-v1", "v1.1", "window", "2026-10-06T13:00:00Z..2026-10-06T14:00:00Z",
                                                       {"hours": [{"change_pct": "3.0"}]}, sha11,
                                                       start="2026-10-06T13:00:00Z", end="2026-10-06T14:00:00Z"))
    _w(root, "assessments/C16/orphan.json", _assessment("C16", "C16-v9", "v9", "run", NAMED, {"total_tokens": 1}))
    # T2: approval findings, the delivery log, the ServiceNow exports (v1.1's APPROVED note sits on v1's incident)
    for ver, d in (("v1", "approval"), ("v1.1", "approval-v1.1")):
        _w(root, "register/%s/approval-finding.json" % d, {"control_ref": "REG", "threshold_version": ver, "scope_kind": "escalation",
                                                         "scope_id": "register-" + ver, "kind": "approval", "detected_at": "2026-10-06T12:40:22Z"})
        _w(root, "register/%s/approved-note-canonical.txt" % d, "APPROVED threshold register %s, sha256 abc\n" % ver)
    f1, f11 = "ifabric:REG:v1:escalation:register-v1:approval", "ifabric:REG:v1.1:escalation:register-v1.1:approval"
    _w(root, "register/approval/t2-sys-id.txt", "sys1\n")
    _w(root, "register/approval/delivery-log.jsonl", "\n".join(json.dumps(x) for x in (
        {"finding_id": f1, "number": "INC0000321", "state": "DELIVERED", "sys_id": "sys1", "ts": "2026-10-06T12:44:12Z"},
        {"finding_id": f11, "number": "INC0000338", "state": "DELIVERED", "sys_id": "sys2", "ts": "2026-10-06T13:41:06Z"},
        {"finding_id": f1, "number": "INC0000321", "state": "RESPONDED", "actor": "owner@example.invalid", "at": "2026-10-06 13:44:39",
         "at_basis": "last_update"},
        {"finding_id": f11, "number": "INC0000338", "state": "AWAITING_RESPONSE", "cutoff": "2026-10-06T15:16:14Z",
         "checked_at": "2026-10-06T15:01:19Z"})) + "\n")
    notes321 = ("2026-10-06 06:44:39 - Fixture Owner (Work notes)\nAPPROVED threshold register v1.1, sha256 abc - more\n\n"
                "2026-10-06 06:02:37 - Fixture Owner (Work notes)\nAPPROVED threshold register v1, sha256 abc - more\n\n"
                "2026-10-06 05:44:07 - Integration (Work notes)\nProofLab finding %s\n\n" % f1)
    _w(root, "servicenow/export/INC0000321.json", {"finding_id": f1, "incident": {"number": "INC0000321", "opened_at": "2026-10-06 12:44:07"},
                                                   "notes_display": {"work_notes": notes321, "comments": ""}})
    _w(root, "servicenow/export/INC0000338.json", {"finding_id": f11, "incident": {"number": "INC0000338", "opened_at": "2026-10-06 13:41:00"},
                                                   "notes_display": {"work_notes": "2026-10-06 06:41:00 - Integration (Work notes)\nProofLab finding x\n\n",
                                                                     "comments": ""}})
    _w(root, "gap-list.md", "# gaps\n")
    return root


@pytest.fixture
def src(tmp_path):
    return build_src(str(tmp_path / "src"))


def test_register_head_is_the_chain_head_not_the_text_sort(src):
    h = history.register_history(src)
    assert h["head"] == "v1.1"
    assert [r["version"] for r in h["versions"]] == ["v0-pilot4", "v1", "v1.1"]
    v11 = h["versions"][-1]
    assert v11["current"] and v11["supersedes"] == "v1" and v11["t1"]["version_id"] == "VID-v11"
    assert v11["t1"]["last_modified"] == "2026-10-06T13:38:05Z" and "POST-HOC" in v11["post_hoc"]


def test_projection_binds_assessments_to_their_version_and_lists_history(src, tmp_path):
    res = projector.project(src, str(tmp_path / "out"))
    idx = res["index"]
    reg = idx["register"]
    assert reg["version"] == "v1.1" and [v["version"] for v in reg["versions"]] == ["v0-pilot4", "v1", "v1.1"]
    by = dict((a["assessment_id"], a) for a in idx["assessments"])
    c16 = [a for a in idx["assessments"] if a["control_ref"] == "C16"]
    assert c16 and c16[0]["verdict"] == "SATISFIED"
    ctl = dict((c["ref"], c["verdict_overall"]) for c in idx["claim"]["controls"])
    assert ctl["C16"] == "SATISFIED" and ctl["C9"] == "SATISFIED"
    proj = json.load(open(os.path.join(str(tmp_path / "out"), "assessments", "C16", projector.safe(c16[0]["assessment_id"]) + ".json")))
    assert proj["threshold"]["observation_limit"]["value"] == 25000 and proj["threshold"]["source_ref"] == "register:register/versions/v1.1.yaml"
    c9 = [a for a in by if a.startswith("C9:")]
    assert len(c9) == 2
    p9 = json.load(open(os.path.join(str(tmp_path / "out"), "assessments", "C9", projector.safe("C9:C9-v1:run:%s:r1" % NAMED) + ".json")))
    assert p9["threshold"]["observation_limit"] == {"value": 75, "operator": "<=", "unit": "% relative change vs baseline"}
    assert p9["measured"]["value"] == 12.5
    # the orphan (C16-v9, in no register) is skipped AND said
    assert any("C16-v9" in s["why"] for s in res["report"]["skipped_assessments"])
    rc9 = [c for c in reg["controls"] if c["ref"] == "C9"][0]
    assert rc9["observation_limit"]["value"] == 75 and rc9["version_date"] == "2026-10-06"
    sys.path.insert(0, os.path.join(REPO, "tests", "projector"))
    import _projector_schema as SC
    sch = SC.load_schema()
    assert SC.validate(idx, sch["$defs"]["packIndex"], sch) == []      # approvals, history, every run: still the contract


def test_approvals_come_from_the_t2_files(src, tmp_path):
    ap = history.approvals(src)
    assert ap["v1"]["status"] == "APPROVED" and ap["v1"]["incident"] == "INC0000321"
    assert ap["v1"]["at"] == "2026-10-06T13:02:37Z" and ap["v1"]["approver"]["name"] == "Fixture Owner"
    assert ap["v1.1"]["status"] == "PENDING" and ap["v1.1"]["incident"] == "INC0000338"
    assert "INC0000321" in ap["v1.1"]["note"] and "not counted" in ap["v1.1"]["note"]
    idx = projector.project(src, str(tmp_path / "out"))["index"]
    assert idx["register"]["approval"]["status"] == "PENDING"       # the head (v1.1), honestly
    vers = dict((v["version"], v["approval"]["status"]) for v in idx["register"]["versions"])
    assert vers == {"v0-pilot4": "MISSING", "v1": "APPROVED", "v1.1": "PENDING"}


def test_every_run_is_listed_with_its_label(src, tmp_path):
    runs = projector.project(src, str(tmp_path / "out"))["index"]["runs"]
    by = dict((r["cid"], r) for r in runs)
    assert set(by) == {NAMED, WARM, PILOT_FAIL, PILOT_OK}
    assert by[NAMED]["provenance"] == "ASSESSED" and by[WARM]["provenance"] == "EXPLORATORY"
    assert by[PILOT_FAIL]["failure_class"].startswith("client-read-timeout") and "FAILED" in by[PILOT_FAIL]["purpose"]
    assert by[PILOT_FAIL]["records_in_store"] == 0 and "store_note" in by[PILOT_FAIL]
    assert [r["cid"] for r in runs] == [PILOT_FAIL, PILOT_OK, WARM, NAMED]     # by start time


def _build(src, tmp_path, *extra):
    wd = tmp_path / "wd"
    os.makedirs(str(wd), exist_ok=True)
    for n in ("run-ids.txt", "gap-list.md"):
        with open(os.path.join(src, n)) as a, open(str(wd / n), "w") as b:
            b.write(a.read())
    with open(os.path.join(src, "register", "versions", "v1.1.yaml")) as a, open(str(wd / "register.yaml"), "w") as b:
        b.write(a.read())
    out = str(tmp_path / "pack")
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PROOFLAB_SCAN_VALUES", None)
    p = subprocess.run([sys.executable, "-m", "prooflab", "pack", "build", "--out", out, "--src", src, "--workdir", str(wd)] + list(extra),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=env, cwd=REPO)
    return p, out


def test_build_prints_skips_stages_named_files_and_fills_the_readme(src, tmp_path):
    p, out = _build(src, tmp_path, "--label", "final", "--strict-readme")
    assert p.returncode == 0, p.stdout
    assert "SKIPPED assessment C16:C16-v9" in p.stdout
    for name in ("named-runs.md", "decisions-log.md", "security-matrix.md", "adversarial", "servicenow", "projection-report.json"):
        assert os.path.exists(os.path.join(out, name)), name
    readme = open(os.path.join(out, "README.md")).read()
    assert "`final`" in readme and "INC0000321" in readme
    assert "the first named run's start" in readme        # no window.json: from the named runs, said so
    assert "FULL: C16, C7 and C9" not in readme and "PARTIAL: not assessed in this pack: C7" in readme
    assert "uploaded after the pack as a sidecar" in readme and "no assessment is BREACHED" in readme
    assert "account id" in readme and "2026-10-06T15:16:14Z" in readme
    assert "register v1 approval APPROVED on INC0000321" in readme
    assert "ADV-R-06" not in readme.split("## 6.")[1].split("## 7.")[0]    # no observed adversarial result is claimed
    ans = json.load(open(os.path.join(out, "pack-index.json")))["answers"]
    assert any(a["key"].startswith("C9|run|") for a in ans) and any(a["key"].startswith("C9|interval|") for a in ans)
