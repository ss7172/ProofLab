import os
import sys

import prooflab

for _p in list(sys.path):
    _cand = os.path.join(_p or ".", "prooflab")
    if os.path.isdir(os.path.join(_cand, "contract")) and _cand not in prooflab.__path__:
        prooflab.__path__.append(_cand)
