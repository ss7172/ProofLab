"""PR-36 driver: rail T-04 (the no-evidence tool-loop guard) through the REAL IT role, the REAL shared app and the
REAL Strands 1.57.2 Agent (SYNTHETIC, offline).

    <venv-strands312>/bin/python tests/it_loop/drive_loop.py --mode enforce --results eeeeeeeeeeee --out OUT.json

What is real: agents/ifabric-it/role.py (its SPEC and prompt) -> ifabric_app.build -> invoke(), start-up with the pin
derived from register/register.yaml (prooflab.registry.pinned, the same path as the live lane), rails, the EP-1 C16
hook, the EP-3 recorder, J2, the emit client (contract validation) posting to a loopback fake audit store, and the
Strands event loop (AfterToolsEvent.end_turn, cancel_tool). What is fake: the model (it calls runbook-lookup with a
new query on every turn while results remain in --results, then gives a J2 answer citing E1), the tool (a local @tool
under the wire name; each result is `e` = no evidence, total_hits 0, or `h` = the INC-4401 hit) and the store.
--no-limit derives the pin from the register with the tool_no_evidence_limit line removed. --freeze adds the
maintenance_freeze constraint to the ticket context. Nothing calls AWS, a cluster or a model.
Writes {"records", "dispatched", "model_calls", "result"}.
"""
import importlib.util
import json
import os
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [SRC, os.path.join(SRC, "agents", "ifabric-customer")]

STORE, TOKEN, DISPATCHED = [], "fake-ledger-write-value", []
WIRE = "runbook-lookup___lookup"
HIT = {"query": "SITE-DEN-12", "category": "incidents", "total_hits": 1, "results": {"incidents": [
    {"id": "INC-4401", "severity": "P2", "status": "open", "summary": "latency on 5G edge slice, SITE-DEN-12",
     "runbook": "RB-EDGE-SLICE-DEGRADATION"}]}}
ANSWER = "- INC-4401 per RB-EDGE-SLICE-DEGRADATION\n" + json.dumps({
    "disposition": "auto-resolve", "deciding_evidence": ["E1"], "reason": "INC-4401 runbook RB-EDGE-SLICE-DEGRADATION",
    "reversible_step": "apply RB-EDGE-SLICE-DEGRADATION step 1; undo by reverting it"})


class Store(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"null")
        ok = self.headers.get("X-Audit-Token") == TOKEN and isinstance(body, (dict, list))
        if ok:
            STORE.extend(body if isinstance(body, list) else [body])
        self.send_response(200 if ok else 400)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


def main(argv):
    opt = dict(zip(argv[::2], argv[1::2]))
    flags = set(a for a in argv if a in ("--no-limit", "--freeze"))
    results = list(opt.get("--results", ""))
    plan = list(results)

    from strands import tool
    from strands.models.model import Model

    class StubModel(Model):
        """Calls the tool (a new query each turn) while results remain in the plan, then answers."""

        def __init__(self):
            self.n = 0

        def update_config(self, **kw):
            pass

        def get_config(self):
            return {}

        def format_request(self, *a, **k):   # ifabric_app._drop_empty_tools wraps it
            return {}

        async def structured_output(self, *a, **kw):
            raise NotImplementedError
            yield

        async def stream(self, messages, tool_specs=None, system_prompt=None, **kw):
            self.n += 1
            yield {"messageStart": {"role": "assistant"}}
            if len(DISPATCHED) < len(plan):
                yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "tu-%d" % self.n, "name": WIRE}}}}
                yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps({"query": "q%d" % self.n})}}}}
                yield {"contentBlockStop": {}}
                yield {"messageStop": {"stopReason": "tool_use"}}
            else:
                yield {"contentBlockDelta": {"delta": {"text": ANSWER}}}
                yield {"contentBlockStop": {}}
                yield {"messageStop": {"stopReason": "end_turn"}}
            yield {"metadata": {"usage": {"inputTokens": 50, "outputTokens": 10, "totalTokens": 60},
                                "metrics": {"latencyMs": 0}}}

    model = StubModel()

    @tool(name=WIRE)
    def lookup(query: str = "") -> str:
        """Synthetic runbook lookup."""
        kind = results.pop(0) if results else "e"
        DISPATCHED.append({"query": query, "kind": kind})
        if kind == "h":
            return json.dumps(HIT)
        return json.dumps({"query": query, "category": "all", "total_hits": 0, "results": {"incidents": []}})

    srv = HTTPServer(("127.0.0.1", 0), Store)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from prooflab.registry import pinned
    with open(os.path.join(SRC, "register", "register.yaml"), "rb") as fh:
        reg = fh.read()
    if "--no-limit" in flags:
        reg = b"".join(l for l in reg.splitlines(True) if not l.strip().startswith(b"tool_no_evidence_limit:"))
    os.environ.update(pinned.env_for(reg, "observe"))
    os.environ.update({"OPENAI_API_KEY": "fake-model-key-value", "AGENTCORE_GATEWAY_MCP_TOKEN": "fake-mcp-value",
                       "AUDIT_URL": "http://127.0.0.1:%d" % srv.server_port, "AUDIT_WRITE_TOKEN": TOKEN,
                       "IFABRIC_RAILS_MODE": opt.get("--mode", "enforce"), "AGENT_NAME": "ifabric-it"})
    for k in ("TOOL_MCP_URL", "AGENTCORE_GATEWAY_MCP_URL"):
        os.environ.pop(k, None)

    from adapters.runtime import model_call
    model_call.make_gateway_model = lambda *a, **k: model
    import ifabric_app
    ifabric_app.load_tools = lambda: [lookup]   # stands in for MCPClient.list_tools_sync()
    spec = importlib.util.spec_from_file_location("it_role", os.path.join(SRC, "agents", "ifabric-it", "role.py"))
    role = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(role)   # the real IT role: ifabric_app.build(SPEC)
    run_id = "ifabric-test-1791300000-36a1b2"
    ctx = {"question": "Customer ticket: latency on the 5G edge slice. Resolve it."}
    if "--freeze" in flags:
        ctx["constraints"] = {"maintenance_freeze": True}
    payload = {"context": ctx,
               "ifabric": {"run_id": run_id, "handoff_id": run_id + ":h1", "tier": "default", "tally_tokens": 0,
                           "tally_calls": 0, "from": "orchestrator"}}
    result = role.app.handlers["main"](payload, types.SimpleNamespace(session_id=run_id + "-" + "0" * 32))
    srv.shutdown()
    with open(opt["--out"], "w") as fh:
        json.dump({"records": STORE, "dispatched": DISPATCHED, "model_calls": model.n, "result": result,
                   "pin": json.loads(os.environ["IFABRIC_PIN_JSON"])}, fh, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
