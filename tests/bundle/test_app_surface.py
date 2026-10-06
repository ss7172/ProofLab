"""ifabric_app.SURFACE against the runtime modules' source, by AST (no import: runs without Strands).

Source tree: $IFABRIC_SRC_ROOT if set (e.g. a scratch tree of the sibling PRs' HEADs), else this repo when
the real adapters are in it (after PR-02/03/04/05/07 merge), else tests/bundle/stubs.
"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
APP = os.path.join(REPO, "agents", "ifabric-customer", "ifabric_app.py")


def _surface():
    for node in ast.parse(open(APP).read()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "SURFACE" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("ifabric_app.py has no SURFACE table")


def _src_root():
    env = os.environ.get("IFABRIC_SRC_ROOT")
    if env:
        return env
    if os.path.isfile(os.path.join(REPO, "adapters", "runtime", "model_call.py")):
        return REPO
    return os.path.join(HERE, "stubs")


def _top_names(path):
    names = set()
    for n in ast.parse(open(path).read()).body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            names.add(n.name)
        elif isinstance(n, ast.Assign):
            names.update(t.id for t in n.targets if isinstance(t, ast.Name))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split(".")[0] for a in n.names)
    return names


def test_every_surface_name_exists_in_the_runtime_modules():
    root, missing = _src_root(), []
    for mod, names in sorted(_surface().items()):
        path = os.path.join(root, *mod.split(".")) + ".py"
        assert os.path.isfile(path), "%s missing under %s" % (mod, root)
        have = _top_names(path)
        missing += ["%s.%s" % (mod, n) for n in names if n not in have]
    assert not missing, "ifabric_app uses names the modules under %s do not define: %s" % (root, missing)


def test_surface_covers_the_bundle_manifest():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bundle_agent_surf", os.path.join(REPO, "tools", "bundle_agent.py"))
    ba = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ba)
    required = set(ba.module_name(p) for p in ba.DEFAULT_REQUIRED)
    assert set(_surface()) <= required          # everything the app imports is embedded (fail closed)
    assert not [m for m in required if m.startswith("prooflab.contract")]


def test_app_has_no_limit_literals_and_no_old_facade():
    text = open(APP).read()
    for old in ("startup.start(", "hooks.providers(", "http_event_hooks(", "tool_call.wrap(", "judgment.decide("):
        assert old not in text
    assert '"max_tokens": st["pin"].max_tokens' in text
    assert "max_tokens\": 9" not in text
