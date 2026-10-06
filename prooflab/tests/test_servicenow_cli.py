"""CLI entry point: python -m prooflab.servicenow {selftest,notify,check}."""
from __future__ import annotations

import json

import pytest

from prooflab.servicenow.cli import main
from prooflab.tests.fake_servicenow import CLIENT_ID, CLIENT_SECRET, OWNER_USER, FakeServiceNow

FINDING = {"control_ref": "C16", "control_id": "ACN-COST-001", "threshold_version": "G-FM-v1",
           "scope_kind": "run", "scope_id": "FM-B", "verdict": "BREACHED",
           "summary": "10,800 tokens > cap 10,000", "detected_at": "2026-10-05T10:00:00Z",
           "evidence": ["gateway:action-123"]}


@pytest.fixture()
def env(monkeypatch, tmp_path):
    fake = FakeServiceNow().start()
    monkeypatch.setenv("SNOW_INSTANCE", fake.base_url)
    monkeypatch.setenv("SNOW_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("SNOW_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setenv("SNOW_OWNER_USER", OWNER_USER)
    monkeypatch.setenv("PROOFLAB_DELIVERY_LOG", str(tmp_path / "log.jsonl"))
    finding_file = tmp_path / "finding.json"
    finding_file.write_text(json.dumps(FINDING))
    yield fake, finding_file, tmp_path
    fake.stop()


def test_selftest_succeeds_with_valid_credentials(env, capsys):
    assert main(["selftest"]) == 0
    assert "OK" in capsys.readouterr().out


def test_selftest_fails_cleanly_with_missing_env(monkeypatch, capsys):
    monkeypatch.delenv("SNOW_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("SNOW_INSTANCE", "x")
    monkeypatch.setenv("SNOW_CLIENT_ID", "y")
    assert main(["selftest"]) == 2
    assert "SNOW_CLIENT_SECRET" in capsys.readouterr().err


def test_notify_dry_run_then_real_then_check(env, capsys):
    fake, finding_file, tmp_path = env
    assert main(["notify", "--finding", str(finding_file), "--dry-run"]) == 0
    assert fake.post_count == 0
    assert main(["notify", "--finding", str(finding_file)]) == 0
    assert fake.post_count == 1
    out = capsys.readouterr().out
    assert "DELIVERED" in out and "INC" in out
    assert main(["check", "--finding", str(finding_file), "--cutoff", "2000-01-01T00:00:00Z"]) == 0
    assert "NO_RESPONSE_OBSERVED" in capsys.readouterr().out


def test_export_command_writes_evidence_file(env, capsys):
    fake, finding_file, tmp_path = env
    assert main(["notify", "--finding", str(finding_file)]) == 0
    out_dir = tmp_path / "evidence"
    assert main(["export", "--finding", str(finding_file), "--out", str(out_dir)]) == 0
    files = list(out_dir.glob("INC*.json"))
    assert len(files) == 1 and json.loads(files[0].read_text())["incident"]["number"].startswith("INC")


def test_case_command_prints_case_json_and_writes_snapshot(env, capsys):
    fake, finding_file, tmp_path = env
    assert main(["notify", "--finding", str(finding_file)]) == 0
    capsys.readouterr()
    out_dir = tmp_path / "cases"
    assert main(["case", "--finding", str(finding_file), "--cutoff", "2099-01-01T00:00:00Z",
                 "--out", str(out_dir), "--aict-url", "https://example/aict"]) == 0
    captured = capsys.readouterr()
    case = json.loads(captured.out)
    assert case["schema"] == "ifabric.servicenow.case/v1"
    assert case["servicenow"]["status"] == "ok" and case["response"]["state"] == "AWAITING_RESPONSE"
    assert case["links"]["aict"] == "https://example/aict"
    assert len(list(out_dir.glob("*.json"))) == 1 and "sha256" in captured.err


def test_case_command_reports_unreachable_servicenow_with_exit_1(env, capsys):
    fake, finding_file, _ = env
    fake.stop()
    assert main(["case", "--finding", str(finding_file), "--cutoff", "2099-01-01T00:00:00Z"]) == 1
    assert json.loads(capsys.readouterr().out)["servicenow"]["status"] == "unreachable"


def test_analyze_command_runs_the_nemotron_agent(env, capsys, monkeypatch):
    from prooflab.tests.fake_gateway import FakeGateway, completion
    fake, finding_file, tmp_path = env
    gateway = FakeGateway().start()
    try:
        monkeypatch.setenv("MODAAS_GATEWAY_URL", gateway.base_url)
        monkeypatch.setenv("MODAAS_MODEL_ALIAS", "nemotron-super-120b")
        assert main(["notify", "--finding", str(finding_file)]) == 0
        capsys.readouterr()
        gateway.replies.append(completion("not a note"))
        gateway.replies.append(completion("still not a note"))
        assert main(["analyze", "--finding", str(finding_file), "--out", str(tmp_path / "a")]) == 1
        assert json.loads(capsys.readouterr().out)["state"] == "REFUSED"
    finally:
        gateway.stop()


def test_analyze_command_requires_gateway_settings(env, capsys, monkeypatch):
    _, finding_file, _ = env
    monkeypatch.delenv("MODAAS_GATEWAY_URL", raising=False)
    assert main(["analyze", "--finding", str(finding_file)]) == 2
    assert "MODAAS_GATEWAY_URL" in capsys.readouterr().err


def test_notify_rejects_invalid_finding(env, capsys):
    _, finding_file, _ = env
    finding_file.write_text(json.dumps({**FINDING, "verdict": "MAYBE"}))
    assert main(["notify", "--finding", str(finding_file)]) == 2
    assert "verdict" in capsys.readouterr().err
