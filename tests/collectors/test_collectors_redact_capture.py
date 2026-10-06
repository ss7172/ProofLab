"""PR-12a tests: T-REDACT-01, sidecars, byte-identical re-capture, exact-value scan, seam rules.
Run: PYTHONPATH=<PR-01 worktree>:<this worktree> $PY39 -m pytest -q -p no:cacheprovider tests/collectors
(conftest.py also finds PR-01's worktree by itself, override with PR01_ROOT)."""
import hashlib
import json
import os
import re
import subprocess

import pytest

from prooflab.adapters.collectors import (agentcore_metrics, aws_spans, capture, cr_status, ledger_export,
                                          modaas_evidence, runtime_logs)
from prooflab.store import redact

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
CID = "ifabric-run-1791137236-102178"
# the synthetic secret values living in the CR fixture (fake; labelled SYNTH)
SECRETS = {"ledger-token": "SYNTH-ledgerTokenValue-0123456789abcdefAB",
           "gateway-key": "SYNTH-gatewayKeyValue-0123456789abcdefAB",
           "stray": "SYNTH0ledger0Token0Value0aB1cD2eF3gH4iJ5"}
NOW = "2026-10-05T18:00:00.000Z"


def _ctx(tmp_path, runner):
    return capture.Ctx(root=str(tmp_path), runner=runner, now=lambda: NOW, sleep=lambda s: None,
                       operator="tester", captured_by="prooflab capture@git:test")


def _read(name):
    with open(os.path.join(FIX, name), "rb") as fh:
        return fh.read()


def _tree_text(root):
    out = ""
    for d, _, fs in os.walk(root):
        for f in fs:
            out += open(os.path.join(d, f), "rb").read().decode("utf-8", "replace")
    return out


def _cr_runner(argv):
    assert argv[0] == "kubectl" and "get" in argv
    return 0, _read("cr-list.synthetic.json"), b""


def test_t_redact_01_cr_three_token_paths(tmp_path):
    sc = cr_status.pull(_ctx(tmp_path, _cr_runner))
    body = open(os.path.join(str(tmp_path), sc["path"])).read()
    for label, value in SECRETS.items():
        assert value not in body, label
    assert redact.scan_tree(str(tmp_path), SECRETS) == []
    doc = json.loads(body)
    agent = doc["items"][0]
    assert "environmentVariables" not in agent["spec"]["awsAgentCore"]
    assert agent["spec"]["awsAgentCore"]["runtimeName"] == "ifabric_subject"       # the rest survives
    assert agent["metadata"]["annotations"] == {"ifabric/note": "kept"}
    assert agent["status"]["imageDigest"].startswith("sha256:")                       # digests are evidence
    paths = [(d["cr"], d["path"]) for d in sc["dropped"]]
    assert ("AgentConfig/ifabric-subject", "spec.awsAgentCore.environmentVariables") in paths
    assert ("AgentConfig/ifabric-subject", "metadata.annotations[kubectl.kubernetes.io/last-applied-configuration]") in paths
    assert ("AgentConfig/ifabric-subject", "metadata.annotations[kopf.zalando.org/last-handled-configuration]") in paths
    assert ("ToolConfig/ifabric-tool", "metadata.annotations[kubectl.kubernetes.io/last-applied-configuration]") in paths
    assert {r["rule"] for r in sc["redactions"]} >= {"cr-token-path", "token-shaped"}
    side = json.load(open(os.path.join(str(tmp_path), sc["path"] + ".capture.json")))
    assert side["dropped"] == sc["dropped"]
    assert not any(v in json.dumps(side) for v in SECRETS.values())


def test_sidecar_fields_and_sha(tmp_path):
    sc = cr_status.pull(_ctx(tmp_path, _cr_runner))
    for f in capture.SIDECAR_FIELDS:
        assert f in sc, f
    data = open(os.path.join(str(tmp_path), sc["path"]), "rb").read()
    assert sc["sha256"] == hashlib.sha256(data).hexdigest()
    assert sc["captured_at"] == NOW and sc["pagination_complete"] is True
    assert sc["command"].startswith("kubectl -n components get")


