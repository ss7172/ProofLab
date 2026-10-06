"""Helpers for tests/assurance: run the GENERATED bundle in a fresh interpreter from an empty cwd, so nothing but
the bundle can supply `prooflab` (work/13 e2e method). The real bedrock_agentcore SDK is used where installed (the
pinned 3.12 stack); the 3.9 venv uses tests/assurance/stubs/ (the same /ping + /invocations contract)."""
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BUNDLE = os.path.join(ROOT, "agents", "ifabric-assurance", "ifabric-assurance.py")
ARTH_NEMOTRON = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "code", "prooflab", "servicenow", "nemotron.py")
STUBS = os.path.join(HERE, "stubs")
REAL_SDK = importlib.util.find_spec("bedrock_agentcore") is not None
ELB_URL = "http://k8s-agw-synthetic0000.elb.us-east-1.amazonaws.com:8081/v1"  # B1's shape; synthetic host
ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/ifabric_assurance_agent-SYNTH0001"


def bundle_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("OPENAI_", "MODAAS_", "IFABRIC_", "OTEL_")) and k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if not REAL_SDK:
        env["PYTHONPATH"] = STUBS
    env.update({k: str(v) for k, v in extra.items()})
    return env


DRIVER = r'''
import json, runpy, sys
g = runpy.run_path(sys.argv[1], run_name="ifabric_assurance_bundle")
out = {}
exec(sys.argv[2], {"g": g, "out": out})
print("DRIVER-RESULT " + json.dumps(out, sort_keys=True, default=str))
'''


def run_driver(snippet, **env):
    """Load the bundle (not as __main__, so no server) and run `snippet` with g = its globals; returns (out, stdout)."""
    proc = subprocess.run([sys.executable, "-c", DRIVER, BUNDLE, snippet], env=bundle_env(**env),
                          cwd=tempfile.mkdtemp(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    lines = proc.stdout.splitlines()
    result = [l for l in lines if l.startswith("DRIVER-RESULT ")]
    assert result, proc.stdout[-2000:] + proc.stderr[-2000:]
    return json.loads(result[-1][len("DRIVER-RESULT "):]), proc.stdout


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Runtime:
    """The generated bundle as a local 'AgentCore runtime' subprocess (python3 ifabric-assurance.py)."""

    def __init__(self, **env):
        self.port = free_port()
        self.env = bundle_env(PORT=self.port, **env)
        self.proc = None
        self.stdout = ""
        self.stderr = ""

    def __enter__(self):
        self.proc = subprocess.Popen([sys.executable, BUNDLE], env=self.env, cwd=tempfile.mkdtemp(),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/ping" % self.port, timeout=1) as r:
                    if r.status == 200:
                        return self
            except Exception:
                time.sleep(0.2)
        self.__exit__(None, None, None)
        raise AssertionError("runtime did not answer /ping: " + self.stderr[-2000:])

    def __exit__(self, *exc):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.stdout, self.stderr = self.proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.stdout, self.stderr = self.proc.communicate()
        return False

    def post(self, payload):
        req = urllib.request.Request("http://127.0.0.1:%d/invocations" % self.port, method="POST",
                                     data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()

    def witness_lines(self):
        out = []
        for line in self.stdout.splitlines():
            try:
                doc = json.loads(line)
            except ValueError:
                continue
            if isinstance(doc, dict) and doc.get("ifabric") == "assurance.witness/1":
                out.append(doc)
        return out


class FakeAwsCli:
    """Stands in for `aws bedrock-agentcore invoke-agent-runtime` (the subprocess seam of prooflab.humanloop.invoke):
    reads the fileb:// payload, POSTs it to the local runtime, writes the body to the out file, as the CLI does."""

    def __init__(self, runtime=None, response=None, exc=None, returncode=0, stderr=""):
        self.runtime, self.response, self.exc = runtime, response, exc
        self.returncode, self.stderr = returncode, stderr
        self.calls = []

    def __call__(self, argv, env=None, **kw):
        payload_path = argv[argv.index("--payload") + 1][len("fileb://"):]
        with open(payload_path, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.calls.append({"argv": list(argv), "env": dict(env or {}), "payload": payload, "kw": kw,
                           "out": argv[-1]})
        if self.exc is not None:
            raise self.exc
        if self.runtime is not None:
            status, body = self.runtime.post(payload)
        else:
            body = json.dumps(self.response) if not isinstance(self.response, str) else self.response
        if self.returncode == 0:
            with open(argv[-1], "w", encoding="utf-8") as fh:
                fh.write(body)
        return subprocess.CompletedProcess(argv, self.returncode, stdout="", stderr=self.stderr)
