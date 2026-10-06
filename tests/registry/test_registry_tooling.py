"""PR-11 tests: pins, freeze, inventory, derive, approval finding, named runs, and the drafts in register/."""
import copy
import hashlib
import json
import os
import sys

import pytest

from prooflab.contract import pin as PIN
from prooflab.contract import register as REG
from prooflab.registry import approval_finding as AF
from prooflab.registry import derive as DV
from prooflab.registry import freeze as FZ
from prooflab.registry import inventory as INV
from prooflab.registry import named_runs as NR
from prooflab.registry import parse as P
from prooflab.registry import pinned as PN

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "fixtures")
REGISTER = os.path.join(ROOT, "register", "register.yaml")
RISKS = os.path.join(ROOT, "register", "risks.yaml")
INVENTORY = os.path.join(ROOT, "register", "inventory.yaml")


def rb(path):
    with open(path, "rb") as fh:
        return fh.read()


# ---- the drafts -------------------------------------------------------------------------------------------------

def test_register_draft_parses_and_validates():
    doc = P.parse_register(rb(REGISTER).decode())
    assert REG.validate_register(doc) == []
    assert sorted(P.kit_view(rb(REGISTER).decode())) == ["16", "7", "9"]
    for key in ("register_version", "status", "frozen_at", "builder", "assurance", "retention", "owner", "owner_name"):
        assert key in doc["top"], key


def test_risks_and_inventory_cross_check():
    reg = P.parse_register(rb(REGISTER).decode())
    risks = P.parse_risks(rb(RISKS).decode())
    inv = P.parse_inventory(rb(INVENTORY).decode())
    assert INV.validate_inventory(inv) == []
    assert INV.cross_check(reg, risks, inv) == []
    ids = [r["risk_id"] for r in risks["entries"]]
    for need in ("R-C16", "R-C7", "R-C9", "R-OWN", "R-JDG", "R-GR-01", "R-GR-02", "R-GR-03", "R-GR-04", "R-GR-05"):
        assert need in ids
    comps = dict((c["component_id"], c) for c in inv["entries"])
    for need in ("ifabric-rails-policy", "ifabric-adversarial-corpus", "ifabric-assurance-agent"):
        assert need in comps
    applies = " ".join(e.get("applies_to", "") for e in reg["entries"])
    assert "ifabric-assurance-agent" not in applies and "ifabric-rails-policy" not in applies


def test_cross_check_catches_assurance_agent_in_applies_to_and_missing_risk_ref():
    reg = P.parse_register(rb(REGISTER).decode())
    risks = P.parse_risks(rb(RISKS).decode())
    inv = P.parse_inventory(rb(INVENTORY).decode())
    bad = copy.deepcopy(reg)
    bad["entries"][0]["applies_to"] += ",ifabric-assurance-agent@x@y"
    del bad["entries"][1]["risk_ref"]
    errs = INV.cross_check(bad, risks, inv)
    assert any("ifabric-assurance-agent" in e for e in errs) and any("no risk_ref" in e for e in errs)


def test_no_secret_shaped_values_in_drafts():
    for path in (REGISTER, RISKS, INVENTORY):
        text = rb(path).decode().lower()
        assert "akia" not in text and "bearer " not in text and "begin " + "private" not in text


def kit_fallback_load_register(text):
    """The kit's no-PyYAML fallback `_load_register`, as vendored in PR-01's tests (tiny; inlined to stay decoupled)."""
    controls, cur = {}, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- control_id:"):
            if cur:
                controls[str(cur["control_id"])] = cur
            cur = {"control_id": line.split(":", 1)[1].strip().strip('"\'')}
        elif cur is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            cur[k] = v.strip().strip('"\'')
    if cur:
        controls[str(cur["control_id"])] = cur
    return controls


def test_kit_parity_on_the_draft_register():
    text = rb(REGISTER).decode()
    ours, kit = P.kit_view(text), kit_fallback_load_register(text)
    assert sorted(ours) == ["16", "7", "9"] and ours == kit
    for cid in ours:
        for field in REG.KIT_FIELDS:
            assert ours[cid][field] == kit[cid][field]
    assert kit["16"]["observation_limit"] == ours["16"]["cap_tier_default"]  # kit field = the default tier's cap


