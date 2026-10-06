#!/usr/bin/env python3
"""Write the ifabric- trio's AgentConfig manifests through the kit's own generator (ARCH 7.1; T3.3, B-G6).

It loads the kit's make-agentcore-agents.py with importlib and calls its _agent_cr(..., tool_alias=<tool>,
env_extra={IFABRIC_*}) per role, so dependsOn.tools, TOOL_MCP_ALIAS and the ledger pair land in the CR
exactly as the kit writes them. It WRITES files and PRINTS the ops-lane commands; it never runs kubectl,
aws or a build, and never takes the generator's approval path (that stamps system-admin).

  python3 tools/make_ifabric_agents.py --roles customer,it,network --pin register/pins/v1-enforce.json \\
      [--out /tmp/ifabric-agents.generated.yaml]

The pin env block is exactly what the runtime verifies (PR-01 prooflab.contract.pin.env_block, PR-04
startup, PR-02 PinnedC16.from_env): IFABRIC_PIN_JSON = the CANONICAL dump of the pin file (sorted keys, no
spaces, ASCII), IFABRIC_PIN_SHA256 = sha256 of THAT string (never of the file bytes), and
IFABRIC_REGISTER_VERSION/_SHA256 = the pin's own register block (an explicit flag must agree with it).

--buildspecs DIR (two-stage images, decision D-B): writes buildspec-ifabric-base.json (the base file decoded to
/app/ifabric_base.py on the kit's base image + SDK layer, tag ifabric-base-<git sha>) and one
buildspec-ifabric-<role>.json per role (FROM <repo>@<base digest>, the role file at the kit's ENTRYPOINT path),
each <= 25,600 chars; it prints the aws codebuild start-build commands for the ops lane and never runs them.

Default (offline): placeholders for the discovered values (subnets, security group, AUDIT_URL and the
ledger token), so the CR shape is reviewable with no cluster read. --discover (OPS LANE ONLY, the
captain's OK): the kit's Discovery reads them (read-only aws/kubectl gets); the file then holds the
ledger token in plain text, so --out must be outside the repo.

Refuses: a source file with the kit's reference file name, a reference image tag, an image that is not a
repo@sha256 digest, a CR name the runtime would refuse, a non-string env value, MODEL_ALIAS in env (the
operator derives it), and any approval annotation. Standard library only; Python 3.9+.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_kit():
    """The kit generator beside the repo (../workshop-assets/...), searched up to 3 levels (worktrees)."""
    d = REPO
    for _ in range(3):
        d = os.path.dirname(d)
        cand = os.path.join(d, "workshop-assets", "reference-impl", "make-agentcore-agents.py")
        if os.path.isfile(cand):
            return cand
    return os.path.join(os.path.dirname(REPO), "workshop-assets", "reference-impl", "make-agentcore-agents.py")


DEFAULT_KIT = _find_kit()
DEFAULT_MODEL = "nemotron-super-120b"
DEFAULT_OUT = "/tmp/ifabric-agents.generated.yaml"
DEFAULT_EXTRA_PIP = "openai==2.54.0"   # pinned through EXTRA_PIP (05 AR-11); confirm against the 3.12 venv
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,38}[a-z0-9]$")   # ARCH 7.1 / PV row 9 (the kit's NAME_RE)
TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")  # build-agent-image.sh's tag check
REFERENCE_TAG_RE = re.compile(r"^reference-agent-v[0-9]+(-agentcore)?$")
REFERENCE_FILE = "agent" + ".py"     # the kit's reference file name: never ours (ARCH 7.1)
APPROVAL_KEYS = ("modaas.tmforum.org/approver", "modaas.tmforum.org/approval-attestation")
RESERVED_ENV = ("MODEL_ALIAS",)       # operator-derived; a declared one is DeclaredEnvInvalid

#: role -> (description, skills, tool alias, STEP_BASE): as the reference trio (kit REFERENCE).
TRIO = {
    "customer": ("ifabric customer agent: customer impact of network faults; first domain of the triad",
                 ["fault-resolution", "customer-domain"], "customer-records", "0"),
    "it": ("ifabric IT agent: incident disposition per runbook; second domain of the triad",
           ["fault-resolution", "it-domain"], "runbook-lookup", "3"),
    "network": ("ifabric network agent: diagnosis and resolution on the twin; third domain of the triad",
                ["fault-resolution", "network-domain"], "network-twin", "6"),
}


class Refused(ValueError):
    """A value the wrapper will not write."""


# ---- the one import site of the pin contract (PR-01 prooflab.contract.pin); a byte-identical fallback
# (sort_keys, separators (",", ":"), ensure_ascii) so the wrapper runs before PR-01 merges.
PIN_ENV_MAX = 5000   # the operator's cap per env value [05 AR-14]
try:
    sys.path.insert(0, REPO)
    from prooflab.contract import pin as _pin  # noqa: E402
except Exception:  # pragma: no cover - PR-01 not merged yet
    _pin = None
finally:
    if sys.path and sys.path[0] == REPO:
        sys.path.pop(0)


def pin_dumps(obj):
    if _pin is not None:
        return _pin.dumps(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def pin_sha256(pin_json):
    if _pin is not None:
        return _pin.sha256_of(pin_json)
    return hashlib.sha256(pin_json.encode("utf-8")).hexdigest()


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def pin_env(raw, register_version=None, register_sha256=None):
    """(pin_json, pin_sha256, register_version, register_sha256) from a pin file's bytes, exactly as the
    runtime checks them. Refuses a pin without a 64-hex register block, a flag that disagrees with the
    pin, and a pin over the operator's env-value cap."""
    try:
        obj = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except ValueError as exc:
        raise Refused("the pin is not JSON: %s" % exc)
    reg = obj.get("register") if isinstance(obj, dict) else None
    if not isinstance(reg, dict) or not isinstance(reg.get("version"), str) or not reg.get("version") \
            or not isinstance(reg.get("sha256"), str) or not _HEX64.match(reg["sha256"]):
        raise Refused("the pin has no register block {version, sha256: 64 hex}")
    for flag, mine in ((register_version, reg["version"]), (register_sha256, reg["sha256"])):
        if flag is not None and flag != mine:
            raise Refused("--register-version/--register-sha256 disagree with the pin's register block")
    if _pin is not None:
        errors = _pin.validate_pin(obj)
        if errors:
            raise Refused("invalid pin: " + "; ".join(errors))
    text = pin_dumps(obj)
    if len(text) > PIN_ENV_MAX:
        raise Refused("the pin is %d chars; the operator caps an env value at %d" % (len(text), PIN_ENV_MAX))
    return text, pin_sha256(text), reg["version"], reg["sha256"]


