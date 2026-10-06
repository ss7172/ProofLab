"""tests/assurance (PR-19): the Assurance runtime bundle, its shim, the invoke helper, the live shapes (G-01/03/22).

Runs on both venvs from the repo root:  $PY312 -m pytest -q -p no:cacheprovider tests/assurance
                                        $PY39  -m pytest -q -p no:cacheprovider tests/assurance
Arth's code is used as-is. Until PR-00 syncs handoff-3 into prooflab/servicenow, the in-process imports of his
package are served from his master copy, handoffs/ifabric-handoff-3/code/prooflab (read-only, unchanged).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ARTH = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "code", "prooflab")
if not os.path.exists(os.path.join(ROOT, "prooflab", "servicenow", "nemotron.py")):
    import prooflab.servicenow  # noqa: E402
    import prooflab.tests  # noqa: E402
    prooflab.servicenow.__path__.insert(0, os.path.join(ARTH, "servicenow"))
    prooflab.tests.__path__.insert(0, os.path.join(ARTH, "tests"))
