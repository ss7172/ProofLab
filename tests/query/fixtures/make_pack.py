"""Regenerates ./pack: a SYNTHETIC evidence pack for the query tests. Shapes follow the 2026-10-05 snapshot
(correlation id families, phases, per-call records); every value is invented, no token, no raw copy.
Run:  python3 make_pack.py   (writes next to this file)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
CID1 = "ifabric-run-1791260000-ab12cd"     # C16 BREACHED
CID2 = "ifabric-run-1791261000-cd34ef"     # C16 SATISFIED
CID3 = "ifabric-adv-1791262000-ee55aa"     # adversarial, outside the window rule's provenance set
REF = "customer-1791250000-0a0a0a"        # reference trio: out of scope
T = "2026-10-06T%s.000Z"


def w(rel, text):
    path = os.path.join(PACK, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as h:
        h.write(text)


def jl(rel, rows):
    w(rel, "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def rec(cid, n, kind, ts, **kw):
    r = {"schema": "ifabric.evidence/1", "record_id": "20261006T%s-%s-%08x" % (ts[11:19].replace(":", "") + "000", kind[:6], n),
         "record_kind": kind, "phase": "ifabric." + kind, "detail": kw.pop("detail", kind), "correlation_id": cid,
         "run.id": cid, "verdict": kw.pop("verdict", "RECORDED"), "ts": ts, "provenance": kw.pop("provenance", "LIVE_SUBJECT"),
         "authorship": kw.pop("authorship", "TESTIMONY"), "source.refs": ["synthetic:fixture#%d" % n], "emitter": "fixture", "null_reasons": {}}
    r.update(kw)
    return r


records = []
for cid, base in ((CID1, "06:00"), (CID2, "06:30")):
    h = base[:2]
    m = int(base[3:])
    records += [
        rec(cid, 1, "handoff", T % ("%s:%02d:00" % (h, m)), **{"handoff.id": cid + ":h1", "actor.id": "ifabric-customer", "actor.runtime_id": "rt-customer",
            "actor.version": "sha-synthetic-1", "principal.platform": "bootstrap-key", "on_behalf_of": "sree", "ep.id": "EP-5", "ep.responsible": "orchestrator"}),
        rec(cid, 2, "decision", T % ("%s:%02d:05" % (h, m)), verdict="ALLOW", **{"ep.id": "EP-1", "inline.action": "proceed", "inline.mode": "observe",
            "ep.responsible": "runtime-hook", "actor.id": "ifabric-customer", "control.ref": "C16", "control.owner": "Sree", "model.id": "nemotron-synthetic"}),
        rec(cid, 3, "platform_decision", T % ("%s:%02d:06" % (h, m)), verdict="ALLOW", authorship="PLATFORM", **{"ep.id": "EP-6", "outcome.real": "SERVED"}),
        rec(cid, 4, "action", T % ("%s:%02d:07" % (h, m)), **{"tool.name": "customer-records", "tool.declared": True, "actor.id": "ifabric-customer"}),
        rec(cid, 5, "approval", T % ("%s:%02d:01" % (h, m)), **{"ep.id": "EP-0", "ep.responsible": "orchestrator"}),
    ]
records.append(rec(CID1, 6, "finding", T % "06:10:00", verdict="ESCALATED", detail="C16 breach raised to the owner"))
records.append(rec(CID1, 7, "notification", T % "06:10:30", detail="delivered to ServiceNow (synthetic)"))
records.append(rec(CID3, 1, "adversarial", T % "06:40:00", provenance="AUTHORIZED_TEST", **{"actor.id": "ifabric-it"}))
records.append(rec(REF, 1, "observation", T % "05:50:00", provenance="UNATTRIBUTED", authorship="PLATFORM"))
jl("store/records.jsonl", records)

jl("derived/run-index.jsonl", [
    {"cid": CID1, "provenance": "LIVE_SUBJECT", "phase": "Alert 1", "condition": "none", "first_span": T % "06:00:00", "last_span": T % "06:12:00", "register_version": "v1"},
    {"cid": CID2, "provenance": "LIVE_SUBJECT", "phase": "Alert 1", "condition": "none", "first_span": T % "06:30:00", "last_span": T % "06:40:00", "register_version": "v1"},
    {"cid": CID3, "provenance": "BASELINE", "phase": "Alert 0", "condition": "adv", "first_span": T % "06:40:00", "last_span": T % "06:41:00", "register_version": "v1"},
    {"cid": REF, "provenance": "UNATTRIBUTED", "phase": "Alert 0", "first_span": T % "05:50:00", "last_span": T % "05:55:00"},
])
jl("derived/run-catalogue.jsonl", [
    {"cid": CID1, "label": "ours: ifabric trio", "source": "ours", "assessed": True},
    {"cid": CID2, "label": "ours: ifabric trio", "source": "ours", "assessed": True},
    {"cid": CID3, "label": "ours: adversarial", "source": "ours", "assessed": False},
    {"cid": REF, "label": "reference trio", "source": "reference", "assessed": False},
])


def assess(control, cid, tv, verdict, value, limit, start, extra=None, kind="run", rev=1):
    a = {"assessment_id": "%s:%s:%s:%s:r%d" % (control, tv, kind, cid, rev), "control_ref": control, "control_id": "X",
         "threshold_version": tv, "register_version": "v1", "scope_kind": kind, "scope_id": cid, "scope_start": start,
         "scope_end": start, "requirement_verdict": verdict, "design": "SATISFIED", "operation": verdict, "deficiency": "operation" if verdict == "BREACHED" else "none",
         "evidence_sufficiency": "COMPLETE", "measured": {"value": value, "unit": "tokens", "source": "gateway-figure-of-record"}, "limit": limit,
         "exceptions": [{"call": "c-9", "over_by": value - limit}] if verdict == "BREACHED" else [],
         "denominators": {"calls": 9}, "completeness": {"expected": 9, "captured": 9, "missing": 0}, "gaps": [],
         "evidence_refs": ["aws-spans:q-SYNTH#1"], "as_of": T % "07:00:00", "evaluator_name": "prooflab.evaluators.%s" % control.lower()}
    a.update(extra or {})
    return a


def put(a):
    w("assessments/%s/%s.json" % (a["control_ref"], a["assessment_id"].replace(":", "_")), json.dumps(a, indent=1, sort_keys=True) + "\n")


put(assess("C16", CID2, "C16-v1", "SATISFIED", 41000, 50000, T % "06:30:00"))
put(assess("C7", CID1, "C7-v1", "SATISFIED", 1.0, 1.0, T % "06:00:00"))
put(assess("C7", CID2, "C7-v1", "BREACHED", 0.8, 1.0, T % "06:30:00"))
put(assess("C9", "hour-06", "C9-v1", "SATISFIED", 3.0, 5.0, T % "06:00:00", kind="hour"))
put(assess("C9", CID1, "C9-v1", "SATISFIED", 3.0, 5.0, T % "06:00:00"))
# C16 for CID1 arrives as a flat `assessment` record in the store (the other accepted shape)
flat = rec(CID1, 8, "assessment", T % "07:00:00", verdict="BREACHED", detail="C16 BREACHED: 121500 > cap 50000", **{
    "control.ref": "C16", "control.id": "ACN-COST-001", "threshold.version": "C16-v1", "threshold.value": 50000, "register.version": "v1",
    "measured.value": 121500, "measured.unit": "tokens", "measured.source": "gateway-figure-of-record", "assessment.id": "C16:C16-v1:run:%s:r1" % CID1,
    "assessment.requirement_verdict": "BREACHED", "assessment.deficiency": "operation", "assessment.evidence_sufficiency": "COMPLETE",
    "assessment.denominators": {"calls": 9}, "assessment.operation": "BREACHED", "assessment.design": "SATISFIED",
    "assessment.scope_start": T % "06:00:00"})
with open(os.path.join(PACK, "store", "records.jsonl"), "a") as h:
    h.write(json.dumps(flat, sort_keys=True) + "\n")


def ctl(cid, num, name, ref, tv, extra=""):
    return ('  - control_id: "%s"\n    name: "%s"\n    metric: "synthetic metric %s"\n    observation_limit: 50000\n    exception_tolerance: 0\n'
            '    measurement_basis: "synthetic basis"\n    owner: "Sree"\n    version_date: "2026-10-06T03:52:10Z"\n    control_ref: %s\n'
            '    threshold_version: %s\n%s' % (num, name, ref, ref, tv, extra))


reg = ('# SYNTHETIC register for the query tests\nversion: v1\nversion_date: "2026-10-06T03:52:10Z"\nclaim_id: C-FM-01\nregister_owner: Sree\ncontrols:\n'
       + ctl(0, "16", "Per-run token spend cap", "C16", "C16-v1", "    risk_ref: R-C16\n") + ctl(0, "7", "Event recording coverage", "C7", "C7-v1")
       + ctl(0, "9", "Drift against a frozen baseline", "C9", "C9-v1"))
w("register/versions/v1.yaml", reg)
w("register/v1.head.json", json.dumps({"LastModified": "2026-10-06T03:55:00Z", "VersionId": "synthetic-1"}) + "\n")
w("register/versions/v1.risks.yaml", 'version: v1\nrisks:\n  - risk_id: R-C16\n    statement: "A run spends more tokens than the cap"\n    owner: "Sree"\n    appetite: "low"\n')
w("register/inventory/inv-1.yaml", 'version: inv-1\nsystem_id: customer-fault-resolution\nsystem_owner: Sree\ncomponents:\n'
  '  - component_id: ifabric-customer\n    owner: "Sree"\n    host: "agentcore-runtime-synthetic"\n    model: "nemotron-synthetic"\n')
w("MANIFEST.json", json.dumps({"files": {}, "note": "synthetic"}) + "\n")
w("window.json", json.dumps({"start": T % "05:00:00", "end": T % "09:00:00"}) + "\n")
