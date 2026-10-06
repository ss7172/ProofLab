"""Tests for tools/make_ifabric_agents.py (PR-06, T3.3 + B-G6): offline only, never a cluster call.

The kit generator is read from ../workshop-assets/reference-impl/ when present; a minimal stand-in with
the same _agent_cr / to_yaml surface is used otherwise, so the refusal tests always run.
"""
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MK = _load(os.path.join(REPO, "tools", "make_ifabric_agents.py"), "make_ifabric_agents_ut")
REF_FILE = "agent" + ".py"
REF_TAGS = ["reference-agent-v" + "5", "reference-agent-v" + "5-agentcore"]
APPROVE_KW = "appr" + "ove"
SHA_IMG = "123.dkr.ecr.us-east-1.amazonaws.com/x-aws-agent-operator@sha256:" + "a" * 64


def _kit():
    if os.path.isfile(MK.DEFAULT_KIT):
        return MK.load_kit(MK.DEFAULT_KIT)
    pytest.skip("kit generator not present at %s" % MK.DEFAULT_KIT)


def _env():
    return MK.env_extra("enforce", '{"c16":{}}', "f" * 64, "v1", "e" * 64)


def test_trio_crs_offline_names_env_strings_no_approval():
    kit = _kit()
    images = dict((r, SHA_IMG) for r in MK.TRIO)
    docs = MK.build_crs(kit, MK.OfflineDiscovery(), list(MK.TRIO), images, MK.DEFAULT_MODEL, _env())
    assert [d["metadata"]["name"] for d in docs] == ["ifabric-customer", "ifabric-it", "ifabric-network"]
    for d, role in zip(docs, MK.TRIO):
        assert MK.NAME_RE.match(d["metadata"]["name"])
        assert "annotations" not in d["metadata"]
        env = d["spec"]["awsAgentCore"]["environmentVariables"]
        assert all(isinstance(v, str) for v in env.values())
        assert env["IFABRIC_RAILS_MODE"] == "enforce"
        assert env["OTEL_SEMCONV_STABILITY_OPT_IN"] == "gen_ai_unredacted_attributes="
        assert "MODEL_ALIAS" not in env
        assert env["TOOL_MCP_ALIAS"] == MK.TRIO[role][2]
        assert d["spec"]["dependsOn"] == {"models": ["nemotron-super-120b"], "tools": [MK.TRIO[role][2]]}
    text = kit.to_yaml(docs)
    assert "modaas.tmforum.org/approver" not in text and "system-admin" not in text


def test_name_regex_on_the_trio():
    for r in MK.TRIO:
        assert MK.NAME_RE.match("ifabric-" + r)
    for bad in ("Ifabric-x", "ifabric_x", "ifabric-", "-ifabric", "i" * 41):
        assert not MK.NAME_RE.match(bad)


def test_refuses_reference_file_name_and_non_ifabric_sources():
    with pytest.raises(MK.Refused):
        MK.check_source("agents/ifabric-customer/" + REF_FILE)
    with pytest.raises(MK.Refused):
        MK.check_source("agents/x/mine.py")
    MK.check_source("agents/ifabric-customer/ifabric-customer.py")


def test_refuses_reference_and_foreign_tags():
    for t in REF_TAGS + ["reference-agent-v6", "my-agent-agentcore", "bad tag", ""]:
        with pytest.raises(MK.Refused):
            MK.check_tag(t)
    assert MK.image_tag("it", "abc123def456") == "ifabric-it-abc123def456"


def test_refuses_tag_images_and_reference_images():
    for uri in ("123.dkr.ecr.us-east-1.amazonaws.com/x-aws-agent-operator:ifabric-it-abc",
                "123.dkr.ecr.us-east-1.amazonaws.com/x-aws-agent-operator:" + REF_TAGS[1]):
        with pytest.raises(MK.Refused):
            MK.check_image(uri)
    MK.check_image(SHA_IMG)


def test_refuses_approval_annotation_non_string_env_and_model_alias():
    kit = _kit()
    cr = kit._agent_cr(MK.OfflineDiscovery(), name="ifabric-it", role="it", step_base="3", description="d",
                       skills=["s"], model="m", image=SHA_IMG, tool_alias="runbook-lookup",
                       env_extra=_env(), **{APPROVE_KW: True})
    with pytest.raises(MK.Refused):
        MK.validate_cr(cr)
    cr = kit._agent_cr(MK.OfflineDiscovery(), name="ifabric-it", role="it", step_base="3", description="d",
                       skills=["s"], model="m", image=SHA_IMG, tool_alias="runbook-lookup",
                       env_extra=dict(_env(), IFABRIC_X=3))
    with pytest.raises(MK.Refused):
        MK.validate_cr(cr)
    with pytest.raises(MK.Refused):
        MK.env_extra("enforce", "{}", "x", "v1", "y", extra={"MODEL_ALIAS": "nemotron-super-120b"})
    cr = kit._agent_cr(MK.OfflineDiscovery(), name="Ifabric_bad", role="it", step_base="3", description="d",
                       skills=["s"], model="m", image=SHA_IMG, env_extra=_env())
    with pytest.raises(MK.Refused):
        MK.validate_cr(cr)


