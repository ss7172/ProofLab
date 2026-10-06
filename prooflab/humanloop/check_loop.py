"""T6.5 Ph2: the check loop (G-05). Stdlib, 3.9.

`check` runs at most every MAX_INTERVAL_S per open finding until the cutoff, and stops at RESPONDED (sticky:
the earliest logged RESPONDED wins, guard (b)). After the cutoff one final check is always made, so silence is
recorded (a cutoff after the last check never records silence, R-19). Approval findings are checked too (the
captain's APPROVED note); they use their own log.
"""
from __future__ import annotations

import time
from typing import Callable, Iterable, List, Optional

from prooflab.adapters import human_loop as hl
from prooflab.contract import clocks as _clocks
from prooflab.humanloop import config as cfg
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.servicenow.notifier import check_response

MAX_INTERVAL_S = 60
DELIVERED_STATE = "DELIVERED"


def _log_for(data: dict, config: cfg.HumanLoopConfig) -> str:
    return config.approval_log if hl.is_approval(data) and config.approval_log else config.delivery_log


def is_open(history: List[dict]) -> bool:
    """Delivered and not yet responded to."""
    return hl.sticky_response(history) is None and any(e.get("state") == DELIVERED_STATE for e in history)


def check_once(findings: Iterable[dict], client, config: cfg.HumanLoopConfig, cutoff: str,
               now: Optional[str] = None) -> List[dict]:
    rows = []
    for data in findings:
        finding = finding_from_dict(data)
        fid = finding.finding_id
        log = DeliveryLog(_log_for(data, config))
        history = log.history(fid)
        if hl.sticky_response(history) is not None:
            rows.append({"finding_id": fid, "action": "stopped", "reason": "RESPONDED"})
            continue
        if not any(e.get("state") == DELIVERED_STATE for e in history):
            rows.append({"finding_id": fid, "action": "skipped", "reason": "not delivered"})
            continue
        outcome = check_response(finding, client, log, owner_user=config.owner_user, cutoff=cutoff,
                                 integration_user=config.integration_user, now=now)
        rows.append({"finding_id": fid, "action": "checked", "state": outcome.state})
    return rows


def run_loop(findings: List[dict], client, config: cfg.HumanLoopConfig, cutoff: str,
             interval_s: float = MAX_INTERVAL_S, sleep: Callable[[float], None] = time.sleep,
             clock: Callable[[], str] = _clocks.now_utc, on_pass: Optional[Callable[[List[dict]], None]] = None,
             max_passes: Optional[int] = None) -> List[List[dict]]:
    """Check every open finding every <= MAX_INTERVAL_S until all responded or the cutoff has passed (plus one
    final check). Returns each pass's rows."""
    interval = min(float(interval_s), MAX_INTERVAL_S)
    cutoff_at = _clocks.parse_utc(cutoff)
    passes: List[List[dict]] = []
    while True:
        rows = check_once(findings, client, config, cutoff, now=clock())
        passes.append(rows)
        if on_pass:
            on_pass(rows)
        passed = _clocks.parse_utc(clock()) >= cutoff_at
        all_done = all(r["action"] in ("stopped", "skipped") for r in rows)
        if passed or all_done or (max_passes is not None and len(passes) >= max_passes):
            return passes
        sleep(interval)
