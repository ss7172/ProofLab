"""PR-31 driver: EP-3 tool rails through the REAL shared app and the REAL Strands Agent (SYNTHETIC, offline).

    <venv-strands312>/bin/python tests/ep3_rails/drive_ep3.py --agent ifabric-network --mode enforce \
        --tool customer-records___customer_lookup --site SITE-ADV-99 --out OUT.json

IFABRIC_SRC_ROOT (optional) points at the tree whose ifabric_app / adapters / prooflab are driven (default: this
repository), so the same driver checks another branch's app (for example PR-28's worktree) without copying it.

What is real: ifabric_app.build(role SPEC) -> invoke(), its start-up, rails (X-01 at discovery, X-02/X-03 at
BeforeToolCallEvent, T-02/T-03 at AfterToolCallEvent), the EP-1 C16 hook, the EP-3 recorder, J2, the emit client
(validation, scrubbing) posting to a loopback fake audit store, and strands.Agent (1.57.2) with its tool executor,
so `cancel_tool` is honoured (or not) by Strands itself. What is fake: the model (a scripted Strands Model: one
toolUse, then a J2 answer), the tools (local @tool stubs under the three wire names, each recording that it ran)
and the store. Nothing calls AWS, a cluster or a model. Writes {"records", "dispatched", "model_tools", "result"}.
"""
import json
import os
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.environ.get("IFABRIC_SRC_ROOT") or os.path.dirname(os.path.dirname(HERE)))
sys.path[:0] = [SRC, os.path.join(SRC, "agents", "ifabric-customer")]

STORE, TOKEN, DISPATCHED, MODEL_TOOLS = [], "fake-ledger-write-value", [], []
WIRE = ("customer-records___customer_lookup", "runbook-lookup___lookup", "network-twin___predict_rsrp")
J2_LINE = json.dumps({"disposition": "gather-evidence", "deciding_evidence": [], "reason": "synthetic EP-3 drive",
                      "reversible_step": "none"})


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
    agent_name, mode, tool_name = opt["--agent"], opt["--mode"], opt["--tool"]
    site = opt.get("--site", "SITE-DEN-12")

    from strands import tool
    from strands.models.model import Model

    class StubModel(Model):
        """Turn 1: a toolUse of `tool_name`; every later turn: the J2 answer."""

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
            MODEL_TOOLS.append(sorted(t["name"] for t in tool_specs or []))
            yield {"messageStart": {"role": "assistant"}}
            if self.n == 1:
                yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "tu-1", "name": tool_name}}}}
                yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps({"site": site})}}}}
                yield {"contentBlockStop": {}}
                yield {"messageStop": {"stopReason": "tool_use"}}
            else:
                yield {"contentBlockDelta": {"delta": {"text": "- synthetic\n" + J2_LINE}}}
                yield {"contentBlockStop": {}}
                yield {"messageStop": {"stopReason": "end_turn"}}
            yield {"metadata": {"usage": {"inputTokens": 50, "outputTokens": 10, "totalTokens": 60},
                                "metrics": {"latencyMs": 0}}}

    def _stub(wire):
        @tool(name=wire)
        def f(site: str = "") -> str:
            """Synthetic read-only lookup."""
            DISPATCHED.append({"tool": wire, "site": site})
            return json.dumps({"site": site, "total_hits": 1, "rows": ["synthetic row"]})
        return f

    srv = HTTPServer(("127.0.0.1", 0), Store)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from prooflab.registry import pinned
    with open(os.path.join(SRC, "register", "register.yaml"), "rb") as fh:
        os.environ.update(pinned.env_for(fh.read(), "observe"))
    os.environ.update({"OPENAI_API_KEY": "fake-model-key-value", "AGENTCORE_GATEWAY_MCP_TOKEN": "fake-mcp-value",
                       "AUDIT_URL": "http://127.0.0.1:%d" % srv.server_port, "AUDIT_WRITE_TOKEN": TOKEN,
                       "IFABRIC_RAILS_MODE": mode, "AGENT_NAME": agent_name})
    for k in ("TOOL_MCP_URL", "AGENTCORE_GATEWAY_MCP_URL"):
        os.environ.pop(k, None)

    from adapters.runtime import model_call
    model_call.make_gateway_model = lambda *a, **k: StubModel()
    import ifabric_app
    ifabric_app.load_tools = lambda: [_stub(w) for w in WIRE]   # stands in for MCPClient.list_tools_sync()
    app = ifabric_app.build({"role": agent_name.split("-", 1)[1], "name": agent_name, "tool_alias": "",
                             "prompt": "You are a synthetic test agent (%s)." % agent_name})
    run_id = "ifabric-test-1791300000-e3a1b2"
    payload = {"context": {"question": "look up the customers at %s" % site},
               "ifabric": {"run_id": run_id, "handoff_id": run_id + ":h1", "tier": "high", "tally_tokens": 0,
                           "tally_calls": 0, "from": "orchestrator"}}
    result = app.handlers["main"](payload, types.SimpleNamespace(session_id=run_id + "-" + "0" * 32))
    srv.shutdown()
    with open(opt["--out"], "w") as fh:
        json.dump({"src": SRC, "records": STORE, "dispatched": DISPATCHED, "model_tools": MODEL_TOOLS,
                   "result": result}, fh, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
