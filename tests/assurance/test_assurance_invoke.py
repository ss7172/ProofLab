"""G-03: the laptop invoke helper against a stubbed subprocess (no AWS)."""
import json
import logging
import os
import subprocess

import pytest

from assurance_support import ARN, FakeAwsCli
from prooflab.humanloop import invoke as inv
from prooflab.servicenow.nemotron import AnalyzerError, CallableAnalyzer

MSGS = [{"role": "system", "content": "sys"}, {"role": "user", "content": "the finding"}]
OK = {"text": "NOTE-TEXT-NEVER-LOGGED", "model_id": "nvidia/nemotron-synthetic", "action_id": "act-ok-1",
      "usage": {"total_tokens": 10}, "latency_ms": 12, "finish_reason": "stop"}


def _call(cli, tmp_path, **kw):
    return inv.invoke_assurance(MSGS, arn=ARN, runner=cli, env={"PATH": "/usr/bin"}, tmpdir=str(tmp_path), **kw)


def test_one_call_with_the_required_argv_env_cid_and_session(tmp_path):
    cli = FakeAwsCli(response=OK)
    out = _call(cli, tmp_path)
    assert len(cli.calls) == 1
    call = cli.calls[0]
    argv = call["argv"]
    assert argv[:3] == ["aws", "bedrock-agentcore", "invoke-agent-runtime"]
    assert argv[argv.index("--agent-runtime-arn") + 1] == ARN
    assert argv[argv.index("--cli-read-timeout") + 1] == "300"
    baggage = argv[argv.index("--baggage") + 1]
    cid = baggage.split("=", 1)[1]
    assert baggage.startswith("modaas-correlation-id=ifabric-assure-")
    assert call["payload"] == {"messages": MSGS, "cid": cid}  # the same CID in the payload
    session = argv[argv.index("--runtime-session-id") + 1]
    assert session.startswith(cid + "-") and len(session) >= 33
    assert argv[argv.index("--trace-parent") + 1].startswith("00-")
    assert call["env"]["AWS_MAX_ATTEMPTS"] == "1" and call["env"]["AWS_RETRY_MODE"] == "standard"
    assert call["kw"]["timeout"] > 300
    assert out["text"] == OK["text"] and out["action_id"] == "act-ok-1" and out["cid"] == cid
    assert os.listdir(str(tmp_path)) == []  # the response and payload files are deleted at once


def test_fresh_cid_and_session_per_call(tmp_path):
    cli = FakeAwsCli(response=OK)
    _call(cli, tmp_path)
    _call(cli, tmp_path)
    s = [c["argv"][c["argv"].index("--runtime-session-id") + 1] for c in cli.calls]
    assert s[0] != s[1]


def test_timeout_is_unavailable_and_never_reinvoked(tmp_path):
    cli = FakeAwsCli(exc=subprocess.TimeoutExpired(["aws"], 330))
    with pytest.raises(AnalyzerError) as err:
        _call(cli, tmp_path)
    assert err.value.kind == "unavailable" and "never re-invoked" in str(err.value)
    assert len(cli.calls) == 1
    assert os.listdir(str(tmp_path)) == []


def test_cli_read_timeout_exit_is_unavailable_once(tmp_path):
    cli = FakeAwsCli(returncode=255, stderr="Read timeout on endpoint URL")
    with pytest.raises(AnalyzerError) as err:
        _call(cli, tmp_path)
    assert err.value.kind == "unavailable" and "timeout" in str(err.value)
    assert len(cli.calls) == 1 and os.listdir(str(tmp_path)) == []


def test_blocked_keeps_the_action_id(tmp_path):
    cli = FakeAwsCli(response={"error": "blocked", "action_id": "act-blk-7"})
    with pytest.raises(AnalyzerError) as err:
        _call(cli, tmp_path)
    assert err.value.kind == "blocked" and err.value.action_id == "act-blk-7"


def test_other_runtime_errors_and_garbage_are_unavailable(tmp_path):
    for response in ({"error": "unavailable", "action_id": None}, {"error": "bad_response"}, "not json", "[1]"):
        with pytest.raises(AnalyzerError) as err:
            _call(FakeAwsCli(response=response), tmp_path)
        assert err.value.kind == "unavailable"
    assert os.listdir(str(tmp_path)) == []


def test_the_kits_output_wrapper_is_unwrapped(tmp_path):
    out = _call(FakeAwsCli(response={"output": OK}), tmp_path)
    assert out["action_id"] == "act-ok-1"


def test_no_arn_means_no_call(tmp_path, monkeypatch):
    monkeypatch.delenv(inv.ARN_ENV, raising=False)
    cli = FakeAwsCli(response=OK)
    with pytest.raises(AnalyzerError) as err:
        inv.invoke_assurance(MSGS, runner=cli, tmpdir=str(tmp_path))
    assert err.value.kind == "unavailable" and cli.calls == []


def test_a_non_assurance_cid_is_refused():
    with pytest.raises(ValueError):
        inv.build_argv(ARN, "s" * 40, "/p", "/o", "ifabric-run-1-abcd", "00-a-b-01")


def test_the_text_is_never_logged_or_printed(tmp_path, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    _call(FakeAwsCli(response=OK), tmp_path)
    captured = capsys.readouterr()
    assert "NOTE-TEXT-NEVER-LOGGED" not in captured.out + captured.err + caplog.text


def test_callable_analyzer_wiring(tmp_path):
    analyzer = inv.assurance_analyzer(arn=ARN, runner=FakeAwsCli(response=OK), tmpdir=str(tmp_path))
    assert isinstance(analyzer, CallableAnalyzer)
    assert analyzer.backend == "agentcore:ifabric_assurance_agent"
    assert analyzer.model_alias == "nemotron-super-120b"
    reply = analyzer.analyze(MSGS)
    assert reply.action_id == "act-ok-1" and reply.finish_reason == "stop" and reply.usage == {"total_tokens": 10}
    assert json.dumps(reply.usage)
