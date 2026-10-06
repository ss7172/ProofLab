"""PR-15a test scaffold. prooflab.contract / prooflab.registry belong to PR-01 and are not in this branch yet.
Until PR-01 merges, set PR01_ROOT (default: the sibling worktree) and its prooflab/ dir is appended to the
`prooflab` package path. The ONE coupling site; after the merge it is a no-op.

Run:  PYTHONPATH=<this worktree> $PY39 -m pytest -q -p no:cacheprovider tests/query
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import prooflab  # noqa: E402

try:
    import prooflab.contract  # noqa: F401
except ImportError:
    pr01 = os.environ.get("PR01_ROOT", "/Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/wt/PR-01-contracts")
    sibling = os.path.join(pr01, "prooflab")
    if os.path.isdir(os.path.join(sibling, "contract")) and sibling not in prooflab.__path__:
        prooflab.__path__.append(sibling)
