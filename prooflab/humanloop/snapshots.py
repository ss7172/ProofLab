"""T6.5 Ph2: case snapshots and the export (G-05). Stdlib, 3.9.

`snapshot_cases` writes Arth's case view per finding (30-60 s while pending, 5-10 min otherwise, once at seal);
`due` is the cadence rule. `export_all` runs Arth's `export` after each owner response and at the final check,
and returns the gap entries for incidents closed in ServiceNow without a linked passing re-test.
"""
from __future__ import annotations

from typing import Callable, Iterable, List, Optional

from prooflab.adapters import human_loop as hl
from prooflab.contract import clocks as _clocks
from prooflab.humanloop import config as cfg
from prooflab.servicenow.case_view import case_view, write_case_snapshot
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.servicenow.notifier import export_incident

PENDING_CADENCE_S = 45      # inside 30-60 s
SETTLED_CADENCE_S = 450     # inside 5-10 min
PENDING_STATES = ("AWAITING_RESPONSE", "DELIVERED", "NO_RESPONSE_OBSERVED")


def is_pending(history: List[dict]) -> bool:
    return hl.sticky_response(history) is None


def cadence_s(pending: bool) -> int:
    return PENDING_CADENCE_S if pending else SETTLED_CADENCE_S


def due(last_at: Optional[str], now: str, pending: bool, sealed: bool = False, sealed_done: bool = False) -> bool:
    """Whether a snapshot is due: once at seal, else by the cadence."""
    if sealed:
        return not sealed_done
    if last_at is None:
        return True
    return (_clocks.parse_utc(now) - _clocks.parse_utc(last_at)).total_seconds() >= cadence_s(pending)


def snapshot_cases(findings: Iterable[dict], client, config: cfg.HumanLoopConfig, cutoff: str, out_dir: str,
                   now: Optional[str] = None, aict_url: Optional[str] = None) -> List[dict]:
    rows = []
    for data in findings:
        finding = finding_from_dict(data)
        log_path = config.approval_log if hl.is_approval(data) and config.approval_log else config.delivery_log
        log = DeliveryLog(log_path)
        case = case_view(finding, client, log, owner_user=config.owner_user, cutoff=cutoff,
                         integration_user=config.integration_user, aict_url=aict_url, now=now)
        path, digest = write_case_snapshot(case, out_dir)
        rows.append({"finding_id": finding.finding_id, "path": str(path), "sha256": digest,
                     "servicenow": case["servicenow"].get("status")})
    return rows


def export_all(findings: Iterable[dict], client, config: cfg.HumanLoopConfig, out_dir: str,
               retests: Optional[dict] = None, read_export: Optional[Callable[[str], dict]] = None) -> dict:
    """Export each finding's incident; `retests` maps finding id -> retest block. Returns
    {"exports": [...], "gaps": [...]}; a finding whose incident is missing is a gap, never an exception."""
    import json
    exports, gaps = [], []
    for data in findings:
        finding = finding_from_dict(data)
        log_path = config.approval_log if hl.is_approval(data) and config.approval_log else config.delivery_log
        try:
            path = export_incident(finding, client, config.integration_user, out_dir, DeliveryLog(log_path))
        except LookupError as err:
            gaps.append({"gap": "no incident to export", "finding_id": finding.finding_id, "reason": str(err)[:200]})
            continue
        exports.append({"finding_id": finding.finding_id, "path": str(path)})
        if read_export:
            doc = read_export(str(path))
        else:
            with open(str(path), encoding="utf-8") as handle:
                doc = json.load(handle)
        gap = hl.closed_without_retest(doc, (retests or {}).get(finding.finding_id), data)
        if gap:
            gaps.append(gap)
    return {"exports": exports, "gaps": gaps}