# ---- pins --------------------------------------------------------------------------------------------------------

def test_pin_roundtrip_byte_for_byte_and_declared_faults_inside():
    data = rb(REGISTER)
    env = PN.env_for(data, "observe")
    pin = PIN.load_pin_env(env)
    assert pin["register"]["sha256"] == hashlib.sha256(data).hexdigest()
    kinds = [f.split(":")[0] for f in pin["c7"]["declared_faults"]]
    assert "suppress-record" in kinds and "inject-tool-output" in kinds
    assert PN.check_pin(data, env["IFABRIC_PIN_JSON"], env["IFABRIC_PIN_SHA256"]) == []
    assert len(env["IFABRIC_PIN_JSON"]) <= PIN.ENV_VALUE_MAX


def test_pin_refuses_undeclared_mode_and_missing_fault():
    data = rb(REGISTER)
    with pytest.raises(PIN.PinError):
        PN.pin_from_register(data, "enforce")  # v0-pilot declares observe only
    no_fault = data.decode().replace("inject-tool-output:ifabric-it:lookup:tool-directive", "suppress-record:ifabric-it:tool.call:2")
    with pytest.raises(PIN.PinError, match="DC-8"):
        PN.pin_from_register(no_fault.encode(), "observe")


def test_check_pin_detects_tampering_and_other_register():
    data = rb(REGISTER)
    env = PN.env_for(data, "observe")
    other = data.decode().replace("cap_tier_default: 300000", "cap_tier_default: 310000").encode()
    assert PN.check_pin(other, env["IFABRIC_PIN_JSON"], env["IFABRIC_PIN_SHA256"])
    assert PN.check_pin(data, env["IFABRIC_PIN_JSON"], "0" * 64)


def test_smoke_register_pin_accepted_by_post_run_check():
    smoke = PN.smoke_register(rb(REGISTER).decode(), cap_tokens=5000, ceiling_tokens=9000)
    doc = P.parse_register(smoke)
    assert doc["top"]["version"] == "v0-smoke" and doc["top"]["status"] == "EXPLORATORY"
    for mode in ("enforce", "observe"):
        env = PN.env_for(smoke.encode(), mode)
        assert PN.check_pin(smoke.encode(), env["IFABRIC_PIN_JSON"], env["IFABRIC_PIN_SHA256"]) == []
        assert PIN.load_pin_env(env)["c16"]["caps"] == {"default": 5000}


def test_check_decisions_against_file_caps():
    data = rb(REGISTER)
    ok = [{"tier": "default", "threshold_value": 300000}]
    assert PN.check_decisions(data, ok) == []
    errs = PN.check_decisions(data, ok + [{"tier": "default", "threshold_value": 1}, {"tier": "nope", "threshold_value": 1}])
    assert len(errs) == 2


# ---- freeze ------------------------------------------------------------------------------------------------------

def freezable(tmp_path, version="v0-pilot"):
    return FZ.freeze(version, REGISTER, RISKS, str(tmp_path))


def test_freeze_writes_bytes_hashes_and_pins_then_refuses_refreeze(tmp_path):
    res = freezable(tmp_path)
    vdir = tmp_path / "versions"
    assert (vdir / "v0-pilot.yaml").read_bytes() == rb(REGISTER)
    assert (vdir / "v0-pilot.risks.yaml").read_bytes() == rb(RISKS)
    assert res["register_sha256"] == hashlib.sha256(rb(REGISTER)).hexdigest()
    assert (vdir / "v0-pilot.sha256").read_text().split()[0] == res["register_sha256"]
    assert FZ.verify("v0-pilot", str(tmp_path)) == []
    pins = sorted(os.listdir(str(tmp_path / "pins")))
    assert pins == ["v0-pilot-observe.json", "v0-pilot-observe.sha256"]
    pin_text = (tmp_path / "pins" / "v0-pilot-observe.json").read_text()
    assert hashlib.sha256(pin_text.encode()).hexdigest() == (tmp_path / "pins" / "v0-pilot-observe.sha256").read_text().split()[0]
    with pytest.raises(FZ.FreezeError, match="already frozen"):
        freezable(tmp_path)
    assert (vdir / "v0-pilot.yaml").read_bytes() == rb(REGISTER)  # untouched


