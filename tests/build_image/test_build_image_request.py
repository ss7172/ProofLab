"""PR-26: tools/ifabric_build_request.py, the StartBuild request for the env-override carrier, over the REAL
merged bundles (conftest builds them in a temp dir). Stdlib + pytest; Python 3.9+."""
import base64
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TRIO = ("customer", "it", "network")
ASSURANCE_FILE = os.path.join(REPO, "agents", "ifabric-assurance", "ifabric-assurance.py")

KIT = os.path.join(os.path.dirname(os.path.dirname(REPO)), "workshop-assets", "reference-impl",
                   "build-agent-image.sh")
FORBIDDEN = "agent" + ".py"


def _env(request):
    return dict((e["name"], e["value"]) for e in request["environmentVariablesOverride"])


def _sha(data):
    return hashlib.sha256(data).hexdigest()


# ---- shape, sizes ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("role", TRIO + ("assurance",))
def test_request_shape_and_sizes(br, requests_by_role, bundles, role):
    req, meta = requests_by_role[role]
    assert req["projectName"] == "a-01-eks-cluster-modaas-image-build"
    assert req["environmentTypeOverride"] == "ARM_CONTAINER"
    assert req["imageOverride"] == "aws/codebuild/amazonlinux-aarch64-standard:3.0"
    assert req["computeTypeOverride"] == "BUILD_GENERAL1_LARGE"
    assert req["privilegedModeOverride"] is True
    env = _env(req)
    assert all(e["type"] == "PLAINTEXT" for e in req["environmentVariablesOverride"])
    assert env["IFABRIC_TAG"] == "ifabric-%s-75881e3" % role
    assert env["IFABRIC_REPO"] == "a-01-eks-cluster-aws-agent-operator"
    assert len(req["buildspecOverride"]) <= 25600 and len(req["buildspecOverride"]) < 2500
    assert all(len(v) <= 44000 for v in env.values())
    assert sum(len(k) + len(v) for k, v in env.items()) <= 46000   # D-B'': 46000 in all, 44000 per value
    assert br.ENV_TOTAL_CAP == 46000 and br.ENV_VALUE_CAP == 44000
    s = meta["sizes"]
    assert s["env_total_chars_with_names"] == sum(len(k) + len(v) for k, v in env.items())
    assert s["role_gzip_base64_chars"] == len(env["IFABRIC_ROLE_B64"])
    role_file = ASSURANCE_FILE if role == "assurance" else bundles[role]
    assert env["IFABRIC_ROLE_SHA256"] == _sha(open(role_file, "rb").read())
    if role == "assurance":
        assert "IFABRIC_BASE_B64" not in env and meta["single_file"] and meta["c16_core_sha256"] is None
    else:
        assert env["IFABRIC_BASE_SHA256"] == _sha(open(bundles["base"], "rb").read())
        assert s["base_gzip_base64_chars"] == len(env["IFABRIC_BASE_B64"])
        core = _sha(open(os.path.join(REPO, "prooflab", "evaluators", "c16_core.py"), "rb").read())
        assert meta["c16_core_sha256"] == core
    # The payload decodes byte-exact (python gzip, mtime 0).
    assert gzip.decompress(base64.b64decode(env["IFABRIC_ROLE_B64"])) == open(role_file, "rb").read()
    print("SIZES %s base_b64=%s role_b64=%d env_total=%d buildspec=%d request=%d" % (
        role, s["base_gzip_base64_chars"], s["role_gzip_base64_chars"], s["env_total_chars_with_names"],
        s["buildspec_chars"], s["request_json_bytes"]))


