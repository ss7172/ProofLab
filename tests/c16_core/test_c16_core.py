"""PR-02 / T1.2: the c16 core decision table (ARCH 3.2, 3.4, 5.1, 11.1). Synthetic pin values only."""
import copy
import dataclasses
import gzip
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

from prooflab.evaluators import c16_core as core
from prooflab.evaluators.c16_core import C16Question, Decision, PinnedC16, bound_for, compare, decide_inline

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE = os.path.join(ROOT, "prooflab", "evaluators", "c16_core.py")

# Synthetic test values (fixtures, not thresholds of record). The pin is ifabric.pin/1 (PR-01 pin.py, ARCH 3.3).
CAP_LOW, CAP_DEFAULT, CEILING = 20000, 50000, 300000
BOUND_KEYS = ("inline_bound_margin_pct", "inline_bound_fallback_tokens", "max_tokens")
C16_KEYS = ("control_id", "threshold_version", "version_date", "tiers", "default_tier", "caps", "safety_ceiling",
            "modes", "mode", "bound")
PIN = {
    "schema": "ifabric.pin/1",
    "register": {"version": "v1", "sha256": "a" * 64},
    "c16": {"control_id": "ACN-COST-001", "threshold_version": "C16-v1", "version_date": "2026-10-06T00:00:00Z",
            "tiers": ["default", "low"], "default_tier": "default", "caps": {"default": CAP_DEFAULT, "low": CAP_LOW},
            "safety_ceiling": CEILING, "modes": ["enforce", "observe"], "mode": "enforce",
            "bound": {"inline_bound_margin_pct": 10, "inline_bound_fallback_tokens": 4000, "max_tokens": 900}},
    "c7": {"declared_faults": ["suppress-record:ifabric-it:tool.call:1"]},
}
_DROP = object()


def pin_dict(**kw):
    """PIN with overrides: c16 keys, bound keys, register_version/register_sha256, schema; _DROP removes a key."""
    d = copy.deepcopy(PIN)
    for k, v in kw.items():
        tgt, key = ((d["c16"]["bound"], k) if k in BOUND_KEYS else (d["c16"], k) if k in C16_KEYS else
                    (d["register"], k[len("register_"):]) if k.startswith("register_") else (d, k))
        if v is _DROP:
            assert key in tgt, key
            del tgt[key]
        else:
            tgt[key] = v
    return d


