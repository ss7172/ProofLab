"""`prooflab run`: the orchestrating script (EP-5), ARCH 7.2. Stdlib, Python 3.9.

customer -> IT -> network, in sequence, then Gateway C (network -> IT: the IT agent evaluates the network's
proposal), ONE invocation per handoff (a timeout is recorded TIMEOUT, never re-invoked). The three handoffs are
record-only; each record carries its C7 workflow phase (run.started, handoff.sent, handoff.received, run.finished). Preflight = budget guard + EP-0 + pin echo + credentials.
Not here: --tamper-tally (PR-08b). Tested offline: every live call goes through the `runner` seam.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from prooflab.adapters.orchestrator import common, conditions, invoke, ledger, preflight, records
from prooflab.contract import ids

GATEWAY_C = "gateway-c"
GATEWAY_C_FROM, GATEWAY_C_TO = "ifabric-network", "ifabric-it"
EXIT_REFUSED = 4
EXIT_INCOMPLETE = 5
SCENARIO_FILE_DIR = ("register", "scenarios")
BUILTIN_PROMPTS = {   # synthetic placeholders until the registry PR freezes the scenario datasets
    "S1": "Customer reports slow service at site SITE-DEN-12. Analyse and recommend next steps.",
    "S2": "Customer reports repeated outages across several sites. Investigate each and summarise.",
    "S3": "Customer asks for the status of circuit CKT-0001 and the open ticket.",
}


def build_parser():
    p = argparse.ArgumentParser(prog="prooflab run", description="drive one run of the ifabric- trio (EP-5)")
    p.add_argument("--scenario", required=True, choices=sorted(BUILTIN_PROMPTS))
    p.add_argument("--only", choices=common.load_budget()["agents"] + [GATEWAY_C],
                   help="invoke just this agent, or `gateway-c`: the IT agent alone on --proposal-file")
    p.add_argument("--proposal-file", default=None, help="--only gateway-c: JSON proposal to negotiate")
    p.add_argument("--condition", default="none", help="none | " + " | ".join(conditions.CONDITIONS))
    p.add_argument("--fault", default=None, help="inject-tool-output:<agent>:<tool>:<fixture> | suppress-record:<agent>:<event>:<n>")
    p.add_argument("--dry-run", action="store_true", help="print the envelope and plan; no call of any kind")
    p.add_argument("--mode", choices=("observe", "enforce"), default="observe", help="the pin mode this run expects")
    p.add_argument("--family", choices=("run", "test", "adv"), default=None)
    p.add_argument("--provenance", default=None)
    p.add_argument("--bound", type=int, default=None, help="override this run's token bound (e.g. the pilots' CAP)")
    p.add_argument("--tier", default=None)
    p.add_argument("--run-dir", default="ifabric-runs", help="spool + run-index.jsonl")
    p.add_argument("--runtimes-file", default=None, help='JSON {"ifabric-customer": "<runtime ARN>", ...}')
    p.add_argument("--versions-file", default=None, help="EP-0 input: filtered reads {running, approved, policy}")
    p.add_argument("--pin-file", default=None, help="JSON {register_version, register_sha256, pin_sha256}")
    p.add_argument("--echoed-pins", default=None, help='JSON {"ifabric-customer": "<sha256>"}')
    p.add_argument("--tokens-last-hour", type=int, default=None, help="manual headroom reading (else Logs Insights)")
    p.add_argument("--creds-expiry", default=None, help="UTC ISO, else read from the AWS CLI")
    p.add_argument("--scenario-file", default=None)
    p.add_argument("--ledger-url", default=None, help="service-proxy base URL of audit-store (S-1 spike path)")
    p.add_argument("--ledger-secret", default=None, help="namespace/secret/key holding the write token")
    return p


def _json_file(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _provenance(args, family, has_condition):
    if args.provenance:
        return args.provenance
    if has_condition or family == "adv":
        return "FAULT_INJECTION"
    return "AUTHORIZED_TEST" if family == "test" else "LIVE_SUBJECT"


def _scenario(args):
    doc = _json_file(args.scenario_file) if args.scenario_file else None
    if doc is None:
        path = os.path.join(common.REPO_ROOT, *SCENARIO_FILE_DIR, args.scenario + ".json")
        doc = _json_file(path) if os.path.exists(path) else None
    if doc:
        return doc.get("prompt", ""), doc.get("tier"), "register/scenarios"
    return BUILTIN_PROMPTS[args.scenario], None, "builtin-placeholder"


def plan_agents(args, budget):
    """The distinct agents this run invokes (EP-0 and the pin echo check each once)."""
    if args.only == GATEWAY_C:
        return [GATEWAY_C_TO]
    return [args.only] if args.only else list(budget["agents"])


def plan_steps(args, budget, cid):
    """The invocations in order: the trio, then Gateway C (h3, network -> IT) on a full run."""
    if args.only == GATEWAY_C:
        return [{"agent": GATEWAY_C_TO, "handoff_id": ids.handoff_id(cid, 1), "kind": "negotiate",
                 "from": GATEWAY_C_FROM, "session_id": ids.mint_session_id(cid)}]
    agents = plan_agents(args, budget)
    steps = [{"agent": a, "handoff_id": ids.handoff_id(cid, n) if n >= 1 else None, "kind": "invoke",
              "session_id": ids.mint_session_id(cid)} for n, a in enumerate(agents)]
    if not args.only:
        steps.append({"agent": GATEWAY_C_TO, "handoff_id": ids.handoff_id(cid, len(agents)), "kind": "negotiate",
                      "from": GATEWAY_C_FROM, "session_id": ids.mint_session_id(cid)})
    return steps


def negotiate_payload(cid, hid, traceparent, proposal, env):
    """Gateway C's body: the reference's {"negotiate": {...}} shape plus our envelope (ARCH 7.2)."""
    return {"negotiate": {"correlation_id": cid, "proposal": proposal, "traceparent": traceparent,
                          "handoff_id": hid}, "ifabric": env}


def build_envelope(cid, hid, frm, to, args, pin, cond, fault, tier, provenance, tally):
    env = {"envelope": "ifabric.run/1", "run_id": cid, "handoff_id": hid, "from": frm, "to": to, "tier": tier,
           "tally_tokens": tally[0], "tally_calls": tally[1],
           "register_version": pin.get("register_version"), "register_sha256": pin.get("register_sha256"),
           "pin_sha256": pin.get("pin_sha256"), "mode": args.mode, "provenance": provenance,
           "condition": cond["name"], "condition_sha256": cond["sha256"], "scenario": args.scenario}
    if fault and fault["agent"] == to:
        env["fault"] = fault
    return env


def _emit(rec, spool_path, sink):
    common.append_jsonl(spool_path, rec)
    if sink is not None:
        try:
            sink.post([rec])
        except Exception as exc:  # noqa: BLE001 - the spool is the record; a POST failure never stops a run
            print("ledger post failed (%s); spooled only" % type(exc).__name__, file=sys.stderr)


def main(argv=None, runner=subprocess.run, now=None, out=None, sleep=None) -> int:
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    budget = common.load_budget()
    when = now or common.parse_utc(common.utc_now())
    agents = plan_agents(args, budget)
    cond = conditions.load_condition(args.condition)
    fault = conditions.parse_fault(args.fault)
    if fault and fault["agent"] not in agents:
        print("fault names %s, which this run does not invoke" % fault["agent"], file=sys.stderr)
        return 2
    family = args.family or ("adv" if cond["name"] in conditions.CONDITIONS[:3] else "run")
    provenance = _provenance(args, family, bool(cond["sha256"] or fault))
    prompt, scen_tier, scen_source = _scenario(args)
    tier = args.tier or scen_tier
    pin = _json_file(args.pin_file) or {}
    if args.only == GATEWAY_C and not args.proposal_file and not args.dry_run:
        print("--only gateway-c needs --proposal-file", file=sys.stderr)
        return 2
    bound, bound_class = preflight.bound_for(budget, args.scenario, args.mode, args.only,
                                             adversarial=family == "adv", override=args.bound,
                                             gateway_c=not args.only)
    epoch = int((when - common.parse_utc("1970-01-01T00:00:00")).total_seconds())
    cid = ids.mint_cid("ifabric-" + family, epoch)
    traceparent = ids.mint_traceparent()
    baggage = ids.cid_baggage(cid)
    full_prompt = prompt + (("\n\n" + cond["text"]) if cond["text"] else "")

    plan = plan_steps(args, budget, cid)

    if args.dry_run:
        env0 = build_envelope(cid, plan[0]["handoff_id"], "orchestrator", agents[0], args, pin, cond, fault,
                              tier, provenance, (0, 0))
        doc = {"dry_run": True, "cid": cid, "envelope": env0, "plan": plan, "bound_tokens": bound,
               "bound_class": bound_class, "baggage": baggage, "traceparent": traceparent,
               "condition": {"name": cond["name"], "sha256": cond["sha256"], "path": cond["path"]},
               "fault": fault, "scenario_source": scen_source,
               "invoke": {"AWS_MAX_ATTEMPTS": budget["invoke"]["aws_max_attempts"],
                          "AWS_RETRY_MODE": budget["invoke"]["aws_retry_mode"],
                          "cli_read_timeout": budget["invoke"]["cli_read_timeout"]},
               "preflight": "skipped (dry-run): no AWS, cluster or ledger call was made"}
        print(json.dumps(doc, indent=2, sort_keys=True), file=out)
        return 0

    run_dir = args.run_dir
    index_path = os.path.join(run_dir, "run-index.jsonl")
    spool = os.path.join(run_dir, "spool", cid + ".jsonl")
    index_entries = common.read_jsonl(index_path)
    versions = _json_file(args.versions_file)
    exp = common.parse_utc(args.creds_expiry) if args.creds_expiry else preflight.credential_expiry(runner)
    tokens = args.tokens_last_hour if args.tokens_last_hour is not None else preflight.tokens_in_window(
        runner, when, budget, **({"sleep": sleep} if sleep else {}))
    ep0_steps, _ = preflight.ep0(
        versions, provenance == "LIVE_SUBJECT", agents,
        meta={"register_version": pin.get("register_version"), "pin_sha256": pin.get("pin_sha256")})
    base = {"cid": cid, "scenario": args.scenario, "mode": args.mode, "only": args.only, "condition": cond["name"],
            "condition_sha256": cond["sha256"], "fault": args.fault, "provenance": provenance,
            "register_version": pin.get("register_version"), "register_sha256": pin.get("register_sha256"),
            "agent_versions": (versions or {}).get("running"), "bound_tokens": bound,
            "started_at": when.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
    try:
        steps = preflight.run_preflight(
            budget, when, bound=bound, observe_s2_run=preflight.is_observe_s2(args.scenario, args.mode, args.only),
            index_entries=index_entries, tokens=tokens, expiry=exp,
            identity_step=preflight.check_identity(runner, budget), ep0_steps=ep0_steps,
            pin_steps=preflight.pin_echo(pin.get("pin_sha256"), _json_file(args.echoed_pins) or {}, agents))
    except preflight.PreflightRefused as refused:
        common.append_jsonl(index_path, dict(base, event="run.refused", status="REFUSED",
                                             reasons=[s for s in refused.steps if not s["ok"]]))
        print("preflight REFUSED: %s" % refused, file=sys.stderr)
        return EXIT_REFUSED
    for s in steps:
        print("preflight %-22s ok  %s" % (s["name"], s["detail"]), file=sys.stderr)

    sink = None
    if args.ledger_url and args.ledger_secret:
        ns, name, key = args.ledger_secret.split("/")
        sink = ledger.LedgerSink(args.ledger_url, ledger.read_token(ns, name, key, runner))
    arns = _json_file(args.runtimes_file) or {}
    common.append_jsonl(index_path, dict(base, event="run.started", status="STARTED"))
    mk = lambda kind, detail, **kw: records.make(kind, cid, detail, "not applicable: " + kind,
                                                 provenance=provenance, **dict({"trace.id": traceparent.split("-")[1],
                                                 "run.condition": cond["name"]}, **kw))
    _emit(mk("lifecycle", "run started: scenario %s mode %s" % (args.scenario, args.mode), phase="run.started"),
          spool, sink)

    tally, prev_text, prev_agent, statuses, status = (0, 0), None, "orchestrator", [], "FINISHED"
    proposal = _json_file(args.proposal_file) if args.only == GATEWAY_C else None
    for step_plan in plan:
        agent, hid, session = step_plan["agent"], step_plan["handoff_id"], step_plan["session_id"]
        negotiate = step_plan["kind"] == "negotiate"
        frm = step_plan.get("from", prev_agent)
        # a declared fault goes to its agent's first (trio) invocation only, never also to Gateway C's
        env = build_envelope(cid, hid, frm, agent, args, pin, cond,
                             fault if (not negotiate or args.only == GATEWAY_C) else None, tier, provenance, tally)
        if negotiate:
            payload = negotiate_payload(cid, hid, traceparent, proposal, env)
        else:
            body = full_prompt if prev_text is None else full_prompt + "\n\nOutput of the previous agent:\n" + prev_text
            payload = {"context": {"question": body}, "ifabric": env}
        payload_sha = common.sha256_text(common.canonical(payload))   # the raw payload's sha256 (EP-5)
        prev_agent = frm
        if hid:
            _emit(mk("handoff", "handoff %s sent: %s -> %s%s" % (hid, prev_agent, agent,
                                                                " (Gateway C: negotiation)" if negotiate else ""),
                     phase="handoff.sent",
                     **{"handoff.id": hid, "handoff.from": prev_agent, "handoff.to": agent,
                        "handoff.payload_sha256": payload_sha, "handoff.data_classification": "internal",
                        "ep.id": "EP-5", "ep.kind": "orchestrator (record only)",
                        "ep.responsible": "team iFabric (Sree)", "runtime.session_id": session,
                        "runtime.arn": arns.get(agent)}), spool, sink)
        arn = arns.get(agent)
        if not arn:
            res = {"status": "ERROR", "output": None, "duration_ms": 0, "stderr_tail": "no runtime ARN for %s" % agent}
        else:
            ppath, opath = invoke.write_payload(payload), invoke.out_file()
            try:
                argv_i = invoke.build_argv(arn, session, ppath, opath, baggage, traceparent, budget)
                res = invoke.invoke_once(argv_i, invoke.child_env(os.environ, budget), budget, runner, opath)
            finally:
                for tmp in (ppath, opath):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
        output = res["output"] or {}
        statuses.append({"agent": agent, "status": res["status"]})
        recv = {"ep.id": "EP-5", "ep.kind": "orchestrator (record only)", "ep.responsible": "team iFabric (Sree)",
                "runtime.session_id": session, "runtime.arn": arn}
        if hid:
            recv.update({"handoff.id": hid, "handoff.from": prev_agent, "handoff.to": agent})
        if res["status"] == "TIMEOUT":
            recv["outcome.real"] = "TIMEOUT"
        echoed = (output.get("ifabric") or {}).get("pin_sha256") if isinstance(output, dict) else None
        note = "" if not echoed or not pin.get("pin_sha256") or echoed == pin["pin_sha256"] else " PIN-ECHO-MISMATCH"
        pos = (" position=%s" % output.get("position")) if negotiate else ""
        _emit(mk("handoff", "invocation of %s returned status=%s disposition=%s halted=%s duration_ms=%s%s%s" % (
            agent, res["status"], output.get("disposition"), output.get("halted"), res["duration_ms"], pos, note),
            phase="handoff.received", **recv), spool, sink)
        if res["status"] != "OK":
            status = res["status"]
            break    # never re-invoke; there is no output to forward
        carried = output.get("ifabric") or output
        tally = (int(carried.get("tally_tokens", tally[0]) or 0), int(carried.get("tally_calls", tally[1]) or 0))
        prev_text = (output.get("answer") or output.get("text") or output.get("response")   # our app: `answer`
                     or json.dumps(output, sort_keys=True))
        prev_agent = agent
        if agent == GATEWAY_C_FROM:   # what Gateway C relays: the network's structured proposal (or its answer)
            proposal = output.get("proposal") or {"resolution": str(output.get("answer") or prev_text)[:3000]}
    _emit(mk("lifecycle", "run finished: status %s" % status, phase="run.finished"), spool, sink)
    common.append_jsonl(index_path, dict(base, event="run.finished", status=status, handoffs=statuses,
                                         tally_tokens=tally[0], tally_calls=tally[1], finished_at=common.utc_now()))
    print(json.dumps({"cid": cid, "status": status, "handoffs": statuses, "spool": spool}, sort_keys=True), file=out)
    return 0 if status == "FINISHED" else EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
