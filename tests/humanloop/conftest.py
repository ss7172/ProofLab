"""Test bootstrap. Before PR-01 merges, prooflab.contract lives in the PR-01 worktree: set
PROOFLAB_CONTRACT_ROOT=<that worktree> and its prooflab/ directory is appended to the package path
(ours stays first, so nothing of ours is shadowed). After the merge the variable is not needed."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import prooflab  # noqa: E402

if importlib.util.find_spec("prooflab.contract") is None:
    extra = os.environ.get("PROOFLAB_CONTRACT_ROOT", "")
    if extra:
        prooflab.__path__.append(os.path.join(extra, "prooflab"))

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:   # --import-mode=importlib does not add the test dir
    sys.path.insert(0, HERE)