def canon(d):
    """PR-01 pin.dumps: sorted keys, no spaces, ASCII."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def env_of(d):
    """PR-01 pin.env_block shape."""
    text = canon(d)
    return {"IFABRIC_PIN_JSON": text, "IFABRIC_PIN_SHA256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "IFABRIC_REGISTER_VERSION": d["register"]["version"], "IFABRIC_REGISTER_SHA256": d["register"]["sha256"]}


def pin(**kw):
    return PinnedC16.from_dict(pin_dict(**kw), "b" * 64)


def q(committed, reserved=0, bound=0, tier="default", basis="projected"):
    return C16Question("ifabric-test-1-ab", tier, committed, reserved, bound, basis)


ENF, OBS = pin(mode="enforce"), pin(mode="observe")


# ---- the decision table ------------------------------------------------------------------------------------
@pytest.mark.parametrize("p,total,verdict,limit_applied,limit_value,action", [
    (ENF, CAP_DEFAULT - 1, "ALLOW", "cap", CAP_DEFAULT, "proceed"),
    (ENF, CAP_DEFAULT, "ALLOW", "cap", CAP_DEFAULT, "proceed"),
    (ENF, CAP_DEFAULT + 1, "DENY", "cap", CAP_DEFAULT, "halt"),
    (OBS, CAP_DEFAULT, "ALLOW", "safety-ceiling", CEILING, "proceed"),
    (OBS, CAP_DEFAULT + 1, "DENY", "safety-ceiling", CEILING, "proceed"),
    (OBS, CEILING, "DENY", "safety-ceiling", CEILING, "proceed"),
    (OBS, CEILING + 1, "DENY", "safety-ceiling", CEILING, "halt"),
    (ENF, 0, "ALLOW", "cap", CAP_DEFAULT, "proceed"),
])
def test_decision_table(p, total, verdict, limit_applied, limit_value, action):
    d = decide_inline(q(total), p, "c" * 64)
    assert (d.verdict, d.limit_applied, d.limit_value, d.action) == (verdict, limit_applied, limit_value, action)
    assert d.measured_value == total and d.threshold_value == CAP_DEFAULT and d.tier == "default"
    assert d.mode == p.mode and d.control_ref == "C16" and d.control_id == "ACN-COST-001"
    assert d.evaluator_name == "prooflab.evaluators.c16_core" and d.evaluator_sha256 == "c" * 64
    assert (d.threshold_version, d.register_version, d.threshold_sha256, d.pin_sha256) == ("C16-v1", "v1", "a" * 64, "b" * 64)
    assert d.bound_basis == "projected"


def test_total_is_committed_plus_reserved_plus_bound():
    d = decide_inline(q(CAP_DEFAULT - 30, 10, 20), ENF)
    assert d.measured_value == CAP_DEFAULT and d.verdict == "ALLOW"
    d = decide_inline(q(CAP_DEFAULT - 30, 11, 20), ENF)
    assert d.measured_value == CAP_DEFAULT + 1 and d.verdict == "DENY" and d.action == "halt"
    assert "committed %d + reserved 11 + bound 20" % (CAP_DEFAULT - 30) in d.reason


def test_boundary_property_loops():
    for p in (ENF, OBS):
        for tier, cap in (("default", CAP_DEFAULT), ("low", CAP_LOW)):
            for delta in range(-3, 4):
                total = cap + delta
                for split in (0, 1, total // 3, total):
                    d = decide_inline(q(total - split, 0, split, tier), p)
                    assert d.verdict == ("DENY" if total > cap else "ALLOW")
                    assert d.threshold_value == cap
                    if p.mode == "enforce":
                        assert d.action == ("halt" if d.verdict == "DENY" else "proceed")
                    else:
                        assert d.action == "proceed"
        for delta in range(-3, 4):
            d = decide_inline(q(CEILING + delta), p)
            assert d.verdict == "DENY"
            assert d.action == ("halt" if (p.mode == "enforce" or delta > 0) else "proceed")


def test_enforce_deny_always_halts_and_observe_halts_only_above_ceiling():
    for total in range(CAP_LOW - 5, CAP_LOW + 5):
        e = decide_inline(q(total, tier="low"), ENF)
        o = decide_inline(q(total, tier="low"), OBS)
        assert e.verdict == o.verdict
        assert (e.verdict == "DENY") == (e.action == "halt")
        assert o.action == "proceed"


def test_tiers_and_unknown_tier_gets_strictest():
    assert decide_inline(q(CAP_LOW + 1, tier="low"), ENF).verdict == "DENY"
    assert decide_inline(q(CAP_LOW + 1, tier="default"), ENF).verdict == "ALLOW"
    for t in ("nope", "", "DEFAULT"):
        d = decide_inline(q(CAP_LOW + 1, tier=t), ENF)
        assert d.tier == "low" and d.threshold_value == CAP_LOW and d.verdict == "DENY" and d.action == "halt"
        assert "unknown tier '%s'" % t in d.reason


def test_huge_values_no_overflow():
    d = decide_inline(q(2 ** 80, 2 ** 70, 2 ** 64), OBS)
    assert d.verdict == "DENY" and d.action == "halt" and d.measured_value == 2 ** 80 + 2 ** 70 + 2 ** 64


def test_ep2_actual_basis_same_function():
    d = decide_inline(q(CAP_DEFAULT - 100, 0, 101, basis="actual"), OBS)
    assert d.bound_basis == "actual" and d.verdict == "DENY" and d.action == "proceed"


# ---- fail closed -------------------------------------------------------------------------------------------
GARBAGE = [-1, None, 1.0, 1.5, "10", True, False, [], float("nan")]


@pytest.mark.parametrize("field", ["committed_tokens", "reserved_tokens", "bound_tokens"])
@pytest.mark.parametrize("bad", GARBAGE)
def test_garbage_token_fields_fail_closed(field, bad):
    good = q(1, 0, 1)
    d = decide_inline(dataclasses.replace(good, **{field: bad}), ENF)
    assert (d.verdict, d.action, d.reason) == ("DENY", "halt", "invalid-question")
    assert d.measured_value is None and d.limit_applied is None


@pytest.mark.parametrize("bad", ["", "guess", None, 3, "ACTUAL"])
def test_bad_bound_basis_fails_closed(bad):
    d = decide_inline(q(1, basis=bad), ENF)
    assert (d.verdict, d.action) == ("DENY", "halt")


@pytest.mark.parametrize("bad", [None, 3])
def test_bad_tier_or_run_id_fails_closed(bad):
    for field in ("tier", "run_id"):
        d = decide_inline(dataclasses.replace(q(1), **{field: bad}), ENF)
        assert (d.verdict, d.action, d.reason) == ("DENY", "halt", "invalid-question")


def test_none_and_garbage_objects_fail_closed():
    for qq, pp in ((None, None), (q(1), {}), (q(1), None), (None, ENF), ("x", ENF), (q(1), "pin")):
        d = decide_inline(qq, pp)
        assert isinstance(d, Decision) and (d.verdict, d.action) == ("DENY", "halt")
        assert d.reason.startswith("invalid-pin") or d.reason in ("evaluator-error", "invalid-question")
    assert decide_inline(None, ENF).reason == "evaluator-error"


def test_tampered_pin_object_fails_closed():
    bad = copy.copy(ENF)
    object.__setattr__(bad, "caps", (("default", -5),))
    d = decide_inline(q(1), bad)
    assert (d.verdict, d.action) == ("DENY", "halt") and d.reason.startswith("invalid-pin")


CAPS_BAD = [{"default": 0, "low": CAP_LOW}, {"default": -1, "low": CAP_LOW}, {"default": "x", "low": CAP_LOW},
            {"default": 1.5, "low": CAP_LOW}, {"default": True, "low": CAP_LOW}, {"default": float(CAP_DEFAULT),
            "low": CAP_LOW}, {"default": str(CAP_DEFAULT), "low": CAP_LOW}, {}]


@pytest.mark.parametrize("change", [dict(caps=c) for c in CAPS_BAD] + [
    dict(safety_ceiling=CAP_DEFAULT - 1), dict(safety_ceiling=None), dict(safety_ceiling=float(CEILING)),
    dict(mode="audit"), dict(mode=None), dict(modes=["observe"]), dict(modes=["enforce", "observe", "x"]),
    dict(modes="enforce,observe"), dict(default_tier="missing"), dict(tiers=["default"]), dict(tiers="default,low"),
    dict(inline_bound_margin_pct=-1), dict(inline_bound_margin_pct=-0.5), dict(inline_bound_margin_pct=True),
    dict(inline_bound_margin_pct="10"), dict(inline_bound_margin_pct=float("nan")),
    dict(inline_bound_margin_pct=float("inf")), dict(inline_bound_margin_pct=None),
    dict(inline_bound_fallback_tokens=None), dict(inline_bound_fallback_tokens=4000.0), dict(max_tokens=-900),
    dict(threshold_version=""), dict(control_id=""), dict(control_id=_DROP), dict(register_version=None),
    dict(register_sha256=None), dict(register_version=_DROP), dict(schema="ifabric.pin/2"), dict(schema=_DROP),
    dict(caps=_DROP), dict(modes=_DROP), dict(bound=_DROP), dict(c16=_DROP), dict(register=_DROP),
    dict(max_tokens=_DROP), dict(safety_ceiling=_DROP), dict(register="v1"), dict(bound=[]),
])
def test_invalid_pin_refused_at_construction(change):
    d = pin_dict(**change)  # the fixture itself must build
    with pytest.raises(ValueError):
        PinnedC16.from_dict(d, "b" * 64)


def test_flat_register_style_pin_refused():
    flat = dict(cap_tier_default=CAP_DEFAULT, default_tier="default", safety_ceiling=CEILING, mode="enforce",
                inline_modes="enforce,observe", inline_bound_margin_pct=10, inline_bound_fallback_tokens=4000,
                max_tokens=900, threshold_version="C16-v1", version="v1", sha256="a" * 64)
    for d in (flat, None, [], "pin"):
        with pytest.raises(ValueError):
            PinnedC16.from_dict(d)


def test_pin_from_nested_ifabric_pin_1():
    p = pin()
    assert p.caps == (("default", CAP_DEFAULT), ("low", CAP_LOW)) and p.default_tier == "default"
    assert p.inline_modes == ("enforce", "observe") and p.mode == "enforce" and p.safety_ceiling == CEILING
    assert (p.inline_bound_margin_pct, p.inline_bound_fallback_tokens, p.max_tokens) == (10, 4000, 900)
    assert (p.threshold_version, p.register_version, p.register_sha256) == ("C16-v1", "v1", "a" * 64)
    assert p.control_id == "ACN-COST-001" and p.pin_sha256 == "b" * 64
    assert pin(tiers=_DROP) == p  # tiers is optional; when present it must name exactly the caps
    assert pin(c7=_DROP, version_date=_DROP) == p  # the core ignores what it does not use
    assert pin(modes=["enforce"]).inline_modes == ("enforce",)
    assert pin(inline_bound_margin_pct=12.5).inline_bound_margin_pct == 12.5


def test_control_id_comes_from_the_pin():
    p = pin(control_id="LIB-C16-X")
    assert decide_inline(q(1), p).control_id == "LIB-C16-X"
    assert decide_inline(q(1, basis="bad"), p).control_id == "LIB-C16-X"  # fail-closed keeps the pin's id
    assert decide_inline(q(1), None).control_id == "ACN-COST-001"  # unreadable pin: the module constant


def test_pin_from_json_checks_sha256():
    text = canon(PIN)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    p = PinnedC16.from_json(text, h.upper())
    assert p.pin_sha256 == h and p.register_version == "v1" and p.register_sha256 == "a" * 64
    assert PinnedC16.from_json(text.encode("utf-8"), h) == p
    for bad in ("0" * 64, None, 5, ""):
        with pytest.raises(ValueError):
            PinnedC16.from_json(text, bad)
    for t in ("[]", "{}", "not json"):
        with pytest.raises(ValueError):
            PinnedC16.from_json(t, hashlib.sha256(t.encode("utf-8")).hexdigest())


def test_pin_from_env():
    assert hasattr(PinnedC16, "from_env")
    env = env_of(PIN)
    p = PinnedC16.from_env(env)
    assert p == PinnedC16.from_json(env["IFABRIC_PIN_JSON"], env["IFABRIC_PIN_SHA256"])
    assert p.pin_sha256 == env["IFABRIC_PIN_SHA256"] and p.caps == (("default", CAP_DEFAULT), ("low", CAP_LOW))
    assert decide_inline(q(CAP_DEFAULT + 1), p).action == "halt"


@pytest.mark.parametrize("key", ["IFABRIC_PIN_JSON", "IFABRIC_PIN_SHA256", "IFABRIC_REGISTER_VERSION",
                                 "IFABRIC_REGISTER_SHA256"])
def test_pin_from_env_missing_key_refused(key):
    env = env_of(PIN)
    for mutate in ("drop", "empty"):
        e = dict(env)
        if mutate == "drop":
            del e[key]
        else:
            e[key] = ""
        with pytest.raises(ValueError):
            PinnedC16.from_env(e)


def test_pin_from_env_sha_and_register_mismatch_refused():
    env = env_of(PIN)
    for key, val in (("IFABRIC_PIN_SHA256", "0" * 64), ("IFABRIC_REGISTER_VERSION", "v2"),
                     ("IFABRIC_REGISTER_SHA256", "d" * 64), ("IFABRIC_PIN_JSON", canon(pin_dict(mode="observe")))):
        with pytest.raises(ValueError):
            PinnedC16.from_env(dict(env, **{key: val}))
    with pytest.raises(Exception):
        PinnedC16.from_env(None)


def test_pr01_pin_module_round_trip():
    """Runs once PR-01 (prooflab.contract.pin) is merged: its env_block feeds from_env unchanged."""
    pinmod = pytest.importorskip("prooflab.contract.pin")
    d = pin_dict()
    assert pinmod.validate_pin(d) == []
    text = pinmod.dumps(d)
    assert text == canon(d)
    p = PinnedC16.from_json(text, pinmod.sha256_of(text))
    assert PinnedC16.from_env(pinmod.env_block(d)) == p
    assert pinmod.load_pin_env(pinmod.env_block(d))["c16"]["caps"] == dict(p.caps)


# ---- bound_for ---------------------------------------------------------------------------------------------
def test_bound_for_terms_and_margin():
    p = pin(inline_bound_margin_pct=10, max_tokens=900, inline_bound_fallback_tokens=4000)
    assert bound_for(10000, 3000, 500, 200, p) == ((10000 + 900) * 110 // 100, "projected")
    assert bound_for(1000, 3000, 500, 200, p) == ((3700 + 900) * 110 // 100, "last-call-plus")
    assert bound_for(None, None, None, None, p) == ((4000 + 900) * 110 // 100, "declared-fallback")
    assert bound_for(None, 3000, 500, None, p) == ((3500 + 900) * 110 // 100, "last-call-plus")
    assert bound_for(3700, 3000, 500, 200, p)[1] == "projected"  # a tie keeps the first term


@pytest.mark.parametrize("pct", [0, 7, 10, 12.5, 7.3, 0.1, 33.333, 100, 250])
def test_bound_for_margin_rounds_up_exactly(pct):
    p = pin(inline_bound_margin_pct=pct, max_tokens=0, inline_bound_fallback_tokens=0)
    num, den = pct.as_integer_ratio()
    for base in range(1, 400):
        b, _ = bound_for(base, None, None, None, p)
        assert type(b) is int
        assert b * 100 * den >= base * (100 * den + num) > (b - 1) * 100 * den  # smallest int >= base*(1+pct/100)
    assert bound_for(None, None, None, None, p) == (0, "declared-fallback")


@pytest.mark.parametrize("args", [(None, None, None, None), (0, 0, 0, 0), (0, None, 0, None), (None, 0, 0, 0)])
def test_bound_for_unknown_usage_falls_back(args):
    p = pin()
    assert bound_for(*args, pin=p) == ((4000 + 900) * 110 // 100, "declared-fallback")


def test_bound_for_partial_last_usage_is_used():
    """ARCH 5.1: the fallback only when neither last input nor last output is known."""
    p = pin()
    assert bound_for(None, 100, None, 0, p) == ((100 + 900) * 110 // 100, "last-call-plus")
    assert bound_for(None, 40000, None, 0, p) == ((40000 + 900) * 110 // 100, "last-call-plus")
    assert bound_for(None, None, 2000, 1500, p) == ((3500 + 900) * 110 // 100, "last-call-plus")
    assert bound_for(None, 40000, 0, 1500, p) == ((41500 + 900) * 110 // 100, "last-call-plus")


def test_bound_for_tool_results_without_last_usage_add_to_fallback():
    p = pin()
    assert bound_for(None, None, None, 10000, p) == ((4000 + 10000 + 900) * 110 // 100, "declared-fallback")


GARBAGE_TERMS = [-5, -1, "9", "x", 1.0, 1500.0, 45000.0, True, False, float("nan"), [], {}]


@pytest.mark.parametrize("pos", [0, 1, 2, 3])
@pytest.mark.parametrize("bad", GARBAGE_TERMS)
def test_bound_for_garbage_term_fails_closed(pos, bad):
    p = pin()
    args = [10000, 3000, 500, 200]
    args[pos] = bad
    assert bound_for(*args, pin=p) == (None, None)
    b, basis = bound_for(*args, pin=p)
    d = decide_inline(C16Question("r", "default", 0, 0, b, basis), p)
    assert (d.verdict, d.action, d.reason) == ("DENY", "halt", "invalid-question")


def test_bound_for_reviewer_case_float_tool_results_cannot_allow_past_cap():
    """Strands estimation threw (projected None), the adapter passed chars/4 as a float: no silent fallback."""
    p = pin(inline_bound_margin_pct=10, inline_bound_fallback_tokens=4000, max_tokens=900)
    b, basis = bound_for(None, 40000, 2000, 1500.0, p)
    assert (b, basis) == (None, None)
    d = decide_inline(C16Question("r", "default", 10000, 0, b, basis), p)
    assert (d.verdict, d.action) == ("DENY", "halt")
    b, basis = bound_for(None, 40000, 2000, 1500, p)
    assert (b, basis) == ((43500 + 900) * 110 // 100, "last-call-plus")
    d = decide_inline(C16Question("r", "default", 10000, 0, b, basis), p)
    assert (d.verdict, d.action) == ("DENY", "halt")  # 10000 + 48840 > 50000
    b, basis = bound_for(None, 40000, None, 0, p)
    assert basis == "last-call-plus" and b >= 40000 + 900


def test_bound_for_never_raises_on_bad_pin():
    for bad in (None, {}, "pin"):
        assert bound_for(1, 1, 1, 1, bad) == (None, None)
        b, basis = bound_for(1, 1, 1, 1, bad)
        d = decide_inline(C16Question("r", "default", 0, 0, b, basis), ENF)
        assert (d.verdict, d.action) == ("DENY", "halt")


def test_bound_never_below_actual_for_strands_loop():
    """In a Strands loop a call's input = last input + last output + tool results (ARCH 5.1)."""
    p = pin(inline_bound_margin_pct=0)
    for li in (1, 100, 5000):
        for lo in (0, 1, p.max_tokens):
            for tr in (0, 10, 999):
                b, _ = bound_for(None, li, lo, tr, p)
                assert b >= li + lo + tr + p.max_tokens


