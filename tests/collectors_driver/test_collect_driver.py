"""M3: the live collect driver, offline: a fake `aws` on PATH and a local stand-in for the kubectl-proxied ledger."""
import json
import os
import stat
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from prooflab import cli
from prooflab.adapters.collectors import capture, driver

CID = "ifabric-run-1791177843-a1b2c3"
TEST_CID = "ifabric-test-1791177843-a1b2c3"
START, END = "2026-10-06T07:35:00Z", "2026-10-06T07:36:40Z"
ARN_C = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/ifabric_customer-AbCdEf1234"
ARN_I = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/ifabric_it-ZyXwVu9876"
TOKEN_VALUE = "tok-" + "z9" * 8          # a synthetic stand-in, not a credential
FAKE_AWS = r'''#!%(py)s
import json, os, sys
a = sys.argv[1:]
with open(os.path.join(os.environ["FAKE_DIR"], "calls.log"), "a") as fh:
    fh.write(json.dumps(a) + "\n")
if os.environ.get("FAKE_EXPIRED"):
    sys.stderr.write("An error occurred (ExpiredToken) when calling: The security token included in the request is expired\n")
    sys.exit(254)
def opt(n):
    return a[a.index(n) + 1] if n in a else None
svc, verb = a[0], a[1]
if (svc, verb) == ("logs", "start-query"):
    print(json.dumps({"queryId": "q-1"}))
elif (svc, verb) == ("logs", "get-query-results"):
    msg = json.dumps({"attributes": {"modaas.run_id": "%(cid)s", "listener": "llm"}})
    print(json.dumps({"status": "Complete", "results": [[{"field": "@timestamp", "value": "2026-10-06 07:35:10.000"},
                      {"field": "@message", "value": msg}, {"field": "@ptr", "value": "p"}]]}))
elif (svc, verb) == ("logs", "filter-log-events"):
    group = opt("--log-group-name")
    if "aict" in group:
        rec = {"eventName": "InvokeAgentRuntime", "eventID": "e1", "eventTime": "2026-10-06T07:36:30Z",
               "resources": [{"ARN": "%(arn)s"}],
               "responseElements": {"runtimeSessionId": "%(cid)s-" + "a" * 32, "statusCode": 200,
                                    "baggage": "modaas-correlation-id=%(cid)s",
                                    "traceParent": "00-" + "b" * 32 + "-" + "c" * 16 + "-01"}}
        msg = json.dumps(rec)
    else:
        msg = "run %(cid)s started"
    print(json.dumps({"events": [{"timestamp": 1, "ingestionTime": 2, "logStreamName": "s", "message": msg}]}))
elif (svc, verb) == ("cloudwatch", "get-metric-statistics"):
    print(json.dumps({"Label": opt("--metric-name"), "Datapoints": [{"Timestamp": "2026-10-06T07:36:00Z", "Maximum": 11034.0, "Sum": 0.0, "Unit": "Milliseconds"}]}))
else:
    sys.stderr.write("fake aws: unsupported %%r\n" %% a[:2]); sys.exit(2)
'''