def test_freeze_refuses_version_mismatch_and_leaves_nothing(tmp_path):
    with pytest.raises(FZ.FreezeError, match="top.version"):
        FZ.freeze("v1", REGISTER, RISKS, str(tmp_path))
    assert not os.path.exists(str(tmp_path / "versions"))


def test_freeze_supersedes_checks_both_bump_directions(tmp_path):
    old = rb(REGISTER)
    new = old.decode().replace("version: v0-pilot", "version: v1").replace("register_version: v0-pilot", "register_version: v1")
    new = new.replace("cap_tier_default: 300000", "cap_tier_default: 90000")  # C16 values changed, version NOT bumped
    reg_path = tmp_path / "new.yaml"
    risks_path = tmp_path / "newrisks.yaml"
    reg_path.write_text(new)
    risks_path.write_text(rb(RISKS).decode().replace("version: v0-pilot", "version: v1", 1))
    with pytest.raises(FZ.FreezeError, match="C16"):
        FZ.freeze("v1", str(reg_path), str(risks_path), str(tmp_path / "out"), REGISTER)


def test_cli_freeze_exit_codes(tmp_path):
    out = str(tmp_path)
    assert FZ.main(["--version", "v0-pilot", "--register", REGISTER, "--risks", RISKS, "--out", out]) == 0
    assert FZ.main(["--version", "v0-pilot", "--register", REGISTER, "--risks", RISKS, "--out", out]) == 2


# ---- inventory freeze --------------------------------------------------------------------------------------------

def test_inventory_freeze_once(tmp_path):
    r = INV.freeze_inventory("inv-1", INVENTORY, str(tmp_path))
    assert (tmp_path / "versions" / "inv-1.yaml").read_bytes() == rb(INVENTORY)
    assert r["sha256"] == hashlib.sha256(rb(INVENTORY)).hexdigest()
    with pytest.raises(INV.InventoryError):
        INV.freeze_inventory("inv-1", INVENTORY, str(tmp_path))
    with pytest.raises(INV.InventoryError):
        INV.freeze_inventory("v1", INVENTORY, str(tmp_path))


# ---- derive ------------------------------------------------------------------------------------------------------

def derive_inputs():
    rules_bytes = rb(os.path.join(FIX, "rules.synthetic.json"))
    return (DV.load_records(os.path.join(FIX, "experiments.synthetic.jsonl")), json.loads(rules_bytes.decode()),
            hashlib.sha256(rules_bytes).hexdigest())


def test_derive_c16_from_s1_s3_only_and_cites_runs():
    records, rules, digest = derive_inputs()
    item = DV.derive_c16(records, rules, digest)
    assert item["normal_need_tokens"] == 33000 and item["value"] == 40000  # 33000 plus 20 percent, rounded up to the step
    assert item["cites"] == ["ifabric-test-1790000001-aaaaaa", "ifabric-test-1790000002-bbbbbb"]
    assert item["rules_sha256"] == digest and item["status"] == "DERIVED"


def test_derive_refuses_cap_from_s2_or_condition_run():
    records, rules, digest = derive_inputs()
    with pytest.raises(DV.DeriveError, match="never derived"):
        DV.derive_c16(records, rules, digest, ["ifabric-test-1790000003-cccccc"])
    with pytest.raises(DV.DeriveError, match="never derived"):
        DV.derive_c16(records, rules, digest, ["ifabric-test-1790000004-dddddd"])


def test_derive_does_not_raise_cap_above_appetite():
    records, rules, digest = derive_inputs()
    rules = dict(rules, appetite_tokens=30000)
    item = DV.derive_c16(records, rules, digest)
    assert item["status"] == "NORMAL_NEED_ABOVE_APPETITE" and item["value"] is None


