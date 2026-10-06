#!/usr/bin/env python3
"""S-0 (in-process): import one bundled ifabric- agent with the real adapters and POST /invocations to it
through Starlette's TestClient, against the stub gateway + stub ledger (stub_gateway.py) on 127.0.0.1.

Proves the wiring the Docker smoke cannot see: start-up passes the real fail-closed checks with a
SYNTHETIC pin (synthetic_pin.json), the model is called through the C16 hook, and decision, action,
rail and judgment records reach the emit client's stdout witness with none rejected.

  <strands 3.12 venv>/bin/python tools/docker_smoke/inprocess_smoke.py --bundle <ifabric-role.py>
  <strands 3.12 venv>/bin/python tools/docker_smoke/inprocess_smoke.py --src-root <dir> --role it

--src-root builds the bundle in memory with NO size gate (a smoke of the wiring, not a release build).
Local only: stub values, never a real key, token or URL. Exit 0 = every check passed.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import stub_gateway  # noqa: E402


def pin_env(path=os.path.join(HERE, "synthetic_pin.json")):
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import make_ifabric_agents as mk  # the wrapper's own env derivation: what the CR will carry
    pin_json, pin_sha, rv, rs = mk.pin_env(open(path, "rb").read())
    return {"IFABRIC_PIN_JSON": pin_json, "IFABRIC_PIN_SHA256": pin_sha,
            "IFABRIC_REGISTER_VERSION": rv, "IFABRIC_REGISTER_SHA256": rs}


def bundle_text(a):
    if a.bundle:
        return open(a.bundle, encoding="utf-8").read(), os.path.basename(a.bundle)[len("ifabric-"):-3]
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import bundle_agent as ba
    report, text = ba.bundle(ba.default_manifest(a.role), a.src_root, REPO, write=False, gate=10 ** 9)
    print(json.dumps({"smoke": "bundle", "gzip_base64_chars": report["gzip_base64_chars"],
                      "gate": ba.GATE_CHARS, "modules": len(report["modules"])}), flush=True)
    return text, a.role


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--bundle")
    p.add_argument("--src-root")
    p.add_argument("--role", default="customer")
    p.add_argument("--port", type=int, default=18191)
    a = p.parse_args(argv)
    text, role = bundle_text(a)
    srv = stub_gateway.serve(a.port, host="127.0.0.1")
    gw = "http://127.0.0.1:%d" % a.port
    os.environ.update({  # stub values only
        "OPENAI_BASE_URL": gw + "/v1", "OPENAI_API_KEY": "stub-key-not-real", "MODEL_ALIAS": "stub-model",
        "AGENT_NAME": "ifabric-" + role, "AUDIT_URL": gw, "AUDIT_WRITE_TOKEN": "stub-ledger-not-real",
        "AGENTCORE_GATEWAY_MCP_TOKEN": "stub-mcp-not-real", "IFABRIC_RAILS_MODE": "enforce"})
    os.environ.pop("AGENTCORE_GATEWAY_MCP_URL", None)
    os.environ.pop("TOOL_MCP_URL", None)
    os.environ.update(pin_env())
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"), "ifabric-inprocess-%s.py" % role)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    out = io.StringIO()
    checks = {}
    try:
        with contextlib.redirect_stdout(out):
            spec = importlib.util.spec_from_file_location("ifabric_smoke_bundle", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            from starlette.testclient import TestClient
            client = TestClient(mod.app)
            ping = client.get("/ping")
            payload = {"ifabric": {"envelope": "ifabric.run/1", "run_id": "ifabric-test-inproc-0001",
                                   "handoff_id": "ifabric-test-inproc-0001:h1", "from": "prooflab",
                                   "to": "ifabric-" + role, "tier": "standard", "tally_tokens": 0,
                                   "tally_calls": 0, "provenance": "LIVE_SUBJECT", "condition": "none"},
                       "context": {"question": "Synthetic smoke: fault at stub site S-0. Who is impacted?"}}
            r1 = client.post("/invocations", json=payload)
            r2 = client.post("/invocations", json=payload)        # same handoff id: the guard refuses
    finally:
        srv.shutdown()
    lines = out.getvalue().splitlines()
    recs = []
    for ln in lines:
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        if isinstance(o, dict):
            recs.append(o)
    kinds = [o.get("record_kind") for o in recs if o.get("schema") == "ifabric.evidence/1"]
    rejected = [o for o in recs if o.get("lifecycle.event") == "record-rejected"]
    body1 = r1.json() if r1.status_code == 200 else {}
    checks["startup-ok"] = any(o.get("event") == "startup-ok" for o in recs)
    checks["no startup-failed"] = not any(o.get("event") == "startup-failed" for o in recs)
    checks["GET /ping 200"] = ping.status_code == 200
    checks["POST /invocations 200"] = r1.status_code == 200
    checks["model called (stub gateway)"] = stub_gateway.STATE["n"] >= 1
    checks["no agent error"] = "error" not in body1
    checks["disposition from J2"] = body1.get("disposition") in ("auto-resolve", "gather-evidence", "escalate")
    checks["decision record (C16)"] = "decision" in kinds
    checks["action record (model call)"] = "action" in kinds
    checks["judgment record"] = "judgment" in kinds
    checks["rail_decision or rails summary"] = "rail_decision" in kinds or any(
        o.get("lifecycle.event") == "rails-summary" for o in recs)
    checks["no record rejected"] = not rejected
    checks["duplicate refused"] = r2.status_code == 200 and r2.json().get("refused") == "duplicate-invocation"
    checks["ledger POSTs reached the stub"] = stub_gateway.STATE["records"] >= 1
    print(json.dumps({"smoke": "inprocess", "role": role, "python": sys.version.split()[0],
                      "record_kinds": sorted(set(k for k in kinds if k)), "records": len(kinds),
                      "rejected": [o.get("reason") for o in rejected][:5],
                      "model_calls": stub_gateway.STATE["n"], "ledger_posts": stub_gateway.STATE["records"],
                      "answer_disposition": body1.get("disposition"), "body_keys": sorted(body1)[:20],
                      "error": body1.get("error"), "checks": checks}, indent=1, sort_keys=True))
    if not all(checks.values()):
        print("---- captured stdout (tail) ----\n" + "\n".join(lines[-30:]))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
