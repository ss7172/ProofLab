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

# Synthetic test values (fixtures, not thresholds of record).
CAP_LOW, CAP_DEFAULT, CEILING = 20000, 50000, 300000
PIN = dict(cap_tier_default=CAP_DEFAULT, cap_tier_low=CAP_LOW, default_tier="default", safety_ceiling=CEILING,
           mode="enforce", inline_modes="enforce,observe", inline_bound_margin_pct=10,
           inline_bound_fallback_tokens=4000, max_tokens=900, threshold_version="C16-v1",
           version="v1", sha256="a" * 64, declared_faults="suppress-record:ifabric-it:tool.call:1")


def pin(**kw):
    d = dict(PIN)
    d.update(kw)
    return PinnedC16.from_dict(d, "b" * 64)


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


@pytest.mark.parametrize("change", [
    dict(cap_tier_default=0), dict(cap_tier_default=-1), dict(cap_tier_default="x"), dict(cap_tier_default=1.5),
    dict(cap_tier_default=True), dict(safety_ceiling=CAP_DEFAULT - 1), dict(safety_ceiling=None),
    dict(mode="audit"), dict(mode=None), dict(inline_modes="observe"), dict(inline_modes="enforce,observe,x"),
    dict(default_tier="missing"), dict(inline_bound_margin_pct=-1), dict(inline_bound_margin_pct=12.5),
    dict(inline_bound_fallback_tokens=None), dict(max_tokens=-900), dict(threshold_version=""),
    dict(version=None), dict(sha256=None),
])
def test_invalid_pin_refused_at_construction(change):
    with pytest.raises(Exception):
        pin(**change)


def test_pin_without_caps_refused():
    d = {k: v for k, v in PIN.items() if not k.startswith("cap_tier_")}
    with pytest.raises(ValueError):
        PinnedC16.from_dict(d)


def test_pin_from_dict_coerces_integral_strings_and_floats():
    p = pin(cap_tier_default=str(CAP_DEFAULT), safety_ceiling=float(CEILING), inline_bound_margin_pct=10.0,
            inline_modes=["enforce", "observe"])
    assert dict(p.caps)["default"] == CAP_DEFAULT and p.safety_ceiling == CEILING and p.inline_bound_margin_pct == 10
    assert p.inline_modes == ("enforce", "observe") and p.caps == (("default", CAP_DEFAULT), ("low", CAP_LOW))


def test_pin_from_json_checks_sha256():
    text = json.dumps(PIN, sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    p = PinnedC16.from_json(text, h.upper())
    assert p.pin_sha256 == h and p.register_version == "v1" and p.register_sha256 == "a" * 64
    assert PinnedC16.from_json(text.encode("utf-8"), h) == p
    with pytest.raises(ValueError):
        PinnedC16.from_json(text, "0" * 64)
    with pytest.raises(ValueError):
        PinnedC16.from_json("[]", hashlib.sha256(b"[]").hexdigest())


def test_pin_prefers_register_version_keys():
    p = PinnedC16.from_dict(dict(PIN, register_version="v1.1", register_sha256="d" * 64))
    assert (p.register_version, p.register_sha256) == ("v1.1", "d" * 64)


# ---- bound_for ---------------------------------------------------------------------------------------------
def test_bound_for_terms_and_margin():
    p = pin(inline_bound_margin_pct=10, max_tokens=900, inline_bound_fallback_tokens=4000)
    assert bound_for(10000, 3000, 500, 200, p) == ((10000 + 900) * 110 // 100, "projected")
    assert bound_for(1000, 3000, 500, 200, p) == ((3700 + 900) * 110 // 100, "last-call-plus")
    assert bound_for(None, None, None, None, p) == ((4000 + 900) * 110 // 100, "declared-fallback")
    assert bound_for(None, 3000, 500, None, p) == ((3500 + 900) * 110 // 100, "last-call-plus")
    assert bound_for(3700, 3000, 500, 200, p)[1] == "projected"  # a tie keeps the first term


def test_bound_for_margin_rounds_up():
    p = pin(inline_bound_margin_pct=7, max_tokens=0, inline_bound_fallback_tokens=0)
    for base in range(1, 400):
        b, _ = bound_for(base, None, None, None, p)
        assert b * 100 >= base * 107 and (b - 1) * 100 < base * 107
    assert bound_for(None, None, None, None, p) == (0, "declared-fallback")


def test_bound_for_unknown_usage_treated_as_missing():
    p = pin()
    fb = bound_for(None, None, None, None, p)
    for args in ((0, 0, 0, 0), (-5, -1, 7, 0), (None, 100, None, 0), ("9", 1.0, 2, 0), (True, 1, 1, -1),
                 (None, 1, 1, "x")):
        assert bound_for(*args, pin=p) == fb, args


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
    d = dict(PIN)
    PinnedC16.from_dict(d)
    assert d == PIN


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
    for bad in ("open(", "os.", "time.", "datetime", "random", "global ", "print(", "environ", "__file__", "match "):
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
p = PinnedC16.from_dict(dict(cap_tier_default=50000, cap_tier_low=20000, default_tier="default",
    safety_ceiling=300000, mode=sys.argv[2], inline_modes="enforce,observe", inline_bound_margin_pct=10,
    inline_bound_fallback_tokens=4000, max_tokens=900, threshold_version="C16-v1", version="v1", sha256="a" * 64))
rows = []
for total in (49999, 50000, 50001, 300000, 300001):
    d = decide_inline(C16Question("r", "default", total, 0, 0, "projected"), p)
    rows.append("%d:%s:%s" % (total, d.verdict, d.action))
rows.append("bound:%d:%s" % bound_for(None, 3000, 500, 200, p))
rows.append("garbage:%s:%s" % (lambda d: (d.verdict, d.action))(decide_inline(None, p)))
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
        assert r.stdout.strip() == want + ",bound:%d:last-call-plus,garbage:DENY:halt" % ((3700 + 900) * 110 // 100)
