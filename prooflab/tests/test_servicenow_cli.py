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


def test_notify_rejects_invalid_finding(env, capsys):
    _, finding_file, _ = env
    finding_file.write_text(json.dumps({**FINDING, "verdict": "MAYBE"}))
    assert main(["notify", "--finding", str(finding_file)]) == 2
    assert "verdict" in capsys.readouterr().err
