import base64
import io
import json
import os
import re
import subprocess
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from prooflab.adapters.orchestrator import common, conditions, invoke, ledger, preflight, run
from prooflab.contract import ids, record as R

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
NOW = common.parse_utc("2026-10-06T04:30:00.000Z")
EXPIRY = "2026-10-06T13:52:47Z"
AGENTS = ["ifabric-customer", "ifabric-it", "ifabric-network"]


def jfile(tmp, name, obj):
    path = os.path.join(str(tmp), name)
    with open(path, "w") as fh:
        json.dump(obj, fh)
    return path


class Proc:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


class FakeAws:
    """The single runner seam: sts, invoke-agent-runtime (records every call), nothing else."""

    def __init__(self, behaviour=None):
        self.invokes = []
        self.behaviour = behaviour or {}

    def __call__(self, argv, **kw):
        if argv[:3] == ["aws", "sts", "get-caller-identity"]:
            return Proc(0, "arn:aws:sts::000000000000:assumed-role/WSParticipantRole/x\n")
        if argv[:3] == ["aws", "bedrock-agentcore", "invoke-agent-runtime"]:
            arn = argv[argv.index("--agent-runtime-arn") + 1]
            agent = arn.rsplit("/", 1)[-1]
            self.invokes.append({"argv": list(argv), "env": dict(kw.get("env") or {}), "agent": agent})
            how = self.behaviour.get(agent, "ok")
            if how == "timeout":
                raise subprocess.TimeoutExpired(argv, 930)
            if how == "cli-timeout":
                return Proc(255, "", "Read timeout on endpoint URL")
            with open(argv[-1], "w") as fh:
                json.dump({"output": {"text": "answer from " + agent, "disposition": "auto-resolve",
                                      "halted": False, "ifabric": {"tally_tokens": 100, "tally_calls": 2}}}, fh)
            return Proc(0, "", "")
        raise AssertionError("unexpected call: %r" % (argv,))


@pytest.fixture
def env(tmp_path):
    runtimes = jfile(tmp_path, "rt.json", {a: "arn:aws:bedrock-agentcore:us-east-1:000000000000:runtime/" + a for a in AGENTS})
    versions = jfile(tmp_path, "v.json", json.load(open(os.path.join(FIX, "versions-synthetic.json"))))
    approval = types.ModuleType("prooflab.evaluators.approval")
    approval.check_versions = lambda running, approved, policy, assessed, meta=None: [
        {"actor_id": a, "verdict": "ALLOW", "action": "proceed"} for a in running]
    sys.modules["prooflab.evaluators.approval"] = approval
    yield types.SimpleNamespace(tmp=tmp_path, rt=runtimes, versions=versions, approval=approval,
                                rundir=str(tmp_path / "runs"))
    sys.modules.pop("prooflab.evaluators.approval", None)


def go(env, extra, runner=None, now=NOW, tokens="0"):
    runner = runner or FakeAws()
    out = io.StringIO()
    argv = ["--scenario", "S1", "--run-dir", env.rundir, "--runtimes-file", env.rt, "--versions-file", env.versions,
            "--creds-expiry", EXPIRY, "--tokens-last-hour", tokens] + extra
    rc = run.main(argv, runner=runner, now=now, out=out)
    return rc, runner, out.getvalue()


def spool_records(env):
    d = os.path.join(env.rundir, "spool")
    recs = []
    for name in sorted(os.listdir(d)):
        recs += [json.loads(l) for l in open(os.path.join(d, name))]
    return recs


def test_one_invoke_per_handoff_on_timeout(env):
    rc, fake, _ = go(env, [], FakeAws({"ifabric-it": "timeout"}))
    assert rc == run.EXIT_INCOMPLETE
    assert [i["agent"] for i in fake.invokes] == ["ifabric-customer", "ifabric-it"]   # IT once, network never
    recs = spool_records(env)
    got = [r for r in recs if r["record_kind"] == "handoff" and r.get("outcome.real") == "TIMEOUT"]
    assert len(got) == 1 and "ifabric-it" in got[0]["detail"] and "status=TIMEOUT" in got[0]["detail"]


def test_cli_read_timeout_text_is_timeout_not_retried(env):
    rc, fake, _ = go(env, [], FakeAws({"ifabric-customer": "cli-timeout"}))
    assert rc == run.EXIT_INCOMPLETE and len(fake.invokes) == 1


