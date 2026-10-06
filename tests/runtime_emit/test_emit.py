import hashlib
import io
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from prooflab.contract.record import validate_record

from adapters.runtime import emit_client as ec
from adapters.runtime import judgment, startup, tool_call

TOKEN = "t0ken-" + "A1b2C3d4E5f6G7h8"      # synthetic, assembled; not a real credential


class FakeLedger(object):
    def __init__(self, mode="ok"):
        self.records, self.headers, self.mode = [], [], mode
        self.invalid = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n)
                if outer.mode == "hang":
                    time.sleep(5)
                    return
                if outer.mode == "500":
                    self.send_response(500)
                    self.end_headers()
                    return
                outer.headers.append(self.headers.get("X-Audit-Token"))
                rec = json.loads(body)
                errs = validate_record(rec)         # PR-01's contract validates every posted record
                if errs:
                    outer.invalid.append(errs)
                outer.records.append(rec)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def ledger():
    l = FakeLedger()
    yield l
    l.stop()
    assert l.invalid == []


def mk(url, out=None, **kw):
    return ec.EmitClient(url, TOKEN, stdout=out or io.StringIO(), **kw)


def ctx(**kw):
    d = dict(run_id="ifabric-test-1791260000-abc123", actor_id="ifabric-it", handoff_id="h-1",
             session_id="sess-1", register_version="v1", pin_sha256="a" * 64)
    d.update(kw)
    return ec.RunContext(**d)


def test_post_roundtrip_and_stdout_witness(ledger):
    out = io.StringIO()
    c = mk(ledger.url, out)
    r = tool_call.ToolCallRecorder(c, ctx(), declared_tools=["a"])
    assert r.before("a", {"x": 1}) == ec.ENQUEUED
    assert r.after("a", {"x": 1}, status=200, call_id="act-1") == ec.ENQUEUED
    assert c.flush()["ok"]
    assert len(ledger.records) == 2 and set(ledger.headers) == {TOKEN}
    lines = [json.loads(x) for x in out.getvalue().splitlines()]
    assert len(lines) == 2 and lines[1]["call.id"] == "act-1"
    assert ledger.records[0]["tool.declared"] is True
    assert [r["tool.phase"] for r in ledger.records] == ["before", "after"]
    assert ledger.records[1]["call.id"] == "act-1" and "call.id" not in ledger.records[1]["null_reasons"]
    assert "tool.args_sha256" in ledger.records[0] and "x" not in json.dumps(ledger.records[0]["detail"])


def test_tool_undeclared_and_real_status(ledger):
    c = mk(ledger.url)
    r = tool_call.ToolCallRecorder(c, ctx(), declared_tools=["a"])
    r.after("zzz", {}, status=403)
    c.flush()
    rec = ledger.records[0]
    assert rec["tool.declared"] is False and rec["outcome.real"] == "REFUSED_403"
    assert rec["null_reasons"]["call.id"]


def test_judgment_records(ledger):
    c = mk(ledger.url)
    cx = ctx()
    assert judgment.record_judgment(c, cx, "resolve", "known fix", ["r1"], ["d1"]) == ec.ENQUEUED
    assert judgment.record_judgment(c, cx, "escalate", "risky") == ec.ENQUEUED
    assert judgment.record_judgment(c, cx, "gather-evidence", "need more") == ec.ENQUEUED
    assert judgment.record_judgment(c, cx, "guess", "x") == ec.REJECTED_SCHEMA
    assert judgment.record_judgment(c, cx, "escalate", " ") == ec.REJECTED_SCHEMA
    c.flush()
    kinds = [(r["judgment.disposition"], r["verdict"], r["control.ref"], r["phase"]) for r in ledger.records]
    # PR-25 decision (ARCH 3.1 EP-4, 5.2): escalate = the C7 `judgment` event + the ESC `escalation` event
    assert kinds == [("auto-resolve", "RECORDED", "C7", "ifabric.judgment"),
                     ("escalate", "RECORDED", "C7", "ifabric.judgment"),
                     ("escalate", "ESCALATED", "ESC", "ifabric.escalation"),
                     ("gather-evidence", "RECORDED", "C7", "ifabric.judgment")]


