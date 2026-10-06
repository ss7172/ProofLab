"""PR-08a test scaffold. Until PR-01 (prooflab.contract) is merged, borrow its package directory:
set PROOFLAB_CONTRACT_ROOT to a checkout of PR-01 (default: the sibling worktree). Inert once merged."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import prooflab  # noqa: E402

try:
    import prooflab.contract  # noqa: F401
except ImportError:
    _alt = os.environ.get("PROOFLAB_CONTRACT_ROOT",
                          os.path.join(os.path.dirname(ROOT), "PR-01-contracts"))
    _pkg = os.path.join(_alt, "prooflab")
    if os.path.isdir(os.path.join(_pkg, "contract")):
        prooflab.__path__.append(_pkg)