def test_sidecar_meta_has_no_payload(br, bundles, tmp_path):
    out = str(tmp_path / "startbuild-ifabric-it.json")
    rc = br.main(["--role", "it", "--tag", "ifabric-it-0123456789abcdef", "--base", bundles["base"],
                  "--role-file", bundles["it"], "--out", out])
    assert rc == 0
    req = json.load(open(out))
    meta_text = open(str(tmp_path / "startbuild-ifabric-it.meta.json")).read()
    meta = json.loads(meta_text)
    env = _env(req)
    for name in ("IFABRIC_BASE_B64", "IFABRIC_ROLE_B64"):
        assert env[name][:40] not in meta_text and env[name][-40:] not in meta_text
    assert meta["files"]["IFABRIC_ROLE"]["in_image"] == "/app/" + FORBIDDEN
    assert meta["files"]["IFABRIC_BASE"]["in_image"] == "/app/ifabric_base.py"
    assert oct(os.stat(out).st_mode & 0o777) == oct(0o600)


def test_deterministic(br, bundles):
    a = br.make_request("network", "ifabric-network-abcdef0", bundles["network"], bundles["base"])
    b = br.make_request("network", "ifabric-network-abcdef0", bundles["network"], bundles["base"])
    assert br.dumps_request(a[0]) == br.dumps_request(b[0])


# ---- refusals ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tag", [
    "reference-agent-v5-agentcore", "reference-agent-v5", "my-agent", "hackathon-helper", "latest",
    "ifabric-customer", "ifabric-customer-12345", "ifabric-customer-75881E3", "ifabric-customer-75881e3-x",
    "ifabric-it-75881e3",                         # another role's tag
    "ifabric-customer-" + "a" * 41, "",
])
def test_refuses_bad_tags(br, bundles, tag):
    with pytest.raises(br.Refused):
        br.make_request("customer", tag, bundles["customer"], bundles["base"])


def test_refuses_reference_file_name(br, bundles, tmp_path):
    p = tmp_path / FORBIDDEN
    shutil.copyfile(bundles["customer"], str(p))
    with pytest.raises(br.Refused):
        br.make_request("customer", "ifabric-customer-75881e3", str(p), bundles["base"])
    base = tmp_path / "b" / FORBIDDEN
    base.parent.mkdir()
    shutil.copyfile(bundles["base"], str(base))
    with pytest.raises(br.Refused):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], str(base))


def test_refuses_wrong_role_file_name(br, bundles):
    with pytest.raises(br.Refused):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["it"], bundles["base"])


def test_refuses_c16_mismatch(br, bundles, tmp_path):
    other = tmp_path / "c16_core.py"
    other.write_bytes(open(os.path.join(REPO, "prooflab", "evaluators", "c16_core.py"), "rb").read() + b"# x\n")
    with pytest.raises(br.Refused, match="evaluator.sha256"):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], bundles["base"],
                        c16_core=str(other))
    # A base whose marker was edited (even with the core literal intact) is refused too.
    text = open(bundles["base"], encoding="utf-8").read()
    bad = tmp_path / "ifabric-base.py"
    bad.write_text(re.sub(r"(# evaluator\.sha256=)[0-9a-f]{64}", r"\g<1>" + "0" * 64, text, count=1),
                   encoding="utf-8")
    with pytest.raises(br.Refused, match="evaluator.sha256"):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], str(bad))


def test_refuses_role_built_against_another_base(br, bundles, tmp_path):
    text = open(bundles["base"], encoding="utf-8").read()
    other = tmp_path / "ifabric-base.py"
    other.write_text(text + "\n# a different base file\n", encoding="utf-8")
    with pytest.raises(br.Refused, match="built against base"):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], str(other))


def test_refuses_oversize(br, bundles, tmp_path, monkeypatch):
    # A real-size request passes; the gates trip when the caps shrink below it, and on a genuinely big file.
    monkeypatch.setattr(br, "ENV_TOTAL_CAP", 30000)
    with pytest.raises(br.Refused, match="total"):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], bundles["base"])
    monkeypatch.undo()
    monkeypatch.setattr(br, "ENV_VALUE_CAP", 20000)
    with pytest.raises(br.Refused, match="per value"):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], bundles["base"])
    monkeypatch.undo()
    monkeypatch.setattr(br, "BUILDSPEC_CAP", 1000)
    with pytest.raises(br.Refused, match="buildspec"):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], bundles["base"])
    monkeypatch.undo()
    import random
    rnd = random.Random(26)
    big = tmp_path / "ifabric-assurance.py"
    big.write_text("X = %r\n" % "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz ") for _ in range(70000)),
                   encoding="utf-8")
    with pytest.raises(br.Refused, match="44000"):
        br.make_request("assurance", "ifabric-assurance-75881e3", str(big))


