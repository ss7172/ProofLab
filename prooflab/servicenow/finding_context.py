"""Optional context an evaluator can attach to a Finding (never part of the finding id).

  measured  {"value": 10800, "unit": "tokens"}
  limit     {"value": 10000, "operator": "<=", "unit": "tokens"}      measured <op> limit = within limit
  register  {"version_date": "2026-10-05", "owner": "annapurna@invences.com", "approval": "INC…"}
  trace     [{"at", "actor", "zone", "action", "decision", "ref", "run_id"}, …]   the agents' movement
  retest    {"assessment": "assessment:…/run_FM-C.r1.json", "verdict": "SATISFIED",
             "threshold_version": "G-FM-v1", "at": "…Z"}   the re-test that closed the finding

With it, the Assurance Agent can compute agent movement and policy alignment; without
it, those checks report "unknown" (never pass). All values are untrusted input.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

OPERATORS = ("<=", "<", ">=", ">", "==")
RETEST_VERDICTS = ("BREACHED", "ESCALATED", "INDETERMINATE", "SATISFIED")  # finding.VERDICTS (no import cycle)
TRACE_MAX = 200
_TEXT_MAX = 200


@dataclass(frozen=True)
class Measurement:
    value: float
    unit: str


@dataclass(frozen=True)
class Limit:
    value: float
    operator: str
    unit: str


@dataclass(frozen=True)
class RegisterRef:
    version_date: str
    owner: str
    approval: str = ""


@dataclass(frozen=True)
class RetestRef:
    assessment: str         # the re-test's assessment id
    verdict: str            # only SATISFIED closes the finding
    threshold_version: str  # must equal the finding's version
    at: str = ""


@dataclass(frozen=True)
class TraceStep:
    at: str
    actor: str
    zone: str          # customer | it | network | gateway | other
    action: str        # model_call | tool_call | handoff | escalate | decision | …
    decision: str = ""  # allowed | blocked | escalated | …
    ref: str = ""      # record reference, e.g. gateway:action-…, pdp:…, span:…
    run_id: str = ""


def _text(data: Mapping, key: str, where: str, required: bool = True) -> str:
    value = data.get(key)
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(f"{where}.{key} is required")
        return ""
    text = str(value).strip()
    if "\n" in text or "\r" in text:
        raise ValueError(f"{where}.{key} must not contain a newline")
    if len(text) > _TEXT_MAX:
        raise ValueError(f"{where}.{key} is longer than {_TEXT_MAX} characters")
    return text


def _number(data: Mapping, key: str, where: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where}.{key} must be a number")
    return float(value)


def _mapping(data: Mapping, key: str) -> Optional[Mapping]:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


def _trace(value) -> Tuple[TraceStep, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("trace must be a list of steps")
    if len(value) > TRACE_MAX:
        raise ValueError(f"trace may hold at most {TRACE_MAX} steps (keep the rest in the Evidence Pack)")
    steps = []
    for index, step in enumerate(value):
        if not isinstance(step, Mapping):
            raise ValueError(f"trace[{index}] must be an object")
        where = f"trace[{index}]"
        steps.append(TraceStep(_text(step, "at", where), _text(step, "actor", where), _text(step, "zone", where),
                               _text(step, "action", where), _text(step, "decision", where, False),
                               _text(step, "ref", where, False), _text(step, "run_id", where, False)))
    return tuple(steps)


def _retest(value: Optional[Mapping]) -> Optional[RetestRef]:
    if value is None:
        return None
    assessment = _text(value, "assessment", "retest")
    if value.get("verdict") not in RETEST_VERDICTS:
        raise ValueError(f"retest.verdict must be one of {RETEST_VERDICTS}")
    return RetestRef(assessment, value["verdict"], _text(value, "threshold_version", "retest"),
                     _text(value, "at", "retest", False))


def parse_context(data: Mapping) -> dict:
    """Validated keyword arguments for Finding(...): measured, limit, register, trace, retest."""
    measured = _mapping(data, "measured")
    limit = _mapping(data, "limit")
    register = _mapping(data, "register")
    if limit is not None and limit.get("operator") not in OPERATORS:
        raise ValueError(f"limit.operator must be one of {OPERATORS}")
    return {
        "measured": Measurement(_number(measured, "value", "measured"), _text(measured, "unit", "measured"))
        if measured is not None else None,
        "limit": Limit(_number(limit, "value", "limit"), limit["operator"], _text(limit, "unit", "limit"))
        if limit is not None else None,
        "register": RegisterRef(_text(register, "version_date", "register"), _text(register, "owner", "register"),
                                _text(register, "approval", "register", False))
        if register is not None else None,
        "trace": _trace(data.get("trace")),
        "retest": _retest(_mapping(data, "retest")),
    }


def format_number(value: float) -> str:
    """Thousands separators, like the evaluator's summary ("10,800 tokens")."""
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,}"
