#!/usr/bin/env python3
"""Write the ifabric- trio's AgentConfig manifests through the kit's own generator (ARCH 7.1; T3.3, B-G6).

It loads the kit's make-agentcore-agents.py with importlib and calls its _agent_cr(..., tool_alias=<tool>,
env_extra={IFABRIC_*}) per role, so dependsOn.tools, TOOL_MCP_ALIAS and the ledger pair land in the CR
exactly as the kit writes them. It WRITES files and PRINTS the ops-lane commands; it never runs kubectl,
aws or a build, and never takes the generator's approval path (that stamps system-admin).

  python3 tools/make_ifabric_agents.py --roles customer,it,network --pin register/pins/v1-enforce.json \\
      --register-version v1 --register-sha256 <sha> [--out /tmp/ifabric-agents.generated.yaml]

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


def ops_commands(roles, git_sha, out, kit_dir, extra_pip):
    lines = ["# ---- ops lane (NOT run by this tool; one action at a time, each with the captain's OK) ----"]
    for role in roles:
        name = "ifabric-" + role
        lines += [
            "python3 tools/bundle_agent.py --role %s" % role,
            "TARGET=agentcore AGENT_SRC=agents/%s/%s.py IMAGE_TAG=%s URI_FILE=/tmp/ifabric-image-uri-%s "
            "EXTRA_PIP='%s' bash %s/build-agent-image.sh" % (name, name, image_tag(role, git_sha), role,
                                                            extra_pip, kit_dir),
        ]
    lines += [
        "python3 tools/make_ifabric_agents.py --discover --roles %s --out %s <same pin/register flags>"
        % (",".join(roles), out),
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
    p.add_argument("--register-version", default="<register-version>")
    p.add_argument("--register-sha256", default="<register-sha256>")
    p.add_argument("--rails-mode", default="enforce", choices=("enforce", "observe", "off"))
    p.add_argument("--extra-pip", default=DEFAULT_EXTRA_PIP)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--discover", action="store_true", help="OPS LANE ONLY: the kit's Discovery reads the cluster")
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
            raw = open(a.pin, "rb").read()
            pin_json = json.dumps(json.loads(raw.decode("utf-8")), separators=(",", ":"), sort_keys=True)
            pin_sha = hashlib.sha256(raw).hexdigest()
        elif a.discover:
            raise Refused("--discover needs --pin (the agents fail closed without one)")
        else:
            pin_json, pin_sha = "<pin-json>", "<pin-sha256>"
        if a.discover and os.path.abspath(a.out).startswith(REPO + os.sep):
            raise Refused("--out inside the repo with --discover would put the ledger token in a tracked tree")
        env = env_extra(a.rails_mode, pin_json, pin_sha, a.register_version, a.register_sha256)
        kit = load_kit(a.kit)
        d = kit.Discovery(None) if a.discover else OfflineDiscovery()
        docs = build_crs(kit, d, roles, images, a.model, env)
    except Refused as e:
        print("make_ifabric_agents: refused: %s" % e, file=sys.stderr)
        return 2
    header = ("# Generated by tools/make_ifabric_agents.py (%s). git %s.\n" % (
        "DISCOVERED values: holds the ledger token in plain text, never commit" if a.discover
        else "offline placeholders", git_sha))
    with open(a.out, "w") as f:
        f.write(header + kit.to_yaml(docs))
    print("wrote %d AgentConfig(s) to %s" % (len(docs), a.out))
    print(ops_commands(roles, git_sha, a.out, os.path.dirname(a.kit), a.extra_pip))
    return 0


if __name__ == "__main__":
    sys.exit(main())
