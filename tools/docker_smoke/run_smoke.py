#!/usr/bin/env python3
"""S-0: the local arm64 Docker smoke of one bundled ifabric- agent (ARCH 7.1; plan S-0, T3.3).

Builds the EXACT image build-agent-image.sh (TARGET=agentcore) writes for CodeBuild: the same base,
the same SDK pins, EXTRA_PIP, the ADOT env line and entrypoint; the bundle goes into the build context
under the kit's fixed in-image file name (inside a temp dir, never in the repo). Then docker run with
stub env and the stub gateway (stub_gateway.py) on the host: GET /ping, POST /invocations.

  python3 tools/docker_smoke/run_smoke.py --bundle agents/ifabric-customer/ifabric-customer.py \\
      --workdir <scratch dir> [--build-only] [--keep]
  # two-stage (D-B): the base image from ifabric-base.py, then the role image FROM it
  python3 tools/docker_smoke/run_smoke.py --base agents/ifabric-base/ifabric-base.py \\
      --bundle agents/ifabric-customer/ifabric-customer.py --workdir <scratch dir>

Two-stage uses make_ifabric_agents.base_dockerfile / role_dockerfile, the exact Dockerfiles the buildspecs
carry, with ONE substitution: the role's FROM names the local base tag instead of <repo>@<base digest>
(no registry here).

Local only: no AWS, no cluster. The smoke-only OTEL_*_EXPORTER=none env keeps ADOT from exporting.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stub_gateway  # noqa: E402

sys.path.insert(0, os.path.dirname(HERE))
import make_ifabric_agents as mk  # noqa: E402  (the two-stage Dockerfiles, byte for byte)

# As build-agent-image.sh, TARGET=agentcore (workshop-assets/reference-impl, read 2026-10-06).
BASE = "public.ecr.aws/docker/library/python:3.12-slim"
SDK_PIP = ("strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 mcp==1.30.0 boto3==1.43.103 "
           "aws-opentelemetry-distro==0.21.0")
SDK_ENV = "ENV OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=urllib,urllib3,botocore,boto3\n"
IN_IMAGE_NAME = "agent" + ".py"   # the kit's fixed in-image name; our repo file is never named so
DEFAULT_EXTRA_PIP = "openai==2.54.0"


def dockerfile(extra_pip=DEFAULT_EXTRA_PIP):
    words = SDK_PIP + "".join(" '%s'" % r for r in extra_pip.split())
    return ("FROM %s\nWORKDIR /app\nRUN pip install --no-cache-dir %s\n%sCOPY %s /app/%s\nEXPOSE 8080\n"
            'ENTRYPOINT ["opentelemetry-instrument", "python3", "/app/%s"]\n'
            % (BASE, words, SDK_ENV, IN_IMAGE_NAME, IN_IMAGE_NAME, IN_IMAGE_NAME))


def _run(cmd, **kw):
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, **kw)


def _http(method, url, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 (report, the smoke decides)
        return None, "%s: %s" % (type(e).__name__, e)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--bundle", required=True)
    p.add_argument("--base", help="two-stage: the ifabric-base.py file (build the base image first)")
    p.add_argument("--workdir", required=True, help="a scratch dir for the build context")
    p.add_argument("--extra-pip", default=DEFAULT_EXTRA_PIP)
    p.add_argument("--tag", default=None)
    p.add_argument("--host-port", type=int, default=18080)
    p.add_argument("--stub-port", type=int, default=18181)
    p.add_argument("--build-only", action="store_true")
    p.add_argument("--keep", action="store_true", help="leave the container running")
    a = p.parse_args(argv)
    base = os.path.basename(a.bundle)
    if base == IN_IMAGE_NAME or not base.startswith("ifabric-"):
        print("run_smoke: the bundle must be an ifabric-<role>.py file", file=sys.stderr)
        return 2
    role = base[len("ifabric-"):-3]
    tag = a.tag or "ifabric-smoke-%s:local" % role
    ctx = os.path.join(a.workdir, "ctx-" + role)
    os.makedirs(ctx, exist_ok=True)
    t0 = time.time()
    if a.base:
        bctx = os.path.join(a.workdir, "ctx-base")
        os.makedirs(bctx, exist_ok=True)
        shutil.copyfile(a.base, os.path.join(bctx, mk.BASE_IN_IMAGE))
        with open(os.path.join(bctx, "Dockerfile"), "w") as f:
            f.write(mk.base_dockerfile(a.extra_pip))
        base_tag = "ifabric-smoke-base:local"
        b = _run(["docker", "build", "--platform", "linux/arm64", "-t", base_tag, bctx])
        print(json.dumps({"smoke": "build base", "rc": b.returncode, "seconds": round(time.time() - t0, 1)}),
              flush=True)
        if b.returncode != 0:
            return 1
        for f in os.listdir(ctx):
            os.remove(os.path.join(ctx, f))
        shutil.copyfile(a.bundle, os.path.join(ctx, base))
        with open(os.path.join(ctx, "Dockerfile"), "w") as f:
            f.write(mk.role_dockerfile(base_tag, role))
    else:
        shutil.copyfile(a.bundle, os.path.join(ctx, IN_IMAGE_NAME))
        with open(os.path.join(ctx, "Dockerfile"), "w") as f:
            f.write(dockerfile(a.extra_pip))
    b = _run(["docker", "build", "--platform", "linux/arm64", "-t", tag, ctx])
    print(json.dumps({"smoke": "build", "rc": b.returncode, "seconds": round(time.time() - t0, 1)}), flush=True)
    if b.returncode != 0:
        return 1
    arch = subprocess.run(["docker", "image", "inspect", tag, "--format", "{{.Architecture}}"],
                          stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
    print(json.dumps({"smoke": "arch", "architecture": arch, "want": "arm64"}), flush=True)
    if arch != "arm64" or a.build_only:
        return 0 if arch == "arm64" else 1
    srv = stub_gateway.serve(a.stub_port)
    name = "ifabric-smoke-" + role
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    gw = "http://host.docker.internal:%d" % a.stub_port
    env = {  # stub values only; never a real key, token or URL
        "OPENAI_BASE_URL": gw + "/v1", "OPENAI_API_KEY": "stub-key-not-real", "MODEL_ALIAS": "nemotron-super-120b",
        "AGENT_NAME": "ifabric-" + role, "AGENT_ROLE": role, "STEP_BASE": "0",
        "AUDIT_URL": gw, "AUDIT_WRITE_TOKEN": "stub-ledger-not-real",
        "AGENTCORE_GATEWAY_MCP_TOKEN": "stub-mcp-not-real",
        "IFABRIC_RAILS_MODE": "enforce",
        "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_unredacted_attributes=",
        "OTEL_TRACES_EXPORTER": "none", "OTEL_METRICS_EXPORTER": "none", "OTEL_LOGS_EXPORTER": "none",
    }
    import inprocess_smoke  # the same SYNTHETIC pin env block the wrapper derives (passes the real start-up)
    env.update(inprocess_smoke.pin_env())
    cmd = ["docker", "run", "-d", "--name", name, "--platform", "linux/arm64", "-p", "%d:8080" % a.host_port]
    for k, v in sorted(env.items()):
        cmd += ["-e", "%s=%s" % (k, v)]
    r = _run(cmd + [tag], stdout=subprocess.PIPE, universal_newlines=True)
    rc = 1
    try:
        if r.returncode != 0:
            return 1
        base_url = "http://127.0.0.1:%d" % a.host_port
        ping = (None, "")
        for _ in range(60):
            ping = _http("GET", base_url + "/ping", timeout=5)
            if ping[0] == 200:
                break
            time.sleep(1)
        print(json.dumps({"smoke": "GET /ping", "status": ping[0], "body": ping[1][:300]}), flush=True)
        payload = {"ifabric": {"envelope": "ifabric.run/1", "run_id": "ifabric-test-smoke-0001",
                               "handoff_id": "ifabric-test-smoke-0001:h1", "tier": "standard",
                               "tally_tokens": 0, "tally_calls": 0, "provenance": "LIVE_SUBJECT"},
                   "context": {"question": "Synthetic smoke: fault at stub site S-0. Who is impacted?"}}
        inv = _http("POST", base_url + "/invocations", payload, timeout=180)
        print(json.dumps({"smoke": "POST /invocations", "status": inv[0], "body": inv[1][:1500]}), flush=True)
        ok_body = inv[0] == 200 and '"refused"' not in inv[1] and '"error"' not in inv[1]
        rc = 0 if (ping[0] == 200 and ok_body) else 1
    finally:
        logs = subprocess.run(["docker", "logs", "--tail", "40", name], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True).stdout
        print("---- container log (tail) ----\n" + logs + "---- end ----", flush=True)
        if not a.keep:
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        srv.shutdown()
    print(json.dumps({"smoke": "result", "ok": rc == 0}), flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