def test_refuses_base_mismatch_by_role_kind(br, bundles):
    with pytest.raises(br.Refused):
        br.make_request("assurance", "ifabric-assurance-75881e3", ASSURANCE_FILE, bundles["base"])
    with pytest.raises(br.Refused):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"])


@pytest.mark.parametrize("extra", ["https://example.invalid/x.whl", "--index-url=x", "git+https://x/y",
                                   "a==1\nb==2", "pkg @ https://x"])
def test_refuses_extra_pip_the_kit_refuses(br, bundles, extra):
    with pytest.raises(br.Refused):
        br.make_request("customer", "ifabric-customer-75881e3", bundles["customer"], bundles["base"],
                        extra_pip=extra)


def test_main_refusal_exit_code(br, bundles, tmp_path, capsys):
    rc = br.main(["--role", "customer", "--tag", "reference-agent-v5-agentcore", "--base", bundles["base"],
                  "--role-file", bundles["customer"], "--out", str(tmp_path / "r.json")])
    assert rc == 2 and not (tmp_path / "r.json").exists()


# ---- the image the buildspec describes ---------------------------------------------------------------------

def _dockerfile(req):
    spec = json.loads(req["buildspecOverride"])
    line = [c for c in spec["phases"]["build"]["commands"] if c.endswith("| base64 -d > Dockerfile")][0]
    return base64.b64decode(line.split()[1]).decode("utf-8")


def test_dockerfile_is_the_kit_shape(br, requests_by_role):
    df = _dockerfile(requests_by_role["customer"][0])
    lines = df.splitlines()
    assert lines[0] == "FROM public.ecr.aws/docker/library/python:3.12-slim"
    assert lines[2] == ("RUN pip install --no-cache-dir strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 "
                        "mcp==1.30.0 boto3==1.43.103 aws-opentelemetry-distro==0.21.0 'openai==2.54.0'")
    # aws_mcp off: ADOT 0.21.0's McpInstrumentor records tool arguments + results in clear on "mcp tools/call" spans
    assert "ENV OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=urllib,urllib3,botocore,boto3,aws_mcp" in lines
    assert sum(l.startswith("ENV OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=") for l in lines) == 1
    assert "COPY ifabric_base.py /app/ifabric_base.py" in lines
    assert "COPY ifabric-customer.py /app/%s" % FORBIDDEN in lines
    assert lines[-1] == 'ENTRYPOINT ["opentelemetry-instrument", "python3", "/app/%s"]' % FORBIDDEN
    one = _dockerfile(requests_by_role["assurance"][0])
    assert "ifabric_base.py" not in one and "COPY ifabric-assurance.py /app/%s" % FORBIDDEN in one


