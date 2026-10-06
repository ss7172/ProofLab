"""The submit wrapper's red-flag lint (PR-49) is replaced here by a stub that passes: these tests exercise the scan
and manifest steps on a minimal synthetic pack, which the real lint rightly refuses. tests/pack_lint covers the lint."""

import pytest


@pytest.fixture(autouse=True)
def _stub_pack_lint(tmp_path_factory, monkeypatch):
    stub = tmp_path_factory.mktemp("lintstub") / "lint-pass.sh"
    stub.write_text('echo "stub lint: $1"; exit 0\n')
    monkeypatch.setenv("PROOFLAB_PACK_LINT", str(stub))
    yield
