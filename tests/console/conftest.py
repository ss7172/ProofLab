"""PR-17 test scaffold: Arth's fixtures (handoffs/ifabric-handoff-3) + a small derived test pack.

Run (no sibling needed; stdlib only):  $PY39 -m pytest -q -p no:cacheprovider tests/console
The derived pack is built per test session from Arth's SYNTHETIC demo data with provenance relabelled so PACK mode
will load it; it is labelled TEST-DERIVED in its title and lives only in a tmp dir.
"""
import copy
import hashlib
import http.client
import json
import os
import sys
import threading

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from prooflab.console import server as srv  # noqa: E402
from prooflab.console import sources as S  # noqa: E402

PLAN = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "evidence-console-plan")
HANDOFF_CODE = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "code", "prooflab", "servicenow")
KEEP_RUNS = ("FM-A", "FM-B")


def _unsynth(obj):
    if isinstance(obj, dict):
        return {k: ("ASSESSED" if (k == "provenance" and v == "SYNTHETIC") else _unsynth(v)) for k, v in obj.items()
                if k != "synthetic"}
    if isinstance(obj, list):
        return [_unsynth(v) for v in obj]
    return obj


def _w(root, rel, obj):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        if isinstance(obj, str):
            handle.write(obj)
        else:
            handle.write(json.dumps(obj, indent=1, ensure_ascii=False))


def write_manifest(root):
    files = []
    for dp, _, names in os.walk(root):
        for n in names:
            full = os.path.join(dp, n)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel == "MANIFEST.json":
                continue
            with open(full, "rb") as h:
                data = h.read()
            files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    files.sort(key=lambda e: e["path"])
    _w(root, "MANIFEST.json", {"schema": "ifabric.evidence-manifest/v1", "algorithm": "sha256", "files": files})


def build_pack(root, with_cases=True):
    D = S.FixturesSource(PLAN).D
    keep = set(KEEP_RUNS)
    idx = copy.deepcopy(D["pack"])
    idx["pack"]["title"] = "TEST-DERIVED pack (from Arth's SYNTHETIC fixtures; relabelled for tests)"
    idx["answers"] = [a for a in idx["answers"] if a["scope"] in keep or a["key"].startswith("C9")]
    idx["auditor"] = [a for a in idx["auditor"] if a["id"] in ("INC0090216", "INC0090217")]
    idx["runs"] = [r for r in idx["runs"] if r["alias"] in keep]
    idx["cases"] = []
    for key in [a["key"] for a in idx["answers"]]:
        _w(root, "answers/%s.json" % key.replace("|", "_"), _unsynth(D["answers"][key]))
    for a in idx["auditor"]:
        _w(root, "auditor/%s.json" % a["id"], _unsynth(D["auditor"][a["id"]]))
    raws = set()
    for alias in keep:
        run = _unsynth(D["runs"][alias])
        _w(root, "runs/%s/run.json" % run["cid"], run)
        recs = _unsynth(D["records"][alias])
        _w(root, "records/C16/%s.jsonl" % alias, "\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n")
        for r in recs:
            raws.add(r["source"]["raw_ref"])
    by_file = {}
    for ref in sorted(raws, key=lambda r: (r.split("#")[0], int(r.split("#L")[1]))):
        by_file.setdefault(ref.split("#")[0][4:], []).append((int(ref.split("#L")[1]), D["raw"][ref]))
    for rel, lines in by_file.items():
        lines.sort()
        assert [n for n, _ in lines] == list(range(1, len(lines) + 1)), rel
        _w(root, rel, "\n".join(t for _, t in lines) + "\n")
        cap = D["captures"].get("capture:" + S.sidecar_for(rel))
        if cap:
            _w(root, S.sidecar_for(rel), cap)
    if with_cases:
        for c in D["cases"][:2]:
            rel = "servicenow/cases/%s.json" % hashlib.sha256(c["finding_id"].encode()).hexdigest()[:12]
            _w(root, rel, c)
            with open(os.path.join(root, rel), "rb") as h:
                sha = hashlib.sha256(h.read()).hexdigest()
            idx["cases"].append({"finding_id": c["finding_id"], "incident": c["servicenow"]["number"], "path": rel, "sha256": sha})
    # a state the console must flag (AT-10): closed, but no retest_ref
    _w(root, "pack-index.json", _unsynth(idx))
    write_manifest(root)
    return root


@pytest.fixture(scope="session")
def pack_template(tmp_path_factory):
    return build_pack(str(tmp_path_factory.mktemp("pack-template")))


@pytest.fixture()
def pack(tmp_path):
    return build_pack(str(tmp_path / "pack"))


class Client(object):
    def __init__(self, server):
        self.server = server
        self.port = server.port
        self.cookie = None
        self.csrf = None

    def request(self, method, path, body=None, headers=None, host=None, cookie=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": host or "127.0.0.1:%d" % self.port}
        if cookie and self.cookie:
            hdrs["Cookie"] = self.cookie
        hdrs.update(headers or {})
        data = None
        if body is not None:
            data = body if isinstance(body, (bytes, str)) else json.dumps(body)
            hdrs.setdefault("Content-Type", "application/json")
        c.request(method, path, body=data, headers=hdrs)
        r = c.getresponse()
        raw = r.read()
        out = (r.status, dict((k.lower(), v) for k, v in r.getheaders()), raw)
        c.close()
        return out

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def json(self, path, **kw):
        st, hd, raw = self.get(path, **kw)
        return st, json.loads(raw.decode("utf-8"))

    def login(self):
        st, hd, raw = self.request("POST", "/api/v1/session", body={"token": self.server.token}, cookie=False)
        assert st == 200, raw
        self.cookie = hd["set-cookie"].split(";")[0]
        self.csrf = json.loads(raw)["data"]["csrf"]
        return self


def start(source):
    server = srv.make_server("127.0.0.1", 0, source)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


@pytest.fixture()
def fixtures_client():
    server = start(S.FixturesSource(PLAN))
    try:
        yield Client(server).login()
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture()
def pack_client(pack):
    server = start(S.PackSource(pack))
    try:
        yield Client(server).login()
    finally:
        server.shutdown()
        server.server_close()
