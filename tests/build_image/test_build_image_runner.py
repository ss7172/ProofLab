"""PR-26: tools/build_ifabric_image.sh, the ops-lane runner, OFFLINE: --dry-run with an `aws` that fails if
called, and the live path against a fake `aws` on PATH (a shell script with canned replies, no network)."""
import json
import os
import re
import stat
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(REPO, "tools", "build_ifabric_image.sh")
DIGEST = "sha256:" + "ab" * 32
FAKE_ACCT = "1" * 12   # a fake 12-digit id: it must never reach stdout

FAKE_AWS = r'''#!/usr/bin/env bash
# fake aws for tests: logs argv (one line per call), replies from $FAKE_STATE
echo "$*" >> "$FAKE_LOG"
case "$1 $2" in
  "ecr describe-images")
    if [ -f "$FAKE_STATE/exists" ]; then echo "@DIGEST@"; exit 0; fi
    echo "An error occurred (ImageNotFoundException) when calling the DescribeImages operation" >&2; exit 254 ;;
  "codebuild start-build")
    echo "a-01-eks-cluster-modaas-image-build:0000-test"; exit 0 ;;
  "codebuild batch-get-builds")
    case "$*" in *phases*) printf 'BUILD\tFAILED\t3\n'; exit 0 ;; esac
    printf '%s\tCOMPLETED\n' "$(cat "$FAKE_STATE/status")"
    [ "$(cat "$FAKE_STATE/status")" = SUCCEEDED ] && touch "$FAKE_STATE/exists"; exit 0 ;;
  "logs filter-log-events")
    printf 'IFABRIC_PUSHED @DIGEST@\n'; exit 0 ;;
  "ecr describe-repositories")
    echo "@ACCT@.dkr.ecr.us-east-1.amazonaws.com/a-01-eks-cluster-aws-agent-operator"; exit 0 ;;
esac
echo "fake aws: unexpected $*" >&2; exit 99
'''.replace("@DIGEST@", DIGEST).replace("@ACCT@", FAKE_ACCT)


def _env_override(env, **kw):
    e = dict(env)
    e.update(kw)
    return e


@pytest.fixture()
def req_path(requests_by_role, br, tmp_path):
    req, meta = requests_by_role["customer"]
    out, _mp = br.write(req, meta, str(tmp_path / "startbuild-ifabric-customer.json"))
    return out, req


@pytest.fixture()
def fake(tmp_path):
    binp = tmp_path / "bin"
    binp.mkdir()
    aws = binp / "aws"
    aws.write_text(FAKE_AWS)
    aws.chmod(aws.stat().st_mode | stat.S_IEXEC)
    state = tmp_path / "state"
    state.mkdir()
    (state / "status").write_text("SUCCEEDED")
    env = dict(os.environ)
    for k in ("AWS_REGION", "AWS_DEFAULT_REGION", "AWS_PROFILE"):
        env.pop(k, None)
    env.update({"PATH": str(binp) + os.pathsep + env.get("PATH", ""), "FAKE_LOG": str(tmp_path / "aws.log"),
                "FAKE_STATE": str(state)})
    return env, tmp_path


