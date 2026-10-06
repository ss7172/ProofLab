"""Generate a single agent.py that embeds UNCHANGED prooflab modules behind an importlib finder,
and measure it exactly as build-agent-image.sh would (gzip -9n | base64, inside the buildspec JSON)."""
import ast, base64, json, subprocess, sys
from pathlib import Path

SRC = Path(sys.argv[1])          # .../code
OUT = Path(sys.argv[2])
SHIM = Path(sys.argv[3])

LOADER = '''# ---- generated bundle loader (ours): serves the embedded, byte-identical prooflab modules
import importlib.abc
import importlib.util
import sys

_PACKAGES = {"prooflab", "prooflab.servicenow"}


class _BundleFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name not in _SOURCES:
            return None
        # A location is set so __file__ exists; registering in sys.modules before exec is what
        # dataclasses need under `from __future__ import annotations` (importlib does it for us).
        return importlib.util.spec_from_file_location(
            name, _ORIGIN + "/" + name.replace(".", "/") + ("/__init__.py" if name in _PACKAGES else ".py"),
            loader=self, submodule_search_locations=[] if name in _PACKAGES else None)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(_SOURCES[module.__name__], module.__file__, "exec"), module.__dict__)


_ORIGIN = "/app/_bundle"
sys.meta_path.insert(0, _BundleFinder())
'''

SETS = {
    "A_analyzer_only": ["prooflab/__init__.py", "prooflab/servicenow/__init__.py", "prooflab/servicenow/nemotron.py"],
    "B_orchestrator": ["prooflab/__init__.py", "prooflab/servicenow/__init__.py"] + [
        f"prooflab/servicenow/{m}.py" for m in ("analysis", "assurance_agent", "assurance_checks", "case_view", "client",
                                                 "delivery_log", "finding", "finding_context", "nemotron", "notifier")],
    "C_all_modules": ["prooflab/__init__.py", "prooflab/servicenow/__init__.py"] + [
        f"prooflab/servicenow/{p.name}" for p in sorted((SRC / "prooflab/servicenow").glob("*.py")) if p.name != "__init__.py"],
}


def modname(rel):
    parts = rel[:-3].split("/")
    return ".".join(parts[:-1]) if parts[-1] == "__init__" else ".".join(parts)


def strip_docstrings(src):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.body \
                and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    out = ast.unparse(tree)
    # ast.unparse drops `from __future__` position? It keeps statements in order; ensure it's still first.
    return out


def build(files, shim, minify=False):
    sources = {}
    for rel in files:
        text = (SRC / rel).read_text(encoding="utf-8")
        sources[modname(rel)] = strip_docstrings(text) if (minify and text.strip()) else text
    body = "_SOURCES = {\n" + "".join(f"    {k!r}: {v!r},\n" for k, v in sources.items()) + "}\n"
    return LOADER.replace("_ORIGIN = ", body + "_ORIGIN = ", 1) + "\n" + shim


def ab64_len(text):
    gz = subprocess.run(["gzip", "-9nc"], input=text.encode("utf-8"), capture_output=True, check=True).stdout
    return len(base64.b64encode(gz)), len(gz)


def spec_overhead(extra_pip, tag="ifabric-assurance-agent", stack="a-01-eks-cluster", acct="123456789012",
                  region="us-east-1"):
    sdk_pip = "strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 mcp==1.30.0 boto3==1.43.103 aws-opentelemetry-distro==0.21.0"
    words = sdk_pip + "".join(f" '{r}'" for r in extra_pip.split())
    layer = f"RUN pip install --no-cache-dir {words}\n" + "ENV OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=urllib,urllib3,botocore,boto3\n"
    docker = ("FROM public.ecr.aws/docker/library/python:3.12-slim\nWORKDIR /app\n" + layer +
              'COPY agent.py /app/agent.py\nEXPOSE 8080\nENTRYPOINT ["opentelemetry-instrument", "python3", "/app/agent.py"]\n')
    d = base64.b64encode(docker.encode()).decode()
    h = f"{acct}.dkr.ecr.{region}.amazonaws.com"; r = f"{stack}-aws-agent-operator"; t = tag; arch = "arm64"
    img = f"{h}/{r}:{t}"
    assert_arch = ('ARCH=$(docker image inspect ' + img + ' --format "{{.Architecture}}")'
                   ' && echo "built architecture: $ARCH (want ' + arch + ')"' ' && [ "$ARCH" = "' + arch + '" ]'
                   ' || { echo "FATAL: built $ARCH, this target requires ' + arch + '"; exit 1; }')
    spec = json.dumps({"version": "0.2", "phases": {
        "pre_build": {"commands": ["uname -m",
                                   f"aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin {h}"]},
        "build": {"commands": ["mkdir -p /tmp/ra && cd /tmp/ra", "echo  | base64 -d | gunzip > agent.py",
                               f"echo {d} | base64 -d > Dockerfile", f"docker build -t {img} .", assert_arch,
                               f"docker push {img}"]}}}, separators=(",", ":"))
    return len(spec)


NEW_AGENT_EXTRA = "strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 mcp==1.30.0 aws-opentelemetry-distro==0.21.0"
for label, extra in (("via new-agent.sh EXTRA_PIP", NEW_AGENT_EXTRA), ("build-agent-image.sh, no EXTRA_PIP", "")):
    ov = spec_overhead(extra)
    print(f"buildspec overhead ({label}): {ov} chars -> AB64 budget {25600 - ov}")
shim = SHIM.read_text(encoding="utf-8")
print(f"shim (ours) raw bytes: {len(shim.encode())}")
for name, files in SETS.items():
    raw = sum(len((SRC / f).read_bytes()) for f in files)
    for minify in (False, True):
        text = build(files, shim, minify)
        b64, gz = ab64_len(text)
        tag = "minified(docstrings/comments removed)" if minify else "verbatim modules"
        print(f"{name:16s} {tag:38s} modules raw={raw:6d} B  agent.py={len(text.encode()):6d} B  gzip={gz:6d} B  gzip+base64={b64:6d} chars")
        if not minify:
            (OUT / f"agent_{name}.py").write_text(text, encoding="utf-8")