def test_env_argv_cid_session_baggage(env):
    rc, fake, out = go(env, [])
    assert rc == 0 and len(fake.invokes) == 3
    cid = json.loads(out)["cid"]
    assert re.match(r"^ifabric-(run|test|adv)-\d+-[0-9a-f]+$", cid)
    for inv in fake.invokes:
        assert inv["env"]["AWS_MAX_ATTEMPTS"] == "1" and inv["env"]["AWS_RETRY_MODE"] == "standard"
        a = inv["argv"]
        assert a[a.index("--cli-read-timeout") + 1] == "900"
        assert a[a.index("--baggage") + 1] == "modaas-correlation-id=" + cid
        sid = a[a.index("--runtime-session-id") + 1]
        assert re.match(r"^" + re.escape(cid) + r"-[0-9a-f]{32}$", sid) and ids.session_cid(sid) == cid
        assert "--trace-parent" in a
    sent = [r for r in spool_records(env) if r["record_kind"] == "handoff" and "sent" in r["detail"]]
    assert [r["handoff.id"] for r in sent] == [cid + ":h1", cid + ":h2"]
    assert sent[0]["handoff.from"] == "ifabric-customer" and sent[0]["handoff.to"] == "ifabric-it"
    for r in sent:
        assert re.match(r"^" + re.escape(cid) + r"-[0-9a-f]{32}$", r["runtime.session_id"])
        assert R.validate_record(r) == []


def test_build_argv_requires_baggage():
    with pytest.raises(ValueError):
        invoke.build_argv("arn", "sid", "p", "o", "", "tp", common.load_budget())


def test_tally_is_carried_forward(env):
    rc, fake, _ = go(env, [])
    payloads = [r for r in spool_records(env) if r["record_kind"] == "handoff"]
    assert rc == 0 and payloads


def test_preflight_refuses_over_one_million(env):
    rc, fake, _ = go(env, [], tokens="900000")          # 900K + the S1 bound (60K) is fine
    assert rc == 0
    env.rundir = str(env.tmp / "runs2")
    rc, fake, _ = go(env, [], tokens="950000")          # 950K + 60K > 1.0M
    assert rc == run.EXIT_REFUSED and fake.invokes == []


def test_unknown_headroom_fails_closed(env):
    out = io.StringIO()
    rc = run.main(["--scenario", "S1", "--run-dir", env.rundir, "--runtimes-file", env.rt, "--versions-file",
                   env.versions, "--creds-expiry", EXPIRY], runner=_NoLogs(), now=NOW, out=out)
    assert rc == run.EXIT_REFUSED


class _NoLogs(FakeAws):
    def __call__(self, argv, **kw):
        if argv[:2] == ["aws", "logs"]:
            return Proc(1, "", "denied")
        return super().__call__(argv, **kw)


def test_third_observe_s2_refused(env):
    env.rundir = str(env.tmp / "s2")
    def s2(when):
        out = io.StringIO()
        fake = FakeAws()
        rc = run.main(["--scenario", "S2", "--mode", "observe", "--run-dir", env.rundir, "--runtimes-file", env.rt,
                       "--versions-file", env.versions, "--creds-expiry", EXPIRY, "--tokens-last-hour", "0"],
                      runner=fake, now=when, out=out)
        return rc, fake
    assert s2(common.parse_utc("2026-10-06T04:00:00Z"))[0] == 0
    assert s2(common.parse_utc("2026-10-06T04:10:00Z"))[0] == 0
    rc, fake = s2(common.parse_utc("2026-10-06T04:20:00Z"))
    assert rc == run.EXIT_REFUSED and fake.invokes == []
    assert s2(common.parse_utc("2026-10-06T05:11:00Z"))[0] == 0      # 04:00 and 04:10 left the rolling hour


def test_guard_pure_over_and_under():
    b = common.load_budget()
    over = preflight.budget_guard(b, NOW, 800000, 300000, False, [])
    assert not over[0]["ok"]
    assert preflight.budget_guard(b, NOW, 700000, 300000, False, [])[0]["ok"]