def test_byte_identical_recapture_of_derived_fixture(tmp_path):
    ledger = _read("ledger-%s.jsonl" % CID)
    fetch = lambda url, headers: (200, ledger)
    a, b = tmp_path / "a", tmp_path / "b"
    sa = ledger_export.pull(_ctx(a, None), CID, "SYNTH-ledgerTokenValue-0123456789abcdefAB", fetch)
    sb = ledger_export.pull(_ctx(b, None), CID, "SYNTH-ledgerTokenValue-0123456789abcdefAB", fetch)
    for rel in (sa["path"], sa["path"] + ".capture.json"):
        r = subprocess.run(["cmp", str(a / rel), str(b / rel)])
        assert r.returncode == 0
    assert open(str(a / sa["path"]), "rb").read() == ledger                 # captured exactly (nothing to redact)
    # a re-capture into the SAME root keeps the file; a changed source becomes a new .r2 file
    ledger_export.pull(_ctx(a, None), CID, "SYNTH-ledgerTokenValue-0123456789abcdefAB", fetch)
    assert not os.path.exists(str(a / sa["path"]) + ".r2")
    sc2 = ledger_export.pull(_ctx(a, None), CID, "SYNTH-ledgerTokenValue-0123456789abcdefAB",
                             lambda u, h: (200, ledger + b'{"x":1}\n'))
    assert sc2["path"].endswith(".r2")


def test_ledger_per_cid_only_and_token_never_written(tmp_path):
    seen = []
    token = SECRETS["ledger-token"]

    def fetch(url, headers):
        seen.append((url, headers))
        return 200, ('{"detail":"echo %s"}\n' % token).encode()

    sc = ledger_export.pull(_ctx(tmp_path, None), CID, token, fetch)
    assert seen[0][0].endswith("/proxy/records?cid=" + CID) and seen[0][1] == {"X-Audit-Token": token}
    assert token not in _tree_text(str(tmp_path))
    assert redact.scan_tree(str(tmp_path), {"t": token}) == []
    with pytest.raises(capture.CaptureError):
        ledger_export.records_url("")
    assert ledger_export.pull(_ctx(tmp_path, None), "ifabric-test-1791137236-aaaaaa", token, fetch) is None
    assert len(seen) == 1
    with pytest.raises(capture.CaptureError):
        ledger_export.pull(_ctx(tmp_path, None), "not-a-run", token, fetch)
    assert sc["scope"] == {"cid": CID}


def test_exact_value_scan_clean_and_dirty(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "ok.txt").write_text("nothing here")
    assert redact.scan_tree(str(tmp_path), SECRETS) == []
    (tmp_path / "x" / "bad.txt").write_text("v=" + SECRETS["gateway-key"])
    import base64
    (tmp_path / "x" / "b64.txt").write_bytes(base64.b64encode(SECRETS["stray"].encode()))
    hits = redact.scan_tree(str(tmp_path), SECRETS)
    assert [(h["path"], h["label"]) for h in hits] == [("x/b64.txt".replace("/", os.sep), "stray"),
                                                      ("x/bad.txt".replace("/", os.sep), "gateway-key")]
    assert SECRETS["gateway-key"] not in json.dumps(hits)
    with pytest.raises(ValueError):
        redact.scan_tree(str(tmp_path), {"short": "abc"})


def _frag(*parts):
    return "".join(parts)


def test_text_rules_union_of_arth_six_and_ours():
    akid = _frag("AK", "IA", "ABCDEFGHIJKLMNOP")
    urltok = _frag("?tk", "n=", "abc123def456")
    text = "\n".join([
        "authorization=Bearer abc.def.ghi",
        "key " + akid,
        "http://cockpit.example/x" + urltok,
        "GET /x?X-Amz-Signature=deadbeef01",
        "OPENAI_API_KEY=sk-live-value",
        "reply <think>private chain</think> done",
        "gen_ai.usage.input_tokens=5290",
        _frag("aws_", "secret_access_key", "=zzzz1234"),
    ])
    out, counts = redact.redact_text(text)
    for leak in ("abc.def.ghi", akid, "abc123def456", "deadbeef01", "sk-live-value", "private chain", "zzzz1234"):
        assert leak not in out, leak
    assert "gen_ai.usage.input_tokens=5290" in out                                   # counts are not secrets
    assert set(counts) >= set(redact.ARTH_RULES) - {"span-content"} | {"presigned-url"}
    assert redact.redact_text(out) == (out, {})                                      # idempotent
    assert set(redact.ARTH_RULES) <= set(redact.ALL_RULES)


def test_span_content_dropped_and_insights_cells(tmp_path):
    span = {"name": "chat", "attributes": {"gen_ai.usage.input_tokens": 5},
            "events": [{"name": "m", "attributes": {"content": "customer record 555-0100", "role": "user"}}]}
    rows = [{"@timestamp": "t", "@message": json.dumps(span)},
            {"field": "AUDIT_WRITE_TOKEN", "value": "SYNTH-ledgerTokenValue-0123456789abcdefAB"},
            {"field": "attributes.gen_ai.usage.input_tokens", "value": "5290"}]
    clean, counts, _ = redact.redact_obj(rows)
    s = json.dumps(clean)
    assert "customer record" not in s and SECRETS["ledger-token"] not in s
    assert '"5290"' in s and counts["span-content"] == 1


