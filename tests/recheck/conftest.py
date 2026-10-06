"""Setup for tests/recheck. Before PR-01/02/09a merge run with
   PYTHONPATH=<wt>/PR-09a-evaluators:<wt>/PR-02-c16core:<wt>/PR-01-contracts  (any order; documented in the PR)
The conftest extends the `prooflab` / `prooflab.evaluators` package paths from PYTHONPATH roots (a regular package in
this worktree would otherwise shadow the siblings). After the merges this is a no-op. Fixtures: tests/evaluators/fixtures
here, else PROOFLAB_FIXTURES, else the PR-09a sibling worktree."""
import glob
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _roots():
    return [p for p in os.environ.get("PYTHONPATH", "").split(":") if p and os.path.isdir(os.path.join(p, "prooflab"))]


def _extend(modname, sub):
    try:
        mod = importlib.import_module(modname)
    except ImportError:
        return
    for r in _roots():
        p = os.path.join(r, *sub)
        if os.path.isdir(p) and p not in mod.__path__:
            mod.__path__.append(p)


_extend("prooflab", ["prooflab"])
try:
    importlib.import_module("prooflab.evaluators")
    _extend("prooflab.evaluators", ["prooflab", "evaluators"])
except ImportError:
    pass


def fixtures_dir():
    cands = [os.environ.get("PROOFLAB_FIXTURES"), os.path.join(ROOT, "tests", "evaluators", "fixtures")]
    cands += [os.path.join(r, "tests", "evaluators", "fixtures") for r in _roots()]
    for c in cands:
        if c and os.path.isdir(c) and glob.glob(os.path.join(c, "*.json")):
            return c
    raise RuntimeError("no evaluator fixtures found (set PROOFLAB_FIXTURES or PYTHONPATH to the PR-09a worktree)")


def load_cases():
    out = []
    for p in sorted(glob.glob(os.path.join(fixtures_dir(), "*.json"))):
        with open(p) as fh:
            out.append(json.load(fh))
    return out
