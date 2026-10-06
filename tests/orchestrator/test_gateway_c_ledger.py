"""PR-28: Gateway C (network -> IT) in the orchestrating script, the C7 workflow phases on its records, the
ledger's one-object-per-POST rule (live 400 on an array), and the fault fixture path (register/conditions/)."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from prooflab.adapters.orchestrator import common, conditions, ledger, preflight, run
from prooflab.contract import record as R
from prooflab.stitch import stitcher

from test_orchestrator_run import FakeAws, Proc, env, go, spool_records  # noqa: F401  (fixture reuse)


class _NetworkProposes(FakeAws):
    """The network answers with a structured proposal; every invocation's payload is kept."""

    def __init__(self, behaviour=None):
        FakeAws.__init__(self, behaviour)
        self.payloads = []

    def __call__(self, argv, **kw):
        if "invoke-agent-runtime" in argv:
            path = argv[argv.index("--payload") + 1][len("fileb://"):]
            self.payloads.append(json.load(open(path)))
        proc = FakeAws.__call__(self, argv, **kw)
        if "invoke-agent-runtime" in argv and self.invokes[-1]["agent"] == "ifabric-network":
            out = json.load(open(argv[-1]))
            out["output"]["proposal"] = {"resolution": "switch to the protection path", "change_risk": "low"}
            out["output"]["answer"] = "network answer text"
            json.dump(out, open(argv[-1], "w"))
        if "invoke-agent-runtime" in argv and "negotiate" in self.payloads[-1]:
            out = json.load(open(argv[-1]))
            out["output"]["position"] = "agree"
            json.dump(out, open(argv[-1], "w"))
        return proc


def test_gateway_c_invokes_it_once_with_the_network_proposal(env):
    fake = _NetworkProposes()
    rc, _, out = go(env, [], fake)
    cid = json.loads(out)["cid"]
    assert rc == 0
    assert [i["agent"] for i in fake.invokes] == ["ifabric-customer", "ifabric-it", "ifabric-network", "ifabric-it"]
    neg = fake.payloads[-1]
    assert set(neg) == {"negotiate", "ifabric"}
    assert neg["negotiate"]["correlation_id"] == cid and neg["negotiate"]["handoff_id"] == cid + ":h3"
    assert neg["negotiate"]["proposal"] == {"resolution": "switch to the protection path", "change_risk": "low"}
    assert neg["negotiate"]["traceparent"] and neg["ifabric"]["from"] == "ifabric-network"
    assert all("context" in p and "prompt" not in p for p in fake.payloads[:3])
    assert fake.payloads[1]["context"]["question"].endswith("answer from ifabric-customer")   # the answer, not JSON
    recs = spool_records(env)
    for r in recs:
        assert R.validate_record(r) == [], r
        assert r["actor"] == "orchestrator"
    phases = [r["phase"] for r in recs]
    assert phases[0] == "run.started" and phases[-1] == "run.finished"
    assert phases.count("handoff.sent") == 3 and phases.count("handoff.received") == 4
    h3 = [r for r in recs if r.get("handoff.id") == cid + ":h3"]
    sent = [r for r in h3 if r["phase"] == "handoff.sent"][0]
    assert sent["handoff.payload_sha256"] == common.sha256_text(common.canonical(neg))
    assert "position=agree" in [r for r in h3 if r["phase"] == "handoff.received"][0]["detail"]
    # the stitcher joins Gateways A, B and C by CID + handoff id
    links = [l for l in stitcher.stitch(recs)["run_index"][0]["links"] if l["key"] == "handoff.id"]
    assert [l["value"] for l in links] == [cid + ":h1", cid + ":h2", cid + ":h3"]


def test_gateway_c_never_reinvoked_on_timeout(env):
    fake = FakeAws({})
    calls = []

    def runner(argv, **kw):
        if "invoke-agent-runtime" in argv:
            calls.append(argv)
            if len(calls) == 4:
                import subprocess
                raise subprocess.TimeoutExpired(argv, 930)
        return fake(argv, **kw)
    rc, _, _ = go(env, [], runner)
    assert rc == run.EXIT_INCOMPLETE and len(calls) == 4
    recs = spool_records(env)
    assert [r for r in recs if r.get("outcome.real") == "TIMEOUT"][0]["handoff.id"].endswith(":h3")


def test_budget_bound_counts_the_extra_it_call():
    b = common.load_budget()
    full, cls = preflight.bound_for(b, "S1", "observe", gateway_c=True)
    assert full == b["bounds"]["trio_s"] + b["bounds"]["gateway_c_extra"] and cls.endswith("+gateway_c")
    assert preflight.bound_for(b, "S1", "observe", only="gateway-c", gateway_c=False)[1] == "smoke_single"


def test_only_gateway_c_needs_a_proposal_and_sends_negotiate(env, tmp_path):
    rc, fake, _ = go(env, ["--only", "gateway-c"])
    assert rc == 2 and not fake.invokes
    prop = tmp_path / "p.json"
    prop.write_text(json.dumps({"resolution": "x"}))
    fake = _NetworkProposes()
    rc, _, _ = go(env, ["--only", "gateway-c", "--proposal-file", str(prop)], fake)
    assert rc == 0 and [i["agent"] for i in fake.invokes] == ["ifabric-it"]
    assert fake.payloads[0]["negotiate"]["proposal"] == {"resolution": "x"}


def test_declared_fault_goes_to_the_trio_invocation_only(env):
    fake = _NetworkProposes()
    rc, _, _ = go(env, ["--fault", "inject-tool-output:ifabric-it:lookup:tool-directive"], fake)
    assert rc == 0
    it = [p for p, i in zip(fake.payloads, fake.invokes) if i["agent"] == "ifabric-it"]
    assert it[0]["ifabric"]["fault"]["fixture_text"] and "fault" not in it[1]["ifabric"]


def test_fault_fixture_is_read_from_register_conditions():
    f = conditions.parse_fault("inject-tool-output:ifabric-it:lookup:tool-directive")
    sums = dict(l.split()[::-1] for l in open(os.path.join(common.REPO_ROOT, "register/conditions/SHA256SUMS")))
    assert f["fixture_path"] == os.path.join("register", "conditions", "tool-directive.txt")
    assert f["fixture_sha256"] == sums["tool-directive.txt"]
    assert common.sha256_text(f["fixture_text"]) == f["fixture_sha256"]


class _OneObjectStore(BaseHTTPRequestHandler):
    """The audit store's rule: one JSON object per POST; an array is a 400 `bad record`."""
    got = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ok = isinstance(body, dict) and self.headers.get("X-Audit-Token") == "fake-ledger-write-value"
        if ok:
            _OneObjectStore.got.append(body)
        self.send_response(200 if ok else 400)
        self.end_headers()
        self.wfile.write(b"ok" if ok else b"bad record")

    def log_message(self, *a):
        pass


def test_ledger_posts_one_object_per_record():
    srv = HTTPServer(("127.0.0.1", 0), _OneObjectStore)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        _OneObjectStore.got = []
        sink = ledger.LedgerSink("http://127.0.0.1:%d" % srv.server_port, "fake-ledger-write-value")
        assert sink.post([{"a": 1}, {"b": 2}]) == 2
        assert _OneObjectStore.got == [{"a": 1}, {"b": 2}]
        import urllib.error
        bad = ledger.LedgerSink("http://127.0.0.1:%d" % srv.server_port, "wrong-value")
        with pytest.raises(urllib.error.HTTPError):
            bad.post([{"a": 1}])
    finally:
        srv.shutdown()
