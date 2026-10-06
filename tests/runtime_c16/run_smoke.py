"""Tiny runner for interpreters without pytest:  python tests/runtime_c16/run_smoke.py"""
import importlib
import os
import sys
import traceback
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))


def main():
    ok = fail = skip = 0
    for modname in ("test_ep1_unit", "test_ep1_strands"):
        mod = importlib.import_module(modname)
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            try:
                getattr(mod, name)()
                ok += 1
                print("PASS", modname, name)
            except unittest.SkipTest as e:
                skip += 1
                print("SKIP", modname, name, e)
            except Exception:
                fail += 1
                print("FAIL", modname, name)
                traceback.print_exc()
    print("passed=%d failed=%d skipped=%d" % (ok, fail, skip))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
