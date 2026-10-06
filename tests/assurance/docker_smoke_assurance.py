#!/usr/bin/env python3
"""S-0 for the Assurance runtime: the local arm64 Docker smoke of agents/ifabric-assurance/ifabric-assurance.py,
on PR-06's harness (tools/docker_smoke/: the kit's exact Dockerfile + the stub OpenAI-compatible gateway).

  python3 tests/assurance/docker_smoke_assurance.py --workdir <scratch dir> [--harness <dir with run_smoke.py>]

No EXTRA_PIP (Arth's analyser is stdlib; build-agent-image.sh without EXTRA_PIP). The container gets the injected
URL shape http://<host>:<port>/v1 (plain HTTP, a non-loopback host: host.docker.internal), stub values only.
Checks: GET /ping 200; POST /invocations {"messages", "cid"} -> 200 with text + the stub's action id; a witness
line in the container log; a bad payload -> {"error": "unavailable"}. Local only: no AWS, no cluster.
Not collected by pytest (no test_ prefix); its observed output is recorded in the PR.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUNDLE = os.path.join(ROOT, "agents", "ifabric-assurance", "ifabric-assurance.py")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--harness", default=os.path.join(ROOT, "tools", "docker_smoke"))
    p.add_argument("--host-port", type=int, default=18090)
    p.add_argument("--stub-port", type=int, default=18191)
    a = p.parse_args(argv)
    sys.path.insert(0, a.harness)
    import run_smoke  # noqa: E402  (PR-06)
    import stub_gateway  # noqa: E402  (PR-06)

    ctx = os.path.join(a.workdir, "ctx-assurance")
    os.makedirs(ctx, exist_ok=True)
    shutil.copyfile(BUNDLE, os.path.join(ctx, run_smoke.IN_IMAGE_NAME))
    with open(os.path.join(ctx, "Dockerfile"), "w") as f:
        f.write(run_smoke.dockerfile(""))
    tag = "ifabric-smoke-assurance:local"
    b = run_smoke._run(["docker", "build", "--platform", "linux/arm64", "-t", tag, ctx])
    if b.returncode != 0:
        return 1
    arch = subprocess.run(["docker", "image", "inspect", tag, "--format", "{{.Architecture}}"],
                          stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
    print(json.dumps({"smoke": "arch", "architecture": arch}), flush=True)
    srv = stub_gateway.serve(a.stub_port)
    name = "ifabric-smoke-assurance"
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = {"OPENAI_BASE_URL": "http://host.docker.internal:%d/v1" % a.stub_port,
           "OPENAI_API_KEY": "stub-key-not-real", "MODEL_ALIAS": "nemotron-super-120b",
           "IFABRIC_ASSURE_MAX_TOKENS": "1200",
           "OTEL_TRACES_EXPORTER": "none", "OTEL_METRICS_EXPORTER": "none", "OTEL_LOGS_EXPORTER": "none"}
    cmd = ["docker", "run", "-d", "--name", name, "--platform", "linux/arm64", "-p", "%d:8080" % a.host_port]
    for k, v in sorted(env.items()):
        cmd += ["-e", "%s=%s" % (k, v)]
    rc = 1
    try:
        if run_smoke._run(cmd + [tag], stdout=subprocess.PIPE).returncode != 0:
            return 1
        base = "http://127.0.0.1:%d" % a.host_port
        ping = (None, "")
        for _ in range(60):
            ping = run_smoke._http("GET", base + "/ping", timeout=5)
            if ping[0] == 200:
                break
            time.sleep(1)
        print(json.dumps({"smoke": "GET /ping", "status": ping[0], "body": ping[1][:200]}), flush=True)
        payload = {"messages": [{"role": "user", "content": "Synthetic smoke: one line please."}],
                   "cid": "ifabric-assure-0-smoke"}
        inv = run_smoke._http("POST", base + "/invocations", payload, timeout=120)
        doc = json.loads(inv[1]) if inv[0] == 200 else {}
        print(json.dumps({"smoke": "POST /invocations", "status": inv[0], "action_id": doc.get("action_id"),
                          "finish_reason": doc.get("finish_reason"), "usage": doc.get("usage"),
                          "has_text": bool(doc.get("text")), "error": doc.get("error")}), flush=True)
        bad = run_smoke._http("POST", base + "/invocations", {"nothing": 1}, timeout=60)
        print(json.dumps({"smoke": "POST /invocations (bad payload)", "status": bad[0], "body": bad[1][:200]}),
              flush=True)
        time.sleep(1)
        logs = subprocess.run(["docker", "logs", name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True).stdout
        witness = [l for l in logs.splitlines() if '"assurance.witness/1"' in l]
        print(json.dumps({"smoke": "witness lines", "count": len(witness)}), flush=True)
        for line in witness:
            print("    " + line, flush=True)
        ok = (ping[0] == 200 and inv[0] == 200 and bool(doc.get("text")) and str(doc.get("action_id", ""))
              .startswith("stub-action-") and bad[0] == 200 and json.loads(bad[1]).get("error") == "unavailable"
              and any('"max_tokens": 1200' in l for l in witness))
        rc = 0 if ok else 1
        if not ok:
            print("---- container log (tail) ----\n" + "\n".join(logs.splitlines()[-40:]), flush=True)
    finally:
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        srv.shutdown()
    print(json.dumps({"smoke": "result", "ok": rc == 0}), flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
