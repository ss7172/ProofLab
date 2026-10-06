import json
import os

import pytest

from prooflab.adapters.platform_ops import deploy_wrapper, live_lane, pause_log
from prooflab.contract import record as R

CID = "ifabric-test-1791260000-ab12cd"
NOW = "2026-10-06T04:30:00.000Z"


def test_deploy_wrapper_emits_valid_ep10_record_without_env_values():
    patch = {"spec": {"awsAgentCore": {"environmentVariables": {"IFABRIC_PIN_JSON": "{...}", "IFABRIC_PIN_SHA256": "a" * 64}}}}
    rec = deploy_wrapper.record_deploy("pin", "ifabric-customer", patch, "agentconfig/ifabric-customer patched",
                                       "pre-authorized (5.2 row 11)", CID, now=NOW, mode="observe", pin_sha256="a" * 64)
    assert R.validate_record(rec) == [] and rec["ep.id"] == "EP-10" and rec["record_kind"] == "action"
    d = json.loads(rec["detail"])
    assert d["env_keys"] == ["IFABRIC_PIN_JSON", "IFABRIC_PIN_SHA256"] and d["deploy"] == "pin"
    assert "{...}" not in rec["detail"]


def test_deploy_wrapper_withholds_secret_shaped_answer():
    answer = "LEDGER_" + "TOKEN=" + "abcdef123456"
    rec = deploy_wrapper.record_deploy("mode", "ifabric-it", {"spec": {}}, answer, "Hold-3", CID, now=NOW, mode="enforce")
    assert "abcdef123456" not in json.dumps(rec) and json.loads(rec["detail"])["answer_withheld"] is True
    assert R.validate_record(rec) == []


def test_render_patch_command_uses_hk():
    cmd = deploy_wrapper.render_patch_command("ifabric-it", "/tmp/p.json")
    assert cmd.startswith("~/firstmate-homes/TrustworthyAI/workshop-local/bin/hk ") and "--dry-run=server" in cmd


def test_pause_log_records_request():
    rec = pause_log.record_pause("agentconfig", "ifabric-it", "pause", "Hold-4", CID, "2026-10-06T04:29:58Z", now=NOW)
    assert R.validate_record(rec) == [] and rec["ep.id"] == "EP-8"
    assert "runtime stays READY" in rec["detail"]
    with pytest.raises(ValueError):
        pause_log.record_pause("pod", "x", "pause", "a", CID, "t")


def test_live_lane_line_fields_and_no_secret(tmp_path):
    path = str(tmp_path / "live-lane-log.jsonl")
    line = live_lane.append(path, action="S-2 smoke", authority="pre-authorized", cid=CID, tokens_before=0,
                            tokens_after=8200, time=NOW)
    assert set(line) == set(live_lane.FIELDS)
    assert json.loads(open(path).read()) == line
    with pytest.raises(ValueError):
        live_lane.log_line("x", "y", ledger_token="abc")
    with pytest.raises(ValueError):
        live_lane.log_line("x", "y", note="LEDGER_" + "TOKEN=abcdef123")
    assert not any("token" in k and k not in ("tokens_before", "tokens_after") for k in line)


def test_conditions_sha256sums_cover_four_texts():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    names = sorted(l.split()[1] for l in open(os.path.join(root, "register/conditions/SHA256SUMS")))
    assert names == ["conflicting-context.txt", "encoded-attack.txt", "prompt-attack.txt", "tool-directive.txt"]
