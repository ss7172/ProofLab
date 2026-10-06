"""Path wiring for PR-11 before PR-01 merges.

Run as: PYTHONPATH=<wt>/PR-01-contracts:<this worktree> python -m pytest -q -p no:cacheprovider tests/registry
Whichever `prooflab` package wins the import, the `prooflab/` and `prooflab/registry/` directories of every sys.path
entry (PR-01's worktree and this one) are merged into its search path. After the merge there is one tree and the
loop adds nothing.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

import prooflab  # noqa: E402

_entries = [p for p in sys.path if p]
for base in _entries:
    d = os.path.join(base, "prooflab")
    if os.path.isdir(d) and d not in list(prooflab.__path__):
        prooflab.__path__.append(d)

import prooflab.registry  # noqa: E402

for base in _entries:
    d = os.path.join(base, "prooflab", "registry")
    if os.path.isdir(d) and d not in list(prooflab.registry.__path__):
        prooflab.registry.__path__.append(d)
