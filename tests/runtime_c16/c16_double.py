"""TEST DOUBLE of the c16 core (prooflab.evaluators.c16_core, PR-02), signatures per ARCH 3.2/3.4.
Used only until the real core is merged; tests install it as model_call._core."""
from dataclasses import dataclass


@dataclass(frozen=True)
class C16Question:
    run_id: str
    tier: str
    committed_tokens: int
    reserved_tokens: int
    bound_tokens: int
    bound_basis: str


@dataclass(frozen=True)
class Decision:
    control_ref: str
    control_id: str
    verdict: str
    reason: str
    measured_value: int
    threshold_value: int
    tier: str
    mode: str
    limit_applied: str
    limit_value: object
    action: str
    bound_basis: object
    threshold_version: str
    register_version: str
    threshold_sha256: str
    pin_sha256: str
    evaluator_name: str
    evaluator_sha256: str


@dataclass(frozen=True)
class PinnedC16:
    cap: int = 400
    ceiling: int = 100000
    mode: str = "enforce"
    margin_pct: int = 0
    max_tokens: int = 50
    fallback: int = 200
    boom: bool = False


def bound_for(projected, last_input, last_output, tool_result_tokens, pin):
    if last_input is None and projected is None:
        base, basis = pin.fallback, "declared-fallback"
    else:
        a = projected or 0
        b = (last_input or 0) + (last_output or 0) + (tool_result_tokens or 0)
        base, basis = (a, "projected") if a >= b else (b, "last-call-plus")
    return (base + pin.max_tokens) * (100 + pin.margin_pct) // 100, basis


def decide_inline(q, pin):
    if pin.boom:
        raise RuntimeError("double: evaluator exploded")
    total = q.committed_tokens + q.reserved_tokens + q.bound_tokens
    deny = total > pin.cap
    limit = pin.cap if pin.mode == "enforce" else pin.ceiling
    halt = total > limit
    return Decision("C16", "ACN-COST-001", "DENY" if deny else "ALLOW",
                    "committed %d + bound %d > cap %d" % (q.committed_tokens, q.bound_tokens, pin.cap),
                    total, pin.cap, q.tier, pin.mode,
                    "cap" if pin.mode == "enforce" else "safety-ceiling", limit,
                    "halt" if halt else "proceed", q.bound_basis, "C16-v1", "v1",
                    "sha-register", "sha-pin", "prooflab.evaluators.c16_core", "sha-core")
