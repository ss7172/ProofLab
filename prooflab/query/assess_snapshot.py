"""`prooflab assess --snapshot DIR` (D1): turn one refreshed snapshot into Assessment documents. Stdlib, Python 3.9.

Reads store/records.jsonl + derived/run-index.jsonl + derived/run-catalogue.jsonl (what `prooflab refresh` wrote) and
a FROZEN register file; runs the stateless evaluators over each assessed run of ours; writes
`<snapshot>/assessments/<C>/<cid>.json` (the contract Assessment as a dict, the shape `prooflab query` reads).

No threshold is held here: the C16 pin is the register's own derivation for the run's mode (the mode the run's EP-1
decisions carried, else `--mode`); the C7 numbers come from the register entry (`observation_limit` as
`coverage_min_pct=..;gap_max_ms=..;violating_gap_share_max_pct=..`, or `--limit C7:key=value` for a value the
register text does not carry yet); the expected workflow events are the register's `workflow_events`, placed by
prooflab/query/workflow_map.py (run.* and handoff.* on the orchestrator, the rest per agent invocation, negotiation
on IT's Gateway C invocation), minus the two conditional ones (escalation: only on an escalate disposition; decision:
per model call, covered by --expect-ep1-decisions).

C9 (PR-41; ARCH 5.3, D3): the AgentCore metric captures under raw/agentcore-metrics/ (prooflab/query/c9_inputs.py:
Latency Maximum + Errors Sum per runtime per 60 s, the figure of record) are cut to each run's W2 window per runtime
and judged two-sided by prooflab.evaluators.c9 against the register's baseline for the run's scenario
(`baseline_value_<runtime>_<scenario>`) and the limits in its `observation_limit` (`max_relative_change_pct=..;
violating_windows_max_pct=..;errors_max=..`, or `--limit C9:key=value`). Missing or not-yet-published datapoints are
INDETERMINATE with a gap, never SATISFIED. Each closed UTC hour holding an assessed run is rolled up into
`assessments/C9/window-<hour>.json` (scope_kind window) for window questions.
"""
from __future__ import annotations

import json
import os
import re

from prooflab.contract import clocks as _clocks
from prooflab.contract import register as _reg
from prooflab.contract import verdicts as V
from prooflab.evaluators import c16, c16_core, c7, c9, claim
from prooflab.registry import parse as P
from prooflab.query import c9_inputs as _c9in
from prooflab.query import workflow_map as _wf
from prooflab.registry import pinned as _pinned
from prooflab.stitch import toolcalls as _toolcalls

CONDITIONAL_EVENTS = _wf.CONDITIONAL_EVENTS
OURS_PREFIX = "ifabric-"
STORE_PATH = ("store", "records.jsonl")


class AssessError(ValueError):
    pass


def _read_jsonl(path):
    rows = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        doc = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(doc, dict):
                        rows.append(doc)
    return rows


def _rid(r):
    return r.get("run.id") or r.get("correlation_id")


def find_register(root, explicit=None):
    """The register to assess against: --register, else the newest frozen register/versions/v*.yaml in the snapshot."""
    if explicit:
        return explicit
    vdir = os.path.join(root, "register", "versions")
    names = sorted(n for n in (os.listdir(vdir) if os.path.isdir(vdir) else [])
                   if n.endswith(".yaml") and not n.endswith(".risks.yaml") and not n.startswith("inv-"))
    if not names:
        raise AssessError("no register: pass --register <frozen register file> (none in %s)" % vdir)
    return os.path.join(vdir, sorted(names, key=lambda n: [int(t) if t.isdigit() else 0 for t in re.split(r"(\d+)", n)])[-1])


def _agents_of(recs):
    seen = []
    for r in recs:
        if r.get("authorship", "TESTIMONY") != "TESTIMONY":
            continue
        for k in ("actor.id", "handoff.to"):
            a = r.get(k)
            if isinstance(a, str) and a.startswith(OURS_PREFIX) and a not in seen:
                seen.append(a)
    return seen


def _stream_of(recs, agent):
    for r in recs:
        if r.get("actor.id") == agent and r.get("handoff.id"):
            return "%s:%s" % (agent, r["handoff.id"])
    return "%s:h0" % agent


def _is_gateway(r):
    return r.get("authorship") == "PLATFORM" and r.get("observed.clock") == "gateway"


def _model_call_span(r):
    return _is_gateway(r) and r.get("tokens.in") is not None and r.get("tokens.out") is not None \
        and r.get("record_kind") in ("metric", "platform_decision")


def _tool_call_span(r):
    """False only for a gateway request the store NAMES as another method (initialize, tools/list, notifications/*,
    a plain http call): not a governed action. An observation that names no method is kept (older shapes)."""
    m = re.match(r"^gateway request (\S+) ", str(r.get("detail") or ""))
    return m is None or m.group(1) == c7.TOOL_METHOD


def run_facts(recs):
    """The evaluators' inputs for ONE run, read from its store records."""
    spans = [r for r in recs if _model_call_span(r)]
    calls, blocked = [], []
    for r in spans:
        calls.append({"action_id": r.get("call.id"), "listener": "llm", "model": r.get("model.id"),
                      "tokens_in": r.get("tokens.in"), "tokens_out": r.get("tokens.out"),
                      "http_status": r.get("outcome.http_status"), "start": r.get("observed.at"),
                      "end": r.get("observed.at"), "handoff_id": r.get("handoff.id")})
        if r.get("outcome.real") == "BLOCKED_GUARDRAIL" and r.get("call.id"):
            blocked.append(r["call.id"])
    ours = [r for r in recs if r.get("authorship", "TESTIMONY") == "TESTIMONY"]
    decisions = [r for r in ours if r.get("record_kind") == "decision"]
    actions = []
    for r in recs:
        if _is_gateway(r) and r.get("call.id"):
            if _model_call_span(r):
                kind = "model.call"
            elif r.get("record_kind") == "observation":
                if not _tool_call_span(r):
                    continue                    # MCP handshake span (initialize, tools/list, notifications): not an action
                kind = "tool.call"
            else:
                continue
            actions.append({"action_id": r["call.id"], "kind": kind, "agent": None, "end": r.get("observed.at"),
                            "method": c7.TOOL_METHOD if kind == "tool.call" else None})
    refusals = [{"call_id": r.get("call.id"), "trace_id": r.get("trace.id")} for r in recs
                if _is_gateway(r) and r.get("record_kind") == "platform_decision"
                and r.get("outcome.real") in c7.REFUSAL_OUTCOMES and r.get("outcome.real") != "BLOCKED_GUARDRAIL"]
    stops = []
    for d in decisions:
        if d.get("ep.id") == "EP-1" and d.get("inline.action") == "halt" and d.get("actor.id"):
            s = {"agent": d["actor.id"], "stream": _stream_of(ours, d["actor.id"])}
            if s not in stops:
                stops.append(s)
    return {"calls": calls, "blocked": blocked, "decisions": decisions, "actions": actions, "refusals": refusals,
            "stops": stops, "ours": ours, "all": recs, "agents": _agents_of(ours)}


def _mode_of(decisions, default):
    modes = [d.get("inline.mode") for d in decisions if d.get("ep.id") == "EP-1" and d.get("inline.mode")]
    return modes[0] if modes and modes[0] in c16_core.MODES else default


def parse_overrides(items):
    out = {}
    for item in items or ():
        ctl, _, kv = item.partition(":")
        key, eq, val = kv.partition("=")
        if not (ctl and eq and key):
            raise AssessError("--limit wants <C>:<key>=<value>, got %r" % item)
        out.setdefault(ctl.upper(), {})[key.strip()] = val.strip()
    return out


def c7_pin(entry, register_sha, register_version, overrides, ep1_deployed):
    after = [x.strip() for x in (entry.get("workflow_events_after_stop") or "").split(",") if x.strip()]
    pin = {"control_id": entry.get("library_id"), "threshold_version": entry.get("threshold_version"),
           "register_sha256": register_sha, "register_version": register_version,
           "observation_limit": entry.get("observation_limit"), "ep1_deployed": bool(ep1_deployed),
           "workflow_events_after_stop": after}
    tol = entry.get("exception_tolerance")
    if tol not in (None, ""):
        pin["exception_tolerance"] = tol
    pin.update(overrides)
    return pin