def test_derive_c7_and_c9_and_cli(capsys):
    records, rules, digest = derive_inputs()
    assert DV.derive_c7_gap(records, rules, digest)["value"] == 17000
    c9 = DV.derive_c9_baseline(records, rules, digest)
    assert c9["baseline_values"]["ifabric-it_S3"] == 8600 and "ifabric-it_S2" not in c9["baseline_values"]
    assert DV.main(["--experiments", os.path.join(FIX, "experiments.synthetic.jsonl"),
                    "--rules", os.path.join(FIX, "rules.synthetic.json")]) == 0
    assert DV.main(["--experiments", os.path.join(FIX, "experiments.synthetic.jsonl"),
                    "--rules", os.path.join(FIX, "rules.synthetic.json"),
                    "--use", "ifabric-test-1790000003-cccccc"]) == 2


def test_derive_code_holds_no_threshold_literals():
    src = rb(os.path.join(ROOT, "prooflab", "registry", "derive.py")).decode()
    assert "300000" not in src and "headroom_pct\"] =" not in src


# ---- approval finding --------------------------------------------------------------------------------------------

def test_approval_finding_passes_arths_finding_from_dict(tmp_path):
    from prooflab.servicenow.finding import finding_from_dict
    path = AF.write_approval_finding("v0-pilot", REGISTER, RISKS, str(tmp_path), "2026-10-06T05:05:00Z")
    data = json.loads(open(path).read())
    f = finding_from_dict(data)
    assert f.control_ref == "REG" and f.kind == "approval" and f.verdict == "ESCALATED"
    reg_sha, risks_sha = hashlib.sha256(rb(REGISTER)).hexdigest(), hashlib.sha256(rb(RISKS)).hexdigest()
    assert "register:sha256=" + reg_sha in data["evidence"] and "risks:sha256=" + risks_sha in data["evidence"]
    assert reg_sha[:12] in data["summary"] and risks_sha[:12] in data["summary"]
    assert AF.approval_note_text("v0-pilot", reg_sha, risks_sha) == \
        "APPROVED threshold register v0-pilot, sha256 %s; risks sha256 %s" % (reg_sha[:12], risks_sha[:12])
    with pytest.raises(FileExistsError):
        AF.write_approval_finding("v0-pilot", REGISTER, RISKS, str(tmp_path), "2026-10-06T05:05:00Z")


def test_approval_finding_rejects_bad_time(tmp_path):
    with pytest.raises(ValueError):
        AF.write_approval_finding("v0-pilot", REGISTER, RISKS, str(tmp_path), "yesterday")


# ---- named runs --------------------------------------------------------------------------------------------------

def test_run_ids_rules():
    good = "ifabric-run-1790000100-abc123\nifabric-run-1790000200-def456\n"
    assert NR.check_run_ids(good, {"ifabric-test-1790000001-aaaaaa"}) == []
    assert NR.check_run_ids("ifabric-test-1790000001-aaaaaa\n", {"ifabric-test-1790000001-aaaaaa"})
    assert any("more than one" in e for e in NR.check_run_ids("ifabric-run-1790000100-abc123 ifabric-run-1790000200-def456\n"))
    assert any("more than one" in e for e in NR.check_run_ids("ifabric-run-1790000100-abc123,ifabric-run-1790000200-def456\n"))
    assert NR.check_run_ids("fault-1791177342-d3f892\n")  # the reference trio is never assessed
    assert NR.check_run_ids("ifabric-run-1790000100-abc123\nifabric-run-1790000100-abc123\n")
    assert NR.check_run_ids("")


def test_run_ids_cli_against_experiments_log(tmp_path):
    ids = tmp_path / "run-ids.txt"
    ids.write_text("ifabric-run-1790000100-abc123\n")
    exp = os.path.join(FIX, "experiments.synthetic.jsonl")
    assert NR.main(["--run-ids", str(ids), "--experiments", exp]) == 0
    ids.write_text("ifabric-run-1790000100-abc123\nifabric-test-1790000002-bbbbbb\n")
    assert NR.main(["--run-ids", str(ids), "--experiments", exp]) == 1
