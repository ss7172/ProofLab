import copy
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import dig, load_cases, run_case  # noqa: E402

CASES = load_cases()
IDS = [c["name"] for c in CASES]


def test_fixture_count():
    assert len(CASES) >= 30


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_case_expectations(case):
    out = run_case(case)
    for path, want in case["expect"].items():
        assert dig(out, path) == want, "%s: %s" % (case["name"], path)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_case_is_json_safe_and_findings_valid(case):
    from prooflab.contract import finding as F, verdicts as V
    out = run_case(case)
    json.dumps(out, sort_keys=True)
    assert out["requirement_verdict"] in V.ASSESSMENT_VERDICTS
    assert out["deficiency"] in ("design", "operation", "both", "none")
    if out["requirement_verdict"] == "NOT_ASSESSED":
        assert out["finding"] is None
    elif out["as_of"]:
        assert F.validate_finding(out["finding"]) == []
        assert out["finding"]["verdict"] == V.finding_verdict(out["requirement_verdict"])
        assert out["finding"]["summary"].startswith("deficiency: " + out["deficiency"])


def _shuffle(x, rnd):
    if isinstance(x, list):
        y = [_shuffle(v, rnd) for v in x]
        rnd.shuffle(y)
        return y
    if isinstance(x, dict):
        keys = list(x)
        rnd.shuffle(keys)
        return dict((k, _shuffle(x[k], rnd)) for k in keys)
    return x


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_stateless_repeat_shuffled_threads(case):
    base = run_case(case)
    for _ in range(3):
        assert run_case(copy.deepcopy(case)) == base
    rnd = random.Random(7)
    for _ in range(5):
        shuffled = copy.deepcopy(case)
        shuffled["inputs"] = _shuffle(shuffled["inputs"], rnd)
        assert run_case(shuffled) == base, "order dependence"
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(lambda _: run_case(copy.deepcopy(case)), range(8)))
    assert all(r == base for r in results)


def test_inputs_not_mutated():
    for case in CASES:
        before = copy.deepcopy(case)
        run_case(case)
        assert case == before