def c9_pin(entry, register_sha, register_version, overrides, scenario, runtimes):
    """The C9 pin for one run: every value from the register entry (or an explicit --limit override)."""
    pin = {"control_id": entry.get("library_id"), "threshold_version": entry.get("threshold_version"),
           "register_sha256": register_sha, "register_version": register_version,
           "observation_limit": entry.get("observation_limit"), "limit_direction": entry.get("limit_direction"),
           "exception_tolerance": entry.get("exception_tolerance")}
    pin.update(_c9in.baseline_pin(entry, scenario, runtimes))
    pin.update(overrides)
    return pin


def _write_assessment(root, d, name):
    path = os.path.join(root, "assessments", d["control_ref"], name + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(d, indent=1, sort_keys=True))
    return path


def c9_hourly(root, c9_runs, as_of, snap_id):
    """Roll the assessed runs' C9 windows up per CLOSED UTC hour (the hour the run started in) -> written list."""
    by_hour = {}
    asof = _c9in.utc(as_of)
    for a, windows, pin, start in c9_runs:
        h0 = _c9in.hour_of(start)
        h1 = h0 + _c9in._dt.timedelta(hours=1)
        if asof is None or h1 > asof:
            continue                                     # only closed hours
        rows = [dict(w, hour=_c9in.iso(h0), runtime=rt, threshold_version=pin.get("threshold_version"), pin=pin)
                for rt, w in sorted(windows.items())]
        slot = by_hour.setdefault((h0, h1), ([], [], {}))
        slot[0].append(a)
        slot[1].extend(rows)
        slot[2].setdefault(pin.get("threshold_version"), pin)
    written = []
    for (h0, h1) in sorted(by_hour):
        runs, rows, pins = by_hour[(h0, h1)]
        a = c9.assess_window(_c9in.iso(h0), _c9in.iso(h1), runs, rows, pins, as_of, snapshot_id=snap_id)
        d = claim.as_dict(a)
        for r in d["measured"].get("hours") or ():
            r.pop("pin", None)
        path = _write_assessment(root, d, "window-" + h0.strftime("%Y%m%dT%H"))
        written.append(("C9", d["scope_id"], d["requirement_verdict"], path))
    return written


def workflow_events(entry, agents, ours):
    """The register's workflow event names, placed by prooflab.query.workflow_map (the one mapping, ARCH 5.2/7.2):
    run.* and handoff.* on the orchestrator, the rest per agent invocation, negotiation on IT's Gateway C only.
    `agents` is kept for the call signature; the invocations come from the script's own EP-5 records."""
    return _wf.expected(_wf.names_of(entry), ours)


