"""T6.5 Ph2: the Assurance analysis between subject runs (G-05). Stdlib, 3.9.

`analyze_between_runs` calls Arth's `run_assurance_agent` for each DELIVERED, analysable finding, only while
`run_active()` is false (the 30 req/min rule), with a per-finding lock, and turns EVERY exception into our own
failure entry `ANALYSIS_FAILED` (the type name only; model text is never logged). `kind: approval` findings,
wiring-test logs and findings without a DELIVERED line are never analysed. One analysis per call, never re-invoked.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, Iterable, List, Optional

from prooflab.humanloop import config as cfg
from prooflab.servicenow.assurance_agent import run_assurance_agent
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict

DELIVERED_STATE = "DELIVERED"
SKIP_KINDS = ("approval",)
FAILED_STATE = "ANALYSIS_FAILED"
_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(fid: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(fid, threading.Lock())


def analysable(data: dict, log: DeliveryLog, log_path: str) -> Optional[str]:
    """None when the finding may be analysed, else the reason it may not."""
    if data.get("kind") in SKIP_KINDS:
        return "approval findings are never analysed"
    if cfg.under_wiring_tests(log_path):
        return "wiring-test log"
    fid = finding_from_dict(data).finding_id
    if not any(e.get("state") == DELIVERED_STATE for e in log.history(fid)):
        return "not delivered"
    return None


def analyze_between_runs(findings: Iterable[dict], client, config: cfg.HumanLoopConfig, analyzer,
                         run_active: Callable[[], bool], out_dir: str, agent_user: Optional[str] = None,
                         force: bool = False) -> List[dict]:
    """One result row per finding. Runs nothing while a subject run is active."""
    rows: List[dict] = []
    log = DeliveryLog(config.delivery_log)
    for data in findings:
        try:
            finding = finding_from_dict(data)
            fid = finding.finding_id
        except (ValueError, KeyError, TypeError) as err:
            rows.append({"finding_id": None, "action": "skipped", "reason": "invalid finding: %s" % type(err).__name__})
            continue
        row = {"finding_id": fid}
        why = analysable(data, log, config.delivery_log)
        if why:
            rows.append({**row, "action": "skipped", "reason": why})
            continue
        if run_active():
            rows.append({**row, "action": "deferred", "reason": "a subject run is active"})
            continue
        lock = _lock_for(fid)
        if not lock.acquire(False):
            rows.append({**row, "action": "skipped", "reason": "analysis in progress"})
            continue
        try:
            kwargs = {"agent_user": agent_user} if agent_user else {}
            outcome = run_assurance_agent(finding, client, log, analyzer, owner_user=config.owner_user,
                                          integration_user=config.integration_user, out_dir=out_dir,
                                          force=force, **kwargs)
            rows.append({**row, "action": "analysed", "state": outcome.state, "reason": outcome.reason})
        except Exception as err:   # noqa: BLE001 - nothing may escape the worker (T6.5)
            log.append(fid, FAILED_STATE, reason=type(err).__name__)
            rows.append({**row, "action": "failed", "reason": type(err).__name__})
        finally:
            lock.release()
    return rows


def start_worker(findings: List[dict], client, config, analyzer, run_active, out_dir, **kw) -> threading.Thread:
    """The one background worker: a thread that makes one pass and records its rows on `.rows`."""
    def work():
        thread.rows = analyze_between_runs(findings, client, config, analyzer, run_active, out_dir, **kw)

    thread = threading.Thread(target=work, name="humanloop-analysis", daemon=True)
    thread.rows = []
    thread.start()
    return thread
