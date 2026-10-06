"""PR-27: an OFFLINE end-to-end rehearsal of the Phase-1 tool chain on SYNTHETIC data (IMPLEMENTATION-PLAN §4.2,
§5.2 rows 11-25, §7 G4/G5; ARCHITECTURE §5.1/§5.2/§5.4/§5.5/§9). Stdlib, Python 3.9.

    /usr/bin/python3 tests/e2e/rehearse.py [--keep] [--json OUT]

Every product step runs the REAL code path: `python3 -m prooflab <verb>` in a fresh temp WORKDIR (the same
interpreter the judge uses), and the agent-side records come from the MERGED adapter constructors (EmitClient,
ModelCallAdapter with the real c16 core and the frozen pin, ToolCallRecorder, judgment, the orchestrator's
records.make) posting into a local FAKE ledger. Nothing here calls AWS, a cluster or ServiceNow: ServiceNow is
Arth's FakeServiceNow on loopback. Where a merged module has no verb for a step, the rehearsal marks that step
XFAIL with a defect id (see DEFECTS) and, to keep the downstream steps real, runs a clearly labelled stand-in
("glue") that calls the merged library functions directly.

Exit 0: no step FAILED (PASS / XFAIL / SKIP only). Exit 1: at least one FAIL. A PASS/FAIL table goes to stdout.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
import zipfile
from dataclasses import asdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in (REPO, os.path.join(REPO, "tests", "store")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from prooflab.contract import ids as IDS  # noqa: E402
from prooflab.contract import verdicts as V  # noqa: E402

PASS, FAIL, XFAIL, SKIP = "PASS", "FAIL", "XFAIL", "SKIP"
QUERY_BUDGET_S = 120.0          # G5: an answer from a fresh unzip in under 2 minutes

# Defects found in merged code (ids used by XFAIL rows; the full text goes to the PR result).
DEFECTS = {
    "D1": "no verb turns a snapshot into Assessment documents: `prooflab assess` only reads assessments/<C>/*.json",
    "D2": "nothing renders sketch.png from architecture/one-page.svg; pack build only copies it from --workdir",
    "D3": "the aws/spans collector output (raw/aws-spans/<cid>/spans.jsonl, Logs Insights @timestamp/@message rows)"
          " is read by neither `refresh` (raw/spans/*.jsonl, flat keys) nor `postrun` (@message is not unpacked)",
    "D4": "no verb builds Finding files from assessments (adapters/human_loop.build_finding has no caller)",
    "D5": "C7 workflow events in the register (run.started, handoff.sent, invocation.received, handoff.received,"
          " run.finished) are never emitted with those phases by the merged orchestrator/app",
    "D6": "EP-1 decision records carry call.id = null (written before the call), so C7's decision:<action_id>"
          " expectation (ep1_deployed) can never be observed",
    "D7": "pack build does not stage findings/ (PACK_TOP lacks it; ARCH 9.1 lists assessments/... findings/)",
    "D8": "EP-1 decision records carry evaluator.sha256 = null (model_call._evaluate never passes it to"
          " decide_inline), so EP-2's replay cannot be reconciled on the same evaluator.sha256 (G5)",
    "D10": "nothing writes kit-crosscheck/<CID>/gateway-log.json (ARCH 9.1: refresh writes it); pack build only"
           " copies the directory if present",
    "D11": "query --control --run prints the T1 LastModified and the run start but never compares them: a register"
           " dated after the run still answers BREACHED/SATISFIED with no gap (G5 date check)",
    "D12": "the declared fault (suppress-record / inject-tool-output) is carried in the envelope by"
           " orchestrator/run.build_envelope but never applied by the app: ifabric_app._envelope drops it from the"
           " translated envelope and nothing in ifabric_app.py or adapters/runtime/ reads it, so a live N4 emits"
           " every record and C7 N4 comes out SATISFIED, not BREACHED (G5 C7 BREACH named run)",
    "D9": "`registry inventory` freezes to register/versions/inv-N.yaml but the query engine (and ARCH 9.1) read"
          " register/inventory/*.yaml: `query --inventory` finds no inventory in the pack",
}

ROLES = ("ifabric-customer", "ifabric-it", "ifabric-network")


# ------------------------------------------------------------------ the step table
class Rehearsal(object):
    def __init__(self, py, work, verbose=False):
        self.py, self.work, self.verbose = py, work, verbose
        self.rows = []
        self.state = {}

    def row(self, step, status, note=""):
        note = " ".join(str(note).split())
        self.rows.append({"step": step, "status": status, "note": note})
        if self.verbose:
            print("%-6s %-46s %s" % (status, step, note), file=sys.stderr)

    def check(self, step, ok, note="", xfail=None):
        """ok True -> PASS; ok False -> XFAIL(defect) when xfail names one, else FAIL."""
        if ok:
            self.row(step, PASS, note)
        elif xfail:
            self.row(step, XFAIL, "[%s] %s" % (xfail, note))
        else:
            self.row(step, FAIL, note)
        return ok

    def cli(self, args, cwd=None, env_extra=None, timeout=300):
        env = dict((k, v) for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "USER"))
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if env_extra:
            env.update(env_extra)
        t0 = time.time()
        p = subprocess.run([self.py, "-m", "prooflab"] + list(args), cwd=cwd or REPO, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), time.time() - t0

    def table(self):
        lines = ["%-4s %-6s %-48s %s" % ("#", "RESULT", "STEP", "NOTE")]
        for i, r in enumerate(self.rows, 1):
            lines.append("%-4d %-6s %-48s %s" % (i, r["status"], r["step"][:48], r["note"]))
        counts = dict((s, sum(1 for r in self.rows if r["status"] == s)) for s in (PASS, FAIL, XFAIL, SKIP))
        lines.append("TOTAL: %d PASS, %d FAIL, %d XFAIL, %d SKIP  (python %s)" % (
            counts[PASS], counts[FAIL], counts[XFAIL], counts[SKIP], self.py))
        return "\n".join(lines)


def _p(*parts):
    return os.path.join(*parts)


def _read(path, mode="r"):
    with open(path, mode) as fh:
        return fh.read()


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(data, bytes) else "w") as fh:
        fh.write(data)
    return path


def _jsonl(rows):
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def _iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + ".%03dZ" % int((t % 1) * 1000)


# ------------------------------------------------------------------ 1. registry: v0-pilot, derive, v1, pins
def make_v1_text(text, version, date, cap):
    """The working register turned into the v1 the live lane freezes (the edits ARCH 3.3 step 4 names)."""
    out, entry = [], None
    for line in text.splitlines():
        key = line.split(":", 1)[0].lstrip("- ").strip()
        ind = line[:len(line) - len(line.lstrip())]
        if key == "control_id":
            entry = line.split(":", 1)[1].strip().strip('"')
        c16 = entry == "16"       # only C16's values change in v1, so only C16 bumps (the version-bump rule)
        if re.match(r"^(version|register_version):", line):
            line = "%s: %s" % (key, version)
        elif re.match(r"^(version_date|frozen_at):", line):
            line = '%s: "%s"' % (key, date)
        elif re.match(r"^supersedes:", line):
            line = "supersedes: v0-pilot"
        elif key == "version_date" and c16:
            line = '%sversion_date: "%s"' % (ind, date)
        elif key == "threshold_version" and c16:
            line = re.sub(r"-v0\b", "-v1", line)
        elif key in ("cap_tier_default",):
            line = "%s%s: %d" % (ind, key, cap)
        elif key == "observation_limit" and c16 and re.search(r":\s*\d+\s*$", line):
            line = "%sobservation_limit: %d" % (ind, cap)
        elif key == "inline_modes":
            line = "%sinline_modes: enforce,observe" % ind
        out.append(line)
    return "\n".join(out) + "\n"


def make_v1_risks(text, version, date):
    out = []
    for line in text.splitlines():
        if re.match(r"^version:", line):
            line = "version: %s" % version
        elif re.match(r"^version_date:", line):
            line = 'version_date: "%s"' % date
        out.append(line)
    return "\n".join(out) + "\n"


def step_registry(R):
    w = R.work
    reg_dir = _p(w, "register")
    os.makedirs(reg_dir)
    shutil.copy(_p(REPO, "register", "register.yaml"), _p(reg_dir, "register.yaml"))
    shutil.copy(_p(REPO, "register", "risks.yaml"), _p(reg_dir, "risks.yaml"))
    shutil.copy(_p(REPO, "register", "inventory.yaml"), _p(reg_dir, "inventory.yaml"))
    rc, out, err, _ = R.cli(["registry", "freeze", "--version", "v0-pilot", "--register", _p(reg_dir, "register.yaml"),
                             "--risks", _p(reg_dir, "risks.yaml"), "--out", reg_dir])
    v0 = _p(reg_dir, "versions", "v0-pilot.yaml")
    R.check("registry freeze v0-pilot (working copy)", rc == 0 and os.path.isfile(v0), (out + err).strip()[:160])
    rc2, _, err2, _ = R.cli(["registry", "freeze", "--version", "v0-pilot", "--register", _p(reg_dir, "register.yaml"),
                             "--risks", _p(reg_dir, "risks.yaml"), "--out", reg_dir])
    R.check("registry freeze refuses a rewrite", rc2 == 2 and "already frozen" in err2, err2.strip()[:120])
    rc, out, err, _ = R.cli(["registry", "pin", "--register", v0, "--mode", "observe"])
    R.check("v0-pilot pin (observe, caps = ceiling)", rc == 0 and json.loads(out or "{}").get("c16", {}).get("mode") == "observe",
            err.strip()[:120])

    # the minimal pilot set: P1 (S1), P3 (S3), P5 (S2 natural, overspends), CIDs minted by the contract
    base = int(time.time()) - 3 * 3600
    pilots = {"P1": IDS.mint_cid("ifabric-test", base + 1), "P3": IDS.mint_cid("ifabric-test", base + 2),
              "P5": IDS.mint_cid("ifabric-test", base + 3)}
    exp = [
        {"run_id": pilots["P1"], "scenario": "S1", "provenance": "PILOT", "condition": "none", "mode": "observe",
         "measured": {"c16_tokens": 21000, "c7_gap_ms_max": 9000,
                      "c9_latency_max_ms": {"ifabric-it": 8400, "ifabric-network": 8300}}},
        {"run_id": pilots["P3"], "scenario": "S3", "provenance": "PILOT", "condition": "none", "mode": "observe",
         "measured": {"c16_tokens": 33000, "c7_gap_ms_max": 11000,
                      "c9_latency_max_ms": {"ifabric-it": 8600, "ifabric-network": 8200}}},
        {"run_id": pilots["P5"], "scenario": "S2", "provenance": "PILOT", "condition": "none", "mode": "observe",
         "measured": {"c16_tokens": 1900000, "c7_gap_ms_max": 15000, "c9_latency_max_ms": {"ifabric-it": 278000}}},
    ]
    exp_path = _write(_p(reg_dir, "experiments", "experiments.jsonl"), _jsonl(exp))
    rules = _p(reg_dir, "experiments", "rules.json")
    shutil.copy(_p(REPO, "tests", "registry", "fixtures", "rules.synthetic.json"), rules)
    rc, out, err, _ = R.cli(["registry", "derive", "--experiments", exp_path, "--rules", rules])
    items = json.loads(out) if rc == 0 else []
    c16 = next((i for i in items if i.get("control_ref") == "C16"), {})
    cap = c16.get("value")
    R.check("registry derive: C16 cap cites P1+P3 only", rc == 0 and c16.get("status") == "DERIVED"
            and sorted(c16.get("cites", [])) == sorted([pilots["P1"], pilots["P3"]]) and isinstance(cap, int),
            "cap=%s cites=%s" % (cap, c16.get("cites")))
    rc, _, err, _ = R.cli(["registry", "derive", "--experiments", exp_path, "--rules", rules, "--use", pilots["P5"]])
    R.check("registry derive refuses a cap from S2 (P5)", rc == 2 and "never derived" in err, err.strip()[:100])
    R.state.update(pilots=pilots, cap=cap, derive=items)

    # v1: derive -> owner approves -> freeze; T1 is the live lane's (a synthetic head.json stands in)
    t1 = time.time() - 3600
    date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t1))
    v1_reg = _write(_p(w, "draft", "register.yaml"), make_v1_text(_read(_p(reg_dir, "register.yaml")), "v1", date, cap or 0))
    v1_risks = _write(_p(w, "draft", "risks.yaml"), make_v1_risks(_read(_p(reg_dir, "risks.yaml")), "v1", date))
    rc, out, err, _ = R.cli(["registry", "freeze", "--version", "v1", "--register", v1_reg, "--risks", v1_risks,
                             "--out", reg_dir, "--supersedes", v0])
    v1 = _p(reg_dir, "versions", "v1.yaml")
    ok = R.check("registry freeze v1 --supersedes v0-pilot", rc == 0 and os.path.isfile(v1), (out + err).strip()[:160])
    if not ok:
        return False
    v1_bytes = _read(v1, "rb")
    head = {"_note": "SYNTHETIC T1 stand-in (the live lane writes the head-object JSON)", "VersionId": "synthetic",
            "LastModified": _iso(t1), "ETag": "synthetic",
            "ChecksumSHA256": hashlib.sha256(v1_bytes).hexdigest()}
    _write(_p(reg_dir, "versions", "v1.head.json"), json.dumps(head, indent=1, sort_keys=True))
    rc, out, err, _ = R.cli(["registry", "inventory", "--version", "inv-1", "--inventory", _p(reg_dir, "inventory.yaml"),
                             "--out", reg_dir])
    R.check("registry inventory freeze inv-1", rc == 0, (out + err).strip()[:160])

    # pin round-trip: the env block the live lane patches -> the core's from_env -> the post-run re-derivation
    from prooflab.evaluators import c16_core
    from prooflab.registry import pinned
    pins = {}
    for mode in ("enforce", "observe"):
        rc, out, err, _ = R.cli(["registry", "pin", "--register", v1, "--mode", mode, "--env"])
        env = json.loads(out) if rc == 0 else {}
        ok = rc == 0 and bool(env)
        detail = err.strip()[:120]
        if ok:
            try:
                pin = c16_core.PinnedC16.from_env(env)
                pj = env["IFABRIC_PIN_JSON"]
                errs = pinned.check_pin(v1_bytes, pj, env["IFABRIC_PIN_SHA256"])
                ok = (not errs and pin.mode == mode and dict(pin.caps).get(pin.default_tier) == cap)
                detail = "mode=%s cap=%s errors=%s" % (pin.mode, dict(pin.caps), errs)
                pins[mode] = {"env": env, "pin": pin, "json": pj}
                _write(_p(w, "pins", "v1-%s.json" % mode), pj)
            except Exception as exc:  # noqa: BLE001 - reported as the row's note
                ok, detail = False, "%s: %s" % (type(exc).__name__, exc)
        R.check("pin round-trip v1 %s (env -> from_env -> check_pin)" % mode, ok, detail)
    R.state.update(v1=v1, v1_bytes=v1_bytes, t1=t1, pins=pins)
    return len(pins) == 2


# ------------------------------------------------------------------ 2. synthetic named runs via the merged adapters
class _SR(object):
    pass


class FakeModelEvent(object):
    """The Strands before/after model-call event shape the adapter reads (as tests/runtime_c16/helpers.FakeEvent)."""

    def __init__(self, projected, tin, tout):
        self.projected_input_tokens = projected
        self.cancel = False
        self.exception = None
        sr = _SR()
        sr.message = {"role": "assistant", "content": [{"text": "ok"}],
                      "metadata": {"usage": {"inputTokens": tin, "outputTokens": tout}}}
        sr.stop_reason = "end_turn"
        self.stop_response = sr


# name -> scenario, mode, plan per agent (model calls, tokens per call), tool calls on the IT agent, suppressed
RUN_PLANS = {
    "N1": {"scenario": "S1", "mode": "enforce", "calls": {"ifabric-customer": 2, "ifabric-it": 3, "ifabric-network": 2},
           "tin": 2200, "tout": 150, "tools": 1, "suppress": False},
    "N2": {"scenario": "S2", "mode": "observe", "calls": {"ifabric-customer": 2, "ifabric-it": 14, "ifabric-network": 4},
           "tin": 3900, "tout": 40, "tools": 2, "suppress": False},
    "N3": {"scenario": "S2", "mode": "enforce", "calls": {"ifabric-customer": 2, "ifabric-it": 14, "ifabric-network": 4},
           "tin": 3900, "tout": 40, "tools": 2, "suppress": False},
    "N4": {"scenario": "S1", "mode": "enforce", "calls": {"ifabric-customer": 2, "ifabric-it": 3, "ifabric-network": 2},
           "tin": 2200, "tout": 150, "tools": 1, "suppress": True,
           "fault": "suppress-record:ifabric-it:tool.call:1"},   # SIMULATED by this driver: see D12
    "N5": {"scenario": "S1", "mode": "enforce", "calls": {"ifabric-customer": 2, "ifabric-it": 3, "ifabric-network": 2},
           "tin": 2200, "tout": 150, "tools": 1, "suppress": False},
}


def _span(cid, aid, listener, tin, tout, t0, t1, trace, agent, status=200):
    """One aws/spans span (the OTel shape the gateway writes: nested attributes, nanosecond strings)."""
    attrs = {"listener": listener, "modaas.run_id": cid, "modaas.action_id": aid, "http.status": str(status),
             "modaas.trace_id": trace}
    if listener == "llm":
        attrs.update({"gen_ai.usage.input_tokens": str(tin), "gen_ai.usage.output_tokens": str(tout),
                      "gen_ai.request.model": "nvidia.nemotron-super-3-120b"})
    return {"attributes": attrs, "startTimeUnixNano": str(int(t0 * 1e9)), "endTimeUnixNano": str(int(t1 * 1e9)),
            "traceId": trace, "spanId": hashlib.sha256(aid.encode()).hexdigest()[:16], "name": listener,
            "_agent": agent}


def gen_run(R, name, cid, plan, client):
    """Drive the merged adapters for one named run; return the platform-side spans and the run facts."""
    from adapters.runtime import emit_client as ec
    from adapters.runtime import judgment as J
    from adapters.runtime import model_call as MC
    from adapters.runtime import tool_call as TC
    from adapters.runtime.tally import RunTally
    from prooflab.adapters.orchestrator import records as ORCH

    pinfo = R.state["pins"][plan["mode"]]
    pin, env = pinfo["pin"], pinfo["env"]
    trace = IDS.mint_traceparent().split("-")[1]
    prov = "FAULT_INJECTION" if plan["suppress"] else "LIVE_SUBJECT"
    mk = lambda kind, detail, **kw: ORCH.make(kind, cid, detail, "not applicable: " + kind, provenance=prov,  # noqa: E731
                                            **dict({"trace.id": trace, "run.condition": "none"}, **kw))
    client.emit(mk("lifecycle", "run started: scenario %s mode %s" % (plan["scenario"], plan["mode"]),
                   phase="run.started"))   # the phases prooflab/adapters/orchestrator/run.py emits (C7, D5)
    spans, actions, workflow, stops = [], [], [], []
    tally_tokens = tally_calls = 0
    prev, n_call, halted = "orchestrator", 0, False
    first = time.time()
    for n, agent in enumerate(ROLES):
        hid = IDS.handoff_id(cid, n) if n >= 1 else None
        if hid:
            client.emit(mk("handoff", "handoff %s sent: %s -> %s" % (hid, prev, agent), phase="handoff.sent",
                           **{"handoff.id": hid, "handoff.from": prev, "handoff.to": agent,
                              "handoff.payload_sha256": hashlib.sha256(cid.encode()).hexdigest(),
                              "handoff.data_classification": "internal", "ep.id": "EP-5",
                              "ep.kind": "orchestrator (record only)", "ep.responsible": "team iFabric (Sree)"}))
        ctx = ec.RunContext(cid, agent, provenance=prov, register_version=env["IFABRIC_REGISTER_VERSION"],
                            pin_sha256=env["IFABRIC_PIN_SHA256"], handoff_id=hid, handoff_from=prev, handoff_to=agent,
                            trace_id=trace, control_owner="Sree")
        stream = "%s:%s" % (agent, hid or "h0")
        client.emit(ec.lifecycle_record(ctx, "invocation.received", "received %s" % hid,   # as ifabric_app.invoke
                                        extra={"phase": "invocation.received"}))
        J.record_intent(client, ctx, "%s answers handoff %s" % (agent, hid or "(none)"))
        workflow += [{"agent": agent, "event": "intent", "stream": stream, "order": 0}]
        tally = RunTally(cid, "default")
        tally.seed(tally_tokens, tally_calls)
        mc = MC.ModelCallAdapter(cid, pin, tier="default", tally=tally, emit=client.emit,
                                 identity={"actor_id": agent, "provenance": prov, "trace_id": trace},
                                 model_id="nemotron-super-120b")
        recorder = TC.ToolCallRecorder(client, ctx, declared_tools=("lookup",))
        for i in range(plan["calls"][agent]):
            if halted:
                break
            n_call += 1
            ev = FakeModelEvent(plan["tin"], plan["tin"], plan["tout"])
            mc.on_before_model_call(ev)
            if ev.cancel:                     # EP-1 halted: no call goes out, so no span
                halted = True
                stops.append({"agent": agent, "stream": stream})
                break
            aid = "act-%s-%04d" % (name, n_call)
            t0 = time.time()
            mc.capture.observe_headers({"x-modaas-action-id": aid}, 200)
            mc.on_after_model_call(ev)
            spans.append(_span(cid, aid, "llm", plan["tin"], plan["tout"], t0, time.time() + 0.001, trace, agent))
            actions.append({"action_id": aid, "kind": "model.call", "agent": agent, "end": _iso(time.time())})
            if agent == "ifabric-it" and i < plan["tools"]:
                tid = "act-%s-t%02d" % (name, i + 1)
                recorder.before("lookup", {"site": "SITE-DEN-12", "n": i})
                t0 = time.time()
                # suppress-record:ifabric-it:tool.call:1 SIMULATED HERE by the rehearsal driver (no merged code
                # applies a declared fault: D12); the dropped record is the EP-3 tool.call AFTER record.
                if not (plan["suppress"] and i == 0):
                    recorder.after("lookup", {"site": "SITE-DEN-12", "n": i}, status=200, call_id=tid, result={"ok": i})
                spans.append(_span(cid, tid, "mcp", 0, 0, t0, time.time() + 0.001, trace, agent))
                actions.append({"action_id": tid, "kind": "tool.call", "agent": agent, "end": _iso(time.time())})
        disp = "escalate" if halted else "resolve"
        J.record_judgment(client, ctx, disp, "C16 halt" if halted else "synthetic rehearsal answer",
                          precedence_rule="c16-halt" if halted else None)
        workflow += [{"agent": agent, "event": "judgment", "stream": stream, "order": 1}]
        if disp == "escalate":
            workflow += [{"agent": agent, "event": "escalation", "stream": stream, "order": 2}]
        tally_tokens, tally_calls = tally.committed, tally.calls
        client.emit(mk("handoff", "invocation of %s returned status=OK halted=%s" % (agent, halted),
                       phase="handoff.received", **dict({"ep.id": "EP-5", "ep.kind": "orchestrator (record only)",
                               "ep.responsible": "team iFabric (Sree)"},
                              **({"handoff.id": hid, "handoff.from": prev, "handoff.to": agent} if hid else {}))))
        prev = agent
        if halted:
            break
    client.emit(mk("lifecycle", "run finished: status FINISHED", phase="run.finished"))
    return {"cid": cid, "spans": spans, "actions": actions, "workflow": workflow, "stops": stops, "halted": halted,
            "tally_tokens": tally_tokens, "start": _iso(first), "end": _iso(time.time()), "provenance": prov,
            "plan": plan}


def step_runs(R):
    from adapters.runtime import emit_client as ec
    from fake_ledger import TEST_CREDENTIAL, FakeLedger
    runs = {}
    base = int(time.time()) - 600
    with FakeLedger() as led:
        client = ec.EmitClient(led.url, TEST_CREDENTIAL, stdout=io.StringIO())
        for k, name in enumerate(sorted(RUN_PLANS)):
            cid = IDS.mint_cid("ifabric-run", base + 60 * k)
            runs[name] = gen_run(R, name, cid, RUN_PLANS[name], client)
        fl = client.flush(timeout=10)
        client.close()
        stats = dict(client.stats)
        rows = list(led.rows)
    R.check("adapters emit into the fake ledger (no reject, no gap)",
            fl["ok"] and stats["rejected"] == 0 and not client.gaps and stats["posted"] == len(rows),
            "posted=%d rejected=%d gaps=%d" % (stats["posted"], stats["rejected"], len(client.gaps)))
    n3 = runs["N3"]
    stop = [r for r in rows if r.get("run.id") == n3["cid"] and r.get("record_kind") == "decision"
            and r.get("outcome.real") == "CANCELLED_C16"]
    R.check("N3 (enforce): EP-1 halted with a stop record", n3["halted"] and bool(stop),
            "halted=%s stop_decisions=%d tally=%s" % (n3["halted"], len(stop), n3["tally_tokens"]))
    n2_deny = [r for r in rows if r.get("run.id") == runs["N2"]["cid"] and r.get("record_kind") == "decision"
               and r.get("verdict") == "DENY"]
    R.check("N2 (observe): DENY recorded, calls served", not runs["N2"]["halted"] and bool(n2_deny),
            "deny decisions=%d" % len(n2_deny))
    R.state.update(runs=runs, ledger_rows=rows)
    step_fault(R)
    return True


# ------------------------------------------------------------------ 2b. the declared fault on the merged path (D12)
FAULT_KEYS = ("fault", "declared_faults")


def _fault_readers(paths):
    """STATIC scan: every `x["fault"]`, `x.get("fault")` or `.declared_faults` read in the given sources."""
    hits = []
    for path in paths:
        tree = ast.parse(_read(path), path)
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Subscript):
                sl = node.slice
                key = sl.value if isinstance(sl, ast.Constant) else None
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" \
                    and node.args and isinstance(node.args[0], ast.Constant):
                key = node.args[0].value
            elif isinstance(node, ast.Attribute) and node.attr in FAULT_KEYS:
                key = node.attr
            if key in FAULT_KEYS:
                hits.append("%s:%d" % (os.path.relpath(path, REPO), node.lineno))
    return hits


def _import_ifabric_app():
    """Import the merged agents/ifabric-customer/ifabric_app.py; bedrock_agentcore / strands are stubbed only
    when absent (they are only used inside build(), which the rehearsal never calls)."""
    saved, added = list(sys.path), []
    stubs = {"bedrock_agentcore": None, "bedrock_agentcore.runtime": {"BedrockAgentCoreApp": object},
             "strands": {"Agent": object}}
    try:
        for name, attrs in stubs.items():
            try:
                __import__(name)
            except ImportError:
                m = types.ModuleType(name)
                for k, v in (attrs or {}).items():
                    setattr(m, k, v)
                sys.modules[name] = m
                added.append(name)
        sys.path.insert(0, _p(REPO, "agents", "ifabric-customer"))
        sys.modules.pop("ifabric_app", None)
        import ifabric_app  # noqa: E402
        return ifabric_app
    finally:
        sys.path[:] = saved
        for name in added:
            sys.modules.pop(name, None)
        sys.modules.pop("ifabric_app", None)


def step_fault(R):
    """N4's C7 BREACH needs the declared fault applied by the RUNTIME. Check the merged path end to end:
    orchestrator envelope -> app envelope translation -> a runtime component that reads it."""
    from prooflab.adapters.orchestrator import conditions as COND
    from prooflab.adapters.orchestrator import run as ORUN
    spec = RUN_PLANS["N4"]["fault"]
    fault = COND.parse_fault(spec)
    args = argparse.Namespace(mode="enforce", scenario="S1")
    pin = {"register_version": "v1", "register_sha256": None, "pin_sha256": None}
    cond = {"name": "none", "sha256": None}
    cid = R.state["runs"]["N4"]["cid"]
    env = ORUN.build_envelope(cid, IDS.handoff_id(cid, 1), "ifabric-customer", fault["agent"], args, pin, cond,
                              fault, "default", "FAULT_INJECTION", (0, 0))
    R.check("orchestrator envelope carries %s to %s" % (spec, fault["agent"]),
            env.get("fault", {}).get("spec") == spec and env.get("provenance") == "FAULT_INJECTION",
            "run.build_envelope fault=%s provenance=%s" % (bool(env.get("fault")), env.get("provenance")))
    try:
        app = _import_ifabric_app()
        translated, raw = app._envelope({"prompt": "x", "ifabric": env})
        carried = "fault" in (translated.get("envelope") or {})
        note = "ifabric_app._envelope: translated keys %s (raw keeps fault=%s)" % (
            sorted((translated.get("envelope") or {}).keys()), "fault" in raw)
    except Exception as exc:  # noqa: BLE001
        carried, note = False, "ifabric_app import/_envelope failed: %s: %s" % (type(exc).__name__, exc)
    R.check("app envelope translation carries the fault", carried, note, xfail="D12")
    srcs = [_p(REPO, "agents", "ifabric-customer", "ifabric_app.py")] + sorted(
        _p(REPO, "adapters", "runtime", f) for f in os.listdir(_p(REPO, "adapters", "runtime")) if f.endswith(".py"))
    readers = _fault_readers(srcs)
    R.check("the merged app applies %s (STATIC scan)" % spec, bool(readers),
            "readers of fault/declared_faults in ifabric_app.py + adapters/runtime/: %s; N4 rows below use a"
            " driver-simulated fault" % (readers or "none"), xfail="D12")


# ------------------------------------------------------------------ 3. snapshot: collectors, refresh, postrun
def step_snapshot(R):
    from prooflab.adapters.collectors import aws_spans, capture
    runs, snap = R.state["runs"], _p(R.work, "snap")
    for name, run in runs.items():
        rows = [r for r in R.state["ledger_rows"] if r.get("correlation_id") == run["cid"]]
        _write(_p(snap, "raw", "ledger", run["cid"] + ".jsonl"), _jsonl(rows))

    # (a) the REAL collector with a fake `aws` runner answering Logs Insights the way AWS does (@timestamp/@message)
    def fake_runner(argv):
        if "start-query" in argv:
            return 0, json.dumps({"queryId": "q-1"}).encode(), b""
        q = R.state["_cur"]
        res = [[{"field": "@timestamp", "value": _iso(int(s["endTimeUnixNano"]) / 1e9)},
                {"field": "@message", "value": json.dumps(dict((k, v) for k, v in s.items() if k != "_agent"),
                                                         sort_keys=True)},
                {"field": "@ptr", "value": "p"}] for s in q]
        return 0, json.dumps({"status": "Complete", "results": res}).encode(), b""

    ctx = capture.Ctx(root=snap, runner=fake_runner, sleep=lambda s: None)
    for name, run in runs.items():
        R.state["_cur"] = run["spans"]
        aws_spans.pull(ctx, run["cid"], run["start"], run["end"])
    coll = [p for p in _walk(_p(snap, "raw")) if p.endswith("spans.jsonl")]
    R.check("collector writes raw/aws-spans/<cid>/spans.jsonl (fake aws)", len(coll) == len(runs), "%d files" % len(coll))

    run_ids = "".join(runs[n]["cid"] + "\n" for n in sorted(runs))
    _write(_p(R.work, "workdir", "run-ids.txt"), run_ids)
    prov = dict((r["cid"], r["provenance"]) for r in runs.values())
    prov.update(dict((cid, "PILOT") for cid in R.state["pilots"].values()))
    prov_path = _write(_p(R.work, "provenance.json"), json.dumps(prov))
    args = ["refresh", "--snapshot", snap, "--run-ids", _p(R.work, "workdir", "run-ids.txt"),
            "--provenance", prov_path, "--as-of", _iso(time.time()), "--join-tolerance-s", "5"]
    rc, out, err, _ = R.cli(args)
    metrics = _metric_cids(snap)
    R.check("refresh sees the collector's aws/spans capture", rc == 0 and runs["N2"]["cid"] in metrics,
            "rc=%d metric runs=%d" % (rc, len(metrics)))

    # postrun straight on the collector's file (what the live lane would run)
    n2 = runs["N2"]
    n2_file = [p for p in coll if n2["cid"] in p][0]
    rc, out, err, _ = R.cli(["postrun", "--cid", n2["cid"], "--spans", n2_file, "--pin", _p(R.work, "pins", "v1-observe.json"),
                             "--pin-sha256", R.state["pins"]["observe"]["env"]["IFABRIC_PIN_SHA256"]])
    R.check("postrun reads the collector's aws/spans capture", rc == 0, (err.strip() or "ok")[:120])

    # the rows EP-2's replay reads (the collector's own file is also read directly by the postrun row above)
    flat_lines = []
    for run in runs.values():
        for s in run["spans"]:
            a = s["attributes"]
            flat = {"ts": _iso(int(s["endTimeUnixNano"]) / 1e9), "protocol": a["listener"], "listener": a["listener"],
                    "modaas.run_id": a["modaas.run_id"], "modaas.action_id": a["modaas.action_id"],
                    "modaas.trace_id": a["modaas.trace_id"], "http.status": a["http.status"]}
            for k in ("gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "gen_ai.request.model"):
                if k in a:
                    flat[k] = a[k]
            flat_lines.append(flat)
        _write(_p(R.work, "spans", run["cid"] + ".json"),
               json.dumps({"rows": [dict((k, v) for k, v in s.items() if k != "_agent") for s in run["spans"]]}))
    rc, out, err, _ = R.cli(args)
    metrics = _metric_cids(snap)
    R.check("refresh -> store + derived (kit-crosscheck + corroboration written)", rc == 0 and all(r["cid"] in metrics for r in runs.values()),
            "rc=%d %s" % (rc, err.strip()[:100]))
    cat = [json.loads(l) for l in _read(_p(snap, "derived", "run-catalogue.jsonl")).splitlines() if l.strip()]
    by = {}
    for row in cat:
        c = row.get("cid") or row.get("run_id")
        by[c] = by.get(c, 0) + 1
    once = all(by.get(r["cid"]) == 1 for r in runs.values())
    R.check("run catalogue: each named run exactly once", once, "rows=%d" % len(cat))

    # EP-2 replay: N2 BREACH by the floor, N3 the halt run; the same evaluator sha256 as EP-1
    ep2 = {}
    for name, mode in (("N2", "observe"), ("N3", "enforce")):
        run = runs[name]
        outp = _p(R.work, "ep2", run["cid"] + ".jsonl")
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        rc, out, err, _ = R.cli(["postrun", "--cid", run["cid"], "--spans", _p(R.work, "spans", run["cid"] + ".json"),
                                 "--pin", _p(R.work, "pins", "v1-%s.json" % mode),
                                 "--pin-sha256", R.state["pins"][mode]["env"]["IFABRIC_PIN_SHA256"], "--out", outp])
        recs = [json.loads(l) for l in _read(outp).splitlines() if l.strip()] if rc == 0 else []
        ep2[name] = recs
        deny = [r for r in recs if r.get("verdict") == "DENY"]
        ep1 = [r for r in R.state["ledger_rows"] if r.get("run.id") == run["cid"] and r.get("ep.id") == "EP-1"
               and r.get("record_kind") == "decision"]
        same_sha = {r.get("evaluator.sha256") for r in recs} == {r.get("evaluator.sha256") for r in ep1}
        want_deny = name == "N2"
        R.check("postrun %s: EP-2 replay (%d decisions, deny=%d)" % (name, len(recs), len(deny)),
                rc == 0 and bool(recs) and (bool(deny) == want_deny), "rc=%d %s" % (rc, err.strip()[:80]))
        R.check("postrun %s: EP-2 evaluator.sha256 == EP-1's" % name, rc == 0 and same_sha,
                "EP-2 %s vs EP-1 %s" % (sorted({str(r.get("evaluator.sha256"))[:12] for r in recs}),
                                         sorted({str(r.get("evaluator.sha256"))[:12] for r in ep1})), xfail="D8")
        if recs:
            _write(_p(snap, "raw", "ledger", run["cid"] + ".ep2.jsonl"), _jsonl(recs))
    R.state["ep2"] = ep2
    rc, out, err, _ = R.cli(args)
    R.check("refresh again with the EP-2 records", rc == 0, err.strip()[:100])
    R.state["snap"] = snap
    return True


def _walk(root):
    for d, _, names in os.walk(root):
        for n in names:
            yield os.path.join(d, n)


def _metric_cids(snap):
    path = _p(snap, "store", "records.jsonl")
    if not os.path.isfile(path):
        return set()
    out = set()
    for line in _read(path).splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("record_kind") == "metric":
                out.add(r.get("run.id"))
    return out


# ------------------------------------------------------------------ 4. assess (D1 stand-in glue) + query on the snapshot
def _store(snap):
    return [json.loads(l) for l in _read(_p(snap, "store", "records.jsonl")).splitlines() if l.strip()]


def c7_pin(R, faithful):
    from prooflab.registry import parse as P
    doc = P.parse_register(R.state["v1_bytes"].decode("utf-8"))
    e = [x for x in doc["entries"] if x.get("control_ref") == "C7"][0]
    reg_sha = hashlib.sha256(R.state["v1_bytes"]).hexdigest()
    gap = next(i for i in R.state["derive"] if i["control_ref"] == "C7")["value"]
    return {"control_id": e["library_id"], "coverage_min_pct": 100, "gap_max_ms": gap,
            "violating_gap_share_max_pct": 0, "exception_tolerance": int(e["exception_tolerance"]),
            "ep1_deployed": faithful, "register_sha256": reg_sha, "register_version": "v1",
            "threshold_version": e["threshold_version"],
            "workflow_events_after_stop": [x.strip() for x in e["workflow_events_after_stop"].split(",")]}, e


def assess_glue(R, snap):
    """STAND-IN for D1: the merged evaluators called directly; Assessment documents written to assessments/<C>/."""
    from prooflab.evaluators import c16, c7, claim
    store = _store(snap)
    out = {}
    for name, run in R.state["runs"].items():
        cid, plan = run["cid"], run["plan"]
        pin = R.state["pins"][plan["mode"]]["pin"]
        calls = [{"action_id": s["attributes"]["modaas.action_id"], "listener": s["attributes"]["listener"],
                  "model": s["attributes"].get("gen_ai.request.model"),
                  "tokens_in": int(s["attributes"].get("gen_ai.usage.input_tokens", 0)),
                  "tokens_out": int(s["attributes"].get("gen_ai.usage.output_tokens", 0)),
                  "http_status": int(s["attributes"]["http.status"]),
                  "start": _iso(int(s["startTimeUnixNano"]) / 1e9), "end": _iso(int(s["endTimeUnixNano"]) / 1e9)}
                 for s in run["spans"]]
        decisions = [r for r in store if r.get("run.id") == cid and r.get("record_kind") == "decision"]
        sa = {"attrs": {}, "tier_rule": "", "envelope_tier": "default", "provenance": run["provenance"], "condition": "none"}
        comp = {"expected_action_ids": [c["action_id"] for c in calls if c["listener"] == "llm"], "spans_ingested": True}
        a16 = c16.assess_run(cid, calls, sa, decisions, pin, comp, _iso(time.time()))
        pin7, _ = c7_pin(R, faithful=False)
        exp = c7.expected_events(cid, run["actions"], [], run["workflow"], run["stops"], pin7)
        obs = [r for r in store if r.get("run.id") == cid]
        a7 = c7.assess_run(cid, exp, obs, [], pin7, _iso(time.time()))
        for a in (a16, a7):
            d = claim.as_dict(a)
            _write(_p(snap, "assessments", d["control_ref"], cid + ".json"), json.dumps(d, indent=1, sort_keys=True))
        out[name] = {"C16": a16.requirement_verdict, "C7": a7.requirement_verdict}
        # the register-faithful C7 expectation (all workflow_events + ep1_deployed) for the D5/D6 rows: the
        # register's names placed by the production mapping (prooflab/query/workflow_map.py, what
        # `assess --snapshot` uses): run.*/handoff.* on the orchestrator, the rest per agent invocation
        if name == "N5":
            from prooflab.query import assess_snapshot as ASN
            pin_reg, entry = c7_pin(R, faithful=False)
            wf = ASN.workflow_events(entry, None, obs)
            af = c7.assess_run(cid, c7.expected_events(cid, run["actions"], [], wf, [], pin_reg), obs, [], pin_reg,
                               _iso(time.time()))
            out["N5-register-events"] = (af.requirement_verdict, [x.get("key") for x in af.exceptions][:4], len(wf))
            pin_ep1, _ = c7_pin(R, faithful=True)
            ae = c7.assess_run(cid, c7.expected_events(cid, run["actions"], [], run["workflow"], [], pin_ep1), obs, [],
                               pin_ep1, _iso(time.time()))
            out["N5-ep1-decisions"] = (ae.requirement_verdict, [x.get("key") for x in ae.exceptions][:4])
    return out


def step_assess(R):
    snap, runs = R.state["snap"], R.state["runs"]
    gap = next(i for i in R.state["derive"] if i["control_ref"] == "C7")["value"]
    rc, out, err, _ = R.cli(["assess", "--snapshot", snap, "--register", R.state["v1"],
                             "--limit", "C7:coverage_min_pct=100", "--limit", "C7:gap_max_ms=%s" % gap,
                             "--limit", "C7:violating_gap_share_max_pct=0"])
    real = {}
    for ctl in ("C16", "C7"):
        for name, run in runs.items():
            fp = _p(snap, "assessments", ctl, run["cid"] + ".json")
            if os.path.isfile(fp):
                real[(name, ctl)] = json.loads(_read(fp))["requirement_verdict"]
    R.check("`prooflab assess --snapshot` writes assessments/<C>/<cid>.json for every named run",
            len(real) == 2 * len(runs), "rc=%d files=%d %s" % (rc, len(real), (err.strip())[:80]))
    c9v = {}
    for name, run in runs.items():                 # PR-41: C9 is assessed too; v1 has no frozen baseline (C9-v1)
        fp = _p(snap, "assessments", "C9", run["cid"] + ".json")
        c9v[name] = json.loads(_read(fp))["requirement_verdict"] if os.path.isfile(fp) else None
    R.check("assess --snapshot C9 under v1: every named run NOT_ASSESSED (no frozen baseline), never a pass",
            all(v == V.NOT_ASSESSED for v in c9v.values()), str(sorted(c9v.items())))
    try:
        got = assess_glue(R, snap)
    except Exception as exc:  # noqa: BLE001
        R.row("assess stand-in glue (evaluators direct)", FAIL, "%s: %s" % (type(exc).__name__, exc))
        return False
    want = {"N1": (V.SATISFIED, V.SATISFIED), "N2": (V.BREACHED, V.SATISFIED), "N3": (V.SATISFIED, None),
            "N4": (None, V.BREACHED), "N5": (None, V.SATISFIED)}
    for name, (w16, w7) in sorted(want.items()):
        g = got[name]
        ok = (w16 is None or g["C16"] == w16) and (w7 is None or g["C7"] == w7)
        R.check("assess %s: C16 %s, C7 %s" % (name, g["C16"], g["C7"]), ok,
                "want C16=%s C7=%s (C7 by the evaluators called directly until D5 lands)%s" % (
                    w16 or "any", w7 or "any",
                    "; fault simulated by the rehearsal driver (D12)" if RUN_PLANS[name].get("fault") else ""))
    R.check("assess --snapshot C16 verdicts == the evaluators called directly (stand-in glue)",
            all(real.get((n, "C16")) == got[n]["C16"] for n in runs),
            "real %s vs glue %s" % (sorted((n, real.get((n, "C16"))) for n in runs),
                                    sorted((n, got[n]["C16"]) for n in runs)))
    R.check("C7 N3 (stopped agent) with workflow_events_after_stop", got["N3"]["C7"] == V.SATISFIED,
            "verdict %s (decision, stop, judgment from the stopped agent)" % got["N3"]["C7"])
    v, ex, n_wf = got["N5-register-events"]
    R.check("C7 N5 with the register's own workflow_events", v == V.SATISFIED and n_wf > 0,
            "verdict %s missing %s; %d workflow events placed by prooflab/query/workflow_map.py (run.*/handoff.* on"
            " the orchestrator, the rest per invocation; this driver has no Gateway C, so no negotiation)"
            % (v, ex, n_wf))
    v, ex = got["N5-ep1-decisions"]
    R.check("C7 N5 expecting one EP-1 decision per model call", v == V.SATISFIED, "verdict %s missing %s" % (v, ex),
            xfail="D6")
    rc, out, err, _ = R.cli(["assess", "--pack", snap, "--out", _p(R.work, "assess-out")])
    R.check("`prooflab assess` over the stored assessments", rc == V.exit_code(V.BREACHED), "rc=%d" % rc)
    R.state["assessed"] = got
    return True


# ------------------------------------------------------------------ 5. findings + FAKE ServiceNow notify
def step_notify(R):
    from prooflab.adapters import human_loop as hl
    from prooflab.registry import parse as P
    from prooflab.tests.fake_servicenow import CLIENT_ID, CLIENT_SECRET, INTEGRATION_USER, OWNER_USER, FakeServiceNow
    snap, runs = R.state["snap"], R.state["runs"]
    fdir = _p(snap, "findings")
    rc, out, err, _ = R.cli(["humanloop", "findings", "--snapshot", snap, "--register", R.state["v1"]],
                            env_extra={"SNOW_OWNER_USER": OWNER_USER})
    made = sorted(os.listdir(fdir)) if os.path.isdir(fdir) else []
    want = sorted("%s-%s.json" % (c, runs[n]["cid"]) for n, c in (("N2", "C16"), ("N4", "C7")))
    R.check("`humanloop findings` builds Finding files from the BREACHED assessments", rc == 0 and set(want) <= set(made),
            "rc=%d %s %s" % (rc, made, err.strip()[:80]))
    srv = FakeServiceNow().start()
    try:
        log = _p(snap, "servicenow", "delivery-log.jsonl")
        os.makedirs(os.path.dirname(log), exist_ok=True)
        env = {"SNOW_INSTANCE": srv.base_url, "SNOW_CLIENT_ID": CLIENT_ID, "SNOW_CLIENT_SECRET": CLIENT_SECRET,
               "SNOW_OWNER_USER": OWNER_USER, "SNOW_INTEGRATION_USER": INTEGRATION_USER,
               "PROOFLAB_DELIVERY_LOG": log, "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}
        rc, out, err, _ = R.cli(["humanloop", "notify"] + [a for f in want for a in ("--finding", _p(fdir, f))], env_extra=env)
        rows = json.loads(out) if rc == 0 and out.strip().startswith("[") else []
        ok = rc == 0 and len(rows) == 2 and all(r.get("state") == "DELIVERED" for r in rows)
        R.check("humanloop notify -> FAKE ServiceNow: 2 DELIVERED", ok, "rc=%d %s" % (rc, (err.strip() or out.strip())[:100]))
        rc2, out2, _, _ = R.cli(["humanloop", "notify"] + [a for f in want for a in ("--finding", _p(fdir, f))], env_extra=env)
        rows2 = json.loads(out2) if rc2 == 0 and out2.strip().startswith("[") else []
        R.check("notify re-run sends nothing new", rc2 == 0 and all(r.get("action") == "skipped" for r in rows2),
                "rc=%d" % rc2)
    finally:
        srv.stop()
    return True


# ------------------------------------------------------------------ 6. pack: redaction, scan, MANIFEST, deliverables
def _fake_token(seed):
    return hashlib.sha256(("rehearsal-" + seed).encode()).hexdigest()[:32]


def step_pack(R):
    snap, w = R.state["snap"], R.work
    toks = [_fake_token("env"), _fake_token("last-applied"), _fake_token("kopf")]
    cr = {"items": [{"kind": "AgentConfig", "metadata": {"name": "ifabric-it", "annotations": {
        "kubectl.kubernetes.io/last-applied-configuration": json.dumps({"spec": {"t": toks[1]}}),
        "kopf.zalando.org/last-handled-configuration": json.dumps({"spec": {"t": toks[2]}})}},
        "spec": {"awsAgentCore": {"environmentVariables": {"AUDIT_WRITE_TOKEN": toks[0], "MODEL_ALIAS": "x"}}},
        "status": {"phase": "Ready"}}]}
    _write(_p(snap, "raw", "cr-status", "cr-status.json"), json.dumps(cr, indent=1))
    _write(_p(snap, "window.json"), json.dumps({"start": _iso(R.state["t1"]), "end": _iso(time.time()),
                                                "note": "SYNTHETIC rehearsal window"}))
    reg_dst = _p(snap, "register")
    if os.path.isdir(reg_dst):
        shutil.rmtree(reg_dst)
    shutil.copytree(_p(w, "register"), reg_dst)
    wd = _p(w, "workdir")
    shutil.copyfile(R.state["v1"], _p(wd, "register.yaml"))
    shutil.copyfile(_p(REPO, "gap-list.md"), _p(wd, "gap-list.md"))
    rc, out, err, _ = R.cli(["registry", "run-ids", "--run-ids", _p(wd, "run-ids.txt"),
                             "--experiments", _p(w, "register", "experiments", "experiments.jsonl")])
    R.check("registry run-ids: one CID per line, no pilot id", rc == 0, (out + err).strip()[:120])
    pack = _p(w, "out", "evidence")
    env = {"PROOFLAB_SCAN_VALUES": "\n".join(toks)}
    rc, out, err, _ = R.cli(["pack", "build", "--out", pack, "--src", snap, "--workdir", wd], env_extra=env)
    R.check("pack build (redact + exact-value scan + MANIFEST)", rc == 0 and os.path.isfile(_p(pack, "MANIFEST.json")),
            (out + err).strip().replace("\n", " | ")[:160])
    hits = [p for p in _walk(pack) if any(t.encode() in _read(p, "rb") for t in toks)]
    R.check("planted tokens in the 3 ARCH 9.3 paths: 0 hits in the pack", rc == 0 and not hits, "hits=%s" % hits[:3])
    rc, out, err, _ = R.cli(["pack", "scan", pack], env_extra=env)
    R.check("pack scan: 0 hits", rc == 0, out.strip()[:80])
    p = subprocess.run([R.py, _p(REPO, "tools", "manifest.py"), "verify", pack], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    R.check("tools/manifest.py verify", p.returncode == 0, p.stdout.decode()[:100].strip())
    R.check("findings/ staged in the pack", os.path.isdir(_p(pack, "findings")), "staged from the snapshot")
    R.state["pack"] = pack
    return True


def _console_row(R, ev, runs):
    """AT-P0 on the fresh unzip: the console starts from the pack alone and serves a stored, composed answer."""
    import socket
    import urllib.error
    import urllib.request
    sk = socket.socket()
    sk.bind(("127.0.0.1", 0))
    port = sk.getsockname()[1]
    sk.close()
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/"), "PYTHONDONTWRITEBYTECODE": "1"}   # the console refuses a shell with secrets
    proc = subprocess.Popen([R.py, "-m", "prooflab", "console", "--data", "pack", "--pack", ev, "--port", str(port)],
                            cwd=ev, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    detail, ok = "", False
    try:
        banner, url = proc.stdout.readline().strip(), proc.stdout.readline().strip()
        if "#k=" not in url:
            raise RuntimeError("no one-time URL: %s" % (banner or url))
        tok = url.split("#k=")[-1]
        base = "http://127.0.0.1:%d" % port
        req = urllib.request.Request(base + "/api/v1/session", data=json.dumps({"token": tok}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        for _ in range(50):             # the banner prints just before the socket listens
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    cookie = r.headers.get("Set-Cookie", "").split(";")[0]
                break
            except urllib.error.HTTPError:
                raise
            except urllib.error.URLError:
                time.sleep(0.1)
        q = urllib.request.Request(base + "/api/v1/ask?q=control%2016%20for%20run%20" + runs["N2"]["cid"], headers={"Cookie": cookie})
        with urllib.request.urlopen(q, timeout=10) as r:
            ans = json.loads(r.read().decode())["data"]
        m = ans["measurement"]
        ok = ans["verdict"]["value"] == V.BREACHED and m["value"] is not None and ans["comparison"]["limit"] is not None
        detail = "%s; %s measured %s vs %s" % (banner[:40], ans["verdict"]["value"], m["value"], ans["comparison"]["limit"])
    except Exception as exc:        # a console that cannot start on the pack is the finding
        detail = "%s: %s" % (type(exc).__name__, str(exc)[:80])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    R.check("console starts on the fresh unzip and answers C16 N2 from the pack", ok, detail)


def step_query(R):
    pack, runs, w = R.state["pack"], R.state["runs"], R.work
    zpath = _p(w, "out", "submission.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in _walk(pack):
            z.write(f, os.path.join("evidence", os.path.relpath(f, pack)))
        for name in ("register.yaml", "gap-list.md", "run-ids.txt", "sketch.png"):
            src = _p(w, "workdir", name)
            if name == "sketch.png" and not os.path.isfile(src):
                src = _p(pack, name)          # pack build stages the checked-in render (evidence-templates/sketch.png)
            if os.path.isfile(src):
                z.write(src, name)
    fresh = _p(w, "fresh")
    with zipfile.ZipFile(zpath) as z:
        z.extractall(fresh)
    ev = _p(fresh, "evidence")
    p = subprocess.run([R.py, _p(REPO, "tools", "manifest.py"), "verify", ev], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    R.check("manifest verify on the fresh unzip", p.returncode == 0, p.stdout.decode()[:80].strip())
    _console_row(R, ev, runs)
    cases = [("C16 run N2 (BREACHED)", ["--control", "C16", "--run", runs["N2"]["cid"]], V.exit_code(V.BREACHED)),
             ("C16 run N1 (SATISFIED)", ["--control", "C16", "--run", runs["N1"]["cid"]], V.exit_code(V.SATISFIED)),
             ("C16 run N3 (SATISFIED, halt)", ["--control", "C16", "--run", runs["N3"]["cid"]], V.exit_code(V.SATISFIED)),
             ("C7 run N4 (BREACHED)", ["--control", "C7", "--run", runs["N4"]["cid"]], V.exit_code(V.BREACHED)),
             ("C7 run N5 (SATISFIED)", ["--control", "C7", "--run", runs["N5"]["cid"]], V.exit_code(V.SATISFIED)),
             ("C9 run N1 -> not assessed (2)", ["--control", "C9", "--run", runs["N1"]["cid"]], 2),
             ("unknown CID -> 2", ["--control", "C16", "--run", IDS.mint_cid("ifabric-run", 1790000000)], 2),
             ("incident N2 (six questions)", ["--incident", runs["N2"]["cid"]], 0)]
    for label, args, want in cases:
        rc, out, err, dt = R.cli(["query"] + args, cwd=ev)
        ok = rc == want and dt < QUERY_BUDGET_S
        if "N2 (BREACHED)" in label:
            ok = ok and "T1 proof" in out and "unknown" not in out.split("T1 proof", 1)[1].split("\n", 1)[0]
        sim = "; fault simulated by the rehearsal driver (D12)" if "N4" in label else ""
        R.check("query %s from the fresh unzip" % label, ok, "rc=%d in %.1fs %s%s" % (rc, dt, err.strip()[:60], sim))
    late = _p(w, "late-t1")             # a copy whose T1 is AFTER the runs: the date check must not pass
    shutil.copytree(ev, late)
    hp = _p(late, "register", "versions", "v1.head.json")
    h = json.loads(_read(hp))
    h["LastModified"] = _iso(time.time() + 3600)
    _write(hp, json.dumps(h))
    rc, out, err, dt = R.cli(["query", "--control", "C16", "--run", runs["N2"]["cid"]], cwd=late)
    R.check("date check: a T1 later than the run is not a clean answer", rc == 2 or not any(l.strip() == "gaps: none" for l in out.splitlines()), "rc=%d %s" % (rc, [l for l in out.splitlines() if l.startswith("gaps:")]))
    R.check("kit-crosscheck/<CID>/gateway-log.json produced", os.path.isdir(_p(ev, "kit-crosscheck")),
            "written by refresh from the gateway records")
    rc, out, err, dt = R.cli(["query", "--claim"], cwd=ev)
    R.check("query --claim", rc == 0 and "partial" in out.lower(), out.strip().splitlines()[0][:100] if out.strip() else err[:80])
    win = "%s..%s" % (_iso(R.state["t1"]), _iso(time.time() + 60))
    rc, out, err, dt = R.cli(["query", "--control", "C16", "--window", win], cwd=ev)
    R.check("query --control C16 --window (Phase 1 window)", rc in (0, 1) and dt < QUERY_BUDGET_S, "rc=%d in %.1fs" % (rc, dt))

    # the six deliverables (R-J-44) on the downloaded zip
    top = set(os.listdir(fresh))
    R.check("deliverable: evidence pack with prooflab/ inside", os.path.isdir(_p(ev, "prooflab")), "")
    same = os.path.isfile(_p(fresh, "register.yaml")) and _read(_p(fresh, "register.yaml"), "rb") == R.state["v1_bytes"]
    R.check("deliverable: register.yaml == register/versions/v1.yaml", same, "")
    R.check("deliverable: risks.yaml frozen with v1 in the pack", os.path.isfile(_p(ev, "register", "versions", "v1.risks.yaml")), "")
    R.check("deliverable: inventory frozen in the pack", os.path.isfile(_p(ev, "register", "versions", "inv-1.yaml")), "")
    rc, out, err, dt = R.cli(["query", "--inventory"], cwd=ev)
    R.check("query --inventory finds the frozen inv-1", rc == 0 and "inv-1" in out, out.strip()[:80])
    lines = _read(_p(fresh, "run-ids.txt")).splitlines() if "run-ids.txt" in top else []
    pil = set(R.state["pilots"].values())
    R.check("deliverable: run-ids.txt one CID per line, no pilot", bool(lines) and all(IDS.is_valid_run_id(l) for l in lines)
            and not (set(lines) & pil), "%d lines" % len(lines))
    R.check("deliverable: control test tool (query runs from the zip)", True, "see the query rows")
    R.check("deliverable: gap-list.md", "gap-list.md" in top, "")
    R.check("deliverable: sketch.png", "sketch.png" in top, "the checked-in render of architecture/one-page.svg (evidence-templates/sketch.png)")
    return True


def _listdir(path):
    return sorted(os.listdir(path)) if os.path.isdir(path) else []


# ------------------------------------------------------------------ main
STEPS = (("registry", step_registry), ("runs", step_runs), ("snapshot", step_snapshot), ("assess", step_assess),
         ("notify", step_notify), ("pack", step_pack), ("query", step_query))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rehearse_phase1")
    ap.add_argument("--python", default=None, help="interpreter for `-m prooflab` (default /usr/bin/python3)")
    ap.add_argument("--keep", action="store_true", help="keep the temp WORKDIR")
    ap.add_argument("--json", help="write the result rows as JSON here")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    py = a.python or ("/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable)
    work = tempfile.mkdtemp(prefix="prooflab-rehearsal-")
    R = Rehearsal(py, work, a.verbose)
    t0 = time.time()
    for name, fn in STEPS:
        try:
            ok = fn(R)
        except Exception as exc:  # noqa: BLE001 - one broken stage is a FAIL row, the table still prints
            import traceback
            R.row("stage %s crashed" % name, FAIL, "%s: %s" % (type(exc).__name__, str(exc)[:140]))
            if a.verbose:
                traceback.print_exc()
            ok = False
        if not ok:
            for later, _ in STEPS[[s for s, _ in STEPS].index(name) + 1:]:
                R.row("stage %s" % later, SKIP, "blocked by stage %s" % name)
            break
    print(R.table())
    print("elapsed %.1fs; WORKDIR %s%s" % (time.time() - t0, work, " (kept)" if a.keep else " (removed)"))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"rows": R.rows, "defects": DEFECTS, "work": work}, fh, indent=1, sort_keys=True)
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 1 if any(r["status"] == FAIL for r in R.rows) else 0


if __name__ == "__main__":
    sys.exit(main())
