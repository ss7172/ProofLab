"""Test-only seam: until PR-01 (prooflab/contract/) merges, `PYTHONPATH=<PR-01 worktree>:<this worktree>` makes the
contract importable. Two checkouts both define a `prooflab` package, so the first one on sys.path would shadow the
other; this adds every sys.path entry's prooflab/ that holds `contract/` to prooflab.__path__. A no-op after the merge."""
import os
import sys

import prooflab

for _p in list(sys.path):
    _cand = os.path.join(_p or ".", "prooflab")
    if os.path.isdir(os.path.join(_cand, "contract")) and _cand not in prooflab.__path__:
        prooflab.__path__.append(_cand)
