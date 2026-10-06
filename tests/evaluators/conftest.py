"""Shared setup for tests/evaluators (reusable by PR-10's rechecker: `run_case`, `load_cases`).

Before PR-01 / PR-02 merge, run with
    PYTHONPATH=<wt>/PR-01-contracts:<wt>/PR-02-c16core  (any order)
or set PROOFLAB_SIBLINGS to those worktree roots (colon separated); this file then extends the `prooflab` and
`prooflab.evaluators` package paths so the sibling modules resolve (a regular package would otherwise shadow them).
After the merges this is a no-op.
"""
import glob
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIXTURES = os.path.join(HERE, "fixtures")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_WT = os.path.join(os.path.dirname(ROOT))
_DEFAULT = [os.path.join(_WT, "PR-01-contracts"), os.path.join(_WT, "PR-02-c16core")]


def _extend():
    sibs = [p for p in (os.environ.get("PROOFLAB_SIBLINGS", "").split(":") + os.environ.get("PYTHONPATH", "").split(":"))
            if p and os.path.isdir(os.path.join(p, "prooflab"))]
    sibs = sibs or _DEFAULT
    pkg = importlib.import_module("prooflab")
    for s in sibs:
        p = os.path.join(s, "prooflab")
        if os.path.isdir(p) and p not in pkg.__path__:
            pkg.__path__.append(p)
    ev = importlib.import_module("prooflab.evaluators")
    for s in sibs:
        p = os.path.join(s, "prooflab", "evaluators")
        if os.path.isdir(p) and p not in ev.__path__:
            ev.__path__.append(p)


try:
    importlib.import_module("prooflab.contract.verdicts")
    importlib.import_module("prooflab.evaluators.c16_core")
except ImportError:
    _extend()

from prooflab.evaluators import c16, c16_core, c7, c9  # noqa: E402


def load_cases():
    out = []
    for p in sorted(glob.glob(os.path.join(FIXTURES, "*.json"))):
        with open(p) as fh:
            out.append(json.load(fh))
    return out


def run_case(case):
    """Run one fixture case through its evaluator; returns the Assessment as a dict."""
    from dataclasses import asdict
    i = dict(case["inputs"])
    kind = case["evaluator"]
    if kind == "c16.assess_run":
        pin = c16_core.PinnedC16.from_dict(case["pin"], "e" * 64)
        res = c16.assess_run(i["run_id"], i["calls"], i["scenario_attrs"], i["decisions"], pin,
                             i["completeness"], i["as_of"])
    elif kind == "c7.assess_run":
        exp = c7.expected_events(i["run_id"], i["gateway_actions"], i["refusals"], i["workflow_events"], i["stops"], case["pin"])
        res = c7.assess_run(i["run_id"], exp, i["observed"], i["link_gaps"], case["pin"], i["as_of"])
    elif kind == "c9.assess_run":
        res = c9.assess_run(i["run_id"], i["windows"], case["pin"], i["as_of"])
    else:
        raise ValueError(kind)
    return asdict(res)


def dig(d, path):
    cur = d
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur
