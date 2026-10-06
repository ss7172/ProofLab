"""M2: `humanloop findings --kind escalation` builds one ESC finding per assessed run from the ledger records."""
import json
import os

from prooflab.humanloop import findings as findings_cli
from prooflab.servicenow.finding import finding_from_dict
from prooflab.adapters import human_loop as hl

from hl_support import env_for

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTER = os.path.join(ROOT, "register", "register.yaml")
CID = "ifabric-run-1791177843-a1b2c3"
PILOT = "ifabric-test-1791177843-ffffff"


def _row(cid, kind, control, verdict, phase, rid, rule=None):
    row = {"run.id": cid, "record_id": rid, "record_kind": kind, "control.ref": control, "verdict": verdict,
           "phase": phase, "judgment.disposition": "escalate", "detail": "agent free text; must not be echoed"}
    row["judgment.precedence_rule"] = rule
    return row


def _snapshot(tmp_path, rows):
    d = tmp_path / "snap" / "raw" / "ledger"
    d.mkdir(parents=True)
    (d / "all.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return str(tmp_path / "snap")


def _rows():
    return [
        _row(CID, "judgment", "C7", "RECORDED", "ifabric.judgment", "rec-j1", "maintenance-freeze"),
        _row(CID, "judgment", "ESC", "ESCALATED", "ifabric.escalation", "rec-e1", "maintenance-freeze"),
        _row(CID, "judgment", "ESC", "ESCALATED", "ifabric.escalation", "rec-e2", "restricted-change"),
        _row(PILOT, "judgment", "ESC", "ESCALATED", "ifabric.escalation", "rec-e3", "x"),
        {"run.id": "ifabric-run-1791177999-000000", "record_id": "r9", "control.ref": "C7", "verdict": "RECORDED",
         "phase": "ifabric.judgment"},
    ]


def test_one_esc_finding_per_assessed_run_passes_arth_contract(tmp_path, capsys):
    snap = _snapshot(tmp_path, _rows())
    assert findings_cli.main(["--kind", "escalation", "--snapshot", snap, "--register", REGISTER],
                             env_for(tmp_path / "l.jsonl")) == 0
    listed = json.loads(capsys.readouterr().out)
    assert len(listed) == 1 and listed[0]["action"] == "written"
    data = json.loads(open(listed[0]["file"]).read())
    f = finding_from_dict(data)       # Arth's validator
    assert (f.control_ref, f.control_id, f.scope_kind, f.scope_id, f.verdict, f.kind) == (
        "ESC", "AGENT-ESCALATION", "escalation", CID, "ESCALATED", "escalation")
    from prooflab.registry import parse as P
    assert f.threshold_version == P.parse_register(open(REGISTER).read())["top"]["version"]   # whatever the register says
    assert "maintenance-freeze" in f.summary and "restricted-change" in f.summary and "free text" not in f.summary
    assert f.evidence[:2] == ("ledger:record_id=rec-e1", "ledger:record_id=rec-e2") and "ledger:record_id=rec-j1" in f.evidence
    assert hl.notify_due(data)        # ESCALATED notifies


def test_rerun_keeps_the_file_and_force_rewrites(tmp_path, capsys):
    snap = _snapshot(tmp_path, _rows())
    argv = ["--kind", "escalation", "--snapshot", snap, "--register", REGISTER]
    findings_cli.main(argv, env_for(tmp_path / "l.jsonl"))
    capsys.readouterr()
    findings_cli.main(argv, env_for(tmp_path / "l.jsonl"))
    assert json.loads(capsys.readouterr().out)[0]["action"] == "kept"
    findings_cli.main(argv + ["--force"], env_for(tmp_path / "l.jsonl"))
    assert json.loads(capsys.readouterr().out)[0]["action"] == "written"


def test_cid_flag_and_all_families(tmp_path, capsys):
    snap = _snapshot(tmp_path, _rows())
    argv = ["--kind", "escalation", "--snapshot", snap, "--register", REGISTER]
    findings_cli.main(argv + ["--cid", PILOT], env_for(tmp_path / "l.jsonl"))
    assert len(json.loads(capsys.readouterr().out)) == 1
    findings_cli.main(argv + ["--all-families", "--out", str(tmp_path / "all")], env_for(tmp_path / "l.jsonl"))
    assert len(json.loads(capsys.readouterr().out)) == 2


def test_no_escalation_records_no_findings(tmp_path, capsys):
    snap = _snapshot(tmp_path, [_rows()[0]])
    assert findings_cli.main(["--kind", "escalation", "--snapshot", snap, "--register", REGISTER],
                             env_for(tmp_path / "l.jsonl")) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_no_named_constraint_says_so(tmp_path, capsys):
    snap = _snapshot(tmp_path, [_row(CID, "judgment", "ESC", "ESCALATED", "ifabric.escalation", "rec-e1")])
    findings_cli.main(["--kind", "escalation", "--snapshot", snap, "--register", REGISTER], env_for(tmp_path / "l.jsonl"))
    data = json.loads(open(json.loads(capsys.readouterr().out)[0]["file"]).read())
    assert "no precedence rule fired" in data["summary"]


def test_reads_the_collect_drivers_nested_ledger_capture_too(tmp_path, capsys):
    d = tmp_path / "snap" / "raw" / "ledger" / CID
    d.mkdir(parents=True)
    (d / "records.jsonl").write_text(json.dumps(_row(CID, "judgment", "ESC", "ESCALATED", "ifabric.escalation", "rec-e1", "r")) + "\n")
    (d / "records.jsonl.capture.json").write_text("{}")
    findings_cli.main(["--kind", "escalation", "--snapshot", str(tmp_path / "snap"), "--register", REGISTER],
                      env_for(tmp_path / "l.jsonl"))
    assert len(json.loads(capsys.readouterr().out)) == 1
