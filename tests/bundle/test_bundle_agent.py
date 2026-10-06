"""Tests for tools/bundle_agent.py (PR-06, T3.3). Stdlib + pytest; Python 3.9+.

Run from the worktree root: python -m pytest -q -p no:cacheprovider tests/bundle
"""
import hashlib
import importlib.util
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
STUBS = os.path.join(HERE, "stubs")
FORBIDDEN = "agent" + ".py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("bundle_agent_ut", os.path.join(REPO, "tools", "bundle_agent.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BA = _load_tool()


def _agents_root(tmp_path, entry_src, app_src="VALUE = 'app'\n"):
    d = tmp_path / "agents" / "ifabric-customer"
    d.mkdir(parents=True)
    (d / "ifabric_app.py").write_text(app_src)
    (d / "role.py").write_text(entry_src)
    return str(tmp_path)


_BUNDLED_ROOTS = ("prooflab", "adapters", "ifabric_app")


def _shadowing(names):
    """The names a bundle serves itself: a copy imported earlier in the session (the real prooflab/adapters, by
    another test) would satisfy `import` from sys.modules and the bundle's finder would never be asked."""
    return [k for k in names if k in _BUNDLED_ROOTS or k.split(".", 1)[0] in _BUNDLED_ROOTS[:2]]


class _Isolated(object):
    """Import a bundle file as a plain module (not __main__) in a clean module namespace (as in a fresh agent
    process), then restore sys.modules and meta_path exactly."""

    def __enter__(self):
        self.saved = dict(sys.modules)
        self.meta = list(sys.meta_path)
        for k in _shadowing(list(sys.modules)):
            del sys.modules[k]
        return self

    def __exit__(self, *exc):
        for k in set(sys.modules) - set(self.saved):
            del sys.modules[k]
        sys.modules.update(self.saved)
        sys.meta_path[:] = self.meta
        return False


def _import_file(path, name="ifabric_bundle_ut"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ENTRY = (
    "import prooflab.evaluators.c16_core as core\n"
    "import adapters.runtime.startup as st\n"
    "import ifabric_app\n"
    "RESULT = core.decide_inline(None, None).action\n"
    "CORE_FILE = core.__file__\n"
    "APP = ifabric_app.VALUE\n"
    "if __name__ == '__main__':\n"
    "    raise SystemExit('never run in tests')\n"
)


def test_bundle_imports_and_core_is_byte_identical(tmp_path):
    root = _agents_root(tmp_path, ENTRY)
    report, text = BA.bundle(BA.default_manifest("customer"), src_root=STUBS, agents_root=root,
                             out_dir=str(tmp_path / "out"))
    assert report["ok"] and report["out"].endswith("ifabric-customer.py")
    core_bytes = open(os.path.join(STUBS, BA.CORE_PATH), "rb").read()
    assert report["c16_core_sha256"] == hashlib.sha256(core_bytes).hexdigest()
    with _Isolated():
        mod = _import_file(report["out"])
        assert mod.RESULT == "proceed"
        assert mod.APP == "app"
        assert mod.CORE_FILE == "/app/_bundle/prooflab/evaluators/c16_core.py"
        assert mod._SOURCES[BA.CORE_MODULE].encode("utf-8") == core_bytes
        assert mod.EVALUATOR_SHA256 == hashlib.sha256(core_bytes).hexdigest()
    assert ("\n# evaluator.sha256=" + report["c16_core_sha256"] + "\n") in text


def test_every_embedded_module_is_byte_identical(tmp_path):
    root = _agents_root(tmp_path, ENTRY)
    report, _ = BA.bundle(BA.default_manifest("customer"), src_root=STUBS, agents_root=root,
                          out_dir=str(tmp_path / "out"))
    with _Isolated():
        mod = _import_file(report["out"])
        for rel in BA.DEFAULT_REQUIRED:
            path = os.path.join(STUBS, rel)
            assert mod._SOURCES[BA.module_name(rel)].encode("utf-8") == open(path, "rb").read(), rel


def test_tampered_literal_fails_closed(tmp_path):
    root = _agents_root(tmp_path, ENTRY)
    report, text = BA.bundle(BA.default_manifest("customer"), src_root=STUBS, agents_root=root,
                             out_dir=str(tmp_path / "out"))
    bad = tmp_path / "tampered.py"
    bad.write_text(text.replace("return Decision(\\'ALLOW\\', \\'proceed\\')",
                                "return Decision(\\'ALLOW\\', \\'halt\\')").replace(
        'return Decision("ALLOW", "proceed")', 'return Decision("ALLOW", "halt")'))
    assert bad.read_text() != text
    with _Isolated():
        with pytest.raises(SystemExit):
            _import_file(str(bad))


def test_over_the_gate_fails_and_writes_nothing(tmp_path):
    import shutil
    src = tmp_path / "src"
    shutil.copytree(STUBS, str(src))
    pad = os.urandom(20000).hex()  # incompressible
    (src / "adapters" / "runtime" / "tally.py").write_text("PAD = %r\n" % pad)
    root = _agents_root(tmp_path, ENTRY)
    out = tmp_path / "out"
    report, _ = BA.bundle(BA.default_manifest("customer"), src_root=str(src), agents_root=root, out_dir=str(out))
    assert not report["ok"] and report["gzip_base64_chars"] > BA.GATE_CHARS and report["out"] is None
    assert not out.exists()
    rc = BA.main(["--role", "customer", "--src-root", str(src), "--agents-root", root, "--out-dir", str(out)])
    assert rc == 3 and not out.exists()


def test_missing_required_module_is_refused(tmp_path):
    import shutil
    src = tmp_path / "src"
    shutil.copytree(STUBS, str(src))
    os.remove(str(src / "adapters" / "runtime" / "hooks.py"))
    root = _agents_root(tmp_path, ENTRY)
    with pytest.raises(BA.BundleError):
        BA.bundle(BA.default_manifest("customer"), src_root=str(src), agents_root=root, write=False)


def test_refuses_the_reference_file_name(tmp_path):
    root = _agents_root(tmp_path, ENTRY)
    os.rename(os.path.join(root, "agents", "ifabric-customer", "role.py"),
              os.path.join(root, "agents", "ifabric-customer", FORBIDDEN))
    m = BA.default_manifest("customer")
    m["entry"] = "agents/ifabric-customer/" + FORBIDDEN
    with pytest.raises(BA.BundleError):
        BA.bundle(m, src_root=STUBS, agents_root=root, write=False)
    m = BA.default_manifest("customer")
    m["name"] = "agent"
    with pytest.raises(BA.BundleError):
        BA.bundle(m, src_root=STUBS, agents_root=root, write=False)


def test_manifest_file_and_missing_optional_reported(tmp_path):
    root = _agents_root(tmp_path, ENTRY)
    m = BA.default_manifest("customer")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps(m))
    report, _ = BA.bundle(BA._load_manifest(str(mf), None), src_root=STUBS, agents_root=root, write=False)
    assert "adapters/runtime/__init__.py" in report["missing_optional"]
    assert "prooflab" in report["synthesized_empty_packages"]


