# c16_core: the ONE C16 decision function (ARCH 3.4, 5.1, 11.1), at EP-1 (inline) and EP-2 (replay).
# Frozen once merged: any change is a new agent build. Stdlib, Python 3.9+, pure: no I/O, clock or state.
# Every limit comes from the pin. Bad input fails closed: DENY + halt.
import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Tuple

NAME = "prooflab.evaluators.c16_core"
MODES = ("enforce", "observe")
BASES = ("projected", "last-call-plus", "declared-fallback", "actual")
CAP = "cap_tier_"


def _n(v):
    return type(v) is int and v >= 0


def _i(v):
    if isinstance(v, str) and v.strip().isdigit():
        return int(v)
    if type(v) is float and v.is_integer():
        return int(v)
    return v


def _s(o, a):
    v = getattr(o, a, None)
    return v if isinstance(v, str) else None


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
    measured_value: Optional[int]
    threshold_value: Optional[int]
    tier: Optional[str]
    mode: Optional[str]
    limit_applied: Optional[str]
    limit_value: Optional[int]
    action: str
    bound_basis: Optional[str]
    threshold_version: Optional[str]
    register_version: Optional[str]
    threshold_sha256: Optional[str]
    pin_sha256: Optional[str]
    evaluator_name: str
    evaluator_sha256: Optional[str]


def _check_pin(p):
    c = p.caps
    t = [k for k, _ in c]
    if not c or len(set(t)) != len(t) or not all(isinstance(k, str) and k and _n(v) and v > 0 for k, v in c):
        raise ValueError("caps")
    if not (_n(p.safety_ceiling) and all(v <= p.safety_ceiling for _, v in c)):
        raise ValueError("safety_ceiling")
    m = p.inline_modes
    if not (p.mode in MODES and isinstance(m, tuple) and p.mode in m and all(x in MODES for x in m)):
        raise ValueError("mode")
    if p.default_tier not in t:
        raise ValueError("default_tier")
    for a in ("inline_bound_margin_pct", "inline_bound_fallback_tokens", "max_tokens"):
        if not _n(getattr(p, a)):
            raise ValueError(a)
    for a in ("threshold_version", "register_version", "register_sha256"):
        if not _s(p, a):
            raise ValueError(a)
    if not isinstance(p.pin_sha256, str):
        raise ValueError("pin_sha256")


@dataclass(frozen=True)
class PinnedC16:
    caps: Tuple[Tuple[str, int], ...]
    default_tier: str
    safety_ceiling: int
    mode: str
    inline_modes: Tuple[str, ...]
    inline_bound_margin_pct: int
    inline_bound_fallback_tokens: int
    max_tokens: int
    threshold_version: str
    register_version: str
    register_sha256: str
    pin_sha256: str = ""

    def __post_init__(self):
        _check_pin(self)

    @classmethod
    def from_dict(cls, d, pin_sha256=""):
        m = d.get("inline_modes")
        if isinstance(m, str):
            m = [x.strip() for x in m.split(",") if x.strip()]
        g = lambda k: _i(d.get(k))
        return cls(tuple(sorted((k[len(CAP):], _i(v)) for k, v in d.items() if k.startswith(CAP))),
                   d.get("default_tier"), g("safety_ceiling"), d.get("mode"), tuple(m or ()),
                   g("inline_bound_margin_pct"), g("inline_bound_fallback_tokens"), g("max_tokens"),
                   d.get("threshold_version"), d.get("register_version", d.get("version")),
                   d.get("register_sha256", d.get("sha256")), pin_sha256)

    @classmethod
    def from_json(cls, text, expected_sha256):
        h = hashlib.sha256(text if isinstance(text, bytes) else text.encode("utf-8")).hexdigest()
        if h != str(expected_sha256).strip().lower():
            raise ValueError("pin sha256 mismatch")
        d = json.loads(text)
        if not isinstance(d, dict):
            raise ValueError("pin")
        return cls.from_dict(d, h)


def compare(total, limit):
    if not (_n(total) and _n(limit)):
        raise ValueError("compare")
    return "over" if total > limit else "within"


def bound_for(projected, last_input, last_output, tool_result_tokens, pin):
    """(bound, basis): max(projected, last in + out + tool results) or the fallback, + max_tokens, + margin %."""
    try:
        _check_pin(pin)
        e = []
        if _n(projected) and projected > 0:
            e.append((projected, "projected"))
        t = 0 if tool_result_tokens is None else tool_result_tokens
        if _n(last_input) and _n(last_output) and _n(t) and last_input + last_output > 0:
            e.append((last_input + last_output + t, "last-call-plus"))
        b, basis = max(e, key=lambda x: x[0]) if e else (pin.inline_bound_fallback_tokens, "declared-fallback")
        b += pin.max_tokens
        return b - (-b * pin.inline_bound_margin_pct // 100), basis
    except Exception:
        return None, None


def _fail(q, pin, sha, why):
    return Decision("C16", "ACN-COST-001", "DENY", why, None, None, _s(q, "tier"), _s(pin, "mode"), None, None,
                    "halt", _s(q, "bound_basis"), _s(pin, "threshold_version"), _s(pin, "register_version"),
                    _s(pin, "register_sha256"), _s(pin, "pin_sha256"), NAME, sha)


def decide_inline(q, pin, evaluator_sha256=None):
    """verdict DENY iff total > cap(tier); action halt iff total > the applied limit (cap | safety ceiling)."""
    try:
        try:
            _check_pin(pin)
        except Exception as x:
            return _fail(q, pin, evaluator_sha256, "invalid-pin: %s" % x)
        c, r, b = q.committed_tokens, q.reserved_tokens, q.bound_tokens
        if not (isinstance(q.run_id, str) and isinstance(q.tier, str) and _n(c) and _n(r) and _n(b)
                and q.bound_basis in BASES):
            return _fail(q, pin, evaluator_sha256, "invalid-question")
        caps = dict(pin.caps)
        tier, note = q.tier, ""
        if tier not in caps:
            tier = min(pin.caps, key=lambda x: (x[1], x[0]))[0]
            note = " (unknown tier '%s': strictest)" % q.tier
        cap, total = caps[tier], c + r + b
        over = compare(total, cap) == "over"
        la, lv = ("cap", cap) if pin.mode == "enforce" else ("safety-ceiling", pin.safety_ceiling)
        act = "halt" if compare(total, lv) == "over" else "proceed"
        why = "committed %d + reserved %d + bound %d (%s) = %d %s cap %d, tier %s%s; %s %d: %s" % (
            c, r, b, q.bound_basis, total, ">" if over else "<=", cap, tier, note, la, lv, act)
        return Decision("C16", "ACN-COST-001", "DENY" if over else "ALLOW", why, total, cap, tier, pin.mode, la, lv,
                        act, q.bound_basis, pin.threshold_version, pin.register_version, pin.register_sha256,
                        pin.pin_sha256, NAME, evaluator_sha256)
    except Exception:
        return _fail(q, pin, evaluator_sha256, "evaluator-error")