# ---- compare -----------------------------------------------------------------------------------------------
def test_compare():
    assert compare(5, 5) == "within" and compare(6, 5) == "over" and compare(0, 0) == "within"
    for bad in ((-1, 5), (5, None), (True, 5), (1.0, 2)):
        with pytest.raises(ValueError):
            compare(*bad)


# ---- purity / idempotence ----------------------------------------------------------------------------------
def test_purity_and_idempotence():
    qq, pp = q(CAP_DEFAULT + 1, 3, 7, tier="low"), pin(mode="observe")
    q0, p0 = copy.deepcopy(qq), copy.deepcopy(pp)
    first = decide_inline(qq, pp, "e" * 64)
    for _ in range(50):
        assert decide_inline(qq, pp, "e" * 64) == first  # a Strands retry re-entry gets the same answer
    assert qq == q0 and pp == p0
    hash(qq), hash(pp), hash(first)  # frozen, hashable: no mutable state inside
    with pytest.raises(dataclasses.FrozenInstanceError):
        qq.committed_tokens = 0
    with pytest.raises(dataclasses.FrozenInstanceError):
        pp.mode = "enforce"
    d = copy.deepcopy(PIN)
    PinnedC16.from_dict(d)
    assert d == PIN
    env = env_of(PIN)
    e0 = dict(env)
    PinnedC16.from_env(env)
    assert env == e0


