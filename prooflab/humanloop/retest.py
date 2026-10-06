"""`prooflab humanloop retest` (M1): the re-test closure verb. Stdlib, Python 3.9.

    prooflab humanloop retest --finding <id|file> --retest-run <cid> [--assessment F.json | --snapshot DIR]
                              [--findings-dir DIR] [--out DIR] [--dry-run]

A finding is closed only by a re-test: the re-test run's assessment of the SAME control and scope kind is SATISFIED
under the SAME register version (`human_loop.closes`, R-J-24). Anything else is refused (exit 2) and nothing is
written. On success the verb (1) writes the one-line re-test link note on the finding's incident through the
integration user (`client.add_work_note`, the same path Arth's notify and the analysis note use), (2) appends
`RETEST_LINKED` to the finding's delivery log (the production log is PROOFLAB_DELIVERY_LOG; --dry-run is refused on
it, guard (a): a dry run writes nothing, and only a log under wiring-tests/ may be named with it), and (3) writes the
closure evidence `<out>/<finding file>-closure.json` ({"closed_by": "retest", "retest_cid": ...}).
A repeat of the same re-test writes no second note.
Exit: 0 ok, 1 ServiceNow problem, 2 refused or bad input.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from typing import Optional

from prooflab.adapters import human_loop as hl
from prooflab.contract import clocks as _clocks
from prooflab.humanloop import config as cfg
from prooflab.servicenow.client import ServiceNowClient, ServiceNowError
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict

STATE = "RETEST_LINKED"
EXIT_OK, EXIT_SERVICENOW, EXIT_REFUSED = 0, 1, 2


class Refused(ValueError):
    """The re-test does not close the finding (or an input is unusable)."""


def locate_finding(ref: str, findings_dir: Optional[str]):
    """(path, finding dict) from a file path or a finding id found in `findings_dir`."""
    candidates = [ref] if os.path.isfile(ref) else []
    if not candidates and findings_dir:
        candidates = sorted(glob.glob(os.path.join(findings_dir, "*.json")))
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if finding_from_dict(data).finding_id == ref or path == ref:
                return path, data
        except (OSError, ValueError, TypeError):
            continue
    raise Refused("no finding %r (give its file, or its id with --findings-dir)" % ref)


def load_assessment(path: Optional[str], snapshot: Optional[str], finding: dict, cid: str) -> dict:
    if not path:
        if not snapshot:
            raise Refused("give --assessment FILE or --snapshot DIR (assessments/<control>/<cid>.json)")
        path = os.path.join(snapshot, "assessments", finding["control_ref"], "%s.json" % cid.replace(":", "_"))
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as err:
        raise Refused("cannot read the re-test assessment %s: %s" % (path, err))


def check_closes(finding: dict, assessment: dict, retest_cid: str, at: Optional[str] = None) -> dict:
    """The retest block, or Refused naming the first rule the re-test fails."""
    if assessment.get("control_ref") != finding.get("control_ref"):
        raise Refused("re-test assessment is for control %s, the finding is %s" % (
            assessment.get("control_ref"), finding.get("control_ref")))
    if assessment.get("scope_kind") != finding.get("scope_kind"):
        raise Refused("re-test assessment scope kind %s differs from the finding's %s" % (
            assessment.get("scope_kind"), finding.get("scope_kind")))
    if finding.get("scope_kind") == "run":
        if assessment.get("scope_id") != retest_cid:
            raise Refused("re-test assessment is for run %s, not --retest-run %s" % (assessment.get("scope_id"), retest_cid))
        if retest_cid == finding.get("scope_id"):
            raise Refused("the re-test run must differ from the finding's own run %s" % retest_cid)
    block = hl.build_retest(assessment, at)
    if block is None:
        raise Refused("re-test assessment has no finding verdict (%s)" % assessment.get("requirement_verdict"))
    if block["threshold_version"] != finding.get("threshold_version"):
        raise Refused("re-test is under register version %s, the finding is under %s" % (
            block["threshold_version"], finding.get("threshold_version")))
    if not hl.closes(finding, block):
        raise Refused("re-test verdict is %s, not SATISFIED: the finding stays open" % block["verdict"])
    return block


def _sys_id(history, client, finding, integration_user):
    for entry in reversed(history):
        if entry.get("state") == "DELIVERED" and entry.get("sys_id"):
            return entry["sys_id"]
    rows = client.find_incidents(finding.finding_id, integration_user)
    if rows:
        return rows[0]["sys_id"]
    raise Refused("finding %s has no delivered incident to link" % finding.finding_id)


def closure_record(finding: dict, fid: str, retest: dict, retest_cid: str, note: str, number=None) -> dict:
    return {"finding_id": fid, "control_ref": finding["control_ref"], "scope_kind": finding["scope_kind"],
            "scope_id": finding["scope_id"], "threshold_version": finding["threshold_version"],
            "closed_by": "retest", "retest_cid": retest_cid, "retest": retest,
            "incident": number, "note": note, "closed_at": retest.get("at")}


def run(finding_ref, retest_cid, config: cfg.HumanLoopConfig, client, findings_dir=None, assessment_path=None,
        snapshot=None, out_dir=None, dry_run=False, now=None) -> dict:
    path, data = locate_finding(finding_ref, findings_dir)
    finding = finding_from_dict(data)
    fid = finding.finding_id
    log_path = config.approval_log if hl.is_approval(data) and config.approval_log else config.delivery_log
    if dry_run and not cfg.under_wiring_tests(log_path):
        raise cfg.ConfigError("--dry-run refused: guard (a), the log %r is not under %s/" % (log_path, cfg.WIRING_TESTS_DIR))
    assessment = load_assessment(assessment_path, snapshot, data, retest_cid)
    retest = check_closes(data, assessment, retest_cid, now or _clocks.now_utc())
    note = hl.retest_note(dict(data, id=fid), retest)
    if not out_dir:
        out_dir = os.path.join(snapshot or os.path.dirname(os.path.abspath(path)), "closures")
    target = os.path.join(out_dir, "%s-closure.json" % os.path.splitext(os.path.basename(path))[0])
    row = {"finding_id": fid, "retest_cid": retest_cid, "note": note, "closure_file": target}
    if dry_run:
        return {**row, "action": "dry-run", "closed": False}
    log = DeliveryLog(log_path)
    history = log.history(fid)
    done = [e for e in history if e.get("state") == STATE and e.get("retest_cid") == retest_cid
            and e.get("retest_assessment") == retest["assessment"]]
    number = None
    if done:
        action, number = "already-linked", done[-1].get("number")
    else:
        client.find_incidents("ifabric:selftest", config.integration_user)   # read-only selftest, as notify does
        sys_id = _sys_id(history, client, finding, config.integration_user)
        client.add_work_note(sys_id, note)
        number = next((e.get("number") for e in reversed(history) if e.get("number")), None)
        log.append(fid, STATE, sys_id=sys_id, number=number, retest_cid=retest_cid,
                   retest_assessment=retest["assessment"], note_digest=hashlib.sha256(note.encode("utf-8")).hexdigest())
        action = "linked"
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.exists(target):
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(closure_record(data, fid, retest, retest_cid, note, number), indent=1, sort_keys=True))
    return {**row, "action": action, "closed": True}


def main(argv=None, env=None, client_factory=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab humanloop retest", description=__doc__.split("\n\n")[0])
    ap.add_argument("--finding", required=True, help="finding file, or its id (with --findings-dir)")
    ap.add_argument("--retest-run", required=True, help="the re-test run's CID")
    ap.add_argument("--assessment", help="the re-test run's assessment JSON")
    ap.add_argument("--snapshot", help="snapshot DIR: assessments/<control>/<cid>.json when --assessment is absent")
    ap.add_argument("--findings-dir", help="where to look the finding id up (default: <snapshot>/findings)")
    ap.add_argument("--out", help="closure evidence directory (default: <snapshot>/closures)")
    ap.add_argument("--dry-run", action="store_true", help="check and print the note; write nothing (wiring-tests/ log only)")
    args = ap.parse_args(argv)
    try:
        config = cfg.HumanLoopConfig.from_env(env)
        fdir = args.findings_dir or (os.path.join(args.snapshot, "findings") if args.snapshot else None)
        client = None if args.dry_run else (client_factory() if client_factory else ServiceNowClient.from_env())
        result = run(args.finding, args.retest_run, config, client, findings_dir=fdir, assessment_path=args.assessment,
                     snapshot=args.snapshot, out_dir=args.out, dry_run=args.dry_run)
    except ServiceNowError as err:
        print("error: %s" % err, file=sys.stderr)
        return EXIT_SERVICENOW
    except (ValueError, OSError, LookupError) as err:    # Refused, ConfigError
        print("refused: %s" % err, file=sys.stderr)
        return EXIT_REFUSED
    print(json.dumps(result, indent=2, sort_keys=True))
    return EXIT_OK
