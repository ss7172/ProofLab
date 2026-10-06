"""PR-12b tests (stubbed subprocess seam; no live call).
Run: $PY39 -m pytest -q -p no:cacheprovider tests/collectors_ph2"""
import json
import os
import re

import pytest

from prooflab.adapters.collectors import (aict_discovery, aict_invocations, capture, gateway_otlp, gateway_stdout,
                                          lambda_codesha, pdp_logs, side_door, supervisor)
from prooflab.contract import finding as finding_mod

NOW = "2026-10-05T18:00:00.000Z"
CID = "ifabric-run-1791137236-102178"
OTHER = "fault-1791179282-8ef1a8"
HEX = "0123456789abcdef0123456789abcdef"
RT = "arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/it_resolution_agent-AbCd"
SIDECAR = ("surface", "path", "command", "scope", "captured_at", "captured_by", "operator", "source_identity",
           "pagination_complete", "line_count", "redactions", "sha256")


def ctx_for(tmp_path, runner):
    return capture.Ctx(root=str(tmp_path), runner=runner, now=lambda: NOW, sleep=lambda s: None,
                       operator="tester", captured_by="prooflab capture@git:test")


def invocation(cid, session, event_time, caller="WSParticipantRole", arn=RT, eid="e1"):
    resp = {"runtimeSessionId": session, "traceParent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01",
            "statusCode": 200}
    if cid:
        resp["baggage"] = "modaas-correlation-id=" + cid
    return json.dumps({"eventName": "InvokeAgentRuntime", "eventTime": event_time, "eventID": eid,
                       "requestParameters": None, "responseElements": resp, "resources": [{"ARN": arn}],
                       "userIdentity": {"arn": "arn:aws:sts::1:assumed-role/%s/x" % caller,
                                        "sessionContext": {"sessionIssuer": {"userName": caller}}}})


def logs_runner(messages):
    def run(argv):
        assert argv[0] == "aws" and argv[1:3] == ["logs", "filter-log-events"]
        return 0, json.dumps({"events": [{"timestamp": i, "ingestionTime": i, "logStreamName": "s", "message": m}
                                         for i, m in enumerate(messages)]}).encode(), b""
    return run


def read_sidecar(tmp_path, sc):
    with open(os.path.join(str(tmp_path), sc["path"] + ".capture.json")) as fh:
        return json.load(fh)


def test_pdp_both_replicas_captured(tmp_path):
    def run(argv):
        if argv[3:5] == ["get", "pods"]:
            return 0, json.dumps({"items": [{"metadata": {"name": "pdp-b"}}, {"metadata": {"name": "pdp-a"}}]}).encode(), b""
        assert argv[3] == "logs"
        return 0, ("line from %s\n" % argv[4]).encode(), b""
    ctx = ctx_for(tmp_path, run)
    scs = pdp_logs.pull(ctx, "app=pdp")
    assert [s["source_identity"]["pod"] for s in scs] == ["pdp-a", "pdp-b"]
    assert all(s["pagination_complete"] and s["source_identity"]["replicas_missing"] == 0 for s in scs)
    assert all(k in read_sidecar(tmp_path, scs[0]) for k in SIDECAR)
    assert scs[0]["path"] == "raw/pdp/pdp/pdp-a.log"


def test_pdp_missing_replica_is_flagged_not_hidden(tmp_path):
    ctx = ctx_for(tmp_path, lambda argv: (0, b"x\n", b""))
    scs = pdp_logs.pull(ctx, "app=pdp", pods=["pdp-a"])
    assert scs[0]["pagination_complete"] is False and scs[0]["source_identity"]["replicas_missing"] == 1


def test_gateway_stdout_keeps_quoted_cid_lines_only(tmp_path):
    ctx = ctx_for(tmp_path, lambda argv: (0, ('a "%s" b\nnoise\n' % CID).encode(), b""))
    scs = gateway_stdout.pull(ctx, CID, "app=gw", pods=["gw-0"])
    with open(os.path.join(str(tmp_path), scs[0]["path"]), "rb") as fh:
        assert fh.read() == ('a "%s" b\n' % CID).encode()
    assert gateway_stdout.pull(ctx, "ifabric-test-1791137236-aaaa", "app=gw", pods=["gw-0"]) is None


def test_gateway_otlp(tmp_path):
    ctx = ctx_for(tmp_path, logs_runner(["trace 1"]))
    sc = gateway_otlp.pull(ctx, "c" * 32, "2026-10-05T17:00:00.000Z", "2026-10-05T17:30:00.000Z")
    assert sc["surface"] == "gateway-otlp" and sc["line_count"] == 1