def test_order_independence():
    qs = [q(n) for n in range(CAP_DEFAULT - 3, CAP_DEFAULT + 4)]
    fwd = [decide_inline(x, ENF) for x in qs]
    rev = [decide_inline(x, ENF) for x in reversed(qs)][::-1]
    assert fwd == rev


def test_decision_fields_match_contract_order():
    names = [f.name for f in dataclasses.fields(Decision)]
    assert names == ["control_ref", "control_id", "verdict", "reason", "measured_value", "threshold_value", "tier",
                     "mode", "limit_applied", "limit_value", "action", "bound_basis", "threshold_version",
                     "register_version", "threshold_sha256", "pin_sha256", "evaluator_name", "evaluator_sha256"]
    assert [f.name for f in dataclasses.fields(C16Question)] == [
        "run_id", "tier", "committed_tokens", "reserved_tokens", "bound_tokens", "bound_basis"]
    json.dumps(dataclasses.asdict(decide_inline(q(1), ENF)))
    json.dumps(dataclasses.asdict(decide_inline(None, None)))


# ---- source rules ------------------------------------------------------------------------------------------
def test_source_is_stdlib_small_and_has_no_io():
    src = open(CORE, encoding="utf-8").read()
    imports = sorted({ln.split()[1].split(".")[0] for ln in src.splitlines() if ln.startswith(("import ", "from "))})
    assert imports == ["dataclasses", "hashlib", "json", "typing"]
    for bad in ("open(", "os.", "time.", "datetime", "random", "global ", "print(", "environ", "__file__", "match ",
                "getenv", "import os", "sys."):
        assert bad not in src, bad
    assert len(base64.b64encode(gzip.compress(src.encode("utf-8")))) < 4000


