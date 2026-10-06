"""Two-stage layout (decision D-B) and the prune/strip fixes: tools/bundle_agent.py --layout two-stage and the
buildspecs tools/make_ifabric_agents.py writes. Stdlib + pytest; Python 3.9+ (strip needs ast.unparse).

With IFABRIC_SRC_ROOT=<a tree holding the real prooflab/ and adapters/> the real-source tests run too.
"""
import base64
import gzip
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
STUBS = os.path.join(HERE, "stubs")
REAL = os.environ.get("IFABRIC_SRC_ROOT")
FORBIDDEN = "agent" + ".py"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BA = _load(os.path.join(REPO, "tools", "bundle_agent.py"), "bundle_agent_ts")
sys.path.insert(0, os.path.join(REPO, "tools"))
MK = _load(os.path.join(REPO, "tools", "make_ifabric_agents.py"), "make_ifabric_agents_ts")
GATE_RX = re.compile(r"(?:evaluator[_.]sha256|c16_core[_a-z]*sha256|C16_CORE_SHA256)\W{0,8}([0-9a-f]{64})", re.I)

ENTRY = (
    "import prooflab.evaluators.c16_core as core\n"
    "import adapters.runtime.startup as st\n"
    "import adapters.runtime.j2 as j2\n"
    "import ifabric_app\n"
    "RESULT = core.decide_inline(None, None).action\n"
    "APP = ifabric_app.VALUE\n"
)


_BUNDLED_ROOTS = ("prooflab", "adapters", "ifabric_app", BA.BASE_MODULE)


class _Isolated(object):
    """A clean module namespace (as in a fresh agent process): the real prooflab/adapters another test imported
    would otherwise satisfy `import` from sys.modules, bypassing the bundle's finder. Restored exactly on exit."""

    def __init__(self, env=None):
        self.env = env or {}

    def __enter__(self):
        self.saved, self.meta, self.old = dict(sys.modules), list(sys.meta_path), dict(os.environ)
        for k in list(sys.modules):
            if k in _BUNDLED_ROOTS or k.split(".", 1)[0] in ("prooflab", "adapters"):
                del sys.modules[k]
        os.environ.update(self.env)
        return self

    def __exit__(self, *exc):
        for k in set(sys.modules) - set(self.saved):
            del sys.modules[k]
        sys.modules.update(self.saved)
        sys.meta_path[:] = self.meta
        os.environ.clear()
        os.environ.update(self.old)
        return False


def _root(tmp_path, entry=ENTRY):
    d = tmp_path / "agents" / "ifabric-customer"
    d.mkdir(parents=True)
    (d / "ifabric_app.py").write_text("VALUE = 'app'\n")
    (d / "role.py").write_text(entry)
    return str(tmp_path)


def _two(tmp_path, src=STUBS, entry=ENTRY, **kw):
    root = _root(tmp_path, entry)
    out = str(tmp_path / "out")
    reports, texts = BA.bundle_two_stage(["customer"], src_root=src, agents_root=root, out_root=out, **kw)
    return dict((r["name"], r) for r in reports), texts, out


def _gzb64(path):
    return len(base64.b64encode(gzip.compress(open(path, "rb").read(), 9, mtime=0)))


def test_two_stage_files_gate_and_core_only_in_base(tmp_path):
    reps, texts, out = _two(tmp_path)
    base, role = reps["ifabric-base"], reps["ifabric-customer"]
    assert base["ok"] and role["ok"]
    assert BA.CORE_MODULE in base["modules"] and BA.CORE_MODULE not in role["modules"]
    core_sha = hashlib.sha256(open(os.path.join(STUBS, BA.CORE_PATH), "rb").read()).hexdigest()
    for r in (base, role):
        assert os.path.basename(r["out"]) == r["name"] + ".py" != FORBIDDEN
        assert _gzb64(r["out"]) <= BA.GATE_CHARS                     # tools/gate.sh's own measure
        assert set(f.lower() for f in GATE_RX.findall(open(r["out"]).read())) == {core_sha}
    assert "model_call" in " ".join(base["modules"])               # the hot path goes first
    assert "ifabric_app" in role["modules"] and "ifabric_app" not in base["modules"]


def test_role_loads_base_and_runs(tmp_path):
    reps, _, out = _two(tmp_path)
    with _Isolated({"IFABRIC_BASE_PATH": reps["ifabric-base"]["out"]}):
        mod = _load(reps["ifabric-customer"]["out"], "ifabric_role_ts")
        assert mod.RESULT == "proceed" and mod.APP == "app"
        core = sys.modules[BA.CORE_MODULE]
        assert core.__loader__.__class__.__name__ == "_BundleFinder"
        base = sys.modules[BA.BASE_MODULE]
        assert base._SOURCES[BA.CORE_MODULE].encode("utf-8") == open(os.path.join(STUBS, BA.CORE_PATH), "rb").read()
        with pytest.raises(SystemExit):        # a role never redefines a base module
            base.extend({BA.CORE_MODULE: "X = 1\n"}, {BA.CORE_MODULE: hashlib.sha256(b"X = 1\n").hexdigest()}, [])


