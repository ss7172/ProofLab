"""LIVE ServiceNow round-trip test of the Assurance Agent's write path, with a TEST stand-in instead of Nemotron.

No model is called. The stand-in echoes the FACTS from the real prompt (like a perfect model) and fills
the judged fields deterministically; the note is labelled "TEST stand-in (no model)". Everything else is
the production code path against the real instance, as ifabric.integration, on test incident INC0010232.

Run from the project root, with SNOW_INSTANCE / SNOW_CLIENT_ID / SNOW_CLIENT_SECRET (and SSL_CERT_FILE) set:
    .venv/bin/python tools/sn_roundtrip_test.py
Prints only test data (no secrets). Exit code 0 = every check passed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prooflab.servicenow.analysis import ANALYSIS_MARKER, MODEL_FIELDS, split_journal  # noqa: E402
from prooflab.servicenow.assurance_agent import run_assurance_agent  # noqa: E402
from prooflab.servicenow.case_view import case_view, display_text  # noqa: E402
from prooflab.servicenow.client import ServiceNowClient  # noqa: E402
from prooflab.servicenow.delivery_log import DeliveryLog  # noqa: E402
from prooflab.servicenow.finding import finding_from_dict  # noqa: E402
from prooflab.servicenow.nemotron import CallableAnalyzer  # noqa: E402
from prooflab.servicenow.notifier import check_response, notify  # noqa: E402

OWNER = "annapurna@invences.com"
INTEGRATION = "ifabric.integration"
FINDING_FILE = ROOT / "prooflab/servicenow/examples/test_finding_agent.json"
OUT = ROOT / "evidence/servicenow/wiring-tests/assurance-agent-roundtrip"
FAR_CUTOFF = "2099-01-01T00:00:00Z"
SECTIONS = ("movement", "decision_trace", "evidence", "policy_alignment", "outcome_validation")
COMPUTED = ("Agent path", "Policy alignment", "Validation", "Model")


def stand_in(messages):
    """Echo the FACTS block exactly and fill the 3 judged fields; no model involved."""
    prompt = messages[-1]["content"]
    facts_block = prompt.split("FACTS (copy exactly):\n", 1)[1].split("\nEVIDENCE:", 1)[0]
    facts = dict(line.split(": ", 1) for line in facts_block.splitlines())
    evidence = prompt.split("EVIDENCE: ", 1)[1].split("\n", 1)[0]
    values = {**facts, "Measured vs limit": "missing", "Evidence refs": evidence,
              "Missing evidence": "measured value"}
    # The model writes MODEL_FIELDS only; the agent adds Agent path / Policy alignment / Validation / Model.
    text = "\n".join([ANALYSIS_MARKER] + [f"{name}: {values[name]}" for name in MODEL_FIELDS])
    return {"text": text, "model_id": "none", "action_id": None, "usage": {}}


def main() -> int:
    client = ServiceNowClient.from_env()
    finding = finding_from_dict(json.loads(FINDING_FILE.read_text()))
    OUT.mkdir(parents=True, exist_ok=True)
    log = DeliveryLog(OUT / "delivery-log-roundtrip.jsonl")
    # Record the delivery in this test log (P4). dry_run: reuses INC0010232 read-only, never creates an incident.
    delivery = notify(finding, client, log, owner_user=OWNER, integration_user=INTEGRATION, dry_run=True)
    analyzer = CallableAnalyzer(stand_in, backend="test:stand-in", model_alias="none",
                                model_family="TEST stand-in (no model)")
    run = lambda: run_assurance_agent(finding, client, log, analyzer, owner_user=OWNER,  # noqa: E731
                                      integration_user=INTEGRATION, out_dir=OUT)
    first = run()
    second = run()
    case = case_view(finding, client, log, owner_user=OWNER, cutoff=FAR_CUTOFF, integration_user=INTEGRATION)
    response = check_response(finding, client, log, owner_user=OWNER, cutoff=FAR_CUTOFF,
                              integration_user=INTEGRATION)
    sys_id = client.find_incidents(finding.finding_id, INTEGRATION)[0]["sys_id"]
    notes = display_text(client.get_incident_display(sys_id, ("work_notes",)).get("work_notes")) or ""
    entries = split_journal(notes)
    analysis = case.get("agent_analysis", {})
    v6 = next((c for c in case.get("outcome_validation", {}).get("checks", []) if c["id"] == "V6"), {})
    checks = {
        "0_existing_incident_DELIVERED": delivery.state == "DELIVERED" and delivery.reused,
        "1_first_run_WRITTEN": first.state == "WRITTEN",
        "2_second_run_SKIPPED": second.state == "SKIPPED",
        "3_case_present_verified_facts_complete": (analysis.get("status") == "present" and analysis.get("verified") is True
                                                   and analysis.get("facts_match") is True and analysis.get("complete") is True),
        "4_note_not_counted_as_owner_reply": response.state != "RESPONDED" or response.actor == OWNER,
        "5_parser_found_entries_and_note": bool(entries) and entries[0].body.startswith(ANALYSIS_MARKER),
        "6_case_has_five_assurance_sections": all(k in case for k in SECTIONS),
        "7_note_has_computed_lines": all((analysis.get("fields") or {}).get(k) for k in COMPUTED),
        "8_stand_in_is_not_validated": (case.get("outcome_validation", {}).get("status") == "failed"
                                        and v6.get("status") == "fail"),
    }
    print(json.dumps({
        "incident": first.number, "delivery": {"state": delivery.state, "reused": delivery.reused},
        "first_run": {"state": first.state, "reason": first.reason},
        "second_run": {"state": second.state, "reason": second.reason},
        "case_agent_analysis": {k: analysis.get(k) for k in ("status", "verified", "facts_match", "complete",
                                                               "finding_matches", "author", "at")},
        "model_line": (analysis.get("fields") or {}).get("Model"),
        "computed_lines": {k: (analysis.get("fields") or {}).get(k) for k in COMPUTED},
        "policy_alignment": {k: case.get("policy_alignment", {}).get(k) for k in ("passed", "total")},
        "outcome_validation": case.get("outcome_validation", {}).get("status"),
        "decision_trace_sources": [e["source"] for e in case.get("decision_trace", [])],
        "owner_response_state": response.state,
        "journal_headers_seen": [f"{e.at} - {e.author} ({e.kind})" for e in entries[:3]],
        "checks": checks, "ALL_PASSED": all(checks.values()),
    }, indent=2))
    if first.state != "WRITTEN":
        print("\nDIAGNOSTIC (first 700 chars of the raw work-notes display text):\n" + notes[:700])
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