def test_no_numeric_threshold_literals():
    import ast
    tree = ast.parse(open(CORE, encoding="utf-8").read())
    nums = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and type(n.value) in (int, float)}
    assert nums <= {0, 1, 100}, nums  # 0/1 are tuple indexes, 100 = percent


def test_register_sha256_matches_core():
    line = open(os.path.join(ROOT, "register", "c16_core.sha256"), encoding="utf-8").read()
    h = hashlib.sha256(open(CORE, "rb").read()).hexdigest()
    assert line == "%s  prooflab/evaluators/c16_core.py\n" % h


# ---- Python 3.9 compatibility ------------------------------------------------------------------------------
PY39_SCRIPT = r'''
import sys
sys.path.insert(0, sys.argv[1])
assert sys.version_info[:2] == (3, 9), sys.version
from prooflab.evaluators.c16_core import C16Question, PinnedC16, decide_inline, bound_for
import hashlib, json
d = {"schema": "ifabric.pin/1", "register": {"version": "v1", "sha256": "a" * 64},
     "c16": {"control_id": "ACN-COST-001", "threshold_version": "C16-v1", "version_date": "2026-10-06T00:00:00Z",
             "tiers": ["default", "low"], "default_tier": "default", "caps": {"default": 50000, "low": 20000},
             "safety_ceiling": 300000, "modes": ["enforce", "observe"], "mode": sys.argv[2],
             "bound": {"inline_bound_margin_pct": 10, "inline_bound_fallback_tokens": 4000, "max_tokens": 900}},
     "c7": {"declared_faults": []}}
text = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
p = PinnedC16.from_env({"IFABRIC_PIN_JSON": text, "IFABRIC_PIN_SHA256": hashlib.sha256(text.encode()).hexdigest(),
                        "IFABRIC_REGISTER_VERSION": "v1", "IFABRIC_REGISTER_SHA256": "a" * 64})
rows = []
for total in (49999, 50000, 50001, 300000, 300001):
    d = decide_inline(C16Question("r", "default", total, 0, 0, "projected"), p)
    rows.append("%d:%s:%s" % (total, d.verdict, d.action))
rows.append("bound:%d:%s" % bound_for(None, 3000, 500, 200, p))
rows.append("garbage:%s:%s" % (lambda d: (d.verdict, d.action))(decide_inline(None, p)))
rows.append("floatterm:%s:%s" % bound_for(None, 40000, 2000, 1500.0, p))
rows.append("partial:%d:%s" % bound_for(None, 40000, None, 0, p))
print(",".join(rows))
'''

