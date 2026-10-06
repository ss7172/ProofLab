"""Test path setup. prooflab.contract is PR-01's package: until PR-01 merges, extend the `prooflab` package path
with its worktree (override with PR01_ROOT). One shim, test-only; the code under test imports prooflab.contract.*."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import prooflab  # noqa: E402

try:
    import prooflab.contract.ids  # noqa: F401
except ImportError:
    pr01 = os.environ.get("PR01_ROOT", "/Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/wt/PR-01-contracts")
    prooflab.__path__.append(os.path.join(pr01, "prooflab"))
