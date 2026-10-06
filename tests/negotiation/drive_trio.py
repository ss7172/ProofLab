"""PR-28 dynamic driver (run on the Strands 3.12 venv, as a subprocess of test_negotiation.py; SYNTHETIC, offline).

    <venv-strands312>/bin/python tests/negotiation/drive_trio.py <S1|S2|S3> --out OUT.json [--fault SPEC]
        [--variant s3-agree|s2-data|p1|p1-empty|p1-blocked]

The REAL orchestrator (`prooflab run`, its preflight with stubbed AWS answers) invokes the REAL shared app
(ifabric_app.build(role SPEC) -> invoke()) in-process through the runner seam; each app writes through its real
EmitClient (kit shape, validation) to a loopback FAKE audit store that, like the live one, takes ONE object per
POST (an array is a 400). Only Strands' Agent is replaced: a scripted fake that drives the same hooks a real
Agent does (EP-1 before/after model call, the rails + EP-3 tool hooks) and answers with scripted JSON.
Nothing calls AWS, a cluster or a model. Writes {"cid", "rc", "records", "results"} to --out (stdout carries
the agents' own witness lines).
"""
import base64
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [REPO, os.path.join(REPO, "agents", "ifabric-customer")]

STORE, TOKEN = [], "fake-ledger-write-value"


class Store(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"null")
        ok = isinstance(body, dict) and self.headers.get("X-Audit-Token") == TOKEN
        if ok:
            STORE.append(body)
        self.send_response(200 if ok else 400)
        self.end_headers()
        self.wfile.write(b"{}" if ok else b"bad record")

    def log_message(self, *a):
        pass


# ---- scripted model answers per scenario and role (the fake model's text; J2 parses it as it would a real one)
def _j(**kw):
    return json.dumps(kw)


EVIDENCE = {"customer": "customers at SITE-DEN-12: 3 enterprise accounts degraded",
            "it": "INC-4471 open; runbook RB-EDGE-SLICE-DEGRADATION approves a protection-path switch",
            "network": "predict_rsrp SITE-DEN-12: -97 dBm, optic loss on the primary path"}
SCRIPT = {
    "S1": {"customer": _j(disposition="resolve", deciding_evidence=["E1"], reason="impact known; notify customers",
                          reversible_step="none needed"),
           "it": _j(disposition="resolve", deciding_evidence=["E1"], reason="the runbook covers this incident",
                    reversible_step="switch back to the primary path"),
           "network": _j(disposition="resolve", deciding_evidence=["E1"], reason="one cause: optic loss",
                         proposed_action="switch to the protection path", change_risk="low: a runbook path",
                         reversible_step="switch back to the primary path"),
           "negotiate": _j(disposition="resolve", deciding_evidence=["E1"], position="agree",
                           reason="the protection-path switch is runbook-approved",
                           reversible_step="switch back to the primary path")},
    "S2": {"customer": _j(disposition="gather-evidence", deciding_evidence=["E1"], reason="cause unclear",
                          named_evidence_needed=["per-site outage times"], reversible_step="none"),
           "it": _j(disposition="gather-evidence", deciding_evidence=["E1"], reason="two causes fit; inconclusive",
                    named_evidence_needed=["optical power history"], reversible_step="temporary reroute, revert"),
           "network": _j(disposition="resolve", deciding_evidence=["E1"], reason="probably the optic",
                         proposed_action="replace the optic", change_risk="medium"),
           # the model AGREES, but the runbook lookup came back empty: J2's empty-evidence rule moves it
           "negotiate": _j(disposition="resolve", deciding_evidence=["E1"], position="agree", reason="looks fine")},
    "S3": {"customer": _j(disposition="escalate", deciding_evidence=["E1"], reason="regulated customer; freeze"),
           "it": _j(disposition="escalate", deciding_evidence=["E1"], reason="maintenance freeze: human approval"),
           "network": _j(disposition="escalate", deciding_evidence=["E1"], reason="change frozen",
                         proposed_action="reroute the regulated slice", change_risk="high: change freeze"),
           "negotiate": _j(disposition="escalate", deciding_evidence=["E1"], position="disagree",
                           reason="maintenance freeze: the change is out of policy; named approval required")},
}
# variants (--variant): the precedence must hold whatever the model says on Gateway C
AGREE = _j(disposition="resolve", deciding_evidence=["E1"], position="agree", reason="the fix is clear",
           reversible_step="switch back")
