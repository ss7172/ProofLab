"""Until the sibling PRs merge, `prooflab.contract` lives in another worktree. PROOFLAB_SIBLINGS (os.pathsep-separated
worktree roots) extends the `prooflab` package path so it resolves; after the merge the variable is not needed."""
import os
import sys

import prooflab

for root in filter(None, os.environ.get("PROOFLAB_SIBLINGS", "").split(os.pathsep)):
    path = os.path.join(root, "prooflab")
    if path not in prooflab.__path__:
        prooflab.__path__.append(path)
here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if here not in sys.path:
    sys.path.insert(0, here)