def test_ep0_declines_paused_and_stale(env):
    def check(running, approved, policy, assessed, meta=None):
        return [{"actor_id": a, "verdict": "DENY", "action": "decline-start"} if running[a].get("paused")
                else {"actor_id": a, "verdict": "ALLOW", "action": "proceed"} for a in running]
    env.approval.check_versions = check
    doc = json.load(open(env.versions))
    doc["running"]["ifabric-it"]["paused"] = True
    path = jfile(env.tmp, "paused.json", doc)
    out = io.StringIO()
    fake = FakeAws()
    rc = run.main(["--scenario", "S1", "--run-dir", env.rundir, "--runtimes-file", env.rt, "--versions-file", path,
                   "--creds-expiry", EXPIRY, "--tokens-last-hour", "0"], runner=fake, now=NOW, out=out)
    assert rc == run.EXIT_REFUSED and fake.invokes == []
    steps, _ = preflight.ep0(json.load(open(path)), True, AGENTS, check)
    assert [s["ok"] for s in steps] == [True, False, True]


def test_ep0_absent_module_is_a_clear_error(env):
    sys.modules.pop("prooflab.evaluators.approval", None)
    sys.modules["prooflab.evaluators.approval"] = None      # forces ImportError
    steps, _ = preflight.ep0(json.load(open(env.versions)), True, AGENTS)
    assert not steps[0]["ok"] and "PR-09a" in steps[0]["detail"]


def test_pin_echo_mismatch_refuses(env):
    pin = jfile(env.tmp, "pin.json", {"register_version": "v1", "register_sha256": "a" * 64, "pin_sha256": "b" * 64})
    echo = jfile(env.tmp, "echo.json", {"ifabric-it": "c" * 64})
    rc, fake, _ = go(env, ["--pin-file", pin, "--echoed-pins", echo])
    assert rc == run.EXIT_REFUSED and fake.invokes == []


def test_expired_credentials_refuse(env):
    out = io.StringIO()
    rc = run.main(["--scenario", "S1", "--run-dir", env.rundir, "--runtimes-file", env.rt, "--versions-file",
                   env.versions, "--creds-expiry", "2026-10-06T04:35:00Z", "--tokens-last-hour", "0"],
                  runner=FakeAws(), now=NOW, out=out)
    assert rc == run.EXIT_REFUSED


def test_logs_insights_headroom_parse_from_derived_fixture():
    doc = json.load(open(os.path.join(FIX, "headroom-derived.json")))

    def runner(argv, **kw):
        if "start-query" in argv:
            return Proc(0, "qid-1\n")
        return Proc(0, json.dumps(doc))
    total = preflight.tokens_in_window(runner, NOW, common.load_budget(), sleep=lambda s: None)
    assert total == sum(int(c["value"]) for c in doc["results"][0])


def test_token_never_in_argv_or_logs(env, capsys):
    token = "tok-" + "Zq7" * 8
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["hdr"] = self.headers.get("X-Audit-Token")
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    calls = []

    class Fake(FakeAws):
        def __call__(self, argv, **kw):
            calls.append(list(argv))
            if argv[0] == "kubectl":
                return Proc(0, base64.b64encode(token.encode()))
            return super().__call__(argv, **kw)
    fake = Fake()
    rc, _, out = go(env, ["--ledger-url", "http://127.0.0.1:%d" % srv.server_port, "--ledger-secret", "ns/sec/key"],
                    fake)
    srv.shutdown()
    err = capsys.readouterr().err
    assert rc == 0 and seen["hdr"] == token                      # it did travel, as the header only
    assert all(token not in " ".join(a) for a in calls)
    assert all(token not in json.dumps(i["env"]) for i in fake.invokes)
    assert token not in out and token not in err
    for name in os.listdir(env.rundir + "/spool"):
        assert token not in open(env.rundir + "/spool/" + name).read()
    assert token not in open(env.rundir + "/run-index.jsonl").read()
    assert token not in repr(ledger.LedgerSink("http://x", token))
    assert any(a[0] == "kubectl" and "jsonpath" in " ".join(a) for a in calls)


def test_only_flag_invokes_one_agent_without_handoff(env):
    rc, fake, _ = go(env, ["--only", "ifabric-customer"])
    assert [i["agent"] for i in fake.invokes] == ["ifabric-customer"]
    assert not [r for r in spool_records(env) if r["record_kind"] == "handoff" and "sent" in r["detail"]]


def test_condition_text_is_appended_and_stamped(env):
    rc, fake, _ = go(env, ["--only", "ifabric-customer", "--condition", "prompt-attack"])
    recs = spool_records(env)
    assert rc == 0 and all(r["run.condition"] == "prompt-attack" for r in recs)
    assert all(r["provenance"] == "FAULT_INJECTION" for r in recs)
    assert recs[0]["run.id"].startswith("ifabric-adv-")


