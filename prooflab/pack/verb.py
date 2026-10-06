"""`python3 -m prooflab pack <sub>` router (PR-49). Stdlib, Python 3.9.

`pack lint <dir>` -> prooflab.pack.redflag (the red-flag lint over a staged pack); every other sub-verb goes to
prooflab.pack.build:main unchanged, so build / scan / verify / index / root behave exactly as before.
"""
from __future__ import annotations

import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["lint"]:
        from prooflab.pack import redflag
        return redflag.main(argv[1:])
    from prooflab.pack import build
    rc = build.main(argv)
    if argv[:1] in (["-h"], ["--help"]):
        print("python3 -m prooflab pack lint <staged pack dir>  red-flag lint (exit 2 = do not submit)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