def test_t_dup_01_second_invocation_refused_and_recorded(ledger):
    c = mk(ledger.url)
    g = startup.InvocationGuard()
    assert g.begin("h-1") is True
    assert g.begin("h-1") is False                       # in flight: refused
    cx = ctx()
    assert startup.refuse_duplicate(c, cx, g) == ec.ENQUEUED
    g.end("h-1")
    assert g.begin("h-1") is False                       # one invocation per handoff, even after
    assert g.begin("h-2") is True
    c.flush()
    rec = ledger.records[0]
    assert rec["lifecycle.event"] == "duplicate-invocation"
    assert rec["runtime.session_id"] == "sess-1" and rec["handoff.id"] == "h-1"


def test_unenveloped_path(ledger):
    e = startup.resolve_envelope({"prompt": "hi"}, now=1791260000, rand="ab12cd")
    assert e.run_id == "ifabric-unenveloped-1791260000-ab12cd"
    assert not e.enveloped and e.provenance == "UNATTRIBUTED" and e.tally == 0 and e.strictest_cap
    assert startup.resolve_envelope(None).run_id.startswith("ifabric-unenveloped-")
    e2 = startup.resolve_envelope({"envelope": {"run_id": "ifabric-run-1791260000-abc123", "handoff_id": "h"}})
    assert e2.enveloped and e2.run_id == "ifabric-run-1791260000-abc123"
    for payload in ({"ifabric": {"run_id": "ifabric-run-1791260000-abc123", "tally_tokens": 7, "tally_calls": 2}},
                    {"input": {"ifabric": {"run_id": "ifabric-run-1791260000-abc123", "tally_tokens": 7,
                                           "tally_calls": 2}}}):
        e3 = startup.resolve_envelope(payload)
        assert e3.enveloped and e3.tally_tokens == 7 and e3.tally_calls == 2 and e3.tally == 7
    c = mk(ledger.url)
    cx = ctx(run_id=e.run_id, enveloped=False)
    startup.record_no_envelope(c, cx)
    c.flush()
    r = ledger.records[0]
    assert r["lifecycle.event"] == "no-envelope" and r["provenance"] == "UNATTRIBUTED"
    assert r["run.id"] == e.run_id


def test_bounded_flush_under_hung_server():
    l = FakeLedger("hang")
    try:
        c = mk(l.url, timeout=3.0)
        for i in range(3):
            judgment.record_judgment(c, ctx(), "escalate", "r%d" % i)
        t0 = time.time()
        res = c.flush(timeout=0.5)
        dt = time.time() - t0
        assert dt < 1.0 and not res["ok"] and res["pending"] >= 1
        assert any("flush-bound-exceeded" in g["reason"] for g in c.gaps)
        assert c.flush_p99_ms() is not None
    finally:
        l.stop()


def test_emit_never_blocks_with_hung_server_and_full_queue():
    l = FakeLedger("hang")
    try:
        out = io.StringIO()
        c = mk(l.url, out, queue_max=5, timeout=3.0)
        t0 = time.time()
        rc = [judgment.record_judgment(c, ctx(), "escalate", "r%d" % i) for i in range(50)]
        assert time.time() - t0 < 1.0
        assert ec.SPOOLED in rc                           # overflow is spooled, not blocked
        assert len(out.getvalue().splitlines()) >= 50     # every record is on stdout regardless
        assert any("queue-full" in g["reason"] for g in c.gaps)
    finally:
        l.stop()


