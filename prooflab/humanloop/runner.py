"""`prooflab humanloop notify` (G-05, Phase 1: notify only). Stdlib, 3.9.

    prooflab humanloop notify --finding F.json [--finding G.json ...] [--findings-dir DIR] [--dry-run]

Per batch: selftest (read-only) first; then, for each finding that is notify-due and whose id is new in its
log, Arth's `notify`. Findings of kind `approval` go to their own absolute log (never the main one) and
are never analysed. Environment names are in config.py; PROOFLAB_DELIVERY_LOG must be absolute.

Process guards for the two accepted upstream bugs:
  (a) a dry-run on an existing incident logs DELIVERED, not DRY_RUN  -> --dry-run is refused unless the
      target log is under a `wiring-tests/` directory;
  (b) a journal read of 0 rows can yield a false NO_RESPONSE_OBSERVED -> `sticky_response` (human_loop.py)
      is the only way this package reads a response: a logged RESPONDED is never overwritten.
Exit codes (as Arth's CLI): 0 ok, 1 ServiceNow problem, 2 bad input or configuration.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Callable, List, Mapping, Optional

from prooflab.adapters import human_loop as hl
from prooflab.humanloop import config as cfg
from prooflab.servicenow.client import ServiceNowClient, ServiceNowError
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.servicenow.notifier import notify

EXIT_OK, EXIT_SERVICENOW, EXIT_INPUT = 0, 1, 2
SELFTEST_QUERY = "ifabric:selftest"   # the same read-only probe as Arth's `selftest`


def selftest(client, integration_user: str) -> None:
    """Read-only: an OAuth token is issued and the incident API answers. Raises ServiceNowError."""
    client.find_incidents(SELFTEST_QUERY, integration_user)


def _load(paths: List[str], directory: Optional[str]) -> List[dict]:
    files = list(paths)
    if directory:
        files += sorted(glob.glob(os.path.join(directory, "*.json")))
    if not files:
        raise ValueError("give at least one --finding or a --findings-dir with *.json files")
    out = []
    for path in files:
        with open(path, encoding="utf-8") as handle:
            out.append(json.load(handle))
    return out


def run_batch(findings: List[dict], client, config: cfg.HumanLoopConfig, dry_run: bool = False) -> List[dict]:
    """Notify the due, new findings. Returns one result row per input finding. Never re-sends."""
    rows: List[dict] = []
    seen = set()
    for data in findings:
        finding = finding_from_dict(data)            # Arth's validator; ValueError on a bad finding
        fid = finding.finding_id
        row = {"finding_id": fid, "kind": finding.kind, "verdict": finding.verdict}
        if not hl.notify_due(data):
            rows.append({**row, "action": "skipped", "reason": "not notify-due"})
            continue
        if hl.is_approval(data):
            if not config.approval_log:
                raise cfg.ConfigError("%s is required to notify an approval finding" % cfg.ENV_APPROVAL_LOG)
            log_path = config.approval_log
        else:
            log_path = config.delivery_log
        if dry_run and not cfg.under_wiring_tests(log_path):
            raise cfg.ConfigError("--dry-run refused: guard (a), the log %r is not under %s/"
                                  % (log_path, cfg.WIRING_TESTS_DIR))
        log = DeliveryLog(log_path)
        if (log_path, fid) in seen or log.history(fid):
            rows.append({**row, "action": "skipped", "reason": "not a new finding id", "log": log_path})
            continue
        seen.add((log_path, fid))
        result = notify(finding, client, log, owner_user=config.owner_user,
                        integration_user=config.integration_user, dry_run=dry_run)
        rows.append({**row, "action": "notified", "state": result.state, "number": result.number,
                     "reused": result.reused, "reason": result.reason, "log": log_path})
    return rows


def _ph2(args, config, findings, client_factory, analyzer_factory) -> int:
    """The Phase 2 verbs: check, snapshot, export, analyze, mirror (T6.5 Ph2, T6.6)."""
    from prooflab.humanloop import analysis, check_loop, mirror, snapshots
    if args.command == "mirror":
        records = mirror.mirror_file(config.delivery_log)
        if config.approval_log and os.path.exists(config.approval_log):
            records += mirror.mirror_file(config.approval_log, {r["record_id"] for r in records})
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        existing = set()
        if os.path.exists(args.out):
            with open(args.out, encoding="utf-8") as handle:
                existing = {json.loads(l)["record_id"] for l in handle if l.strip()}
        new = [r for r in records if r["record_id"] not in existing]
        with open(args.out, "a", encoding="utf-8") as handle:
            for rec in new:
                handle.write(json.dumps(rec, sort_keys=True) + "\n")
        print(json.dumps({"mirrored": len(new), "already": len(records) - len(new)}))
        return EXIT_OK
    client = client_factory() if client_factory else ServiceNowClient.from_env()
    if args.command == "check":
        passes = check_loop.run_loop(findings, client, config, args.cutoff, interval_s=args.interval,
                                     max_passes=1 if args.once else None)
        print(json.dumps(passes[-1], indent=2, sort_keys=True))
        bad = [r for r in passes[-1] if r.get("state") in ("NOT_DELIVERED", "RESPONSE_UNKNOWN")]
        return EXIT_SERVICENOW if bad else EXIT_OK
    if args.command == "snapshot":
        rows = snapshots.snapshot_cases(findings, client, config, args.cutoff, args.out)
        print(json.dumps(rows, indent=2, sort_keys=True))
        return EXIT_SERVICENOW if any(r["servicenow"] == "unreachable" for r in rows) else EXIT_OK
    if args.command == "export":
        retests = {}
        for path in sorted(glob.glob(os.path.join(args.closures, "*-closure.json"))) if args.closures else ():
            with open(path, encoding="utf-8") as handle:       # written by `humanloop retest`
                doc = json.load(handle)
            retests[doc["finding_id"]] = doc["retest"]
        result = snapshots.export_all(findings, client, config, args.out, retests=retests or None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return EXIT_OK
    if args.command == "analyze":
        analyzer = analyzer_factory() if analyzer_factory else None
        if analyzer is None:
            from prooflab.humanloop.invoke import assurance_analyzer
            analyzer = assurance_analyzer()
        rows = analysis.analyze_between_runs(findings, client, config, analyzer,
                                             run_active=lambda: args.run_active, out_dir=args.out)
        print(json.dumps(rows, indent=2, sort_keys=True))
        return EXIT_OK
    return EXIT_INPUT


def main(argv: Optional[List[str]] = None, env: Optional[Mapping[str, str]] = None,
         client_factory: Optional[Callable[[], object]] = None,
         analyzer_factory: Optional[Callable[[], object]] = None) -> int:
    if argv and argv[0] == "findings":          # D4: build Finding files from the snapshot's BREACHED assessments
        from prooflab.humanloop import findings as _findings
        return _findings.main(argv[1:], env)
    if argv and argv[0] == "retest":            # M1: link a passing re-test to its incident and record the closure
        from prooflab.humanloop import retest as _retest
        return _retest.main(argv[1:], env, client_factory)
    parser = argparse.ArgumentParser(prog="prooflab humanloop", description="human loop: notify",
                                     epilog="also: `findings` (build Finding files from a snapshot: --kind breach|"
                                            "escalation) and `retest` (close a finding with a passing re-test run); "
                                            "each has its own --help")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("findings", help="build Finding files from a snapshot (--kind breach|escalation)")
    sub.add_parser("retest", help="link a passing re-test run to the finding's incident and record the closure")
    notify_p = sub.add_parser("notify", help="selftest, then notify new notify-due findings")
    notify_p.add_argument("--finding", action="append", default=[], help="finding JSON file (repeatable)")
    notify_p.add_argument("--findings-dir", help="directory of finding *.json files")
    notify_p.add_argument("--dry-run", action="store_true",
                          help="refused unless the delivery log is under wiring-tests/ (guard a)")
    for name, helptext in (("check", "check loop: poll each open finding (<= 60 s) until the cutoff"),
                           ("snapshot", "write Arth's case view per finding"),
                           ("export", "export each incident as evidence JSON"),
                           ("analyze", "Assurance analysis, only between subject runs"),
                           ("mirror", "delivery log -> notification records (JSONL)")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--finding", action="append", default=[], help="finding JSON file (repeatable)")
        p.add_argument("--findings-dir", help="directory of finding *.json files")
        if name in ("check", "snapshot"):
            p.add_argument("--cutoff", required=True, help="ISO-8601 UTC response cutoff")
        if name == "check":
            p.add_argument("--interval", type=float, default=60, help="seconds between passes (capped at 60)")
            p.add_argument("--once", action="store_true", help="one pass, then the cutoff rule")
        if name in ("snapshot", "export", "analyze", "mirror"):
            p.add_argument("--out", required=True, help="output directory (file for mirror)")
        if name == "export":
            p.add_argument("--closures", help="directory of `humanloop retest` closure files: a closed incident "
                                              "with a passing re-test is then not a 'closed without re-test' gap")
        if name == "analyze":
            p.add_argument("--run-active", action="store_true", help="a subject run is active: defer")
    args = parser.parse_args(argv)
    try:
        config = cfg.HumanLoopConfig.from_env(env)
        findings = [] if args.command == "mirror" and not (args.finding or args.findings_dir) \
            else _load(args.finding, args.findings_dir)
        if args.command != "notify":
            return _ph2(args, config, findings, client_factory, analyzer_factory)
        if args.dry_run and not cfg.under_wiring_tests(config.delivery_log):
            raise cfg.ConfigError("--dry-run refused: guard (a), the log %r is not under %s/"
                                  % (config.delivery_log, cfg.WIRING_TESTS_DIR))
        client = client_factory() if client_factory else ServiceNowClient.from_env()
        selftest(client, config.integration_user)    # before each batch, before anything is logged
        rows = run_batch(findings, client, config, dry_run=args.dry_run)
    except ServiceNowError as err:
        print("error: %s" % err, file=sys.stderr)
        return EXIT_SERVICENOW
    except (ValueError, OSError, LookupError) as err:   # ConfigError is a ValueError
        print("error: %s" % err, file=sys.stderr)
        return EXIT_INPUT
    print(json.dumps(rows, indent=2, sort_keys=True))
    bad = [r for r in rows if r["action"] == "notified" and r["state"] not in ("DELIVERED", "DRY_RUN")]
    return EXIT_SERVICENOW if bad else EXIT_OK
