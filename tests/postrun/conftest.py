"""PR-23 test scaffold. Before PR-01 / PR-02 merge, prooflab.contract and prooflab.evaluators.c16_core live in
sibling worktrees; this one small site extends the package paths to them (nothing is copied). After the merge
the imports resolve in this tree and nothing here does anything. Override with PROOFLAB_SIBLING_ROOTS=a:b."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

WT = os.path.dirname(ROOT)
SIBLINGS = [p for p in os.environ.get("PROOFLAB_SIBLING_ROOTS", "").split(os.pathsep) if p] or [
    os.path.join(WT, "PR-01-contracts"), os.path.join(WT, "PR-02-c16core")]


def _extend(pkg_name, rel):
    pkg = importlib.import_module(pkg_name)
    for root in SIBLINGS:
        d = os.path.join(root, *rel)
        if os.path.isdir(d) and d not in pkg.__path__:
            pkg.__path__.append(d)


try:
    importlib.import_module("prooflab.contract.record")
    importlib.import_module("prooflab.evaluators.c16_core")
except ImportError:
    _extend("prooflab", ["prooflab"])
    _extend("prooflab.evaluators", ["prooflab", "evaluators"])
    for _m in [m for m in sys.modules if m.startswith("prooflab.contract") or m.startswith("prooflab.evaluators.")]:
        del sys.modules[_m]


def sha_file():
    own = os.path.join(ROOT, "register", "c16_core.sha256")
    if os.path.exists(own):
        return own
    for root in SIBLINGS:
        p = os.path.join(root, "register", "c16_core.sha256")
        if os.path.exists(p):
            return p
    raise RuntimeError("register/c16_core.sha256 not found")