def test_condition_sums_and_tamper_detected(tmp_path):
    root = str(tmp_path)
    os.makedirs(root + "/register/conditions")
    for n in conditions.CONDITIONS:
        open("%s/register/conditions/%s.txt" % (root, n), "w").write("text " + n)
    open(root + "/register/conditions/SHA256SUMS", "w").write("0" * 64 + "  prompt-attack.txt\n")
    with pytest.raises(ValueError):
        conditions.load_condition("prompt-attack", root)


def test_dry_run_envelope_with_condition_sha():
    out = io.StringIO()
    rc = run.main(["--dry-run", "--scenario", "S1", "--only", "ifabric-customer", "--condition", "prompt-attack"],
                  out=out)
    doc = json.loads(out.getvalue())
    sums = dict(l.split()[::-1] for l in open(os.path.join(common.REPO_ROOT, "register/conditions/SHA256SUMS")))
    assert rc == 0 and doc["dry_run"] and doc["envelope"]["condition"] == "prompt-attack"
    assert doc["envelope"]["condition_sha256"] == sums["prompt-attack.txt"] == doc["condition"]["sha256"]
    assert doc["envelope"]["run_id"] == doc["cid"] and doc["baggage"] == "modaas-correlation-id=" + doc["cid"]


def test_fault_parse():
    f = conditions.parse_fault("inject-tool-output:ifabric-it:customer-records:fx1")
    assert f["tool"] == "customer-records" and f["fixture"] == "fx1" and f["fixture_sha256"] is None
    with pytest.raises(ValueError):
        conditions.parse_fault("inject-tool-output:ifabric-it")


def test_run_records_are_valid_and_index_written(env):
    rc, _, out = go(env, [])
    for r in spool_records(env):
        assert R.validate_record(r) == []
    idx = [json.loads(l) for l in open(env.rundir + "/run-index.jsonl")]
    assert [e["event"] for e in idx] == ["run.started", "run.finished"]
    assert idx[1]["status"] == "FINISHED"


def _real_check_versions():
    """The real PR-09a function (skip if absent). Needs PR-09a + PR-02 on PYTHONPATH until they merge."""
    saved = sys.modules.pop("prooflab.evaluators.approval", None)
    import prooflab
    for root in filter(None, os.environ.get("PROOFLAB_SIBLING_ROOTS", "").split(os.pathsep)):   # pre-merge borrowing
        if os.path.join(root, "prooflab") not in prooflab.__path__:
            prooflab.__path__.append(os.path.join(root, "prooflab"))
    try:
        import prooflab.evaluators as ev
        for root in filter(None, os.environ.get("PROOFLAB_SIBLING_ROOTS", "").split(os.pathsep)):
            ev.__path__.append(os.path.join(root, "prooflab", "evaluators"))   # c16_core lives in a sibling
    except ImportError:
        pass
    try:
        import importlib
        return importlib.import_module("prooflab.evaluators.approval").check_versions
    except ImportError:
        pytest.skip("prooflab.evaluators.approval (PR-09a) not importable")
    finally:
        if saved is not None:
            sys.modules["prooflab.evaluators.approval"] = saved


def test_ep0_real_check_versions_integration(env):
    real = _real_check_versions()
    doc = json.load(open(env.versions))
    steps, _ = preflight.ep0(doc, True, AGENTS, real, meta={"register_version": "v1", "pin_sha256": "b" * 64})
    assert [s["ok"] for s in steps] == [True, True, True]
    doc["running"]["ifabric-it"]["paused"] = True
    doc["running"]["ifabric-network"]["generation"] = 3          # stale: approved_generation 2
    steps, ds = preflight.ep0(doc, True, AGENTS, real)
    by = {s["name"]: s for s in steps}
    assert by["ep0.ifabric-customer"]["ok"]
    assert not by["ep0.ifabric-it"]["ok"] and "paused" in by["ep0.ifabric-it"]["detail"]
    assert not by["ep0.ifabric-network"]["ok"] and "stale" in by["ep0.ifabric-network"]["detail"]
    doc["running"]["ifabric-it"]["paused"] = False
    doc["approved"]["ifabric-it"] = ["sha256:other|synthetic-model-1"]
    steps, _ = preflight.ep0(doc, True, AGENTS, real)
    assert not [s for s in steps if s["name"] == "ep0.ifabric-it"][0]["ok"]