def _run(args, env):
    return subprocess.run(["bash", SCRIPT] + args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def _calls(tmp):
    p = tmp / "aws.log"
    return p.read_text().splitlines() if p.exists() else []


def test_dry_run_calls_nothing_and_prints_no_payload(req_path, fake):
    out, req = req_path
    env, tmp = fake
    never = tmp / "never"
    never.mkdir()
    (never / "aws").write_text("#!/bin/sh\necho CALLED >&2\nexit 99\n")
    (never / "aws").chmod(0o755)
    r = _run(["--request", out, "--dry-run"], _env_override(env, PATH=str(never) + os.pathsep + os.environ["PATH"]))
    assert r.returncode == 0, r.stderr
    assert "CALLED" not in r.stderr
    text = r.stdout + r.stderr
    envs = dict((e["name"], e["value"]) for e in req["environmentVariablesOverride"])
    for name in ("IFABRIC_BASE_B64", "IFABRIC_ROLE_B64"):
        assert envs[name][:32] not in text and envs[name][-32:] not in text
    assert not re.search(r"[A-Za-z0-9+/=]{200,}", text)                 # no base64 blob of any kind
    bgb = [l for l in r.stdout.splitlines() if "batch-get-builds" in l]
    assert bgb and all("--query" in l for l in bgb)
    sb = [l for l in r.stdout.splitlines() if "start-build" in l]
    assert sb and all("--cli-input-json file://" in l and "--query 'build.id'" in l for l in sb)
    assert "imageTag=ifabric-customer-75881e3" in r.stdout
    assert "/aws/codebuild/a-01-eks-cluster-modaas-image-build" in r.stdout


def test_default_uri_file_matches_make_ifabric_agents(req_path, fake):
    """The runner's default URI file is the one make_ifabric_agents reads (/tmp/ifabric-image-uri-<role>)."""
    out, req = req_path
    env, tmp = fake
    r = _run(["--request", out, "--dry-run"], env)
    assert r.returncode == 0, r.stderr
    assert "-> /tmp/ifabric-image-uri-customer" in r.stdout
    src = open(os.path.join(REPO, "tools", "make_ifabric_agents.py")).read()
    assert '"/tmp/ifabric-image-uri-%s" % r' in src


def test_live_path_with_fake_aws(req_path, fake):
    out, req = req_path
    env, tmp = fake
    uri_file = tmp / "uri"
    r = _run(["--request", out, "--region", "us-east-1", "--uri-file", str(uri_file)], env)
    assert r.returncode == 0, r.stderr + r.stdout
    assert uri_file.read_text() == ("%s.dkr.ecr.us-east-1.amazonaws.com/a-01-eks-cluster-aws-agent-operator@%s\n"
                                    % (FAKE_ACCT, DIGEST))
    assert FAKE_ACCT not in r.stdout + r.stderr                         # the URI goes to the file only
    assert DIGEST in r.stdout
    calls = _calls(tmp)
    assert calls[0].startswith("ecr describe-images")                   # the tag-exists check comes first
    assert [c for c in calls if c.startswith("codebuild start-build")][0].endswith("--query build.id --output text")
    assert all("--query" in c for c in calls)                           # every read narrowed
    logs = [c for c in calls if c.startswith("logs filter-log-events")][0]
    assert "--log-stream-names 0000-test" in logs and "--filter-pattern IFABRIC_PUSHED" in logs


def test_refuses_existing_tag(req_path, fake):
    out, _req = req_path
    env, tmp = fake
    (tmp / "state" / "exists").write_text("")
    r = _run(["--request", out, "--region", "us-east-1", "--uri-file", str(tmp / "uri")], env)
    assert r.returncode == 3
    assert "already exists" in r.stderr
    assert not [c for c in _calls(tmp) if "start-build" in c]
    assert not (tmp / "uri").exists()


def test_failed_build_writes_nothing(req_path, fake):
    out, _req = req_path
    env, tmp = fake
    (tmp / "state" / "status").write_text("FAILED")
    r = _run(["--request", out, "--region", "us-east-1", "--uri-file", str(tmp / "uri")], env)
    assert r.returncode == 1 and "build FAILED" in r.stderr
    assert not (tmp / "uri").exists()


def test_refuses_a_request_with_a_reference_tag(req_path, fake, tmp_path):
    out, req = req_path
    env, tmp = fake
    bad = json.loads(json.dumps(req))
    for e in bad["environmentVariablesOverride"]:
        if e["name"] == "IFABRIC_TAG":
            e["value"] = "reference-agent-v5-agentcore"
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    for extra in ([], ["--dry-run"]):
        r = _run(["--request", str(p), "--region", "us-east-1"] + extra, env)
        assert r.returncode == 2 and "REFUSED" in r.stderr
    assert _calls(tmp) == []
