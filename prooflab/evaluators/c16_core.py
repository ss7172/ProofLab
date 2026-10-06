# c16_core: the ONE C16 decision function (ARCH 3.4, 5.1, 11.1), at EP-1 (inline) and EP-2 (replay).
# Frozen once merged: any change is a new agent build. Stdlib, Python 3.9+, pure: no I/O, clock or state.
# Every limit comes from the pin (ifabric.pin/1, ARCH 3.3). Bad input fails closed: DENY + halt.
import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Tuple

NAME = "prooflab.evaluators.c16_core"
SCHEMA = "ifabric.pin/1"
CONTROL_ID = "ACN-COST-001"  # used only when the pin itself is unreadable
MODES = ("enforce", "observe")
BASES = ("projected", "last-call-plus", "declared-fallback", "actual")
ENV = ("IFABRIC_PIN_JSON", "IFABRIC_PIN_SHA256", "IFABRIC_REGISTER_VERSION", "IFABRIC_REGISTER_SHA256")


def _n(v):
    return type(v) is int and v >= 0


def _pct(v):
    """A non-negative finite margin (int or float) as an exact (num, den); None if invalid."""
    try:
        if type(v) not in (int, float) or not v >= 0:
            return None
        return v.as_integer_ratio()
    except Exception:
        return None


def _s(o, a):
    try:
        v = getattr(o, a, None)
    except Exception:
        return None
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
    if _pct(p.inline_bound_margin_pct) is None:
        raise ValueError("inline_bound_margin_pct")
    for a in ("inline_bound_fallback_tokens", "max_tokens"):
        if not _n(getattr(p, a)):
            raise ValueError(a)
    for a in ("threshold_version", "register_version", "register_sha256", "control_id"):
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
    inline_bound_margin_pct: float  # int or float; rounded up exactly (as_integer_ratio)
    inline_bound_fallback_tokens: int
    max_tokens: int
    threshold_version: str
    register_version: str
    register_sha256: str
    pin_sha256: str = ""
    control_id: str = CONTROL_ID

    def __post_init__(self):
        _check_pin(self)

    @classmethod
    def from_dict(cls, d, pin_sha256=""):
        """The parsed ifabric.pin/1 object: {schema, register:{version, sha256}, c16:{..., caps, modes, bound}}."""
        if not isinstance(d, dict) or d.get("schema") != SCHEMA:
            raise ValueError("schema")
        r, c = d.get("register"), d.get("c16")
        if not (isinstance(r, dict) and isinstance(c, dict)):
            raise ValueError("register/c16")
        caps, modes, b = c.get("caps"), c.get("modes"), c.get("bound")
        if not (isinstance(caps, dict) and isinstance(modes, list) and isinstance(b, dict)):
            raise ValueError("caps/modes/bound")
        tiers = c.get("tiers", sorted(caps))
        if not isinstance(tiers, list) or sorted(tiers) != sorted(caps):
            raise ValueError("tiers")
        return cls(tuple(sorted(caps.items())), c.get("default_tier"), c.get("safety_ceiling"), c.get("mode"),
                   tuple(modes), b.get("inline_bound_margin_pct"), b.get("inline_bound_fallback_tokens"),
                   b.get("max_tokens"), c.get("threshold_version"), r.get("version"), r.get("sha256"),
                   pin_sha256, c.get("control_id"))

    @classmethod
    def from_json(cls, text, expected_sha256):
        h = hashlib.sha256(text if isinstance(text, bytes) else text.encode("utf-8")).hexdigest()
        if not isinstance(expected_sha256, str) or h != expected_sha256.strip().lower():
            raise ValueError("pin sha256 mismatch")
        return cls.from_dict(json.loads(text), h)

    @classmethod
    def from_env(cls, env):
        """Start-up builder (ARCH 3.3 H1). env is a mapping passed in (the core reads nothing itself)."""
        v = [env.get(k) for k in ENV]
        miss = [k for k, x in zip(ENV, v) if not (isinstance(x, str) and x)]
        if miss:
            raise ValueError("missing env: " + ",".join(miss))
        text, sha, rv, rs = v
        p = cls.from_json(text, sha)
        if (p.register_version, p.register_sha256) != (rv, rs):
            raise ValueError("register version/sha256 in env disagree with the pin")
        return p


def compare(total, limit):
    if not (_n(total) and _n(limit)):
        raise ValueError("compare")
    return "over" if total > limit else "within"


def bound_for(projected, last_input, last_output, tool_result_tokens, pin):
    """(bound, basis): max(projected, last in + out + tool results) or fallback + tool results, + max_tokens,
    + margin % (rounded up). None/0 = unknown; any other invalid term -> (None, None), which decide_inline denies."""
    try:
        _check_pin(pin)
        v = [0 if x is None else x for x in (projected, last_input, last_output, tool_result_tokens)]
        if not all(_n(x) for x in v):
            return None, None
        p, li, lo, t = v
        e = [(p, "projected")] if p else []
        if li or lo:
            e.append((li + lo + t, "last-call-plus"))
        b, basis = max(e, key=lambda x: x[0]) if e else (pin.inline_bound_fallback_tokens + t, "declared-fallback")
        b += pin.max_tokens
        num, den = _pct(pin.inline_bound_margin_pct)
        return b - (-b * num // (den * 100)), basis
    except Exception:
        return None, None


def _fail(q, pin, sha, why):
    return Decision("C16", _s(pin, "control_id") or CONTROL_ID, "DENY", why, None, None, _s(q, "tier"),
                    _s(pin, "mode"), None, None, "halt", _s(q, "bound_basis"), _s(pin, "threshold_version"),
                    _s(pin, "register_version"), _s(pin, "register_sha256"), _s(pin, "pin_sha256"), NAME, sha)


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
        return Decision("C16", pin.control_id, "DENY" if over else "ALLOW", why, total, cap, tier, pin.mode, la,
                        lv, act, q.bound_basis, pin.threshold_version, pin.register_version, pin.register_sha256,
                        pin.pin_sha256, NAME, evaluator_sha256)
    except Exception:
        return _fail(q, pin, evaluator_sha256, "evaluator-error")