def test_aict_invocations_exact_join(tmp_path):
    good = invocation(CID, CID + "-" + HEX, "2026-10-05T17:10:00Z", eid="e1")
    other_run = invocation(OTHER, OTHER + "-" + HEX, "2026-10-05T17:11:00Z", eid="e2")
    wrong_session = invocation(CID, "ifabric-run-1-aaaa-" + HEX, "2026-10-05T17:12:00Z", eid="e3")
    model_call = json.dumps({"eventName": "ConverseStream"})
    ctx = ctx_for(tmp_path, logs_runner([other_run, good, wrong_session, model_call]))
    sc = aict_invocations.pull(ctx, [RT], "2026-10-05T17:00:00.000Z", "2026-10-05T17:30:00.000Z")
    assert sc["line_count"] == 3                      # the Converse record is not an invocation
    with open(os.path.join(str(tmp_path), sc["path"])) as fh:
        rows = [json.loads(l) for l in fh]
    j = aict_invocations.join_run(aict_invocations.records(rows), CID)
    assert [m["event_id"] for m in j["matches"]] == ["e1"]
    assert [m["event_id"] for m in j["mismatched"]] == ["e3"]    # baggage without a matching session: never joined
    assert j["matches"][0]["trace_id"] == "a" * 32


def test_aict_retry_same_session_is_surfaced():
    s = CID + "-" + HEX
    recs = aict_invocations.records([invocation(CID, s, "2026-10-05T17:10:00Z", eid="a"),
                                     invocation(CID, s, "2026-10-05T17:10:30Z", eid="b")])
    assert aict_invocations.join_run(recs, CID)["retried_sessions"] == [s]


def test_aict_pull_refused_before_delivery_lag(tmp_path):
    ctx = ctx_for(tmp_path, logs_runner([]))
    with pytest.raises(capture.CaptureError):
        aict_invocations.pull(ctx, [RT], "2026-10-05T17:00:00.000Z", "2026-10-05T17:55:00.000Z")
    assert ctx.calls == []


def test_aict_pull_byte_identical_recapture(tmp_path):
    msgs = [invocation(CID, CID + "-" + HEX, "2026-10-05T17:10:00Z")]
    ctx = ctx_for(tmp_path, logs_runner(msgs))
    a = aict_invocations.pull(ctx, [RT], "2026-10-05T17:00:00.000Z", "2026-10-05T17:30:00.000Z")
    b = aict_invocations.pull(ctx, [RT], "2026-10-05T17:00:00.000Z", "2026-10-05T17:30:00.000Z")
    assert a == b


def test_side_door_flags_foreign_cid_and_no_cid(tmp_path):
    rows = [invocation(CID, CID + "-" + HEX, "2026-10-05T17:10:00Z", eid="ours"),
            invocation(OTHER, OTHER + "-" + HEX, "2026-10-05T17:11:00Z", eid="foreign"),
            invocation(None, "sess-" + HEX, "2026-10-05T17:12:00Z", eid="nocid", caller="IdeRole"),
            invocation(OTHER, OTHER + "-" + HEX, "2026-10-05T17:13:00Z", eid="elsewhere",
                       arn="arn:aws:bedrock-agentcore:us-east-1:1:runtime/other-XyZ")]
    inv = aict_invocations.records([{"message": m} for m in rows])
    flagged = side_door.flag(inv, our_runtime_arns=[RT])
    assert [f["event_id"] for f in flagged] == ["foreign", "nocid"]
    assert flagged[0]["reasons"] == ["cid-not-ours"] and flagged[0]["cid_family"] == "fault"
    assert flagged[1]["label"] == "unattributed:it_resolution_agent-AbCd:2026-10-05T17:12:00Z"
    assert side_door.flag(inv, our_runtime_arns=[RT], ours=[OTHER])[0]["event_id"] == "nocid"
    ctx = ctx_for(tmp_path, lambda argv: pytest.fail("no live call"))
    sc = side_door.pull(ctx, [{"message": m} for m in rows], "2026-10-05T17:00:00Z", "2026-10-05T17:30:00Z",
                        our_runtime_arns=[RT])
    assert sc["line_count"] == 2 and all(k in read_sidecar(tmp_path, sc) for k in SIDECAR)


def test_side_door_flags_foreign_caller():
    inv = aict_invocations.records([{"message": invocation(CID, CID + "-" + HEX, "2026-10-05T17:10:00Z",
                                                           caller="a-02-IdeInstanceRole")}])
    assert side_door.flag(inv, our_callers=["WSParticipantRole"])[0]["reasons"] == ["caller-not-ours"]
    assert side_door.flag(inv, our_callers=["a-02-IdeInstanceRole"]) == []