def test_dockerfile_matches_make_ifabric_agents_and_kit(br):
    sys.path.insert(0, os.path.join(REPO, "tools"))
    try:
        import make_ifabric_agents as mk
    finally:
        sys.path.pop(0)
    assert br.KIT_SDK_PIP == mk.KIT_SDK_PIP and br.KIT_SDK_ENV == mk.KIT_SDK_ENV
    assert br.KIT_BASE_IMAGE == mk.KIT_BASE_IMAGE and br.KIT_ENTRY_PATH == mk.KIT_ENTRY_PATH
    assert br.DEFAULT_EXTRA_PIP == mk.DEFAULT_EXTRA_PIP
    assert br.BASE_CTX == mk.BASE_IN_IMAGE
    import importlib.util
    spec = importlib.util.spec_from_file_location("bundle_agent_bi", os.path.join(REPO, "tools", "bundle_agent.py"))
    ba = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ba)
    assert "/app/" + br.BASE_CTX == ba.BASE_IN_IMAGE      # where the role loader opens the base
    if not os.path.isfile(KIT):
        pytest.skip("the kit script is not beside the repo")
    kit = open(KIT).read()
    assert 'SDK_PIP="%s"' % br.KIT_SDK_PIP in kit
    assert br.EXTRA_PIP_RE.pattern in kit
    assert '["opentelemetry-instrument", "python3", "/app/%s"]' % FORBIDDEN in kit


def test_buildspec_order_and_hygiene(br, requests_by_role):
    for role, (req, _m) in requests_by_role.items():
        spec = json.loads(req["buildspecOverride"])
        pre = spec["phases"]["pre_build"]["commands"]
        login = [i for i, c in enumerate(pre) if "get-login-password" in c][0]
        checks = [i for i, c in enumerate(pre) if "sha256sum -c" in c]
        assert checks and max(checks) < login, role       # verified BEFORE the ECR login
        text = req["buildspecOverride"]
        assert not re.search(r"\b\d{12}\b", text)          # no account id
        for word in ("printenv", "set -x", " env ", "IFABRIC_PUSHED"):
            if word == "IFABRIC_PUSHED":
                assert word in text
            else:
                assert word not in text
        assert _env(req)["IFABRIC_ROLE_B64"][:40] not in text
        assert any('[ "$ARCH" = "arm64" ]' in c for c in spec["phases"]["build"]["commands"])


# ---- the decode commands, run locally ----------------------------------------------------------------------

def _need(*tools):
    for t in tools:
        if not shutil.which(t):
            pytest.skip("%s not on PATH" % t)


@pytest.mark.parametrize("role", TRIO + ("assurance",))
def test_buildspec_decode_runs_locally(br, bundles, tmp_path, monkeypatch, role):
    """Take the buildspec's own pre_build commands up to the first aws call, run them in bash with the env
    values, and check both files: sha256 (sha256sum -c inside the commands), and ast parses each."""
    _need("bash", "base64", "gunzip", "sha256sum")
    build_dir = str(tmp_path / "ifb")
    monkeypatch.setattr(br, "BUILD_DIR", build_dir)
    if role == "assurance":
        req, _meta = br.make_request(role, "ifabric-assurance-75881e3", ASSURANCE_FILE)
    else:
        req, _meta = br.make_request(role, "ifabric-%s-75881e3" % role, bundles[role], bundles["base"])
    pre = json.loads(req["buildspecOverride"])["phases"]["pre_build"]["commands"]
    cut = [i for i, c in enumerate(pre) if "aws " in c][0]
    script = "set -e\n" + "\n".join(c for c in pre[:cut] if c != "uname -m") + "\n"
    env = dict(os.environ)
    env.update(_env(req))
    r = subprocess.run(["bash", "-c", script], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    assert r.returncode == 0, r.stdout
    assert r.stdout.count(": OK") == (1 if role == "assurance" else 2)
    assert "IFABRIC_ENV_OK" in r.stdout
    names = ["ifabric-%s.py" % role] + ([] if role == "assurance" else ["ifabric_base.py"])
    for n in names:
        p = os.path.join(build_dir, n)
        src = ASSURANCE_FILE if role == "assurance" else (bundles["base"] if n == "ifabric_base.py" else bundles[role])
        assert open(p, "rb").read() == open(src, "rb").read()
        chk = subprocess.run([sys.executable, "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read())", p])
        assert chk.returncode == 0
    # A tampered value fails the in-build check (and so the build) before any login.
    env["IFABRIC_ROLE_SHA256"] = "0" * 64
    r = subprocess.run(["bash", "-c", script], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    assert r.returncode != 0
