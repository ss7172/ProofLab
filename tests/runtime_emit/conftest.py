"""Until PR-01 is merged, this worktree's own prooflab/ package (PR-00) has no `contract`.
Merge any sys.path entry that carries prooflab/contract (PYTHONPATH=<PR-01 worktree>) into it."""
import os
import sys

import prooflab

for entry in list(sys.path):
    pkg = os.path.join(entry or ".", "prooflab")
    if os.path.isdir(os.path.join(pkg, "contract")) and pkg not in prooflab.__path__:
        prooflab.__path__.append(pkg)