def test_lambda_codesha_keeps_only_three_fields_and_never_gets_function(tmp_path):
    full = [{"FunctionName": "customer-records", "CodeSha256": "abc=", "LastModified": "2026-10-05T00:00:00.000+0000",
             "Environment": {"Variables": {"SECRET_VALUE": "SYNTH-should-not-land"}}, "Role": "r", "CodeSize": 5}]
    ctx = ctx_for(tmp_path, lambda argv: (0, json.dumps(full).encode(), b""))
    sc = lambda_codesha.pull(ctx)
    text = open(os.path.join(str(tmp_path), sc["path"])).read()
    assert "SYNTH" not in text and "Environment" not in text and "Role" not in text
    assert json.loads(text) == {"FunctionName": "customer-records", "CodeSha256": "abc=",
                                "LastModified": "2026-10-05T00:00:00.000+0000"}
    assert ctx.calls[0][1:3] == ["lambda", "list-functions"]
    forbidden = "get-" + "function"
    assert all(forbidden not in " ".join(c) for c in ctx.calls)
    with pytest.raises(capture.CaptureError):
        capture.run(ctx, ["aws", "lambda", forbidden, "--function-name", "x"])


def test_aict_discovery_filters_by_aict_user(tmp_path):
    def ev(name, user, eid, source="sts.amazonaws.com"):
        return {"CloudTrailEvent": json.dumps({"eventName": name, "eventID": eid, "eventTime": "2026-10-05T17:00:00Z",
                                               "eventSource": source, "userIdentity": {"userName": user}})}
    def run(argv):
        if "AttributeKey=EventName,AttributeValue=AssumeRole" in argv:
            return 0, json.dumps({"Events": [ev("AssumeRole", "aict-user", "1"), ev("AssumeRole", "someone", "2")]}).encode(), b""
        return 0, json.dumps({"Events": [ev("ListAgentRuntimes", "aict-user", "3"), ev("ListAgentRuntimes", "x", "4"),
                                         ev("InvokeAgentRuntime", "aict-user", "5")]}).encode(), b""
    ctx = ctx_for(tmp_path, run)
    sc = aict_discovery.pull(ctx, "aict-user", "2026-10-05T16:00:00Z", "2026-10-05T18:00:00Z")
    with open(os.path.join(str(tmp_path), sc["path"])) as fh:
        got = [json.loads(l)["eventID"] for l in fh]
    assert got == ["1", "3"]


def test_supervisor_expired_token_becomes_monitoring_gap(tmp_path):
    def expired(argv):
        return 255, b"", b"An error occurred (ExpiredToken) when calling the FilterLogEvents operation"
    ctx = ctx_for(tmp_path, expired)
    jobs = [("aict", lambda: aict_invocations.pull(ctx, [RT], "2026-10-05T17:00:00.000Z", "2026-10-05T17:30:00.000Z")),
            ("otlp", lambda: pytest.fail("must be skipped"))]
    res = supervisor.run_jobs(ctx, jobs)
    assert res["skipped"] == ["otlp"] and len(res["gaps"]) == 1
    gap = res["gaps"][0]
    assert gap["kind"] == "monitoring-gap" and finding_mod.validate_finding(gap) == []
    assert os.path.exists(os.path.join(str(tmp_path), "raw/supervisor/run/monitoring-gap.jsonl"))
    assert len(ctx.calls) == 1                       # never retried


def test_supervisor_other_errors_do_not_stop_the_run(tmp_path):
    ctx = ctx_for(tmp_path, lambda argv: (1, b"", b"boom"))
    res = supervisor.run_jobs(ctx, [("a", lambda: capture.run(ctx, ["aws", "x"])), ("b", lambda: "ok")])
    assert res["gaps"] == [] and len(res["errors"]) == 1 and res["done"][0]["job"] == "b"


def test_no_threshold_or_verdict_literals_in_modules():
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(os.path.dirname(os.path.dirname(here)), "prooflab", "adapters", "collectors")
    for name in ("pdp_logs", "gateway_stdout", "gateway_otlp", "aict_invocations", "aict_discovery", "side_door",
                 "lambda_codesha", "supervisor"):
        src = open(os.path.join(d, name + ".py")).read()
        assert not re.search(r"""["'](BREACHED|SATISFIED|INDETERMINATE|ESCALATED)["']""", src), name