def test_aws_spans_via_stubbed_insights(tmp_path):
    calls = []
    span = {"attributes": {"modaas.run_id": CID, "listener": "llm", "gen_ai.usage.input_tokens": 100},
            "events": [{"attributes": {"content": "SECRET PROMPT"}}]}
    results = {"status": "Complete", "results": [[{"field": "@timestamp", "value": "2026-10-05 17:00:00.000"},
                                                  {"field": "@message", "value": json.dumps(span)},
                                                  {"field": "@ptr", "value": "p1"}]]}

    def runner(argv):
        calls.append(argv)
        if "start-query" in argv:
            return 0, b'{"queryId":"q-1"}', b""
        return 0, json.dumps(results).encode(), b""

    ctx = _ctx(tmp_path, runner)
    sc = aws_spans.pull(ctx, CID, "2026-10-05T17:00:00Z", "2026-10-05T17:30:00Z")
    body = open(os.path.join(str(tmp_path), sc["path"])).read()
    assert "SECRET PROMPT" not in body and "@ptr" not in body and "gen_ai.usage.input_tokens" in body
    assert 'attributes.modaas.run_id = "%s"' % CID in sc["scope"]["query"]
    assert sc["source_identity"]["log_group"] == "aws/spans" and sc["pagination_complete"] is True
    assert aws_spans.pull(ctx, "ifabric-test-1791137236-aaaaaa", "2026-10-05T17:00:00Z", "2026-10-05T17:30:00Z") is None


def test_paginated_log_collectors_and_metrics(tmp_path):
    pages = [{"events": [{"timestamp": 1, "ingestionTime": 2, "logStreamName": "s", "message": "a " + CID}],
              "nextToken": "n1"},
             {"events": [{"timestamp": 3, "ingestionTime": 4, "logStreamName": "s", "message": "b " + CID}]}]
    seen = []

    def runner(argv):
        seen.append(argv)
        if "get-metric-statistics" in argv:
            return 0, b'{"Label":"Latency","Datapoints":[]}', b""
        return 0, json.dumps(pages[1 if "--next-token" in argv else 0]).encode(), b""

    ctx = _ctx(tmp_path, runner)
    sc = runtime_logs.pull(ctx, "rt-abc", CID, "2026-10-05T17:00:00Z", "2026-10-05T17:30:00Z")
    assert sc["line_count"] == 2 and sc["pagination_complete"] is True and sc["source_identity"]["pages"] == 2
    assert "/aws/bedrock-agentcore/runtimes/rt-abc-DEFAULT" in sc["command"]
    sc = modaas_evidence.pull(ctx, CID, "2026-10-05T17:00:00Z", "2026-10-05T17:30:00Z")
    assert sc["line_count"] == 2 and "/modaas/evidence" in sc["command"]
    m = agentcore_metrics.pull_all(ctx, ["rt-abc"], "2026-10-05T16:00:00Z", "2026-10-05T17:00:00Z")
    assert len(m) == 2 and open(os.path.join(str(tmp_path), m[0]["path"]), "rb").read() == b'{"Label":"Latency","Datapoints":[]}'
    assert m[0]["scope"]["statistic"] == "Maximum" and m[0]["scope"]["dimensions"]
    with pytest.raises(capture.CaptureError):                                          # open hour
        agentcore_metrics.pull(ctx, "rt-abc", "Latency", "Maximum", "2026-10-05T17:00:00Z", "2026-10-05T19:00:00Z")


def test_seam_rules_and_no_forbidden_verbs(tmp_path):
    ctx = _ctx(tmp_path, lambda argv: (0, b"{}", b""))
    for argv in (["curl", "http://x"], ["aws", "lambda", "get" + "-function", "--function-name", "f"],
                 ["aws", "bedrock-agentcore-control", "get-agent" + "-runtime"]):
        with pytest.raises(capture.CaptureError):
            capture.run(ctx, argv)
    assert ctx.calls == []                                                             # never reached the seam
    exp = _ctx(tmp_path, lambda argv: (254, b"", b"ExpiredTokenException: expired"))
    with pytest.raises(capture.ExpiredTokenError):
        capture.run(exp, ["aws", "sts", "get-caller-identity"])
    # nothing the collectors wrote could hold a runtime description: no collector issues that verb at all
    src = ""
    cdir = os.path.join(os.path.dirname(os.path.dirname(HERE)), "prooflab", "adapters", "collectors")
    for f in os.listdir(cdir):
        if f.endswith(".py") and f != "capture.py":
            src += open(os.path.join(cdir, f)).read()
    assert "agent" + "-runtime" not in src.replace("bedrock-agentcore", "")
    assert not re.search(r"\b(get|describe)-agent", src)
