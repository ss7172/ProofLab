"""Command line for the human loop.

  python -m prooflab.servicenow selftest
  python -m prooflab.servicenow notify --finding finding.json [--dry-run]
  python -m prooflab.servicenow check  --finding finding.json --cutoff 2026-10-06T14:00:00Z
  python -m prooflab.servicenow export --finding finding.json [--out evidence/servicenow/incidents]

Environment:
  SNOW_INSTANCE, SNOW_CLIENT_ID, SNOW_CLIENT_SECRET   (required)
  SNOW_OWNER_USER        owner who is assigned the incident (default annapurna@invences.com)
  SNOW_INTEGRATION_USER  OAuth app user, ignored when detecting responses (default ifabric.integration)
  PROOFLAB_DELIVERY_LOG  JSONL evidence log (default evidence/servicenow/delivery-log.jsonl)
Exit codes: 0 ok, 1 ServiceNow problem, 2 bad input or configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from prooflab.servicenow.client import ServiceNowClient, ServiceNowError
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import Finding, finding_from_dict
from prooflab.servicenow.notifier import check_response, export_incident, notify

DEFAULT_OWNER = "annapurna@invences.com"
DEFAULT_INTEGRATION_USER = "ifabric.integration"
DEFAULT_LOG = "evidence/servicenow/delivery-log.jsonl"
DEFAULT_EXPORT_DIR = "evidence/servicenow/incidents"
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
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        client = ServiceNowClient.from_env()
        log = DeliveryLog(os.environ.get("PROOFLAB_DELIVERY_LOG", DEFAULT_LOG))
        owner = os.environ.get("SNOW_OWNER_USER", DEFAULT_OWNER)
        integration_user = os.environ.get("SNOW_INTEGRATION_USER", DEFAULT_INTEGRATION_USER)
        if args.command == "selftest":
            client.find_incidents("ifabric:selftest", integration_user)
            print(f"OK: OAuth token issued and incident API readable at {client.base_url}")
            return EXIT_OK
        finding = _load_finding(args.finding)
        if args.command == "notify":
            result = notify(finding, client, log, owner_user=owner,
                            integration_user=integration_user, dry_run=args.dry_run)
            print(json.dumps(result.__dict__, indent=2))
            return EXIT_OK if result.state in ("DELIVERED", "DRY_RUN") else EXIT_SERVICENOW
        if args.command == "export":
            path = export_incident(finding, client, integration_user, args.out)
            print(f"OK: wrote {path}")
            return EXIT_OK
        outcome = check_response(finding, client, log, owner_user=owner,
                                 integration_user=integration_user, cutoff=args.cutoff)
        print(json.dumps(outcome.__dict__, indent=2))
        return EXIT_SERVICENOW if outcome.state in ("NOT_DELIVERED", "RESPONSE_UNKNOWN") else EXIT_OK
    except (ValueError, OSError, LookupError, json.JSONDecodeError) as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_INPUT
    except ServiceNowError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_SERVICENOW