PY39 = [x for x in (os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-local/.venv-py39/bin/python"),
                    "/usr/bin/python3") if os.path.exists(x)]


def _py39():
    for exe in PY39:
        out = subprocess.run([exe, "-c", "import sys;print(sys.version_info[:2]==(3,9))"],
                             capture_output=True, text=True)
        if out.stdout.strip() == "True":
            return exe
    pytest.skip("no Python 3.9 interpreter found")


def test_python39_compileall_and_table():
    exe = _py39()
    src = "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], 'exec')"
    r = subprocess.run([exe, "-B", "-c", src, CORE], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    exp = {
        "enforce": "49999:ALLOW:proceed,50000:ALLOW:proceed,50001:DENY:halt,300000:DENY:halt,300001:DENY:halt",
        "observe": "49999:ALLOW:proceed,50000:ALLOW:proceed,50001:DENY:proceed,300000:DENY:proceed,300001:DENY:halt",
    }
    for mode, want in exp.items():
        r = subprocess.run([exe, "-B", "-c", PY39_SCRIPT, ROOT, mode], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == want + ",bound:%d:last-call-plus,garbage:DENY:halt,floatterm:None:None,partial:%d:last-call-plus" % (
            (3700 + 900) * 110 // 100, (40000 + 900) * 110 // 100)