def test_outage_records_gap_and_stdout_keeps_record():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                                              # nothing listens: connection refused
    out = io.StringIO()
    c = ec.EmitClient("http://127.0.0.1:%d" % port, TOKEN, stdout=out, attempts=2, backoff=0.01)
    judgment.record_judgment(c, ctx(), "gather-evidence", "x")   # one judgment record (escalate emits two)
    assert c.flush(timeout=2.0)["ok"]
    assert c.stats["failed"] == 1 and c.gaps[0]["lifecycle.event"] == "monitoring-gap"
    assert "monitoring-gap" in out.getvalue() and "ifabric.judgment" in out.getvalue()


def test_http_500_is_retried_then_gap():
    l = FakeLedger("500")
    try:
        c = mk(l.url, attempts=2, backoff=0.01)
        judgment.record_judgment(c, ctx(), "gather-evidence", "x")   # one record (escalate emits two)
        c.flush(timeout=2.0)
        assert c.stats["failed"] == 1 and c.gaps
    finally:
        l.stop()


def _pin_env():
    pin = json.dumps({"cap": "from-register"}, sort_keys=True)
    return {"OPENAI_API_KEY": "gw-" + "k" * 12, "AGENTCORE_GATEWAY_MCP_TOKEN": "mcp-" + "m" * 12,
            "AUDIT_URL": "http://127.0.0.1:8080", "AUDIT_WRITE_TOKEN": TOKEN,
            "IFABRIC_PIN_JSON": pin,
            "IFABRIC_PIN_SHA256": hashlib.sha256(pin.encode()).hexdigest(),
            "IFABRIC_REGISTER_VERSION": "v1", "IFABRIC_REGISTER_SHA256": "a" * 64}


def test_startup_ok_echoes_pin_not_token():
    out = io.StringIO()
    cfg = startup.load_startup(_pin_env(), out)
    assert cfg.pin_sha256 in out.getvalue() and cfg.max_retries == 0
    assert TOKEN not in out.getvalue() and TOKEN not in repr(cfg)


@pytest.mark.parametrize("mut", [
    lambda e: e.pop("AUDIT_WRITE_TOKEN"),
    lambda e: e.pop("OPENAI_API_KEY"),
    lambda e: e.__setitem__("AGENTCORE_GATEWAY_MCP_TOKEN", "  "),
    lambda e: e.__setitem__("AUDIT_URL", "not a url"),
    lambda e: e.__setitem__("IFABRIC_PIN_SHA256", "f" * 64),
    lambda e: e.__setitem__("IFABRIC_PIN_SHA256", "xyz"),
    lambda e: e.__setitem__("IFABRIC_PIN_JSON", "{not json"),
    lambda e: e.__setitem__("IFABRIC_REGISTER_SHA256", "short"),
    lambda e: e.pop("IFABRIC_REGISTER_VERSION"),
])
def test_startup_fails_closed(mut):
    env = _pin_env()
    mut(env)
    with pytest.raises(startup.StartupError) as ei:
        startup.load_startup(env)
    for v in (TOKEN, env.get("OPENAI_API_KEY", "")):
        if v:
            assert v not in str(ei.value)


def test_scrub_exact_value_shapes_and_exception(ledger):
    out = io.StringIO()
    c = mk(ledger.url, out)
    c.scrubber.extend(["gw-kkkkkkkkkkkk"])
    aws = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
    pem = "-----BEGIN " + "PRIVATE KEY-----"
    ghp = "gh" + "p_" + "a" * 30
    brr = "Bearer " + "z" * 30
    ck = "t" + "kn=" + "abc123"
    dirty = "x %s %s %s %s %s %s %s" % (TOKEN, "gw-kkkkkkkkkkkk", aws, pem, ghp, brr, ck)
    try:
        raise RuntimeError("upstream said " + TOKEN)
    except RuntimeError as e:
        exc_txt = ec.scrub_exception(e, c.scrubber)
    assert TOKEN not in exc_txt
    cx = ctx()
    rec = ec.new_record(cx, "action", "EP-3", "k", "emit", dirty, "RECORDED",
                        extra={"reason": dirty})
    assert c.emit(rec) == ec.ENQUEUED
    c.flush()
    blob = json.dumps(ledger.records) + out.getvalue()
    for bad in (TOKEN, "gw-kkkkkkkkkkkk", aws, pem, ghp, brr, ck):
        assert bad not in blob
    assert ec.REDACTED in blob


def test_validator_rejects_secret_keys_and_bad_records(ledger):
    c = mk(ledger.url)
    rec = ec.new_record(ctx(), "action", "EP-3", "k", "emit", "d", "RECORDED")
    assert ec.validate(rec) is None
    bad = dict(rec)
    bad["AUDIT_WRITE_TOKEN"] = "x"
    assert c.emit(bad) == ec.REJECTED_SCHEMA
    import copy
    bad = copy.deepcopy(rec)
    del bad["null_reasons"]["call.id"]
    assert c.emit(bad) == ec.REJECTED_SCHEMA
    assert c.emit("nope") == ec.REJECTED_SCHEMA
    assert c.emit(None) == ec.REJECTED_SCHEMA
    ok = dict(rec)
    ok["tokens.in"] = 5                                 # token COUNTS are fine
    assert ec.validate(ok) is None


def test_critical_records_survive_a_full_queue():
    l = FakeLedger("hang")
    try:
        c = mk(l.url, queue_max=3, timeout=3.0)
        for i in range(10):
            c.emit(ec.new_record(ctx(), "action", "EP-3", "k", "emit", "a%d" % i, "RECORDED"))
        time.sleep(0.2)                                  # the worker holds one in flight (hung)
        for i in range(10):
            c.emit(ec.new_record(ctx(), "action", "EP-3", "k", "emit", "b%d" % i, "RECORDED"))
        assert judgment.record_judgment(c, ctx(), "escalate", "critical") == ec.ENQUEUED
        assert c.stats["shed"] >= 1
    finally:
        l.stop()


def test_real_outcome_vocabulary_and_nulls(ledger):
    for st, want in ((200, "SERVED"), (403, "REFUSED_403"), (404, "PAUSED_404"), (405, "METHOD_405"),
                     (429, "CEILING_429"), (500, "ERROR_5XX"), (503, "ERROR_5XX"), (400, None), (None, "SERVED")):
        got = tool_call.real_outcome(st)
        assert got == want
        assert got is None or got in tool_call.OUTCOME_VOCAB
    assert tool_call.real_outcome(None, True) is None
    c = mk(ledger.url)
    r = tool_call.ToolCallRecorder(c, ctx(), declared_tools=["a"])
    r.after("a", {}, status=None, error=RuntimeError("boom"))
    r.after("a", {}, status=422)
    c.flush()
    for rec in ledger.records:
        assert rec["outcome.real"] is None and rec["null_reasons"]["outcome.real"]


def _stdout_records(out):
    return [json.loads(x) for x in out.getvalue().splitlines()]


def test_every_emitted_and_witnessed_record_is_contract_valid(ledger):
    out = io.StringIO()
    c = mk(ledger.url, out)
    cx = ctx()
    r = tool_call.ToolCallRecorder(c, cx, declared_tools=["a"])
    r.before("a", {"x": 1}, tool_use_id="tu-1")
    r.after("a", {"x": 1}, status=200, call_id="act-1", result={"ok": 1}, suspicious=True, tool_use_id="tu-1")
    r.after("a", {}, status=None, error=RuntimeError("boom"))
    judgment.record_judgment(c, cx, "escalate", "risky", ["r1"], ["d1"], "undo", "P1",
                             model_disposition="auto-resolve", valid=True, reasked=False, evidence_needed=["e"])
    judgment.record_intent(c, cx, "triage")
    startup.record_no_envelope(c, ctx(run_id="ifabric-unenveloped-1791260000-ab12cd", enveloped=False))
    g = startup.InvocationGuard()
    g.begin("h-1")
    startup.refuse_duplicate(c, cx, g)
    assert c.flush()["ok"]
    assert len(ledger.records) == 8                     # the escalate judgment adds its `escalation` record
    lines = _stdout_records(out)
    assert len(lines) == 8
    for rec in lines:
        assert validate_record(rec) == [], rec["record_id"]
    assert {r["lifecycle.duplicate_state"] for r in lines if "lifecycle.duplicate_state" in r} == {"in-flight"}


