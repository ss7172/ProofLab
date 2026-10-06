"""A small SYNTHETIC pack source tree for the projector tests (derived shapes, no real data, no token values)."""
import json
import os

A = "ifabric-run-1790000000-aaaaaa"      # named PASS run
B = "ifabric-run-1790000100-bbbbbb"      # named BREACH run
E = "ifabric-run-1790000200-eeeeee"      # exploratory (not in run-ids.txt), provenance LIVE_SUBJECT on its records
S = "fault-1790000300-ssssss"            # a SYNTHETIC-labelled run: never enters the pack
SHA = "a" * 64

REGISTER = """version: v1-fixture
version_date: 2026-10-06
owner: owner@example.invalid
owner_name: Fixture Owner
controls:
  - control_id: 16
    control_ref: C16
    threshold_version: C16-v1
    name: Per-run token spend cap
    metric: tokens per run
    metric_unit: tokens per run
    observation_limit: 300
    exception_tolerance: 0
    measurement_basis: gateway llm lines
    enforcement_point: EP-1
    version_date: 2026-10-06
    owner: owner@example.invalid
  - control_id: 7
    control_ref: C7
    threshold_version: C7-v1
    name: Automatic event recording
    metric: gap rate
    metric_unit: percent
    observation_limit: 10
    exception_tolerance: 1
    measurement_basis: expected events
    enforcement_point: EP-5
    version_date: 2026-10-06
    owner: owner@example.invalid
"""


def rec(rid, cid, kind, ts, prov="LIVE_SUBJECT", **extra):
    r = {"schema": "ifabric.evidence/1", "record_id": rid, "record_kind": kind, "phase": "ifabric." + kind,
         "detail": "fixture", "correlation_id": cid, "run.id": cid, "verdict": "RECORDED", "ts": ts,
         "provenance": prov, "authorship": "PLATFORM", "source.refs": ["gateway:action_id=" + rid],
         "emitter": "fixture-adapter", "null_reasons": {}, "emitted.at": ts, "emitted.clock": "gateway"}
    r.update(extra)
    return r


def assessment(cid, verdict, value, rev=1, ctl="C16", finding=True):
    a = {"assessment_id": "%s:%s-v1:run:%s:r%d" % (ctl, ctl, cid, rev), "control_ref": ctl,
         "control_id": {"C16": "ACN-COST-001", "C7": "AIA-LOG-001"}[ctl], "threshold_version": ctl + "-v1",
         "threshold_sha256": SHA, "register_version": "v1-fixture", "scope_kind": "run", "scope_id": cid,
         "scope_start": "2026-10-06T07:00:00Z", "scope_end": "2026-10-06T07:05:00Z", "requirement_verdict": verdict,
         "design": "effective", "operation": "ineffective" if verdict == "BREACHED" else "effective",
         "deficiency": "operation" if verdict == "BREACHED" else "none", "evidence_sufficiency": "sufficient",
         "measured": {"value": value, "unit": "tokens per run"}, "exceptions": [],
         "denominators": {"expected": {"count": 3, "source": "fixture"}, "observed": 3, "matched": 3, "missing": 0},
         "completeness": {}, "formula": "sum(tokens.in + tokens.out)", "evidence_refs": ["gateway:run=" + cid, "ev-1"],
         "gaps": ["fixture gap"] if verdict == "BREACHED" else [], "evaluator_name": "prooflab.evaluators.%s" % ctl.lower(),
         "evaluator_sha256": "b" * 64, "as_of": "2026-10-06T08:00:00Z", "snapshot_id": "snap-1", "finding": None}
    if verdict == "BREACHED" and finding:
        a["finding"] = {"control_ref": ctl, "control_id": a["control_id"], "threshold_version": ctl + "-v1",
                        "scope_kind": "run", "scope_id": cid, "verdict": "BREACHED", "summary": "fixture breach",
                        "detected_at": "2026-10-06T08:00:00Z", "evidence": ["gateway:run=" + cid], "kind": "finding"}
    return a


def build(root):
    def w(rel, text):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
    w("FIXTURE-SYNTHETIC.txt", "synthetic test data; not evidence\n")
    w("run-ids.txt", "# named runs\nFM-A %s\nFM-B=%s\n" % (A, B))
    w("window.json", json.dumps({"start": "2026-10-05T22:00:00Z", "end": "2026-10-06T14:00:00Z"}))
    w("register/versions/v1-fixture.yaml", REGISTER)
    w("claim.json", json.dumps({"id": "C-FIXTURE", "text": "Fixture claim text.", "approval": {"status": "PENDING"}}))
    w("gap-list.md", "# gaps\n")
    rows = []
    n = 0
    for cid, toks in ((A, (100, 120)), (B, (200, 220)), (E, (50, 60))):
        for i, t in enumerate(toks):
            n += 1
            rows.append(rec("r%03d" % n, cid, "action", "2026-10-06T07:0%d:00Z" % (i + 1), prov=("PILOT" if cid == E else "LIVE_SUBJECT"),
                            **{"tokens.in": t, "tokens.out": 10, "model.id": "m", "call.id": "act-%d" % n,
                               "actor.id": "ifabric-it", "trace.id": "t" * 32}))
        n += 1
        rows.append(rec("r%03d" % n, cid, "handoff", "2026-10-06T07:03:00Z", prov=("PILOT" if cid == E else "LIVE_SUBJECT"),
                        **{"handoff.from": "a", "handoff.to": "b"}))
    rows.append(rec("r900", B, "decision", "2026-10-06T07:04:00Z", verdict="DENY",
                    **{"ep.id": "EP-1", "inline.mode": "observe", "inline.action": "halt"}))
    rows.append(rec("r901", B, "notification", "2026-10-06T07:06:00Z", **{"ep.id": "EP-13", "control.ref": "C16"}))
    rows.append(rec("r902", A, "approval", "2026-10-06T07:00:30Z", **{"control.ref": "APPROVAL"}))
    rows.append(rec("r903", S, "action", "2026-10-06T07:02:00Z", prov="SYNTHETIC", **{"tokens.in": 1, "tokens.out": 1, "model.id": "m"}))
    rows.append(rec("r904", B, "judgment", "2026-10-06T07:05:00Z", **{"reason": "c16-budget-halt", "deciding_evidence": ["ledger:x"],
                                                                      "reversible_step": "none"}))
    w("store/records.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    w("assessments/C16/a.json", json.dumps(assessment(A, "SATISFIED", 350)))
    w("assessments/C16/b1.json", json.dumps(assessment(B, "SATISFIED", 300, rev=1)))
    w("assessments/C16/b2.json", json.dumps(assessment(B, "BREACHED", 430, rev=2)))
    w("assessments/C7/b.json", json.dumps(assessment(B, "BREACHED", 20, ctl="C7")))
    w("servicenow/cases/case1.json", json.dumps({"finding_id": "ifabric:C16:C16-v1:run:%s:finding" % B, "incident": "INC0000001"}))
    w("MANIFEST.json", json.dumps({"files": [{"path": "run-ids.txt"}]}))
    return root