SYNTH_PIN = os.path.join(REPO, "tools", "docker_smoke", "synthetic_pin.json")


def _yaml_env(text, key):
    """The first value of `key` in the kit's YAML (to_yaml writes JSON-quoted scalars)."""
    import json
    for line in text.splitlines():
        k, sep, v = line.strip().partition(": ")
        if sep and k.strip('"') == key:
            return json.loads(v)
    raise AssertionError("no %s in the generated YAML" % key)


def test_pin_env_hashes_the_env_string_not_the_file_bytes():
    import hashlib
    import json
    raw = open(SYNTH_PIN, "rb").read()
    assert b"\n  " in raw                                  # pretty-printed on disk
    pin_json, pin_sha, rv, rs = MK.pin_env(raw)
    assert pin_json == json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert pin_sha == hashlib.sha256(pin_json.encode("utf-8")).hexdigest()
    assert pin_sha != hashlib.sha256(raw).hexdigest()
    obj = json.loads(raw)
    assert (rv, rs) == (obj["register"]["version"], obj["register"]["sha256"])
    assert MK._HEX64.match(rs) and MK._HEX64.match(pin_sha)


def test_pin_env_refuses_disagreeing_flags_and_a_pin_without_register():
    raw = open(SYNTH_PIN, "rb").read()
    with pytest.raises(MK.Refused):
        MK.pin_env(raw, register_version="v-other")
    with pytest.raises(MK.Refused):
        MK.pin_env(raw, register_sha256="e" * 64)
    with pytest.raises(MK.Refused):
        MK.pin_env(b'{"c16": {"mode": "enforce"}}')
    with pytest.raises(MK.Refused):
        MK.pin_env(b"not json")


def test_discover_refuses_placeholders_in_env_or_image():
    kit = _kit()
    pin_json, pin_sha, rv, rs = MK.pin_env(open(SYNTH_PIN, "rb").read())
    env = MK.env_extra("enforce", pin_json, pin_sha, rv, rs)
    docs = MK.build_crs(kit, MK.OfflineDiscovery(), ["it"], {"it": SHA_IMG}, MK.DEFAULT_MODEL, env)
    with pytest.raises(MK.Refused):        # OfflineDiscovery's AUDIT_URL/token placeholders
        MK.refuse_placeholders(docs)
    ph_img = "<repo>@sha256:<digest-of-ifabric-it-x>"
    docs[0]["spec"]["awsAgentCore"]["containerUri"] = ph_img
    with pytest.raises(MK.Refused):
        MK.refuse_placeholders(docs)


def test_main_offline_writes_file_and_prints_ops_commands(tmp_path, capsys):
    import hashlib
    _kit()
    out = tmp_path / "trio.yaml"
    rc = MK.main(["--out", str(out), "--git-sha", "abc123def456", "--pin", SYNTH_PIN] +
                 ["--image=%s=%s" % (r, SHA_IMG) for r in MK.TRIO])
    assert rc == 0
    text = out.read_text()
    assert text.count("kind: \"AgentConfig\"") == 3
    assert "<ledger-write-token-from-discovery>" in text
    printed = capsys.readouterr().out
    assert "imageTag=ifabric-base-abc123def456" in printed
    assert "imageTag=ifabric-customer-abc123def456" in printed
    assert "--privileged-mode-override" in printed and "start-build" in printed
    assert "kubectl apply --dry-run=server" in printed
    assert "HOLD for the captain" in printed
    assert " " + REF_FILE not in printed
    pin_json = _yaml_env(text, "IFABRIC_PIN_JSON")
    assert hashlib.sha256(pin_json.encode("utf-8")).hexdigest() == _yaml_env(text, "IFABRIC_PIN_SHA256")
    assert MK._HEX64.match(_yaml_env(text, "IFABRIC_REGISTER_SHA256"))
    assert _yaml_env(text, "IFABRIC_REGISTER_VERSION") == "synthetic-s0"


def test_main_refuses_discover_without_pin_and_inside_repo(tmp_path):
    assert MK.main(["--discover", "--out", str(tmp_path / "x.yaml")]) == 2
    assert MK.main(["--discover", "--pin", SYNTH_PIN, "--out", os.path.join(REPO, "x.yaml")]) == 2
    assert not os.path.exists(os.path.join(REPO, "x.yaml"))