VARIANTS = {
    # S3: the IT model AGREES and calls it resolved; the freeze (constraints) and the network's escalate win
    "s3-agree": {"S3": {"negotiate": AGREE}},
    # S2: the runbook lookup returns data and the model agrees, but the network proposed gather-evidence
    "s2-data": {"S2": {"network": _j(disposition="gather-evidence", deciding_evidence=["E1"], reason="two causes fit",
                                     named_evidence_needed=["QoS policy change log"],
                                     proposed_action="collect the QoS change log", change_risk="none: read-only"),
                       "negotiate": AGREE}},
}
# PR-38 replay of pilot P1's shapes (ops-lane b3): customer and network answer bullets with no JSON and the platform
# guardrail blocks their J2 re-ask (the live shape: HTTP 200, content_filter, 0/0 tokens, text BLOCKED); every IT
# runbook lookup finds nothing (h1 and Gateway C). p1-empty: the network's answer is empty too, so Gateway C gets an
# empty proposal. p1-blocked: the guardrail blocks the network's own TASK call (as ADV-H-01 does), text BLOCKED.
BLOCKED = "Input blocked by policy."   # what the platform returns in the content of a blocked call (Strands: end_turn)
P1 = {"customer": "- 3 enterprise accounts at SITE-DEN-12 have degraded service [EVIDENCE E1]\n- tell them a fix is under way",
      "network": "- Probable root cause: optic loss on eth-1/7 [EVIDENCE E1]\n- Proposed resolution: move the slice "
                 "from eth-1/7 to eth-1/8.\n- Change risk: low; revert by moving it back to eth-1/7."}
EMPTY_LOOKUP = json.dumps({"query": "SITE-DEN-12", "category": "all", "total_hits": 0, "results": {"incidents": []}})
TOOL = {"customer": "customer-records___customer_lookup", "it": "runbook-lookup___lookup",
        "network": "network-twin___predict_rsrp"}


class _Ev(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeAgent(object):
    """Stands in for strands.Agent: the same hook calls a real Agent makes, a scripted answer."""
    scenario, variant, n = "S1", None, [0]

    def __init__(self, model=None, tools=None, system_prompt="", hooks=(), callback_handler=None):
        self.mc, self.th, self.calls = hooks[0], hooks[1], 0
        self.role = next(r for r in TOOL if "(ifabric-%s)" % r in system_prompt)

    def _model_call(self, finish="stop", usage=(800, 120)):
        FakeAgent.n[0] += 1
        ev = _Ev(projected_input_tokens=800, cancel=None)
        self.mc.on_before_model_call(ev)
        if ev.cancel:
            return False
        self.mc.capture.observe_headers({"x-modaas-action-id": "act-%04d" % FakeAgent.n[0]}, 200)
        self.mc.finish.record(finish)
        msg = {"metadata": {"usage": {"inputTokens": usage[0], "outputTokens": usage[1]}}}
        self.mc.on_after_model_call(_Ev(stop_response=_Ev(message=msg), exception=None))
        return True

    def _tool(self, text):
        tu = {"name": TOOL[self.role], "input": {"site": "SITE-DEN-12"}, "toolUseId": "tu-%d" % FakeAgent.n[0]}
        before = _Ev(tool_use=tu, cancel_tool=None)
        self.th.before(before)
        if before.cancel_tool:
            return False
        self.th.after(_Ev(tool_use=tu, result={"status": "success", "content": [{"text": text}]},
                          exception=None, cancel_message=None))
        return True

    def _p1(self):
        self.calls += 1
        blocked_task = self.role == "network" and self.variant == "p1-blocked"
        if self.calls > 1 or blocked_task:   # the J2 re-ask (or p1-blocked's task call): blocked by the guardrail
            self._model_call("content_filter", (0, 0))
            return BLOCKED
        if self.role == "it":   # P1's loop: lookups that find nothing, until rail T-07 (or a hard test bound)
            for _ in range(40):
                if not self._model_call() or not self._tool(EMPTY_LOOKUP) or self.th.inv.stop:
                    break
            return ""
        self._model_call()
        self._tool(EVIDENCE[self.role])
        self._model_call()
        return "" if self.role == "network" and self.variant == "p1-empty" else P1[self.role]

    def __call__(self, question):
        if self.variant in ("p1", "p1-empty", "p1-blocked"):
            return self._p1()
        negotiate = question.startswith("NEGOTIATION (Gateway C)")
        if not self._model_call():
            return "stopped"
        tu = {"name": TOOL[self.role], "input": {"site": "SITE-DEN-12"}, "toolUseId": "tu-%d" % FakeAgent.n[0]}
        before = _Ev(tool_use=tu, cancel_tool=None)
        self.th.before(before)
        if not before.cancel_tool:
            empty = negotiate and self.scenario == "S2" and self.variant != "s2-data"
            text = "{}" if empty else EVIDENCE[self.role]
            self.th.after(_Ev(tool_use=tu, result={"status": "success", "content": [{"text": text}]},
                              exception=None, cancel_message=None))
        self._model_call()
        key = "negotiate" if negotiate else self.role
        return "- finding\n- action\n%s" % SCRIPT[self.scenario][key]


def main(argv):
    scenario = argv[0]
    fault = argv[argv.index("--fault") + 1] if "--fault" in argv else None
    FakeAgent.scenario = scenario
    FakeAgent.variant = argv[argv.index("--variant") + 1] if "--variant" in argv else None
    for scen, roles in VARIANTS.get(FakeAgent.variant, {}).items():
        SCRIPT[scen] = dict(SCRIPT[scen], **roles)
    srv = HTTPServer(("127.0.0.1", 0), Store)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % srv.server_port

    from prooflab.registry import pinned
    reg = open(os.path.join(REPO, "register", "register.yaml"), "rb").read()
    env = pinned.env_for(reg, "observe")   # the register's declared inline mode
    os.environ.update(env)
    os.environ.update({"OPENAI_API_KEY": "fake-model-key-value", "AGENTCORE_GATEWAY_MCP_TOKEN": "fake-mcp-value",
                       "AUDIT_URL": url, "AUDIT_WRITE_TOKEN": TOKEN, "IFABRIC_RAILS_MODE": "enforce"})
    for k in ("TOOL_MCP_URL", "AGENTCORE_GATEWAY_MCP_URL", "AGENT_NAME"):
        os.environ.pop(k, None)

    from adapters.runtime import model_call
    model_call.make_gateway_model = lambda *a, **k: types.SimpleNamespace(format_request=lambda *x, **y: {})
    import ifabric_app
    ifabric_app.Agent = FakeAgent
    apps = {}
    for role in ("customer", "it", "network"):
        path = os.path.join(REPO, "agents", "ifabric-" + role, "role.py")
        spec = importlib.util.spec_from_file_location("role_" + role, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        apps["ifabric-" + role] = mod.app.handlers["main"]

    results = []

    def runner(cmd, **kw):
        if cmd[:3] == ["aws", "sts", "get-caller-identity"]:
            return types.SimpleNamespace(returncode=0, stdout="arn:aws:sts::0:assumed-role/WSParticipantRole/x\n",
                                         stderr="")
        if cmd[:1] == ["kubectl"]:   # the ledger Secret read: a fake value, base64 as the cluster returns it
            return types.SimpleNamespace(returncode=0, stdout=base64.b64encode(TOKEN.encode()), stderr=b"")
        if cmd[:3] == ["aws", "bedrock-agentcore", "invoke-agent-runtime"]:
            agent = cmd[cmd.index("--agent-runtime-arn") + 1].rsplit("/", 1)[-1]
            payload = json.load(open(cmd[cmd.index("--payload") + 1][len("fileb://"):]))
            sid = cmd[cmd.index("--runtime-session-id") + 1]
            out = apps[agent](payload, types.SimpleNamespace(session_id=sid))
            results.append({"agent": agent, "negotiate": "negotiate" in payload, "result": out})
            json.dump(out, open(cmd[-1], "w"), default=str)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError("unexpected call %r" % (cmd,))

    sys.modules["prooflab.evaluators.approval"] = types.SimpleNamespace(
        check_versions=lambda running, approved, policy, assessed, meta=None: [
            {"actor_id": a, "verdict": "ALLOW", "action": "proceed"} for a in running])
    from prooflab.adapters.orchestrator import common, run
    tmp = tempfile.mkdtemp(prefix="pr28-drive-")
    rt = os.path.join(tmp, "rt.json")
    json.dump({a: "arn:aws:bedrock-agentcore:us-east-1:000000000000:runtime/" + a for a in apps}, open(rt, "w"))
    vf = os.path.join(REPO, "tests", "orchestrator", "fixtures", "versions-synthetic.json")
    pinf = os.path.join(tmp, "pin.json")
    json.dump({"register_version": env["IFABRIC_REGISTER_VERSION"], "register_sha256": env["IFABRIC_REGISTER_SHA256"],
               "pin_sha256": env["IFABRIC_PIN_SHA256"]}, open(pinf, "w"))
    args = ["--scenario", scenario, "--mode", "observe", "--run-dir", os.path.join(tmp, "runs"), "--runtimes-file", rt,
            "--versions-file", vf, "--pin-file", pinf, "--creds-expiry", "2099-01-01T00:00:00Z",
            "--tokens-last-hour", "0", "--ledger-url", url, "--ledger-secret", "components/audit-store/token"]
    if fault:
        args += ["--fault", fault]
    out = io.StringIO()
    rc = run.main(args, runner=runner, now=common.parse_utc(common.utc_now()), out=out)
    cid = json.loads(out.getvalue())["cid"]
    import time
    deadline = time.time() + 5
    while time.time() < deadline and not any(r.get("phase") == "run.finished" for r in STORE):
        time.sleep(0.05)
    time.sleep(0.3)   # the emit clients' background POSTs
    with open(argv[argv.index("--out") + 1], "w") as fh:
        json.dump({"cid": cid, "rc": rc, "records": STORE, "results": results}, fh, default=str)
    srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
