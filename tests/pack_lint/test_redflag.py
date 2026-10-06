"""PR-49: the red-flag lint over a staged pack. One clean fixture passes; one mutation per rule fails it.

Fixtures are built in tmp_path from one clean template; secret-shaped strings are assembled at runtime."""
import json
import os
import subprocess
import sys

import pytest

from prooflab.pack import redflag

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CID = "ifabric-run-1000000000-aaaaaa"
START = "2026-10-06T13:56:15.236Z"

REG_TOP = """# test register
version: %(v)s
version_date: "%(f)s"
supersedes: %(s)s
status: FROZEN
frozen_at: "%(f)s"
controls:
  - control_id: "16"
"""


def _w(root, rel, data):
    path = os.path.join(str(root), *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(data if isinstance(data, str) else json.dumps(data, indent=1))


def _r(root, rel):
    with open(os.path.join(str(root), *rel.split("/"))) as fh:
        return json.load(fh)


def _answer(verdict="SATISFIED", value=22271, limit=25000):
    return {
        "schema": "ifabric.answer/v1",
        "control": {"ref": "C16"},
        "scope": {"kind": "run", "id": CID, "cid": CID, "start": START},
        "verdict": {"value": verdict, "label": verdict, "reason": "measured %s vs limit <= %s tokens" % (value, limit)},
        "measurement": {"value": value, "unit": "tokens"},
        "comparison": {"limit": limit, "operator": "<=", "within_limit": True, "exceptions_count": 0,
                       "exceptions_allowed": 0.0},
        "exceptions": [],
        "rule": {"register_version": "v2", "date_before_scope": True, "approval": {"status": "APPROVED", "ref": "x:y"}},
        "audit_question": {"decision": {"outcome": "ALLOWED", "text": "control test SATISFIED"},
                           "under_whose_authority": {"text": "register owner o@example.com; approved"}},
        "source": {"manifest_status": "OK"},
    }


def _assessment():
    return {"control_ref": "C16", "scope_kind": "run", "scope_id": CID, "scope_start": "2026-10-06T13:56:25.033Z",
            "requirement_verdict": "SATISFIED", "operation": "OPERATED", "deficiency": "none",
            "measured": {"total_tokens": 22271, "cap": 25000},
            "finding": {"summary": "C16 run %s: 22271 tokens, cap 25000, under cap by 2729" % CID,
                        "verdict": "SATISFIED"}}


@pytest.fixture
def pack(tmp_path):
    root = tmp_path / "pack"
    _w(root, "register/versions/v2.yaml", REG_TOP % {"v": "v2", "f": "2026-10-06T13:36:43Z", "s": "v1"})
    _w(root, "register/superseded/v1.yaml", REG_TOP % {"v": "v1", "f": "2026-10-06T12:39:29Z", "s": "v0"})
    _w(root, "register/versions/v2.head.json", {"LastModified": "2026-10-06T13:36:44+00:00", "VersionId": "abc"})
    _w(root, "register/approval-finding.json", {"version": "v2", "kind": "finding", "control_ref": "REG"})
    _w(root, "run-ids.txt", CID + "\n")
    _w(root, "derived/run-catalogue.jsonl", json.dumps({"run_id": CID, "label": "LIVE_SUBJECT", "assessed": True,
                                                         "tokens_in": 20000, "tokens_out": 2271}) + "\n")
    _w(root, "assessments/C16/%s.json" % CID, _assessment())
    _w(root, "answers/C16_run_%s.json" % CID, _answer())
    _w(root, "auditor/%s.json" % CID, {"questions": {"integrity": {"answer": "MANIFEST.json verified (OK)"}}})
    _w(root, "MANIFEST.json", {"files": {"run-ids.txt": "0" * 64}})
    _w(root, "README.md", "# Pack\n\nRuns: `run-ids.txt`, answers in `answers/`, query `prooflab query --run <CID>`.\n"
                          "`named-runs.md` (not in this pack)\n")
    _w(root, "pack-index.json", {
        "schema": "ifabric.pack-index/v1",
        "integrity": {"status": "VERIFIED", "files": 10},
        "register": {"version": "v2", "approval": {"status": "APPROVED"}},
        "runs": [{"cid": CID, "started_at": START, "verdicts": {"C16": "SATISFIED"}}],
        "answers": [{"control_ref": "C16", "scope": CID, "verdict": "SATISFIED"}],
        "claim": {"controls": [{"ref": "C16", "verdict_overall": "SATISFIED"}]},
        "named_runs": {"entries": [{"control": "C16", "scope": {"cid": CID}}]},
        "findings": [{"control_ref": "C16", "scope_id": CID,
                      "summary": "C16 run %s: 22271 tokens, cap 25000, under cap by 2729" % CID}],
    })
    return root


def _rules(root):
    return sorted(set(f.rule for f in redflag.lint(str(root))))


def _edit(root, rel, fn):
    doc = _r(root, rel)
    fn(doc)
    _w(root, rel, doc)


ANS = "answers/C16_run_%s.json" % CID


def test_clean_pack_passes(pack):
    assert redflag.lint(str(pack)) == []
    assert redflag.main([str(pack)]) == 0


def test_r1_false_dated_after_when_head_missing(pack):
    os.remove(str(pack / "register/versions/v2.head.json"))
    _edit(pack, ANS, lambda d: d["rule"].update(date_before_scope=False))
    found = [f for f in redflag.lint(str(pack)) if f.rule.startswith("R1")]
    assert found and all(f.rule == "R1" for f in found) and "not in the pack" in found[0].hint


def test_r1_text_flagged_even_with_proof(pack):
    _edit(pack, ANS, lambda d: d["audit_question"].update(decision={"outcome": "ALLOWED",
                                                                   "text": "RULE DATED AFTER TEST"}))
    found = [f for f in redflag.lint(str(pack)) if f.rule.startswith("R1")]
    assert found and found[0].rule == "R1" and "FALSE" in found[0].hint


def test_r1_true_when_head_after_scope(pack):
    _w(pack, "register/versions/v2.head.json", {"LastModified": "Tue, 06 Oct 2026 14:30:00 GMT"})
    _edit(pack, ANS, lambda d: d["rule"].update(date_before_scope=False))
    assert "R1-TRUE" in _rules(pack)
    assert redflag.main([str(pack)]) == 2


def test_r2_approval_missing_but_evidence_present(pack):
    _edit(pack, ANS, lambda d: d["rule"].update(approval={"status": "MISSING"}))
    found = [f for f in redflag.lint(str(pack)) if f.rule == "R2"]
    assert found and "FALSE" in found[0].hint and "approval-finding.json" in found[0].hint


def test_r2_approval_missing_and_evidence_omitted(pack):
    os.remove(str(pack / "register/approval-finding.json"))
    _edit(pack, "pack-index.json", lambda d: d["register"].update(approval={"status": "MISSING"}))
    found = [f for f in redflag.lint(str(pack)) if f.rule == "R2"]
    assert found and "omitted" in found[0].hint


def test_r3_not_assessed_with_definite_assessment(pack):
    _edit(pack, "pack-index.json", lambda d: d["claim"]["controls"][0].update(verdict_overall="NOT_ASSESSED"))
    _edit(pack, ANS, lambda d: d["verdict"].update(value="INDETERMINATE"))
    assert "R3" in _rules(pack)


def test_r4_shown_register_not_chain_head(pack):
    _edit(pack, "pack-index.json", lambda d: d["register"].update(version="v1"))
    assert "R4" in _rules(pack)


def test_r4_head_by_supersedes_not_name_sort(pack):
    # v10 supersedes v2: a text sort would pick v2 as the latest; the chain says v10
    _w(pack, "register/versions/v10.yaml", REG_TOP % {"v": "v10", "f": "2026-10-06T14:00:00Z", "s": "v2"})
    found = [f for f in redflag.lint(str(pack)) if f.rule == "R4"]
    assert any("head of the frozen chain is v10" in f.hint for f in found)


def test_r5_named_run_not_live_subject_and_undeclared_run(pack):
    rows = [{"run_id": CID, "label": "EXPLORATORY", "assessed": True},
            {"run_id": "ifabric-run-2-bbbbbb", "label": "OURS-ROLE-UNDECLARED", "assessed": False}]
    _w(pack, "derived/run-catalogue.jsonl", "\n".join(json.dumps(r) for r in rows) + "\n")
    texts = [f.text for f in redflag.lint(str(pack)) if f.rule == "R5"]
    assert any("EXPLORATORY" in t for t in texts) and any("OURS-ROLE-UNDECLARED" in t for t in texts)


def test_r5_cid_listed_twice(pack):
    rows = [{"run_id": CID, "label": "LIVE_SUBJECT"}, {"run_id": CID, "label": "LIVE_SUBJECT"}]
    _w(pack, "derived/run-catalogue.jsonl", "\n".join(json.dumps(r) for r in rows) + "\n")
    assert "R5" in _rules(pack)


def test_r6_answer_number_differs_from_assessment(pack):
    _edit(pack, ANS, lambda d: d["measurement"].update(value=21000))
    assert "R6" in _rules(pack)


def test_r6_catalogue_tokens_contradict_c16(pack):
    _w(pack, "derived/run-catalogue.jsonl", json.dumps({"run_id": CID, "label": "LIVE_SUBJECT", "tokens_in": 37974,
                                                        "tokens_out": 1925}) + "\n")
    assert "R6" in _rules(pack)


def test_r7_placeholder_and_missing_file(pack):
    _w(pack, "README.md", "# Pack\nWindow <WINDOW_START> .. see `security-matrix.md` and `prooflab query <CID>`\n")
    texts = [f.text for f in redflag.lint(str(pack)) if f.rule == "R7"]
    assert "<WINDOW_START>" in texts and "security-matrix.md" in texts and not any("<CID>" in t for t in texts)


def test_r8_integrity_banner_vs_manifest(pack):
    _edit(pack, "pack-index.json", lambda d: d.update(integrity={"status": "UNVERIFIED", "files": 0}))
    _w(pack, "auditor/%s.json" % CID, {"questions": {"integrity": {"answer": "MANIFEST.json missing (gap)"}}})
    assert len([f for f in redflag.lint(str(pack)) if f.rule == "R8"]) == 2


def test_r8_satisfied_with_exceptions_and_degraded_operation(pack):
    def ans(d):
        d["comparison"]["exceptions_count"] = 1
        d["exceptions"] = [{"kind": "model-span-after-halt"}]
        d["audit_question"]["decision"] = {"outcome": "STOPPED", "text": "control test SATISFIED; a call was DENIED"}
    _edit(pack, ANS, ans)
    _edit(pack, "assessments/C16/%s.json" % CID, lambda d: d.update(operation="DEGRADED", deficiency="operation"))
    hints = " ".join(f.hint for f in redflag.lint(str(pack)) if f.rule == "R8")
    assert "exception" in hints and "halted" in hints and "deficiency" in hints


def test_r8_negative_headroom_wording(pack):
    _edit(pack, "assessments/C16/%s.json" % CID,
          lambda d: d["finding"].update(summary="C16 run x: 22271 tokens, cap 25000, headroom -2729"))
    assert "R8" in _rules(pack)


def test_r9_secret_shaped_string_in_records(pack):
    fake = "AK" + "IA" + "Q" * 16
    _w(pack, "records/%s/ev.json" % CID, {"detail": "leaked " + fake})
    found = [f for f in redflag.lint(str(pack)) if f.rule == "R9"]
    assert found and fake not in found[0].line()


def test_r9_unredacted_token_field(pack):
    _w(pack, "store/records.jsonl", json.dumps({"ledger": {"write_token": "z" * 8 + "9" * 24}}) + "\n")
    assert "R9" in _rules(pack)


def test_r9_redacted_token_field_passes(pack):
    _w(pack, "store/records.jsonl", json.dumps({"ledger": {"write_token": "REDACTED"}}) + "\n")
    assert redflag.lint(str(pack)) == []


def test_shipped_source_is_not_scanned(pack):
    _w(pack, "prooflab/console/static/app.js", 'spill("RULE DATED AFTER TEST"); spill("approval MISSING")')
    assert redflag.lint(str(pack)) == []


def test_cli_verb_exit_codes(pack, tmp_path):
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
    run = lambda d: subprocess.run([sys.executable, "-m", "prooflab", "pack", "lint", d], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert run(str(pack)).returncode == 0
    _edit(pack, ANS, lambda d: d["rule"].update(date_before_scope=False))
    p = run(str(pack))
    assert p.returncode == 2 and p.stdout.startswith("R1")
    assert run(str(tmp_path / "nope")).returncode == 1


def test_submit_wrapper_refuses_a_flagged_pack(pack, tmp_path, monkeypatch):
    monkeypatch.delenv("PROOFLAB_PACK_LINT", raising=False)
    scan = tmp_path / "scan.sh"
    scan.write_text('echo "RESULT: clean"; exit 0\n')
    man = tmp_path / "manifest.py"
    man.write_text("import sys; sys.exit(0)\n")
    sub = tmp_path / "submit.sh"
    sub.write_text("echo SUBMITTED\n")
    env = dict(os.environ, PROOFLAB_PYTHON=sys.executable, PROOFLAB_REPO=REPO, PROOFLAB_MANIFEST_PY=str(man),
               PROOFLAB_PREPUSH_SCAN=str(scan), SUBMIT_SH=str(sub))
    env.pop("PROOFLAB_PACK_LINT", None)
    cmd = ["bash", os.path.join(REPO, "tools", "submit_wrapper.sh"), "--dry-run", "--evidence", str(pack)]
    ok = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert ok.returncode == 0 and "pack lint clean" in ok.stdout and "DRY-RUN" in ok.stdout
    _edit(pack, ANS, lambda d: d["rule"].update(approval={"status": "MISSING"}))
    bad = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert bad.returncode != 0 and "REFUSED: pack lint" in bad.stderr and "DRY-RUN" not in bad.stdout
