#!/usr/bin/env python3
"""Write one CodeBuild StartBuild request (--cli-input-json) for one ifabric- agent image (ARCH 7.1; 05 AR-03/AR-05).

The carrier the ops lane proved on 2026-10-06 (ops-lane/build-probe-report.md): the agent source rides in the
StartBuild environmentVariablesOverride as gzip+base64 (one value of 46,548 chars was accepted), so the
buildspecOverride stays small (~1.6K, far under CodeBuild's 25,600) and no file needs to fit in it. One build
per role, ONE image holding both two-stage files (no FROM <repo>@<digest>: the build role cannot pull layers,
work/18 §1.4):

  IFABRIC_BASE_B64 / IFABRIC_BASE_SHA256  -> /app/ifabric_base.py   (where the role loader looks)
  IFABRIC_ROLE_B64 / IFABRIC_ROLE_SHA256  -> /app/<kit entry name>   (the kit's ENTRYPOINT path; our file
                                             keeps its own ifabric-<role>.py name in the build context)
  IFABRIC_REPO, IFABRIC_TAG

The buildspec decodes each value and checks it with `sha256sum -c` BEFORE the ECR login, then builds the kit's
agentcore Dockerfile shape (same base, the kit's pinned pip line + EXTRA_PIP checked by the kit's own regex,
the ADOT env line, the ENTRYPOINT), asserts arm64, pushes, and prints `IFABRIC_PUSHED sha256:<digest>`.
The assurance role is one file (no base): only the IFABRIC_ROLE_* pair is carried.

  python3 tools/ifabric_build_request.py --role customer --tag ifabric-customer-<gitsha> \\
      --base <out>/ifabric-base/ifabric-base.py --role-file <out>/ifabric-customer/ifabric-customer.py \\
      --out <dir outside the repo>/startbuild-ifabric-customer.json
  python3 tools/ifabric_build_request.py --role assurance --tag ifabric-assurance-<gitsha> \\
      --role-file agents/ifabric-assurance/ifabric-assurance.py --out <dir>/startbuild-ifabric-assurance.json

Writes the request JSON and a sidecar <out minus .json>.meta.json (role, tag, file sha256s, sizes, the c16
core sha256) that holds NO base64 value. Refuses: a tag that is not ifabric-<role>-<7..40 hex> or is a
reference tag; a source file named as the kit's reference file; a buildspec over 25,600 chars; any env value
over 44,000 chars or the env total over 46,000 chars (decision D-B'', 2026-10-06 06:20Z: the 03:29Z CodeBuild
probe accepted one value of 46,548 chars and ~46.7K in all; margin kept on both); a base whose evaluator.sha256 marker is not the
sha256 of prooflab/evaluators/c16_core.py; a role pinned to a different base file. It never calls AWS.
Standard library only; Python 3.9+.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_PATH = "prooflab/evaluators/c16_core.py"

PROJECT = "a-01-eks-cluster-modaas-image-build"      # the CFT's CodeBuild project (probe, 2026-10-06)
ECR_REPO = "a-01-eks-cluster-aws-agent-operator"      # the CFT repo the build role may push to (05 AR-05)
ROLES = ("customer", "it", "network", "assurance")
SINGLE_FILE_ROLES = ("assurance",)                    # one self-contained file, no base

BUILDSPEC_CAP = 25600          # CodeBuild's buildspecOverride limit
# D-B'' (06:20Z): the 2026-10-06 03:29Z CodeBuild StartBuild probe (ops-lane/build-probe-report.md) was accepted
# with one value of 46,548 chars and ~46.7K of names + values in all. The gates keep a margin under both.
ENV_VALUE_CAP = 44000          # per value (proven 46,548)
ENV_TOTAL_CAP = 46000          # all override names + values (proven ~46.7K)

TAG_RE = re.compile(r"^ifabric-([a-z]+)-[0-9a-f]{7,40}$")
REFERENCE_TAGS = ("reference-agent-v5", "reference-agent-v5-agentcore", "my-agent", "hackathon-helper", "latest")
REFERENCE_FILE = "agent" + ".py"                      # the kit's reference file name: never one of OUR sources

# The kit's TARGET=agentcore image (workshop-assets/reference-impl/build-agent-image.sh :97-99, :172).
KIT_BASE_IMAGE = "public.ecr.aws/docker/library/python:3.12-slim"
KIT_SDK_PIP = ("strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 mcp==1.30.0 boto3==1.43.103 "
               "aws-opentelemetry-distro==0.21.0")
# Kit line + aws_mcp: ADOT 0.21.0's McpInstrumentor (entry point aws_mcp, amazon/opentelemetry/distro/instrumentation/
# mcp/_wrappers.py) sets gen_ai.tool.call.arguments / gen_ai.tool.call.result on the "mcp tools/call" span in clear
# (live S-2: customer records in the runtime log group). Disabling it removes the producer (R-GR-02, T-SPAN-01).
KIT_SDK_ENV = "ENV OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=urllib,urllib3,botocore,boto3,aws_mcp\n"
KIT_ENTRY_PATH = "/app/" + REFERENCE_FILE             # the in-image path the kit's ENTRYPOINT runs
# The kit's EXTRA_PIP check, verbatim (build-agent-image.sh :141).
EXTRA_PIP_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9,._-]+\])?((==|>=|<=|~=|!=|<|>)[A-Za-z0-9.*+!_-]+"
                          r"(,(==|>=|<=|~=|!=|<|>)[A-Za-z0-9.*+!_-]+)*)?$")
DEFAULT_EXTRA_PIP = "openai==2.54.0"   # as make_ifabric_agents / docker_smoke: the smoked image = the built one

BASE_CTX = "ifabric_base.py"           # /app/ifabric_base.py: tools/bundle_agent.py BASE_IN_IMAGE
BUILD_DIR = "/tmp/ifb"                 # the build context inside CodeBuild (tests point it at a temp dir)
GZIP_HOW = "python gzip level 9 mtime=0, base64 without newlines"

MARKER_RE = re.compile(r"^# evaluator\.sha256=([0-9a-f]{64})$", re.M)
BASE_PIN_RE = re.compile(r"^_BASE_FILE_SHA256 = '([0-9a-f]{64})'$", re.M)
ARCH = "arm64"


class Refused(ValueError):
    """A request this tool will not write."""


def check_tag(tag, role):
    if tag in REFERENCE_TAGS:
        raise Refused("tag %r is a reference tag; pushing under it would replace that image" % tag)
    m = TAG_RE.match(tag or "")
    if not m:
        raise Refused("tag %r is not ifabric-<role>-<git sha, 7..40 hex>" % tag)
    if m.group(1) != role:
        raise Refused("tag %r names role %r, not --role %r" % (tag, m.group(1), role))
    return tag


def check_extra_pip(extra_pip):
    words = (extra_pip or "").split()
    if any(c in (extra_pip or "") for c in "\n\t\r"):
        raise Refused("EXTRA_PIP must be space-separated requirements on one line")
    for req in words:
        if not EXTRA_PIP_RE.match(req):
            raise Refused("EXTRA_PIP: %r is not a plain pip requirement (name, [extras], version)" % req)
    return words


def check_source_name(path):
    if os.path.basename(path) == REFERENCE_FILE:
        raise Refused("refusing a source file named %s (%s): our files are never named so" % (REFERENCE_FILE, path))


def gz_b64(data):
    """gzip (level 9, mtime 0: deterministic) then base64 with no newlines: what the buildspec decodes."""
    return base64.b64encode(gzip.compress(data, 9, mtime=0)).decode("ascii")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def dockerfile(role_ctx, with_base, extra_pip_words):
    words = KIT_SDK_PIP + "".join(" '%s'" % r for r in extra_pip_words)
    copies = ("COPY %s /app/%s\n" % (BASE_CTX, BASE_CTX) if with_base else "") + \
        "COPY %s %s\n" % (role_ctx, KIT_ENTRY_PATH)
    return ("FROM %s\nWORKDIR /app\nRUN pip install --no-cache-dir %s\n%s%sEXPOSE 8080\n"
            'ENTRYPOINT ["opentelemetry-instrument", "python3", "%s"]\n'
            % (KIT_BASE_IMAGE, words, KIT_SDK_ENV, copies, KIT_ENTRY_PATH))


def decode_commands(role_ctx, with_base, build_dir=None):
    """The pre-ECR-login part: decode each env value and verify it (sha256sum -c) before anything else."""
    d = build_dir or BUILD_DIR
    cmds = ["uname -m", "mkdir -p %s && cd %s" % (d, d)]
    pairs = ([("IFABRIC_BASE", BASE_CTX)] if with_base else []) + [("IFABRIC_ROLE", role_ctx)]
    for var, name in pairs:
        cmds.append("printf '%%s' \"$%s_B64\" | base64 -d | gunzip > %s" % (var, name))
        cmds.append("echo \"$%s_SHA256  %s\" | sha256sum -c -" % (var, name))
    cmds.append("echo \"IFABRIC_ENV_OK %s\"" % " ".join(
        "%s_b64len=${#%s_B64} %s_rawlen=$(wc -c < %s)" % (var.lower(), var, var.lower(), name)
        for var, name in pairs))
    return cmds


def buildspec(role_ctx, with_base, extra_pip_words, build_dir=None):
    """The --buildspec-override (compact JSON, the kit's form; JSON is YAML). No account id appears: the ECR
    host is built in-build from the project's injected AWS_ACCOUNT_ID. No env/printenv/set -x."""
    d = build_dir or BUILD_DIR
    d64 = base64.b64encode(dockerfile(role_ctx, with_base, extra_pip_words).encode("utf-8")).decode("ascii")
    # Not an f-string / %: the Go template braces must survive as written (as the kit's :177).
    assert_arch = ('ARCH=$(docker image inspect "$IMG" --format "{{.Architecture}}")'
                   ' && echo "built architecture: $ARCH (want ' + ARCH + ')"'
                   ' && [ "$ARCH" = "' + ARCH + '" ]'
                   ' || { echo "FATAL: built $ARCH, this target requires ' + ARCH + '"; exit 1; }')
    pre = decode_commands(role_ctx, with_base, d) + [
        'ACCT="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}";'
        ' ECR_HOST="$ACCT.dkr.ecr.$AWS_REGION.amazonaws.com"; IMG="$ECR_HOST/$IFABRIC_REPO:$IFABRIC_TAG"',
        'aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$ECR_HOST"',
    ]
    build = [
        "cd %s" % d,
        "echo %s | base64 -d > Dockerfile" % d64,
        'docker build -t "$IMG" .',
        assert_arch,
        'docker push "$IMG"',
        'echo "IFABRIC_PUSHED $(docker image inspect "$IMG" --format "{{index .RepoDigests 0}}" | sed "s/.*@//")"',
    ]
    return json.dumps({"version": "0.2", "phases": {"pre_build": {"commands": pre},
                                                     "build": {"commands": build}}}, separators=(",", ":"))


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _check_python(data, path):
    import ast
    try:
        ast.parse(data.decode("utf-8"), filename=path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise Refused("%s is not UTF-8 Python source: %s" % (path, exc))


def make_request(role, tag, role_file, base_file=None, c16_core=None, project=PROJECT, repo=ECR_REPO,
                 extra_pip=DEFAULT_EXTRA_PIP):
    """Return (request dict, meta dict). Raises Refused on any gate."""
    if role not in ROLES:
        raise Refused("role %r is not one of %s" % (role, ", ".join(ROLES)))
    check_tag(tag, role)
    words = check_extra_pip(extra_pip)
    single = role in SINGLE_FILE_ROLES
    if single and base_file:
        raise Refused("role %s is one self-contained file: no --base" % role)
    if not single and not base_file:
        raise Refused("role %s needs --base (the two-stage base file)" % role)
    files = [("IFABRIC_ROLE", role_file)] + ([] if single else [("IFABRIC_BASE", base_file)])
    for _var, path in files:
        check_source_name(path)
    role_ctx = os.path.basename(role_file)
    if role_ctx != "ifabric-%s.py" % role:
        raise Refused("the role file must be named ifabric-%s.py (got %s)" % (role, role_ctx))
    raw = dict((var, _read(path)) for var, path in files)
    for var, path in files:
        _check_python(raw[var], path)
    core_sha = None
    if not single:
        core_sha = sha256(_read(c16_core or os.path.join(REPO, CORE_PATH)))
        btxt = raw["IFABRIC_BASE"].decode("utf-8")
        m = MARKER_RE.search(btxt)
        if not m or m.group(1) != core_sha:
            raise Refused("the base's evaluator.sha256 marker (%s) is not sha256(%s) = %s"
                          % (m.group(1) if m else "absent", CORE_PATH, core_sha))
        rtxt = raw["IFABRIC_ROLE"].decode("utf-8")
        rm = MARKER_RE.search(rtxt)
        if rm and rm.group(1) != core_sha:
            raise Refused("the role's evaluator.sha256 marker (%s) is not the c16 core's %s" % (rm.group(1), core_sha))
        pin = BASE_PIN_RE.search(rtxt)
        if not pin:
            raise Refused("the role file pins no base (_BASE_FILE_SHA256): not a two-stage role bundle")
        if pin.group(1) != sha256(raw["IFABRIC_BASE"]):
            raise Refused("the role file was built against base %s, not this base %s (bundle both with the same "
                          "Python)" % (pin.group(1), sha256(raw["IFABRIC_BASE"])))
    env = []
    sizes = {}
    for var, _path in sorted(files, key=lambda x: x[0]):
        b64 = gz_b64(raw[var])
        env.append({"name": var + "_B64", "value": b64, "type": "PLAINTEXT"})
        env.append({"name": var + "_SHA256", "value": sha256(raw[var]), "type": "PLAINTEXT"})
        sizes[var] = {"raw_bytes": len(raw[var]), "gzip_base64_chars": len(b64)}
    env.append({"name": "IFABRIC_REPO", "value": repo, "type": "PLAINTEXT"})
    env.append({"name": "IFABRIC_TAG", "value": tag, "type": "PLAINTEXT"})
    spec = buildspec(role_ctx, not single, words)
    if len(spec) > BUILDSPEC_CAP:
        raise Refused("the buildspec is %d chars; CodeBuild accepts at most %d" % (len(spec), BUILDSPEC_CAP))
    for e in env:
        if len(e["value"]) > ENV_VALUE_CAP:
            raise Refused("env %s is %d chars; the gate is %d per value" % (e["name"], len(e["value"]), ENV_VALUE_CAP))
    values = sum(len(e["value"]) for e in env)
    with_names = sum(len(e["value"]) + len(e["name"]) for e in env)
    if with_names > ENV_TOTAL_CAP:
        raise Refused("the env overrides total %d chars (names + values); the gate is %d"
                      % (with_names, ENV_TOTAL_CAP))
    request = {
        "projectName": project,
        "environmentTypeOverride": "ARM_CONTAINER",
        "imageOverride": "aws/codebuild/amazonlinux-aarch64-standard:3.0",
        "computeTypeOverride": "BUILD_GENERAL1_LARGE",
        "privilegedModeOverride": True,
        "buildspecOverride": spec,
        "environmentVariablesOverride": env,
    }
    meta = {
        "role": role, "tag": tag, "project": project, "repo": repo, "single_file": single,
        "files": dict((var, {"path": os.path.abspath(path), "context_name": BASE_CTX if var == "IFABRIC_BASE"
                             else role_ctx, "in_image": "/app/" + BASE_CTX if var == "IFABRIC_BASE"
                             else KIT_ENTRY_PATH, "sha256": sha256(raw[var])}) for var, path in files),
        "c16_core_sha256": core_sha,
        "sizes": {
            "base_gzip_base64_chars": sizes.get("IFABRIC_BASE", {}).get("gzip_base64_chars"),
            "role_gzip_base64_chars": sizes["IFABRIC_ROLE"]["gzip_base64_chars"],
            "base_raw_bytes": sizes.get("IFABRIC_BASE", {}).get("raw_bytes"),
            "role_raw_bytes": sizes["IFABRIC_ROLE"]["raw_bytes"],
            "env_values_chars": values, "env_total_chars_with_names": with_names,
            "env_value_cap": ENV_VALUE_CAP, "env_total_cap": ENV_TOTAL_CAP,
            "buildspec_chars": len(spec), "buildspec_cap": BUILDSPEC_CAP,
        },
        "env_names": [e["name"] for e in env],
        "extra_pip": " ".join(words),
        "encoding": GZIP_HOW,
    }
    meta["sizes"]["request_json_bytes"] = len(dumps_request(request).encode("utf-8"))
    return request, meta


def dumps_request(request):
    return json.dumps(request, indent=1, sort_keys=True) + "\n"


def meta_path(out):
    return (out[:-5] if out.endswith(".json") else out) + ".meta.json"


def write(request, meta, out):
    if os.path.basename(out) == REFERENCE_FILE:
        raise Refused("refusing to write %s" % out)
    d = os.path.dirname(os.path.abspath(out))
    os.makedirs(d, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(dumps_request(request))
    mp = meta_path(out)
    with open(mp, "w") as f:
        f.write(json.dumps(meta, indent=1, sort_keys=True) + "\n")
    return out, mp


def main(argv=None):
    p = argparse.ArgumentParser(description="Write a StartBuild request for one ifabric- agent image (offline).")
    p.add_argument("--role", required=True, choices=ROLES)
    p.add_argument("--tag", required=True, help="ifabric-<role>-<git sha>")
    p.add_argument("--role-file", required=True, help="ifabric-<role>.py (the two-stage role file, or assurance's)")
    p.add_argument("--base", help="ifabric-base.py (customer/it/network)")
    p.add_argument("--c16-core", default=None, help="default: <repo>/" + CORE_PATH)
    p.add_argument("--project", default=PROJECT)
    p.add_argument("--repo", default=ECR_REPO)
    p.add_argument("--extra-pip", default=DEFAULT_EXTRA_PIP, help="'' for none; the kit's regex applies")
    p.add_argument("--out", required=True, help="the request JSON path (keep it outside the repo)")
    a = p.parse_args(argv)
    try:
        request, meta = make_request(a.role, a.tag, a.role_file, a.base, a.c16_core, a.project, a.repo, a.extra_pip)
        out, mp = write(request, meta, a.out)
    except (Refused, OSError) as exc:
        print("ifabric_build_request: REFUSED: %s" % exc, file=sys.stderr)
        return 2
    s = meta["sizes"]
    print("wrote %s (%d B) and %s" % (out, s["request_json_bytes"], mp))
    print("role=%s tag=%s base_b64=%s role_b64=%d env_total=%d (cap %d) buildspec=%d (cap %d)" % (
        a.role, a.tag, s["base_gzip_base64_chars"], s["role_gzip_base64_chars"], s["env_total_chars_with_names"],
        ENV_TOTAL_CAP, s["buildspec_chars"], BUILDSPEC_CAP))
    return 0


if __name__ == "__main__":
    sys.exit(main())
