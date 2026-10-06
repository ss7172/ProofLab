"""The one contract: four transports, one record (ARCH §3.2). Version `ifabric.contract/1`. Stdlib, 3.9.

  evaluate(q, pin) -> Decision      synchronous, in the path; EXACTLY ONE CALLER: adapters/runtime/model_call.py
  emit(record) -> EmitReceipt       async enqueue; never raises (implemented by adapters/runtime/emit_client.py)
  callback(event) -> record         a later verdict (notify-then-poll; only the poller calls it)
  pull(source, window, as_of) -> Capture ; normalize(capture) -> [record]   off the path

C16Question / Decision / PinnedC16 live in prooflab.evaluators.c16_core (PR-02) and are re-exported here
lazily (one import site: `_core()`), so the in-path and off-path copies are one file with one sha256.
A change to this module is a PR that bumps CONTRACT_VERSION (R-D-06).
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field

CONTRACT_VERSION = "ifabric.contract/1"
CORE_MODULE = "prooflab.evaluators.c16_core"
EMIT_RECEIPTS = ("ENQUEUED", "SPOOLED", "REJECTED_SCHEMA")
EVALUATOR_ERROR = "evaluator-error"


def _core():
    """THE one coupling to PR-02's c16 core."""
    return importlib.import_module(CORE_MODULE)


def __getattr__(name):  # PEP 562: C16Question, Decision, PinnedC16 re-exported from the core
    if name in ("C16Question", "Decision", "PinnedC16"):
        return getattr(_core(), name)
    raise AttributeError(name)


def evaluate(q, pin):
    """Pure. Delegates to c16_core.decide_inline(q, pin). An exception inside becomes a fail-closed
    Decision (verdict DENY, action halt, reason evaluator-error), decided here, never in the adapter."""
    core = _core()
    try:
        return core.decide_inline(q, pin)
    except Exception as exc:  # noqa: BLE001 - fail closed on anything
        return _fail_closed(core, q, pin, exc)


def _fail_closed(core, q, pin, exc):
    maker = getattr(core, "fail_closed_decision", None)
    if maker is not None:
        return maker(q, pin, EVALUATOR_ERROR)
    g = lambda obj, name, default=None: getattr(obj, name, default)
    total = sum(int(g(q, k, 0) or 0) for k in ("committed_tokens", "reserved_tokens", "bound_tokens"))
    return core.Decision(
        control_ref="C16", control_id=g(pin, "control_id", "ACN-COST-001"), verdict="DENY",
        reason="%s: %s" % (EVALUATOR_ERROR, type(exc).__name__), measured_value=total,
        threshold_value=0, tier=g(q, "tier", ""), mode=g(pin, "mode", "enforce"), limit_applied="cap",
        limit_value=None, action="halt", bound_basis=g(q, "bound_basis"),
        threshold_version=g(pin, "threshold_version", ""), register_version=g(pin, "register_version", ""),
        threshold_sha256=g(pin, "register_sha256", ""), pin_sha256=g(pin, "pin_sha256", ""),
        evaluator_name=CORE_MODULE, evaluator_sha256=g(core, "CORE_SHA256", ""),
    )


# --- the other transports' shapes --------------------------------------------------------------

@dataclass(frozen=True)
class DeferredVerdict:
    """A verdict that arrives later (owner response, human approval, or cutoff silence)."""
    finding_id: str
    run_id: str
    kind: str                 # "owner-response" | "approval" | "cutoff-silence"
    observed_at: str          # UTC, the ServiceNow clock
    actor: str                # the human (ServiceNow user) or "cutoff"
    detail: str
    source_refs: tuple = ()


@dataclass(frozen=True)
class SourceSpec:
    system: str               # e.g. "aws-spans", "modaas-evidence", "pdp", "ledger", "servicenow"
    query: str                # the exact query / filter text (recorded in the capture manifest)
    by_run_id: "str | None" = None


@dataclass(frozen=True)
class Window:
    start: str                # UTC
    end: str                  # UTC


@dataclass(frozen=True)
class Capture:
    """Raw bytes exactly as pulled + the capture manifest (Arth's .capture.json sidecar fields)."""
    source: SourceSpec
    window: Window
    as_of: str
    path: str
    sha256: str
    manifest: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Assessment:
    """The control test's output (§3.2). As a record: record_kind assessment, fields under assessment.*."""
    assessment_id: str
    control_ref: str
    control_id: str
    threshold_version: str
    threshold_sha256: str
    register_version: str
    scope_kind: str
    scope_id: str
    scope_start: str
    scope_end: str
    requirement_verdict: str
    design: str
    operation: str
    deficiency: str
    evidence_sufficiency: str
    measured: dict
    exceptions: list
    denominators: dict
    completeness: dict
    formula: str
    evidence_refs: list
    gaps: list
    evaluator_name: str
    evaluator_sha256: str
    as_of: str
    snapshot_id: str
    finding: "dict | None" = None


def assessment_id(control_ref: str, threshold_version: str, scope_kind: str, scope_id: str, n: int) -> str:
    """`<control_ref>:<threshold_version>:<scope_kind>:<scope_id>:r<n>`."""
    return "%s:%s:%s:%s:r%d" % (control_ref, threshold_version, scope_kind, scope_id, int(n))
