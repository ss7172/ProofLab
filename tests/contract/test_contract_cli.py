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
    expected = {
        "run": "prooflab.adapters.orchestrator.run:main", "refresh": "prooflab.store.snapshot:main",
        "postrun": "prooflab.adapters.postrun.cli:main", "humanloop": "prooflab.humanloop.runner:main",
        "collect": "prooflab.adapters.collectors.cli:main", "registry": "prooflab.registry.cli:main",
        "assess": "prooflab.query.cli:assess_main", "query": "prooflab.query.cli:main",
    }
    for verb, target in expected.items():
        assert cli.VERBS[verb][0] == target


def test_register_is_an_alias_of_registry(monkeypatch):
    seen = {}
    monkeypatch.setitem(cli.VERBS, "registry", ("prooflab.contract.ids:mint_cid", "x", "PR-11"))
    import prooflab.contract.ids as ids
    monkeypatch.setattr(ids, "mint_cid", lambda argv: seen.setdefault("argv", argv) and 0)
    assert cli.main(["register", "freeze", "v1"]) == 0
    assert seen["argv"] == ["freeze", "v1"]
