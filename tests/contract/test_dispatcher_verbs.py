"""Every registered verb resolves to a real main(argv): `python3 -m prooflab <verb> --help` exits 0 (PR-25).

Run on this interpreter (the suite runs it on 3.9 and 3.12) and, when present, on the system /usr/bin/python3
(macOS 3.9.6, the laptop hub's interpreter). --help also catches a main that reads files or env before parsing.
"""
import os
import subprocess
import sys

import pytest

from prooflab import cli

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYSTEM_PY = "/usr/bin/python3"
INTERPRETERS = [sys.executable] + ([SYSTEM_PY] if os.path.exists(SYSTEM_PY) and SYSTEM_PY != sys.executable else [])


def _env():
    env = dict((k, v) for k, v in os.environ.items() if k != "PYTHONPATH")
    env["PYTHONPATH"] = ROOT
    return env


def test_every_verb_target_exists_in_process():
    import importlib
    for verb in cli.VERBS:
        module, func = cli._split(cli.VERBS[verb][0])
        assert callable(getattr(importlib.import_module(module), func, None)), verb


@pytest.mark.parametrize("python", INTERPRETERS)
@pytest.mark.parametrize("verb", sorted(cli.VERBS))
def test_verb_help_exits_zero(python, verb):
    proc = subprocess.run([python, "-m", "prooflab", verb, "--help"], cwd=ROOT, env=_env(), stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
    assert proc.returncode == 0, (verb, python, proc.stderr[-400:])
    assert proc.stdout.strip(), (verb, python)