def refuse_placeholders(docs):
    """--discover writes what will be applied: no '<...>' placeholder may survive into it."""
    for cr in docs:
        ac = cr["spec"]["awsAgentCore"]
        bad = [k for k, v in ac["environmentVariables"].items() if "<" in v]
        if "<" in ac.get("containerUri", ""):
            bad.append("containerUri")
        if bad:
            raise Refused("CR %s still holds placeholders in: %s" % (cr["metadata"]["name"], ", ".join(sorted(bad))))


class OfflineDiscovery(object):
    """Placeholders in the kit Discovery's shape: no aws, no kubectl."""

    def region(self):
        return os.environ.get("AWS_REGION") or "us-east-1"

    def subnets(self):
        return ["<subnet-id-from-discovery>"]

    def security_group(self):
        return "<cluster-sg-from-discovery>"

    def audit_url(self):
        return "<AUDIT_URL-from-discovery>"

    def audit_token(self):
        return "<ledger-write-token-from-discovery>"


def load_kit(path):
    if os.path.basename(path) == REFERENCE_FILE:
        raise Refused("the kit generator path looks like an agent source: %s" % path)
    spec = importlib.util.spec_from_file_location("kit_make_agentcore_agents", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def image_tag(role, git_sha):
    tag = "ifabric-%s-%s" % (role, git_sha)
    check_tag(tag)
    return tag


def check_tag(tag):
    if not TAG_RE.match(tag or ""):
        raise Refused("IMAGE_TAG %r is not a valid image tag" % tag)
    if REFERENCE_TAG_RE.match(tag) or not tag.startswith("ifabric-"):
        raise Refused("IMAGE_TAG %r: a reference tag, or not an ifabric- tag" % tag)


def check_source(path):
    base = os.path.basename(path)
    if base == REFERENCE_FILE:
        raise Refused("refusing an agent source named %s (it would push over the reference trio)" % REFERENCE_FILE)
    if not re.match(r"^ifabric-[a-z][a-z0-9-]*\.py$", base):
        raise Refused("agent source %r must be ifabric-<role>.py" % base)


def check_image(uri):
    if "@sha256:" not in uri or ":" + "reference-agent" in uri or "/reference-agent" in uri:
        raise Refused("containerUri %r must be repo@sha256:<digest> of an ifabric- build" % uri)


def env_extra(rails_mode, pin_json, pin_sha256, register_version, register_sha256, extra=None):
    env = {
        "IFABRIC_RAILS_MODE": rails_mode,
        "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_unredacted_attributes=",
        "IFABRIC_PIN_JSON": pin_json,
        "IFABRIC_PIN_SHA256": pin_sha256,
        "IFABRIC_REGISTER_VERSION": register_version,
        "IFABRIC_REGISTER_SHA256": register_sha256,
    }
    env.update(extra or {})
    for k in RESERVED_ENV:
        if k in env:
            raise Refused("%s is operator-derived; never declare it" % k)
    return env


def validate_cr(cr):
    md = cr.get("metadata", {})
    name = md.get("name", "")
    if not NAME_RE.match(name) or not name.startswith("ifabric-"):
        raise Refused("CR name %r fails %s or is not ifabric-" % (name, NAME_RE.pattern))
    ann = md.get("annotations") or {}
    if any(k in ann for k in APPROVAL_KEYS):
        raise Refused("CR %s carries an approval annotation: approval is the captain's, in the live lane" % name)
    ac = cr["spec"]["awsAgentCore"]
    check_image(ac["containerUri"])
    for k, v in ac["environmentVariables"].items():
        if not isinstance(v, str):
            raise Refused("env %s=%r is not a string (the CRD type is map[string]string)" % (k, v))
    for k in RESERVED_ENV:
        if k in ac["environmentVariables"]:
            raise Refused("%s must not be declared" % k)
    return cr


def build_crs(kit, d, roles, images, model, env):
    docs = []
    for role in roles:
        desc, skills, tool, step = TRIO[role]
        name = "ifabric-" + role
        # Never the generator's approval keyword: the CR goes to Reviewing and the captain annotates.
        cr = kit._agent_cr(d, name=name, role=role, step_base=step, description=desc, skills=skills,
                           model=model, image=images[role], tool_alias=tool, env_extra=dict(env))
        docs.append(validate_cr(cr))
    return docs


# ---- the two-stage image build (D-B; work/05 AR-03/AR-05): two --buildspec-override files, mirroring
# build-agent-image.sh TARGET=agentcore (same base, SDK pins, ADOT env line, ENTRYPOINT, arm64 assertion,
# ECR login, push to the CFT repo the CodeBuild role may push to). Written as files; never started here.
BUILDSPEC_CAP = 25600                        # CodeBuild's buildspecOverride limit
KIT_BASE_IMAGE = "public.ecr.aws/docker/library/python:3.12-slim"
KIT_SDK_PIP = ("strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 mcp==1.30.0 boto3==1.43.103 "
               "aws-opentelemetry-distro==0.21.0")
# Kit line + aws_mcp: ADOT 0.21.0's McpInstrumentor (entry point aws_mcp, amazon/opentelemetry/distro/instrumentation/
# mcp/_wrappers.py) sets gen_ai.tool.call.arguments / gen_ai.tool.call.result on the "mcp tools/call" span in clear
# (live S-2: customer records in the runtime log group). Disabling it removes the producer (R-GR-02, T-SPAN-01).
KIT_SDK_ENV = "ENV OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=urllib,urllib3,botocore,boto3,aws_mcp\n"
KIT_ENTRY_PATH = "/app/" + REFERENCE_FILE    # the in-image path the kit's ENTRYPOINT runs; our files keep their names
BASE_FILE = "agents/ifabric-base/ifabric-base.py"
BASE_IN_IMAGE = "ifabric_base.py"            # /app/ifabric_base.py, where the role loader looks
CODEBUILD_ARM = ["--environment-type-override", "ARM_CONTAINER",
                 "--image-override", "aws/codebuild/amazonlinux-aarch64-standard:3.0",
                 "--compute-type-override", "BUILD_GENERAL1_LARGE", "--privileged-mode-override"]
DIGEST_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*(/[A-Za-z0-9._-]+)+@sha256:[0-9a-f]{64}$")


def base_dockerfile(extra_pip=DEFAULT_EXTRA_PIP):
    words = KIT_SDK_PIP + "".join(" '%s'" % r for r in extra_pip.split())
    return ("FROM %s\nWORKDIR /app\nRUN pip install --no-cache-dir %s\n%sCOPY %s /app/%s\nEXPOSE 8080\n"
            % (KIT_BASE_IMAGE, words, KIT_SDK_ENV, BASE_IN_IMAGE, BASE_IN_IMAGE))


def role_dockerfile(base_ref, role):
    src = "ifabric-%s.py" % role
    return ('FROM %s\nWORKDIR /app\nCOPY %s %s\nEXPOSE 8080\n'
            'ENTRYPOINT ["opentelemetry-instrument", "python3", "%s"]\n' % (base_ref, src, KIT_ENTRY_PATH,
                                                                          KIT_ENTRY_PATH))


def gz_b64(data):
    import base64
    import gzip
    try:
        gz = subprocess.run(["gzip", "-9nc"], input=data, stdout=subprocess.PIPE, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        gz = gzip.compress(data, 9, mtime=0)
    return base64.b64encode(gz).decode("ascii")


def buildspec(src_b64, ctx_name, dockerfile, ecr_host, repo, tag, arch="arm64"):
    """The --buildspec-override JSON (compact), the kit's phases plus one digest line after the push."""
    import base64
    img = "%s/%s:%s" % (ecr_host, repo, tag)
    d64 = base64.b64encode(dockerfile.encode("utf-8")).decode("ascii")
    assert_arch = ('ARCH=$(docker image inspect ' + img + ' --format "{{.Architecture}}")'
                   ' && echo "built architecture: $ARCH (want ' + arch + ')"'
                   ' && [ "$ARCH" = "' + arch + '" ]'
                   ' || { echo "FATAL: built $ARCH, this target requires ' + arch + '"; exit 1; }')
    digest = ('echo "IFABRIC_IMAGE_DIGEST=$(docker image inspect ' + img +
              ' --format "{{index .RepoDigests 0}}")"')
    return json.dumps({"version": "0.2", "phases": {
        "pre_build": {"commands": [
            "uname -m",
            "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin %s"
            % ecr_host]},
        "build": {"commands": [
            "mkdir -p /tmp/ifb && cd /tmp/ifb",
            "echo %s | base64 -d | gunzip > %s" % (src_b64, ctx_name),
            "echo %s | base64 -d > Dockerfile" % d64,
            "docker build -t %s ." % img,
            assert_arch,
            "docker push %s" % img,
            digest]}}}, separators=(",", ":"))


# Worst-case fixed text for the budget: a 12-digit account, a 14-char region, a 40-char stack name.
_WC_HOST = "0" * 12 + ".dkr.ecr." + "x" * 14 + ".amazonaws.com"
_WC_REPO = "s" * 40 + "-aws-agent-operator"
_WC_TAG = "ifabric-network-" + "f" * 12
BUILDSPEC_MARGIN = 64


def buildspec_overheads(extra_pip=DEFAULT_EXTRA_PIP):
    """(base, role) fixed buildspec chars around the gzip+base64 source, worst case + a margin: the bundler
    lowers each file's budget to BUILDSPEC_CAP minus this."""
    b = buildspec("", BASE_IN_IMAGE, base_dockerfile(extra_pip), _WC_HOST, _WC_REPO, _WC_TAG)
    r = buildspec("", "ifabric-network.py", role_dockerfile(_WC_HOST + "/" + _WC_REPO + "@sha256:" + "0" * 64,
                                                            "network"), _WC_HOST, _WC_REPO, _WC_TAG)
    return len(b) + BUILDSPEC_MARGIN, len(r) + BUILDSPEC_MARGIN


def write_buildspecs(out_dir, roles, bundles_root, git_sha, ecr_host, repo, base_ref, extra_pip=DEFAULT_EXTRA_PIP):
    """Write buildspec-ifabric-base.json and buildspec-ifabric-<role>.json; returns {name: (path, chars)}.
    Refuses a missing bundle file, a non-ifabric tag and a buildspec over CodeBuild's cap."""
    os.makedirs(out_dir, exist_ok=True)
    jobs = [("ifabric-base", os.path.join(bundles_root, BASE_FILE), BASE_IN_IMAGE, base_dockerfile(extra_pip),
             "ifabric-base-%s" % git_sha)]
    for role in roles:
        src = os.path.join(bundles_root, "agents", "ifabric-%s" % role, "ifabric-%s.py" % role)
        check_source(src)
        jobs.append(("ifabric-" + role, src, os.path.basename(src), role_dockerfile(base_ref, role),
                     image_tag(role, git_sha)))
    written = {}
    for name, src, ctx_name, dockerfile, tag in jobs:
        check_tag(tag)
        if not os.path.isfile(src):
            raise Refused("bundle file missing: %s (run tools/bundle_agent.py first)" % src)
        with open(src, "rb") as f:
            spec = buildspec(gz_b64(f.read()), ctx_name, dockerfile, ecr_host, repo, tag)
        if len(spec) > BUILDSPEC_CAP:
            raise Refused("buildspec for %s is %d chars; CodeBuild accepts at most %d" % (name, len(spec),
                                                                                        BUILDSPEC_CAP))
        path = os.path.join(out_dir, "buildspec-%s.json" % name)
        with open(path, "w") as f:
            f.write(spec)
        written[name] = (path, len(spec), tag)
    return written


def _git_sha():
    try:
        return subprocess.run(["git", "-C", REPO, "rev-parse", "--short=12", "HEAD"], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, universal_newlines=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "nogit"


def _read_uri(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def ops_commands(roles, git_sha, out, region, buildspec_dir):
    """The ops-lane sequence for the two-stage build (D-B). Printed only; this tool never runs any of it."""
    bs = buildspec_dir or "<--buildspecs DIR>"
    arm = " ".join(CODEBUILD_ARM)
    start = ('aws codebuild start-build --project-name "${STACK}-modaas-image-build" %s '
             '--buildspec-override file://%s/buildspec-%%s.json --query build.id --output text' % (arm, bs))
    digest = ('echo "${ECR_HOST}/${STACK}-aws-agent-operator@$(aws ecr describe-images --region %s '
              '--repository-name "${STACK}-aws-agent-operator" --image-ids imageTag=%%s '
              '--query \'imageDetails[0].imageDigest\' --output text)" | tee %%s' % region)
    roles_arg = ",".join(roles)
    lines = ["# ---- ops lane (NOT run by this tool; one action at a time, each with the captain's OK) ----",
             "# 0. the kit's own lookups (build-agent-image.sh): STACK, ACCT, ECR_HOST",
             "#    STACK=<eks cluster tag aws:cloudformation:stack-name>; ACCT=$(aws sts get-caller-identity "
             "--query Account --output text); ECR_HOST=${ACCT}.dkr.ecr.%s.amazonaws.com" % region,
             "# 1. bundle (two-stage) with Python 3.12, then write the buildspecs with the real host/repo:",
             "python3.12 tools/bundle_agent.py --layout two-stage",
             "python3 tools/make_ifabric_agents.py --roles %s --pin <pin> --buildspecs %s --account $ACCT "
             "--stack $STACK --git-sha %s" % (roles_arg, bs, git_sha),
             "# 2. the base image (once), then its digest:",
             start % "ifabric-base",
             "aws codebuild batch-get-builds --ids <build id> --query 'builds[0].buildStatus' --output text",
             digest % ("ifabric-base-" + git_sha, "/tmp/ifabric-base-image-uri"),
             "# 3. role buildspecs FROM <repo>@<base digest> (read from /tmp/ifabric-base-image-uri):",
             "python3 tools/make_ifabric_agents.py --roles %s --pin <pin> --buildspecs %s --account $ACCT "
             "--stack $STACK --git-sha %s" % (roles_arg, bs, git_sha),
             "# 4. each role image, then its digest (the AgentConfig containerUri):"]
    for role in roles:
        lines += [start % ("ifabric-" + role),
                  digest % (image_tag(role, git_sha), "/tmp/ifabric-image-uri-%s" % role)]
    lines += [
        "# 5. the AgentConfigs",
        "python3 tools/make_ifabric_agents.py --discover --roles %s --out %s --pin <the same pin file>"
        % (roles_arg, out),
        "kubectl apply --dry-run=server -f %s" % out,
        "kubectl apply -f %s" % out,
        "# HOLD for the captain (approval is hers; record the words and the time, EP-10):",
    ]
    for role in roles:
        lines.append("#   kubectl -n components annotate agentconfig ifabric-%s %s=<captain> "
                     "%s='<attestation words>'" % (role, APPROVAL_KEYS[0], APPROVAL_KEYS[1]))
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="Write the ifabric- trio AgentConfigs (never applies them).")
    p.add_argument("--roles", default="customer,it,network")
    p.add_argument("--kit", default=os.environ.get("IFABRIC_KIT_GENERATOR", DEFAULT_KIT))
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--image", action="append", default=[], help="role=repo@sha256:... (default: URI_FILE)")
    p.add_argument("--git-sha", default=None)
    p.add_argument("--pin", help="the in-path pin JSON file (register/pins/<v>-<mode>.json)")
    p.add_argument("--register-version", default=None, help="optional: must equal the pin's register.version")
    p.add_argument("--register-sha256", default=None, help="optional: must equal the pin's register.sha256")
    p.add_argument("--rails-mode", default="enforce", choices=("enforce", "observe"))  # D-C: no "off"
    p.add_argument("--extra-pip", default=DEFAULT_EXTRA_PIP)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--discover", action="store_true", help="OPS LANE ONLY: the kit's Discovery reads the cluster")
    p.add_argument("--buildspecs", metavar="DIR",
                   help="write buildspec-ifabric-base.json and buildspec-ifabric-<role>.json (two-stage, D-B)")
    p.add_argument("--bundles-root", default=REPO, help="where agents/ifabric-*/ifabric-*.py are (default: repo)")
    p.add_argument("--account", default="DRYRUN-ACCOUNT", help="ECR account (default: the kit's dry-run placeholder)")
    p.add_argument("--stack", default="eks-cluster", help="CFT stack name (repo <stack>-aws-agent-operator)")
    p.add_argument("--region", default=os.environ.get("AWS_REGION") or "us-east-1")
    p.add_argument("--base-image", default=None,
                   help="<repo>@sha256:<digest> of the ifabric-base build (default: /tmp/ifabric-base-image-uri)")
    a = p.parse_args(argv)
    try:
        roles = [r.strip() for r in a.roles.split(",") if r.strip()]
        for r in roles:
            if r not in TRIO:
                raise Refused("unknown role %r" % r)
            check_source("agents/ifabric-%s/ifabric-%s.py" % (r, r))
        git_sha = a.git_sha or _git_sha()
        images = {}
        for item in a.image:
            role, _, uri = item.partition("=")
            images[role] = uri
        for r in roles:
            images.setdefault(r, _read_uri("/tmp/ifabric-image-uri-%s" % r) or
                              "<repo>@sha256:<digest-of-%s>" % image_tag(r, git_sha))
        if a.pin:
            with open(a.pin, "rb") as f:
                pin_json, pin_sha, reg_v, reg_s = pin_env(f.read(), a.register_version, a.register_sha256)
        elif a.discover:
            raise Refused("--discover needs --pin (the agents fail closed without one)")
        else:
            pin_json, pin_sha = "<pin-json>", "<pin-sha256>"
            reg_v, reg_s = a.register_version or "<register-version>", a.register_sha256 or "<register-sha256>"
        if a.discover and os.path.abspath(a.out).startswith(REPO + os.sep):
            raise Refused("--out inside the repo with --discover would put the ledger token in a tracked tree")
        env = env_extra(a.rails_mode, pin_json, pin_sha, reg_v, reg_s)
        kit = load_kit(a.kit)
        d = kit.Discovery(None) if a.discover else OfflineDiscovery()
        docs = build_crs(kit, d, roles, images, a.model, env)
        if a.discover:
            refuse_placeholders(docs)
    except Refused as e:
        print("make_ifabric_agents: refused: %s" % e, file=sys.stderr)
        return 2
    header = ("# Generated by tools/make_ifabric_agents.py (%s). git %s.\n" % (
        "DISCOVERED values: holds the ledger token in plain text, never commit" if a.discover
        else "offline placeholders", git_sha))
    with open(a.out, "w") as f:
        f.write(header + kit.to_yaml(docs))
    print("wrote %d AgentConfig(s) to %s" % (len(docs), a.out))
    if a.buildspecs:
        ecr_host = "%s.dkr.ecr.%s.amazonaws.com" % (a.account, a.region)
        repo = "%s-aws-agent-operator" % a.stack
        base_ref = a.base_image or _read_uri("/tmp/ifabric-base-image-uri")
        if base_ref and not DIGEST_RE.match(base_ref):
            print("make_ifabric_agents: refused: --base-image %r is not <repo>@sha256:<64 hex>" % base_ref,
                  file=sys.stderr)
            return 2
        base_ref = base_ref or "%s/%s@sha256:<digest-of-ifabric-base-%s>" % (ecr_host, repo, git_sha)
        try:
            written = write_buildspecs(a.buildspecs, roles, a.bundles_root, git_sha, ecr_host, repo, base_ref,
                                       a.extra_pip)
        except Refused as e:
            print("make_ifabric_agents: refused: %s" % e, file=sys.stderr)
            return 2
        for name, (path, n, tag) in sorted(written.items()):
            print("wrote %s (%d chars <= %d; IMAGE_TAG %s)" % (path, n, BUILDSPEC_CAP, tag))
        if "<" in base_ref or a.account == "DRYRUN-ACCOUNT":
            print("NOTE: the buildspecs hold placeholders (account and/or base digest): review only; rerun with "
                  "--account/--stack and the base digest before any start-build")
    print(ops_commands(roles, git_sha, a.out, a.region, a.buildspecs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
