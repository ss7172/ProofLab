"""PR-26 fixtures: the REAL merged two-stage bundles, generated into a temp dir by tools/bundle_agent.py with the
interpreter running the tests (never committed), and the request writer loaded from tools/."""
import importlib.util
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TRIO = ("customer", "it", "network")
ASSURANCE_FILE = os.path.join(REPO, "agents", "ifabric-assurance", "ifabric-assurance.py")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def br():
    return _load(os.path.join(REPO, "tools", "ifabric_build_request.py"), "ifabric_build_request_t")


@pytest.fixture(scope="session")
def bundles(tmp_path_factory):
    """{'base': path, 'customer': path, 'it': path, 'network': path} from the real sources (two-stage layout)."""
    out = str(tmp_path_factory.mktemp("bundles"))
    r = subprocess.run([sys.executable, os.path.join(REPO, "tools", "bundle_agent.py"), "--out-dir", out],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=REPO)
    assert r.returncode == 0, r.stdout
    paths = {"base": os.path.join(out, "ifabric-base", "ifabric-base.py")}
    for role in TRIO:
        paths[role] = os.path.join(out, "ifabric-" + role, "ifabric-%s.py" % role)
    for p in paths.values():
        assert os.path.isfile(p), p
    return paths


@pytest.fixture(scope="session")
def requests_by_role(br, bundles):
    """(request, meta) per role, tag ifabric-<role>-<7 hex>; assurance from the committed one-file handler."""
    out = {}
    for role in TRIO:
        out[role] = br.make_request(role, "ifabric-%s-75881e3" % role, bundles[role], bundles["base"])
    out["assurance"] = br.make_request("assurance", "ifabric-assurance-75881e3", ASSURANCE_FILE)
    return out