def test_no_stale_null_reason_on_a_non_null_table_a_field(ledger):
    c = mk(ledger.url)
    r = tool_call.ToolCallRecorder(c, ctx(), declared_tools=["a"])
    r.after("a", {}, status=200, call_id="act-9")
    r.after("a", {}, status=200)
    c.flush()
    for rec in ledger.records:
        for k in rec["null_reasons"]:
            assert rec[k] is None, k
    assert ledger.records[0]["call.id"] == "act-9" and ledger.records[1]["call.id"] is None


def test_local_and_contract_validators_agree_on_golden_records(ledger):
    import copy
    golden = [
        ec.new_record(ctx(), "action", "EP-3", "k", "emit", "d", "RECORDED"),
        tool_call.ToolCallRecorder(mk(ledger.url), ctx(), ["a"])._rec("after", "a", {}, "RECORDED", "d",
                                                                      {"outcome.http_status": 200}, "act-1"),
        ec.lifecycle_record(ctx(), "intent", "i"),
    ]
    for rec in golden:
        assert validate_record(rec) == [] and ec._validate_local(rec) is None and ec.validate(rec) is None
    mutations = [
        lambda r: r["null_reasons"].pop("trace.id", None) or r.__setitem__("trace.id", None),
        lambda r: r.pop("emitted.at"),
        lambda r: r.__setitem__("record_id", "bad id"),
        lambda r: r.__setitem__("schema", "x"),
        lambda r: r["null_reasons"].__setitem__("ep.id", "stale"),
        lambda r: r.pop("ep.id"),
        lambda r: r.__setitem__("AUDIT_WRITE_TOKEN", "x"),
    ]
    for m in mutations:
        bad = copy.deepcopy(golden[0])
        m(bad)
        assert validate_record(bad) != [] and ec._validate_local(bad) is not None
        assert ec.validate(bad) is not None
    unknown = copy.deepcopy(golden[0])
    unknown["bogus.field"] = 1                       # only the contract knows the full field list
    assert ec.validate(unknown) is not None


def test_outage_then_recovery_posts_and_gap_is_recorded():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                                              # ledger down: connection refused
    out = io.StringIO()
    c = ec.EmitClient("http://127.0.0.1:%d" % port, TOKEN, stdout=out, attempts=1, backoff=0.01)
    judgment.record_judgment(c, ctx(), "gather-evidence", "during outage")   # one record
    assert c.flush(timeout=2.0)["ok"]
    assert c.stats["failed"] == 1 and c.stats["posted"] == 0
    assert c.gaps and c.gaps[0]["lifecycle.event"] == "monitoring-gap"
    assert validate_record(c.gaps[0]) == []
    l = FakeLedger.__new__(FakeLedger)                     # bring a ledger up on the same port
    FakeLedger.__init__(l)
    try:
        c._port = int(l.url.rsplit(":", 1)[1])
        judgment.record_judgment(c, ctx(), "gather-evidence", "after recovery")
        assert c.flush(timeout=2.0)["ok"]
        assert c.stats["posted"] >= 1 and len(l.records) == 1 and l.invalid == []
    finally:
        l.stop()


def test_flush_p99_reported_over_20_flushes(ledger):
    c = mk(ledger.url)
    for i in range(25):
        judgment.record_judgment(c, ctx(), "gather-evidence", "r%d" % i)   # one record per flush
        assert c.flush()["ok"]
    assert len(c.flush_ms) >= 20 and len(ledger.records) == 25
    p99 = c.flush_p99_ms()
    print("flush_p99_ms=%.1f over %d flushes" % (p99, len(c.flush_ms)))
    assert p99 is not None and p99 < c.flush_bound * 1000.0