def test_real_trio_sources_fit_the_gate_with_stub_modules(tmp_path):
    for role in BA.ROLES:
        report, text = BA.bundle(BA.default_manifest(role), src_root=STUBS, agents_root=REPO, write=False)
        assert report["ok"], report
        assert report["gzip_base64_chars"] <= BA.GATE_CHARS
        assert "ifabric_app" in report["modules"]
        assert ("\"role\": \"%s\"" % role) in text


def test_no_trio_source_is_named_like_the_reference():
    for role in BA.ROLES:
        names = os.listdir(os.path.join(REPO, "agents", "ifabric-" + role))
        assert FORBIDDEN not in names


def test_strip_keeps_core_byte_identical_and_prune_drops_unreached(tmp_path):
    root = _agents_root(tmp_path, ENTRY)
    report, text = BA.bundle(BA.default_manifest("customer"), src_root=STUBS, agents_root=root,
                             out_dir=str(tmp_path / "out"), do_prune=True, do_strip=True)
    assert report["ok"]
    # tally is reached by nothing statically, but it is a required entry and a SURFACE module: never pruned
    assert "adapters.runtime.tally" not in report["pruned"]
    for rel in BA.DEFAULT_REQUIRED:
        assert BA.module_name(rel) in report["modules"]
    assert BA.CORE_MODULE not in report["stripped_not_byte_identical"]
    core_bytes = open(os.path.join(STUBS, BA.CORE_PATH), "rb").read()
    with _Isolated():
        mod = _import_file(report["out"])
        assert mod._SOURCES[BA.CORE_MODULE].encode("utf-8") == core_bytes
        assert mod.RESULT == "proceed"


# tools/gate.sh (PR-00) check_agents_py: the pattern it greps every agents/*/ifabric-*.py with. Read from the
# gate when it is in the tree; this copy otherwise (PR-00 5634b06).
_GATE_RX = r"(?:evaluator[_.]sha256|c16_core[_a-z]*sha256|C16_CORE_SHA256)\W{0,8}([0-9a-f]{64})"


def _gate_pattern():
    import re
    gate = os.path.join(REPO, "tools", "gate.sh")
    if os.path.isfile(gate):
        m = re.search(r'pat = re\.compile\(r"(.+?)", re\.I\)', open(gate).read())
        if m:
            return re.compile(m.group(1), re.I)
    return re.compile(_GATE_RX, re.I)


def test_gate_sh_finds_exactly_the_core_sha256_in_a_bundle(tmp_path):
    root = _agents_root(tmp_path, ENTRY)
    report, text = BA.bundle(BA.default_manifest("customer"), src_root=STUBS, agents_root=root, write=False)
    found = _gate_pattern().findall(text)
    assert found, "PR-00 gate would print SHA FAIL: no embedded c16 core sha256 marker found"
    assert set(f.lower() for f in found) == {report["c16_core_sha256"]}   # the gate fails on ANY other match


def test_no_contract_module_is_ever_embedded(tmp_path):
    import shutil
    root = _agents_root(tmp_path, ENTRY)
    report, _ = BA.bundle(BA.default_manifest("customer"), src_root=STUBS, agents_root=root, write=False)
    assert not [m for m in report["modules"] if m.startswith("prooflab.contract")]
    assert not [p for p in BA.DEFAULT_REQUIRED + BA.DEFAULT_OPTIONAL if p.startswith("prooflab/contract")]
    src = tmp_path / "src"
    shutil.copytree(STUBS, str(src))
    (src / "prooflab" / "contract").mkdir()
    (src / "prooflab" / "contract" / "record.py").write_text("X = 1\n")
    m = BA.default_manifest("customer")
    m["optional"].append("prooflab/contract/record.py")
    with pytest.raises(BA.BundleError):
        BA.bundle(m, src_root=str(src), agents_root=root, write=False)
