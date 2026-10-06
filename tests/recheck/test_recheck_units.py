"""Independence, purity and sensitivity checks for the rechecker."""
import copy
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import ROOT, load_cases  # noqa: E402
from prooflab.recheck.rechecker import derive_tier, recheck_case  # noqa: E402

SRC = os.path.join(ROOT, "prooflab", "recheck")
CASES = dict((c["name"], c) for c in load_cases())


def _py_files():
    return [os.path.join(SRC, f) for f in sorted(os.listdir(SRC)) if f.endswith(".py")]


def test_grep_no_import_of_evaluators_except_c16_core():
    pat = re.compile(r"^\s*(?:from\s+prooflab\.evaluators(?:\.(\w+))?\s+import\s+([\w, ]+)|import\s+prooflab\.evaluators\.(\w+))",
                     re.M)
    for f in _py_files():
        text = open(f).read()
        for m in pat.finditer(text):
            mods = set(x.strip() for x in (m.group(2) or "").split(",") if x.strip())
            if m.group(1):
                mods.add(m.group(1))
            if m.group(3):
                mods.add(m.group(3))
            assert mods <= {"c16_core"}, "%s imports %s" % (f, mods)
        for bad in ("evaluators.c16 ", "evaluators.c7", "evaluators.c9", "evaluators.claim", "evaluators import c16,"):
            assert bad not in text.replace("evaluators.c16_core", ""), (f, bad)


def test_grep_no_threshold_literals():
    # no cap, gap, share or percent number may appear as a literal in the rechecker (all come from the pin)
    banned = re.compile(r"\b(?:5000|8000|10000|20000|40000|300000|150000|900|800|10)\b")
    for f in _py_files():
        for n, line in enumerate(open(f), 1):
            code = line.split("#")[0]
            if code.strip().startswith(('"""', "'''")):
                continue
            assert not banned.search(code), "%s:%d %s" % (f, n, line.strip())


def test_stdlib_only():
    std = {"datetime", "prooflab"}
    for f in _py_files():
        for m in re.finditer(r"^\s*(?:from|import)\s+(\w+)", open(f).read(), re.M):
            assert m.group(1) in std, (f, m.group(1))


@pytest.mark.parametrize("name", sorted(CASES))
def test_pure_and_does_not_mutate(name):
    case = CASES[name]
    before = copy.deepcopy(case)
    a = recheck_case(case)
    assert recheck_case(copy.deepcopy(case)) == a
    assert case == before


def test_sensitivity_cap_from_pin_only():
    c = copy.deepcopy(CASES["c16_satisfied"])
    assert recheck_case(c)["verdict"] == "SATISFIED"
    c["pin"]["c16"]["caps"]["standard"] = 10
    assert recheck_case(c)["verdict"] == "BREACHED"


def test_c7_gap_rule_is_strictly_less_than_G():
    c = copy.deepcopy(CASES["c7_stalled_step_is_violating_gap"])
    c["pin"]["gap_max_ms"] = 10 ** 6
    assert recheck_case(c)["verdict"] == "SATISFIED"
    c["pin"]["gap_max_ms"] = 25900  # the stalled gap is exactly 25.9 s: not < G, so violating
    assert recheck_case(c)["gap_verdict"] == "BREACHED"


def test_c9_two_sided_default_and_increase_only():
    c = copy.deepcopy(CASES["c9_faster_breached_two_sided"])
    assert recheck_case(c)["verdict"] == "BREACHED"
    c["pin"]["limit_direction"] = "increase"
    assert recheck_case(c)["verdict"] == "SATISFIED"


def test_c9_missing_datapoint_never_healthy():
    assert recheck_case(CASES["c9_missing_datapoint_indeterminate"])["verdict"] == "INDETERMINATE"


def test_tier_rule_unknown_falls_to_default():
    assert derive_tier("impact=high->high;*->standard", {"impact": "low"}, "standard") == "standard"
    assert derive_tier("impact=high->high", {"impact": "low"}, "standard") == "standard"
    assert derive_tier("impact=high->high;*->standard", {"impact": "high"}, "standard") == "high"