class _Ledger(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        type(self).seen.append((self.path, self.headers.get("X-Audit-Token")))
        rows = [{"correlation_id": CID, "step": 1, "phase": "intent", "ts": "2026-10-06T07:35:05Z", "seq": 1},
                {"correlation_id": CID, "step": 2, "phase": "close", "ts": "2026-10-06T07:36:35Z", "seq": 2,
                 "note": "echo " + self.headers.get("X-Audit-Token", "")}]
        body = "".join(json.dumps(r) + "\n" for r in rows).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    fake_dir = tmp_path / "fake"
    (tmp_path / "bin").mkdir()
    fake_dir.mkdir()
    aws = tmp_path / "bin" / "aws"
    aws.write_text(FAKE_AWS % {"py": sys.executable, "cid": CID, "arn": ARN_C})
    aws.chmod(aws.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", "%s%s%s" % (tmp_path / "bin", os.pathsep, os.environ.get("PATH", "")))
    monkeypatch.setenv("FAKE_DIR", str(fake_dir))
    monkeypatch.delenv("FAKE_EXPIRED", raising=False)
    monkeypatch.setenv("LEDGER_TOK", TOKEN_VALUE)
    runtimes = tmp_path / "runtimes.json"
    runtimes.write_text(json.dumps({"ifabric-customer": ARN_C, "ifabric-it": ARN_I}))
    _Ledger.seen = []
    srv = HTTPServer(("127.0.0.1", 0), _Ledger)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield {"tmp": tmp_path, "runtimes": str(runtimes), "out": str(tmp_path / "work"), "calls": fake_dir / "calls.log",
           "ledger": "http://127.0.0.1:%d" % srv.server_address[1]}
    srv.shutdown()


def _calls(env):
    return [json.loads(l) for l in env["calls"].read_text().splitlines()] if env["calls"].exists() else []


def _ctx(env, now, include_test=False, sleeps=None):
    return capture.Ctx(root=env["out"], now=lambda: now, sleep=(sleeps.append if sleeps is not None else (lambda s: None)),
                       include_test=include_test, captured_by="prooflab collect")


def _run(env, extra, now, cid=CID, include_test=False, sleeps=None, capsys=None):
    argv = ["--cid", cid, "--runtimes", env["runtimes"], "--out", env["out"]] + extra
    if include_test:
        argv.append("--include-test")
    code = driver.main(argv, ctx=_ctx(env, now, include_test, sleeps))
    cap = capsys.readouterr() if capsys else None
    out = cap.out if cap else ""
    assert code != 2 or cap is None, cap.err
    return code, (json.loads(out) if out.startswith("{") else None)


def test_all_surfaces_captured_with_sidecars_and_a_per_cid_ledger(env, capsys):
    code, res = _run(env, ["--surfaces", "aws_spans,agentcore_metrics,aict_invocations,ledger_export,runtime_logs",
                           "--start", START, "--end", END, "--token-env", "LEDGER_TOK", "--ledger-url", env["ledger"]],
                     "2026-10-06T08:00:00Z", capsys=capsys)
    assert code == 0, res
    assert [r["surface"] for r in res["results"]] == ["ledger_export", "aws_spans", "agentcore_metrics",
                                                      "aict_invocations", "runtime_logs"]
    assert all(r["status"] == "captured" and r["files"] for r in res["results"])
    for r in res["results"]:
        for f in r["files"]:
            assert os.path.isfile(os.path.join(env["out"], f)) and os.path.isfile(os.path.join(env["out"], f + ".capture.json"))
    assert len(res["results"][2]["files"]) == 4          # 2 runtimes x (Latency Maximum, Errors Sum)
    assert any(f.endswith("raw/runtime-logs/%s/ifabric_it-ZyXwVu9876.jsonl" % CID) for f in res["results"][4]["files"])
    # ledger: one GET, per CID, with the header; the token value is in no written file
    assert [p for p, _t in _Ledger.seen] == ["/api/v1/namespaces/components/services/audit-store:8080/proxy/records?cid=" + CID]
    assert _Ledger.seen[0][1] == TOKEN_VALUE
    for dirpath, _d, names in os.walk(env["out"]):
        for n in names:
            assert TOKEN_VALUE.encode() not in open(os.path.join(dirpath, n), "rb").read()
    # the aict capture keeps the run's record; the metric calls carry the full dimension set and a one-minute period
    metric = [c for c in _calls(env) if c[:2] == ["cloudwatch", "get-metric-statistics"]][0]
    assert "Name=Name,Value=ifabric_customer::DEFAULT" in metric and metric[metric.index("--period") + 1] == "60"


def test_window_comes_from_the_ledger_when_not_given(env, capsys):
    code, res = _run(env, ["--surfaces", "ledger_export,aws_spans", "--token-env", "LEDGER_TOK",
                           "--ledger-url", env["ledger"] + "/api/v1/namespaces/components/services/audit-store:8080/proxy"],
                     "2026-10-06T08:00:00Z", capsys=capsys)
    assert code == 0 and res["window"] == {"start": "2026-10-06T07:35:05.000Z", "end": "2026-10-06T07:36:35.000Z"}
    spans = [c for c in _calls(env) if c[:2] == ["logs", "start-query"]][0]
    assert str(capture.to_epoch("2026-10-06T07:35:05Z")) in spans


def test_not_yet_rules_and_retry_hint(env, capsys):
    now = "2026-10-06T07:37:10Z"                       # end + 30 s
    code, res = _run(env, ["--surfaces", "aws_spans,agentcore_metrics,aict_invocations,runtime_logs",
                           "--start", START, "--end", END], now, capsys=capsys)
    by = {r["surface"]: r for r in res["results"]}
    assert code == driver.EXIT_NOT_YET
    assert by["aws_spans"]["status"] == "not-yet" and by["aws_spans"]["retry_at"] == "2026-10-06T07:37:40.000Z"
    assert by["aict_invocations"]["status"] == "not-yet" and by["aict_invocations"]["retry_at"] == "2026-10-06T07:46:40.000Z"
    assert "--surfaces aict_invocations" in by["aict_invocations"]["hint"] and CID in by["aict_invocations"]["hint"]
    assert by["agentcore_metrics"]["status"] == "captured" and by["runtime_logs"]["status"] == "captured"
    assert not [c for c in _calls(env) if c[:2] in (["logs", "start-query"],)]
    assert not [c for c in _calls(env) if c[:2] == ["logs", "filter-log-events"] and "aict" in " ".join(c)]


def test_metrics_wait_for_the_oc20_delay(env, capsys):
    code, res = _run(env, ["--surfaces", "agentcore_metrics", "--start", START, "--end", END], "2026-10-06T07:36:50Z",
                     capsys=capsys)                    # end + 10 s < 15.5 s
    assert code == driver.EXIT_NOT_YET and res["results"][0]["retry_at"] == "2026-10-06T07:36:55.500Z"
    assert not _calls(env)


def test_wait_sleeps_until_due(env, capsys):
    sleeps = []
    code, res = _run(env, ["--surfaces", "aws_spans", "--start", START, "--end", END, "--wait"],
                     "2026-10-06T07:37:00Z", sleeps=sleeps, capsys=capsys)
    assert code == 0 and res["results"][0]["status"] == "captured"
    assert len(sleeps) == 1 and 39.9 < sleeps[0] < 41.0 + 0.1


def test_test_traffic_skipped_unless_included(env, capsys):
    code, res = _run(env, ["--surfaces", "aws_spans,runtime_logs", "--start", START, "--end", END],
                     "2026-10-06T08:00:00Z", cid=TEST_CID, capsys=capsys)
    assert code == 0 and [r["status"] for r in res["results"]] == ["skipped", "skipped"] and not _calls(env)
    code, res = _run(env, ["--surfaces", "aws_spans", "--start", START, "--end", END], "2026-10-06T08:00:00Z",
                     cid=TEST_CID, include_test=True, capsys=capsys)
    assert code == 0 and res["include_test"] is True and res["results"][0]["status"] == "captured"


def test_expired_credentials_are_an_error_row_not_a_traceback(env, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_EXPIRED", "1")
    code, res = _run(env, ["--surfaces", "aws_spans", "--start", START, "--end", END], "2026-10-06T08:00:00Z", capsys=capsys)
    assert code == driver.EXIT_ERROR and "credentials expired" in res["results"][0]["reason"]


def test_ledger_needs_a_token_variable_and_no_window_is_an_error(env, capsys):
    code, res = _run(env, ["--surfaces", "ledger_export"], "2026-10-06T08:00:00Z", capsys=capsys)
    assert code == driver.EXIT_ERROR and "--token-env" in res["results"][0]["reason"]
    code, res = _run(env, ["--surfaces", "aws_spans"], "2026-10-06T08:00:00Z", capsys=capsys)
    assert code == driver.EXIT_ERROR and "no run window" in res["results"][0]["reason"]


def test_usage_errors(env, capsys):
    base = ["--runtimes", env["runtimes"], "--out", env["out"]]
    assert driver.main(["--cid", CID, "--surfaces", "side_door"] + base) == 2
    assert driver.main(["--cid", "not-a-cid", "--surfaces", "aws_spans"] + base) == 2
    assert driver.main(["--cid", CID, "--runtimes", str(env["tmp"] / "nope.json"), "--out", env["out"]]) == 2
    assert driver.main(["--runtimes", env["runtimes"], "--out", env["out"]]) == 2
    bad = env["tmp"] / "bad.json"
    bad.write_text(json.dumps({"x": "not-an-arn"}))
    assert driver.main(["--cid", CID, "--runtimes", str(bad), "--out", env["out"]]) == 2
    assert driver.main(["--cid", CID, "--start", "yesterday"] + base) == 2


def test_help_lists_the_options_through_the_dispatcher(capsys):
    with pytest.raises(SystemExit) as stop:
        cli.main(["collect", "--help"])
    assert stop.value.code == 0
    text = capsys.readouterr().out
    for flag in ("--cid", "--include-test", "--surfaces", "--runtimes", "--out", "--wait", "--token-env"):
        assert flag in text


def test_there_is_no_full_ledger_get():
    import inspect
    from prooflab.adapters.collectors import ledger_export
    assert "?cid=" in inspect.getsource(ledger_export.records_url)
    with pytest.raises(capture.CaptureError):
        ledger_export.records_url("")
