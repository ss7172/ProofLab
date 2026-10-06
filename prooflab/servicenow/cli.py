"""Command line for the human loop.

  python -m prooflab.servicenow selftest
  python -m prooflab.servicenow notify --finding finding.json [--dry-run]
  python -m prooflab.servicenow check  --finding finding.json --cutoff 2026-10-06T14:00:00Z
  python -m prooflab.servicenow export --finding finding.json [--out evidence/servicenow/incidents]
  python -m prooflab.servicenow analyze --finding finding.json [--force]   (Nemotron assurance agent)
  python -m prooflab.servicenow case   --finding finding.json --cutoff ... [--out evidence/servicenow/cases]
  python -m prooflab.servicenow serve  --finding a.json [--finding b.json] --cutoff ... [--port 8765]

Environment:
  SNOW_INSTANCE, SNOW_CLIENT_ID, SNOW_CLIENT_SECRET   (required)
  SNOW_OWNER_USER        owner who is assigned the incident (default annapurna@invences.com)
  SNOW_INTEGRATION_USER  OAuth app user, ignored when detecting responses (default ifabric.integration)
  SNOW_AGENT_USER        ServiceNow agent's AI user, never counted as a response (default ifabric.assurance.agent)
  SNOW_AICT_URL          optional link to the AI Control Tower view shown in the case panel
  MODAAS_GATEWAY_URL, MODAAS_MODEL_ALIAS, MODAAS_API_KEY (optional)   for `analyze` (Nemotron via modaas-agw)
  PROOFLAB_DELIVERY_LOG  JSONL evidence log (default evidence/servicenow/delivery-log.jsonl)
Exit codes: 0 ok, 1 ServiceNow problem, 2 bad input or configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from prooflab.servicenow.case_view import case_view, write_case_snapshot
from prooflab.servicenow.client import ServiceNowClient, ServiceNowError
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import Finding, finding_from_dict
from prooflab.servicenow.notifier import (DEFAULT_AGENT_USER, check_response, export_incident,
                                          notify)

DEFAULT_OWNER = "annapurna@invences.com"
DEFAULT_INTEGRATION_USER = "ifabric.integration"
DEFAULT_LOG = "evidence/servicenow/delivery-log.jsonl"
DEFAULT_EXPORT_DIR = "evidence/servicenow/incidents"
DEFAULT_PORT = 8765
EXIT_OK, EXIT_SERVICENOW, EXIT_INPUT = 0, 1, 2


def _load_finding(path: str) -> Finding:
    with open(path, encoding="utf-8") as handle:
        return finding_from_dict(json.load(handle))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m prooflab.servicenow",
                                     description="iFabric ProofLab -> ServiceNow human loop")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest", help="get an OAuth token and read one incident")
    notify_p = sub.add_parser("notify", help="open (or reuse) the incident for a finding")
    notify_p.add_argument("--finding", required=True, help="finding JSON file")
    notify_p.add_argument("--dry-run", action="store_true", help="log the payload, write nothing")
    check_p = sub.add_parser("check", help="record the owner's response or silence")
    check_p.add_argument("--finding", required=True, help="finding JSON file")
    check_p.add_argument("--cutoff", required=True, help="ISO-8601 UTC time after which silence is final")
    export_p = sub.add_parser("export", help="save the incident and its notes as evidence JSON")
    export_p.add_argument("--finding", required=True, help="finding JSON file")
    export_p.add_argument("--out", default=DEFAULT_EXPORT_DIR, help="output directory")
    case_p = sub.add_parser("case", help="print the GUI case JSON (read-only)")
    case_p.add_argument("--finding", required=True, help="finding JSON file")
    case_p.add_argument("--cutoff", required=True, help="ISO-8601 UTC response cutoff")
    case_p.add_argument("--out", help="also save a snapshot here and print its sha256")
    case_p.add_argument("--aict-url", default=os.environ.get("SNOW_AICT_URL"))
    analyze_p = sub.add_parser("analyze", help="run the Nemotron assurance agent on the finding's incident")
    analyze_p.add_argument("--finding", required=True, help="finding JSON file")
    analyze_p.add_argument("--force", action="store_true", help="analyze even if a note exists")
    analyze_p.add_argument("--out", default="evidence/servicenow/assurance-agent",
                           help="evidence directory for the run record")
    serve_p = sub.add_parser("serve", help="local read-only case panel on 127.0.0.1")
    serve_p.add_argument("--finding", required=True, action="append", help="finding JSON file")
    serve_p.add_argument("--cutoff", required=True, help="ISO-8601 UTC response cutoff")
    serve_p.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_p.add_argument("--aict-url", default=os.environ.get("SNOW_AICT_URL"))
    return parser


def _settings() -> dict:
    return {"owner_user": os.environ.get("SNOW_OWNER_USER", DEFAULT_OWNER),
            "integration_user": os.environ.get("SNOW_INTEGRATION_USER", DEFAULT_INTEGRATION_USER),
            "agent_user": os.environ.get("SNOW_AGENT_USER", DEFAULT_AGENT_USER)}


def _case(args, client: ServiceNowClient, log: DeliveryLog, users: dict) -> int:
    case = case_view(_load_finding(args.finding), client, log, cutoff=args.cutoff,
                     aict_url=args.aict_url, **users)
    print(json.dumps(case, indent=2, sort_keys=True))
    if args.out:
        path, digest = write_case_snapshot(case, args.out)
        print(f"OK: wrote {path} sha256={digest}", file=sys.stderr)
    return EXIT_SERVICENOW if case["servicenow"]["status"] == "unreachable" else EXIT_OK


def _serve(args, client: ServiceNowClient, log: DeliveryLog, users: dict) -> int:
    from prooflab.servicenow.serve import serve_forever  # http.server only needed here
    findings = [_load_finding(path) for path in args.finding]
    serve_forever(lambda: [case_view(f, client, log, cutoff=args.cutoff,
                                     aict_url=args.aict_url, **users) for f in findings],
                  port=args.port)
    return EXIT_OK


def _analyze(args, client: ServiceNowClient, log: DeliveryLog, users: dict) -> int:
    from prooflab.servicenow.assurance_agent import run_assurance_agent
    from prooflab.servicenow.nemotron import GatewayAnalyzer
    analyzer = GatewayAnalyzer.from_env()
    outcome = run_assurance_agent(_load_finding(args.finding), client, log, analyzer,
                                  owner_user=users["owner_user"],
                                  integration_user=users["integration_user"],
                                  agent_user=users["agent_user"], out_dir=args.out, force=args.force)
    print(json.dumps({**outcome.__dict__, "evidence_path": str(outcome.evidence_path or "")}, indent=2))
    return EXIT_OK if outcome.state in ("WRITTEN", "SKIPPED") else EXIT_SERVICENOW


def _run(args, client: ServiceNowClient, log: DeliveryLog) -> int:
    users = _settings()
    if args.command == "case":
        return _case(args, client, log, users)
    if args.command == "analyze":
        return _analyze(args, client, log, users)
    if args.command == "serve":
        return _serve(args, client, log, users)
    finding = _load_finding(args.finding)
    if args.command == "notify":
        result = notify(finding, client, log, owner_user=users["owner_user"],
                        integration_user=users["integration_user"], dry_run=args.dry_run)
        print(json.dumps(result.__dict__, indent=2))
        return EXIT_OK if result.state in ("DELIVERED", "DRY_RUN") else EXIT_SERVICENOW
    if args.command == "export":
        print(f"OK: wrote {export_incident(finding, client, users['integration_user'], args.out, log)}")
        return EXIT_OK
    outcome = check_response(finding, client, log, cutoff=args.cutoff, **users)
    print(json.dumps(outcome.__dict__, indent=2))
    return EXIT_SERVICENOW if outcome.state in ("NOT_DELIVERED", "RESPONSE_UNKNOWN") else EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        client = ServiceNowClient.from_env()
        log = DeliveryLog(os.environ.get("PROOFLAB_DELIVERY_LOG", DEFAULT_LOG))
        if args.command == "selftest":
            client.find_incidents("ifabric:selftest", _settings()["integration_user"])
            print(f"OK: OAuth token issued and incident API readable at {client.base_url}")
            return EXIT_OK
        return _run(args, client, log)
    except (ValueError, OSError, LookupError, json.JSONDecodeError) as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_INPUT
    except ServiceNowError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_SERVICENOW