def test_role_fails_closed_without_the_exact_base(tmp_path):
    reps, _, out = _two(tmp_path)
    role = reps["ifabric-customer"]["out"]
    with _Isolated({"IFABRIC_BASE_PATH": str(tmp_path / "nope.py")}):
        with pytest.raises(SystemExit, match="missing"):
            _load(role, "ifabric_role_ts1")
    bad = tmp_path / "bad_base.py"
    bad.write_text(open(reps["ifabric-base"]["out"]).read() + "\n# edited\n")
    with _Isolated({"IFABRIC_BASE_PATH": str(bad)}):
        with pytest.raises(SystemExit, match="not the base bundle"):
            _load(role, "ifabric_role_ts2")


def test_role_fails_closed_when_the_base_serves_another_core(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(STUBS, str(src))
    with open(str(src / BA.CORE_PATH), "a") as f:
        f.write("\n# another core\n")
    other_reps, _, _ = _two(tmp_path / "o", src=str(src))
    reps, _, _ = _two(tmp_path / "r")
    other_base = other_reps["ifabric-base"]["out"]
    role_text = open(reps["ifabric-customer"]["out"]).read()
    role_text = role_text.replace(reps["ifabric-customer"]["base_file_sha256"],
                                  hashlib.sha256(open(other_base, "rb").read()).hexdigest())
    forged = tmp_path / "ifabric-customer.py"
    forged.write_text(role_text)
    with _Isolated({"IFABRIC_BASE_PATH": other_base}):
        with pytest.raises(SystemExit, match="pinned c16 core"):
            _load(str(forged), "ifabric_role_ts3")


def test_prune_keeps_every_surface_and_required_module(tmp_path):
    app = open(os.path.join(REPO, "agents", "ifabric-customer", "ifabric_app.py")).read()
    surface = BA.surface_modules(app)
    assert len(surface) >= 10
    # the REAL app (loads every adapter by name) and a role entry that imports only ifabric_app
    report, text = BA.bundle(BA.default_manifest("customer"), src_root=STUBS, agents_root=REPO, write=False,
                             do_prune=True)
    for m in surface:
        assert m in report["modules"], m
    # a module only the SURFACE names (not required, not imported) still survives the prune
    m = BA.default_manifest("customer")
    m["required"] = [BA.CORE_PATH]
    m["optional"] = m["optional"] + [r for r in BA.DEFAULT_REQUIRED if r != BA.CORE_PATH]
    report, _ = BA.bundle(m, src_root=STUBS, agents_root=REPO, write=False, do_prune=True)
    for mod in surface:
        assert mod in report["modules"], mod
    # and one neither imported, named nor required is dropped
    src = tmp_path / "src"
    shutil.copytree(STUBS, str(src))
    (src / "adapters" / "runtime" / "unused_xyz.py").write_text("X = 1\n")
    m["optional"].append("adapters/runtime/unused_xyz.py")
    report, _ = BA.bundle(m, src_root=str(src), agents_root=REPO, write=False, do_prune=True)
    assert "adapters.runtime.unused_xyz" in report["pruned"]
    reps, _ = BA.bundle_two_stage(["customer"], src_root=STUBS, agents_root=REPO, write=False, do_prune=True)
    served = set(reps[0]["modules"]) | set(reps[1]["modules"])
    assert set(surface) <= served


def test_strip_drops_docstrings_and_annotations_but_keeps_dataclass_fields():
    src = ('"""doc"""\nfrom __future__ import annotations\nfrom dataclasses import dataclass\n'
           'X: int = 3\nY: str\n\n@dataclass\nclass P:\n    """doc"""\n    a: int\n    b: str = "x"\n\n'
           'def f(a: int, *r: str, k: "T" = 1, **kw: dict) -> int:\n    """doc"""\n    z: int = a  # c\n'
           '    return z\n')
    out = BA.strip_docstrings(src)
    assert '"""' not in out and "# c" not in out and "-> int" not in out and "a: int," not in out
    ns = {}
    exec(compile(out, "<s>", "exec"), ns)
    assert ns["f"](4) == 4 and ns["X"] == 3 and ns["P"](1).b == "x"
    assert out.startswith("from __future__ import annotations")


def test_buildspecs_fit_and_mirror_the_kit(tmp_path):
    reps, _, out = _two(tmp_path)
    # files where write_buildspecs looks: <root>/agents/ifabric-*/ifabric-*.py
    broot = tmp_path / "broot"
    for name in ("ifabric-base", "ifabric-customer"):
        d = broot / "agents" / name
        d.mkdir(parents=True)
        shutil.copyfile(reps[name]["out"], str(d / (name + ".py")))
    host = "0" * 12 + ".dkr.ecr.ap-southeast-2.amazonaws.com"
    base_ref = host + "/" + "s" * 40 + "-aws-agent-operator@sha256:" + "a" * 64
    written = MK.write_buildspecs(str(tmp_path / "bs"), ["customer"], str(broot), "abc123def456", host,
                                  "s" * 40 + "-aws-agent-operator", base_ref)
    assert sorted(written) == ["ifabric-base", "ifabric-customer"]
    for name, (path, n, tag) in written.items():
        spec = open(path).read()
        assert n == len(spec) <= MK.BUILDSPEC_CAP
        assert tag.startswith(name + "-") and "reference-agent" not in spec
        cmds = json.loads(spec)["phases"]["build"]["commands"]
        dockerfile = base64.b64decode(cmds[2].split()[1]).decode()
        ctx = cmds[1].rsplit("> ", 1)[1]
        assert ctx != FORBIDDEN
        src_bytes = gzip.decompress(base64.b64decode(cmds[1].split()[1]))
        assert src_bytes == open(reps[name]["out"], "rb").read()
        if name == "ifabric-base":
            assert "COPY ifabric_base.py /app/ifabric_base.py" in dockerfile and "ENTRYPOINT" not in dockerfile
            assert "RUN pip install --no-cache-dir " + MK.KIT_SDK_PIP + " 'openai==2.54.0'" in dockerfile
            assert MK.KIT_SDK_ENV in dockerfile
        else:
            assert dockerfile.startswith("FROM " + base_ref + "\n")
            assert 'ENTRYPOINT ["opentelemetry-instrument", "python3", "/app/' + FORBIDDEN + '"]' in dockerfile
            assert "COPY ifabric-customer.py /app/" in dockerfile
        assert any(c.startswith("docker push ") for c in cmds) and "IFABRIC_IMAGE_DIGEST" in cmds[-1]


def test_buildspec_at_the_bundle_budget_stays_under_the_cap():
    bb, rb = BA.buildspec_budgets()
    assert bb <= BA.GATE_CHARS and rb <= BA.GATE_CHARS
    host = "0" * 12 + ".dkr.ecr." + "x" * 14 + ".amazonaws.com"
    repo = "s" * 40 + "-aws-agent-operator"
    b = MK.buildspec("A" * bb, MK.BASE_IN_IMAGE, MK.base_dockerfile(), host, repo, "ifabric-base-" + "f" * 12)
    r = MK.buildspec("A" * rb, "ifabric-network.py", MK.role_dockerfile(host + "/" + repo + "@sha256:" + "0" * 64,
                                                                       "network"), host, repo,
                     "ifabric-network-" + "f" * 12)
    assert len(b) <= MK.BUILDSPEC_CAP and len(r) <= MK.BUILDSPEC_CAP


def test_buildspecs_refuse_missing_bundles_and_a_non_digest_base(tmp_path, capsys):
    with pytest.raises(MK.Refused):
        MK.write_buildspecs(str(tmp_path / "bs"), ["customer"], str(tmp_path), "abc", "h", "r", "h/r@sha256:" + "a" * 64)
    rc = MK.main(["--out", str(tmp_path / "t.yaml"), "--buildspecs", str(tmp_path / "bs"),
                  "--base-image", "repo:latest"])
    assert rc == 2


def test_rails_mode_off_is_gone():
    with pytest.raises(SystemExit):
        MK.main(["--rails-mode", "off", "--out", "/dev/null"])


@pytest.mark.skipif(not REAL, reason="IFABRIC_SRC_ROOT not set (the real sibling modules)")
def test_real_sources_two_stage_fit_and_serve_every_surface_module(tmp_path):
    reports, texts = BA.bundle_two_stage(BA.ROLES, src_root=REAL, agents_root=REPO, out_root=str(tmp_path),
                                         do_prune=True)
    app = open(os.path.join(REPO, "agents", "ifabric-customer", "ifabric_app.py")).read()
    base = reports[0]
    for r in reports:
        assert r["ok"], (r["name"], r["gzip_base64_chars"])
        assert _gzb64(r["out"]) <= BA.GATE_CHARS
    for r in reports[1:]:
        assert set(BA.surface_modules(app)) <= set(base["modules"]) | set(r["modules"])
        assert BA.CORE_MODULE not in r["modules"]
    core = open(os.path.join(REAL, BA.CORE_PATH), "rb").read()
    with _Isolated():
        b = _load(base["out"], "ifabric_base_real")
        assert b._SOURCES[BA.CORE_MODULE].encode("utf-8") == core
