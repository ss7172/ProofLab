"""PR-26 (opt-in: IFABRIC_DOCKER_SMOKE=1): build the EXACT Dockerfile the request's buildspec writes, from the
files its own decode commands produce, on local Docker (arm64), then run it against the stub gateway of
tools/docker_smoke/ (stub values only): GET /ping, POST /invocations. Local only; no registry, no AWS.

  IFABRIC_DOCKER_SMOKE=1 <venv>/bin/python -m pytest -q tests/build_image/test_build_image_docker_smoke.py
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SMOKE = os.path.join(REPO, "tools", "docker_smoke")
ASSURANCE_FILE = os.path.join(REPO, "agents", "ifabric-assurance", "ifabric-assurance.py")

pytestmark = pytest.mark.skipif(os.environ.get("IFABRIC_DOCKER_SMOKE") != "1" or not shutil.which("docker"),
                                reason="opt-in local Docker smoke: set IFABRIC_DOCKER_SMOKE=1")


def _http(method, url, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def _context(br, req, ctx):
    """Run the buildspec's decode commands into ctx, then write its Dockerfile there (as the build phase does)."""
    spec = json.loads(req["buildspecOverride"])
    pre = spec["phases"]["pre_build"]["commands"]
    cut = [i for i, c in enumerate(pre) if "aws " in c][0]
    env = dict(os.environ)
    env.update(dict((e["name"], e["value"]) for e in req["environmentVariablesOverride"]))
    r = subprocess.run(["bash", "-c", "set -e\n" + "\n".join(c for c in pre[:cut] if c != "uname -m")], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    assert r.returncode == 0, r.stdout
    line = [c for c in spec["phases"]["build"]["commands"] if c.endswith("| base64 -d > Dockerfile")][0]
    with open(os.path.join(ctx, "Dockerfile"), "wb") as f:
        f.write(base64.b64decode(line.split()[1]))


@pytest.mark.parametrize("role", ["customer", "it", "network", "assurance"])
def test_docker_smoke(br, bundles, tmp_path, monkeypatch, role):
    ctx = str(tmp_path / "ifb")
    monkeypatch.setattr(br, "BUILD_DIR", ctx)
    if role == "assurance":
        req, _m = br.make_request(role, "ifabric-assurance-75881e3", ASSURANCE_FILE)
    else:
        req, _m = br.make_request(role, "ifabric-%s-75881e3" % role, bundles[role], bundles["base"])
    _context(br, req, ctx)
    tag = "ifabric-pr26-smoke-%s:local" % role
    b = subprocess.run(["docker", "build", "--platform", "linux/arm64", "-t", tag, ctx],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    assert b.returncode == 0, b.stdout[-3000:]
    arch = subprocess.run(["docker", "image", "inspect", tag, "--format", "{{.Architecture}}"],
                          stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
    assert arch == "arm64"
    sys.path.insert(0, SMOKE)
    try:
        import inprocess_smoke
        import stub_gateway
    finally:
        sys.path.remove(SMOKE)
    stub_port, host_port = 18191, 18091
    srv = stub_gateway.serve(stub_port)
    name = "ifabric-pr26-smoke-" + role
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    gw = "http://host.docker.internal:%d" % stub_port
    env = {  # stub values only
        "OPENAI_BASE_URL": gw + "/v1", "OPENAI_API_KEY": "stub-key-not-real", "MODEL_ALIAS": "nemotron-super-120b",
        "AGENT_NAME": "ifabric-" + role, "AGENT_ROLE": role, "STEP_BASE": "0",
        "AUDIT_URL": gw, "AUDIT_WRITE_TOKEN": "stub-ledger-not-real", "AGENTCORE_GATEWAY_MCP_TOKEN": "stub-mcp-not-real",
        "IFABRIC_RAILS_MODE": "enforce", "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_unredacted_attributes=",
        "OTEL_TRACES_EXPORTER": "none", "OTEL_METRICS_EXPORTER": "none", "OTEL_LOGS_EXPORTER": "none",
    }
    if role != "assurance":
        env.update(inprocess_smoke.pin_env())
    cmd = ["docker", "run", "-d", "--name", name, "--platform", "linux/arm64", "-p", "%d:8080" % host_port]
    for k, v in sorted(env.items()):
        cmd += ["-e", "%s=%s" % (k, v)]
    logs = ""
    try:
        r = subprocess.run(cmd + [tag], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        assert r.returncode == 0, r.stdout
        ping = (None, "")
        for _ in range(60):
            ping = _http("GET", "http://127.0.0.1:%d/ping" % host_port, timeout=5)
            if ping[0] == 200:
                break
            time.sleep(1)
        logs = subprocess.run(["docker", "logs", "--tail", "40", name], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True).stdout
        assert ping[0] == 200, (ping, logs)
        if role != "assurance":
            payload = {"ifabric": {"envelope": "ifabric.run/1", "run_id": "ifabric-test-pr26-0001",
                                   "handoff_id": "ifabric-test-pr26-0001:h1", "tier": "standard",
                                   "tally_tokens": 0, "tally_calls": 0, "provenance": "LIVE_SUBJECT"},
                       "context": {"question": "Synthetic smoke: fault at stub site S-0. Who is impacted?"}}
            inv = _http("POST", "http://127.0.0.1:%d/invocations" % host_port, payload, timeout=180)
            assert inv[0] == 200 and '"refused"' not in inv[1] and '"error"' not in inv[1], (inv, logs)
    finally:
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        srv.shutdown()
