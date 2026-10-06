"""The one `python3 -m prooflab` dispatcher (G-19)."""
import os
import subprocess
import sys

from prooflab import cli

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# FEATURE-MAP risk line: run, registry, query, refresh, pack, humanloop, console, watch, tail, recheck.
PLANNED = ("run", "registry", "query", "refresh", "pack", "humanloop", "console", "watch", "tail", "recheck",
           "assess", "collect", "postrun")


def test_planned_verbs_are_registered():
    assert set(PLANNED) <= set(cli.VERBS)
    for verb, (target, text, owner) in cli.VERBS.items():
        assert ":" in target and text and owner


def test_help_lists_every_verb(capsys):
    assert cli.main(["--help"]) == 0
    out = capsys.readouterr().out
    for verb in cli.VERBS:
        assert "  " + verb in out


def test_no_args_is_usage(capsys):
    assert cli.main([]) == cli.EXIT_USAGE


def test_unknown_verb(capsys):
    assert cli.main(["nope"]) == cli.EXIT_USAGE
    assert "unknown verb" in capsys.readouterr().err


def test_unbuilt_verb_says_so(capsys, monkeypatch):
    monkeypatch.setitem(cli.VERBS, "ghost", ("prooflab.no_such_module_xyz:main", "x", "PR-99"))
    assert cli.main(["ghost"]) == cli.EXIT_NOT_BUILT
    assert "not built yet" in capsys.readouterr().err


def test_dispatch_passes_argv(monkeypatch):
    import types
    mod = types.ModuleType("prooflab_fake_verb")
    seen = []
    mod.main = lambda argv: seen.append(argv) or 7
    monkeypatch.setitem(sys.modules, "prooflab_fake_verb", mod)
    monkeypatch.setitem(cli.VERBS, "fake", ("prooflab_fake_verb:main", "x", "PR-01"))
    monkeypatch.setattr(cli, "is_built", lambda verb: True)
    assert cli.main(["fake", "--x", "1"]) == 7 and seen == [["--x", "1"]]


def test_module_entry_point():
    proc = subprocess.run([sys.executable, "-m", "prooflab", "--help"], cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    assert proc.returncode == 0 and "humanloop" in proc.stdout


def test_every_target_lives_under_prooflab():
    """FEATURE-MAP R1: laptop-side code imports as prooflab.* (the judge runs it from the unzipped pack)."""
    for verb, (target, _text, _owner) in cli.VERBS.items():
        assert target.startswith("prooflab."), (verb, target)


def test_routes_match_the_owners_modules():
    """The module paths the owning PRs' branches actually ship (fix round 2)."""
    expected = {
        "run": "prooflab.adapters.orchestrator.run:main", "registry": "prooflab.registry:main",
        "query": "prooflab.query.cli:main", "assess": "prooflab.query.cli:assess_main",
        "refresh": "prooflab.store.snapshot:main", "pack": "prooflab.pack.build:main",
        "humanloop": "prooflab.humanloop.runner:main", "console": "prooflab.console.server:main",
        "watch": "prooflab.watch.cli:main", "tail": "prooflab.watch.tail:main",
        "recheck": "prooflab.recheck.rechecker:main", "collect": "prooflab.adapters.collectors:main",
        "postrun": "prooflab.adapters.postrun.c16_replay:main", "servicenow": "prooflab.servicenow.cli:main",
    }
    assert {v: t for v, (t, _x, _o) in cli.VERBS.items()} == expected


def test_registry_subdispatcher(capsys, monkeypatch):
    import types
    import prooflab.registry as reg
    assert cli.is_built("registry")
    assert reg.main(["--help"]) == 0 and "freeze" in capsys.readouterr().out
    assert reg.main(["nope"]) == reg.EXIT_USAGE
    monkeypatch.setitem(reg.SUBVERBS, "ghost", ("prooflab.registry.no_such_xyz", "x"))
    assert reg.main(["ghost"]) == reg.EXIT_NOT_BUILT
    mod = types.ModuleType("prooflab_fake_freeze")
    seen = []
    mod.main = lambda argv: seen.append(argv) or 0
    monkeypatch.setitem(sys.modules, "prooflab_fake_freeze", mod)
    monkeypatch.setitem(reg.SUBVERBS, "freeze", ("prooflab_fake_freeze", "x"))
    import importlib.util
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda n, *a: object() if n == "prooflab_fake_freeze" else real(n, *a))
    assert cli.main(["registry", "freeze", "v1"]) == 0 and seen == [["v1"]]


def test_missing_function_in_a_built_module_exits_not_built(capsys, monkeypatch):
    monkeypatch.setitem(cli.VERBS, "ghost", ("prooflab.contract.ids:no_such_main", "x", "PR-99"))
    assert cli.main(["ghost"]) == cli.EXIT_NOT_BUILT
    assert "has no no_such_main()" in capsys.readouterr().err


def test_register_is_an_alias_of_registry(monkeypatch):
    seen = {}
    monkeypatch.setitem(cli.VERBS, "registry", ("prooflab.contract.ids:mint_cid", "x", "PR-11"))
    import prooflab.contract.ids as ids
    monkeypatch.setattr(ids, "mint_cid", lambda argv: seen.setdefault("argv", argv) and 0)
    assert cli.main(["register", "freeze", "v1"]) == 0
    assert seen["argv"] == ["freeze", "v1"]