def assess_snapshot(root, register=None, controls=("C16", "C7", "C9"), runs=None, default_mode="observe",
                    overrides=None, expect_ep1=False, as_of=None):
    """-> {"written": [(control, cid, verdict, path)], "skipped": [(control, cid, why)], "register": path}."""
    store = _read_jsonl(os.path.join(root, *STORE_PATH))
    if not store:
        raise AssessError("no store/records.jsonl in %s: run `prooflab refresh --snapshot` first" % root)
    reg_path = find_register(root, register)
    with open(reg_path, "rb") as fh:
        reg_bytes = fh.read()
    try:
        doc = P.parse_register(reg_bytes.decode("utf-8"))
    except ValueError as exc:
        raise AssessError("register does not parse: %s" % exc)
    entries = dict((e.get("control_ref"), e) for e in doc["entries"])
    reg_sha = _reg.register_sha256(reg_bytes)
    reg_version = doc["top"].get("version") or doc["top"].get("register_version") or ""
    cat = _read_jsonl(os.path.join(root, "derived", "run-catalogue.jsonl"))
    idx = dict((r.get("run_id") or r.get("cid"), r) for r in _read_jsonl(os.path.join(root, "derived", "run-index.jsonl")))
    if runs:
        cids = list(runs)
    else:
        cids = sorted(r["run_id"] for r in cat if r.get("assessed") and (r.get("run_id") or "").startswith(OURS_PREFIX))
    manifest = {}
    try:
        with open(os.path.join(root, "SNAPSHOT.json"), "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (IOError, OSError, ValueError):
        pass
    as_of = as_of or manifest.get("as_of") or _clocks.now_utc()
    snap_id = "snapshot:%s" % (manifest.get("as_of") or "unknown")
    by_run = {}
    for r in store:
        by_run.setdefault(_rid(r), []).append(r)
    ov = parse_overrides(overrides) if not isinstance(overrides, dict) else overrides
    written, skipped = [], []
    pins = {}
    metrics, warmups, c9_runs = None, (), []
    for cid in cids:
        recs = by_run.get(cid, [])
        if not recs:
            skipped += [(c, cid, "no records for this run in the store") for c in controls]
            continue
        f = run_facts(recs)
        prov = (idx.get(cid) or {}).get("provenance") or next(
            (r.get("provenance") for r in f["ours"] if r.get("provenance")), None)
        cond = next((r.get("run.condition") for r in f["ours"] if r.get("run.condition")), None) or "none"
        docs = []
        if "C16" in controls:
            if "C16" not in entries:
                skipped.append(("C16", cid, "no C16 entry in the register"))
            else:
                mode = _mode_of(f["decisions"], default_mode)
                if mode not in pins:
                    pins[mode] = c16_core.PinnedC16.from_env(_pinned.env_for(reg_bytes, mode))
                ep1 = [d for d in f["decisions"] if d.get("ep.id") == "EP-1"]
                tiers = [d.get("threshold.tier") for d in ep1 if d.get("threshold.tier")]
                sa = {"attrs": {}, "tier_rule": "", "envelope_tier": tiers[0] if tiers else None,
                      "provenance": prov, "condition": cond}
                comp = {"expected_action_ids": [d["call.id"] for d in ep1 if d.get("call.id")],
                        "spans_ingested": bool(f["calls"]), "blocked_action_ids": f["blocked"]}
                docs.append(c16.assess_run(cid, f["calls"], sa, f["decisions"], pins[mode], comp, as_of,
                                           snapshot_id=snap_id))
        if "C7" in controls:
            if "C7" not in entries:
                skipped.append(("C7", cid, "no C7 entry in the register"))
            else:
                pin7 = c7_pin(entries["C7"], reg_sha, reg_version, ov.get("C7", {}), expect_ep1)
                exp = c7.expected_events(cid, f["actions"], f["refusals"],
                                         workflow_events(entries["C7"], f["agents"], f["ours"]), f["stops"], pin7)
                slack = claim.frac(pin7.get("tool_join_slack_ms"))
                ours7, joined = _toolcalls.join_records(f["all"], f["ours"], float(slack) if slack is not None else 0)
                docs.append(c7.assess_run(cid, exp, ours7, [], pin7, as_of, snapshot_id=snap_id,
                                          provenance=prov, condition=cond))
        if "C9" in controls:
            if "C9" not in entries:
                skipped.append(("C9", cid, "no C9 entry in the register"))
            else:
                if metrics is None:
                    metrics, warmups = _c9in.read_metrics(root), _c9in.warm_up_index(by_run)
                windows, facts = _c9in.run_windows(recs, metrics, as_of, warmups)
                pin9 = c9_pin(entries["C9"], reg_sha, reg_version, ov.get("C9", {}), facts["scenario"], windows)
                a9 = c9.assess_run(cid, windows, pin9, as_of, snapshot_id=snap_id, provenance=prov, condition=cond,
                                   first_span_at=facts["started"], inputs=facts)
                docs.append(a9)
                start = _c9in.utc(facts["started"])
                if start is not None and windows:
                    c9_runs.append((a9, windows, pin9, start))
        for a in docs:
            d = claim.as_dict(a)
            path = _write_assessment(root, d, cid)
            written.append((d["control_ref"], cid, d["requirement_verdict"], path))
    if c9_runs:
        written += c9_hourly(root, c9_runs, as_of, snap_id)
    return {"written": written, "skipped": skipped, "register": reg_path}


def worst_exit(written):
    worst = 0
    for _, _, verdict, _ in written:
        code = V.exit_code(verdict)
        worst = code if code == 1 or (worst != 1 and code > worst) else worst
    return worst
