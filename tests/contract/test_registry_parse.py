"""The strict flat-YAML parser and kit parity (ARCH §3.3 rules 1-7; T1.1 kit-parity test)."""
import importlib.util
import os

import pytest

from prooflab.contract import register as REG
from prooflab.registry import parse as P

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
KIT_EVALUATE = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-assets/starter/evaluate.py")
KIT_REGISTER = os.path.join(os.path.dirname(KIT_EVALUATE), "register.yaml")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KIT = _load(os.path.join(FIX, "kit_fallback.py"), "kit_fallback_oracle")


def text(name="register.synthetic.yaml"):
    with open(os.path.join(FIX, name)) as handle:
        return handle.read()


def test_kit_parity_on_our_register():
    ours = P.kit_view(text())
    kit = KIT.kit_fallback_load_register(text())
    assert sorted(ours) == ["16", "7", "9"]
    assert ours == kit  # every key, not just the kit fields
    for cid in ours:
        for field in REG.KIT_FIELDS:
            assert ours[cid][field] == kit[cid][field]


def test_synthetic_register_is_schema_valid():
    doc = P.parse_register(text())
    assert REG.validate_register(doc) == []
    assert doc["top"]["version"] == "v0-smoke"
    assert REG.control_versions(doc)["C16"] == ("C16-v1", "2026-10-06T03:52:10Z")
    assert REG.tier_caps(REG.controls_by_ref(doc)["C16"]) == {"high": 80000, "standard": 50000}


@pytest.mark.skipif(not os.path.exists(KIT_EVALUATE), reason="workshop kit not on this machine")
def test_vendored_oracle_is_the_kit_code():
    with open(KIT_EVALUATE) as handle:
        kit_src = handle.read()
    body = kit_src.split("    controls, cur = {}, None", 1)[1].split("def _load_evidence", 1)[0]
    with open(os.path.join(FIX, "kit_fallback.py")) as handle:
        ours = handle.read()
    assert body.strip() in ours.replace("\n", "\n")  # same lines, same indentation


@pytest.mark.skipif(not os.path.exists(KIT_EVALUATE), reason="workshop kit not on this machine")
def test_kit_loader_itself_without_pyyaml(monkeypatch):
    kit = _load(KIT_EVALUATE, "kit_evaluate_under_test")
    monkeypatch.setattr(kit, "yaml", None)
    path = os.path.join(FIX, "register.synthetic.yaml")
    from pathlib import Path
    assert kit._load_register(Path(path)) == P.kit_view(text())


@pytest.mark.skipif(not os.path.exists(KIT_REGISTER), reason="workshop kit not on this machine")
def test_kit_starter_template_parses_identically():
    with open(KIT_REGISTER) as handle:
        kit_text = handle.read()
    assert P.kit_view(kit_text) == KIT.kit_fallback_load_register(kit_text)


BASE = 'version: v1\nversion_date: "2026-10-06T03:52:10Z"\ncontrols:\n  - control_id: "16"\n    name: x\n'


@pytest.mark.parametrize("bad,why", [
    (BASE + "    nested:\n      a: 1\n", "rule 2"),
    (BASE + "    metric: |\n", "rule 6"),
    (BASE + "    metric: >\n", "rule 6"),
    (BASE + "    list: [a, b]\n", "rule 2"),
    (BASE + "    metric: a#b\n", "rule 4"),
    (BASE + '    metric: "a # b"\n', "rule 4"),
    (BASE + "trailer: 1\n", "rule 3"),
    (BASE + "    just a continuation line\n", "rule 6"),
    (BASE + "    - item\n", "rule 2"),
    (BASE + "    name: y\n", "duplicate"),
    (BASE + "  - control_id: \"16\"\n", "duplicate control_id"),
    (BASE + "    metric : x\n", "whitespace before"),
    (BASE + "    metric: a: b\n", "': '"),
    (BASE + "    metric: \"'quoted'\"\n", "edge"),
    (BASE + "    metric: \"open\n", "unterminated"),
    ("  version: v1\ncontrols:\n", "rule 1"),
    ("version: v1\n", "no list key"),
    (BASE.replace("    name: x\n", "\tname: x\n"), "tabs"),
])
def test_strict_rejections(bad, why):
    with pytest.raises(P.RegisterParseError) as info:
        P.parse_register(bad)
    assert why in str(info.value)


def test_comments_and_values():
    doc = P.parse_register(BASE + "    # a comment line\n    metric: \"a, b\"   # trailing comment\n    n: 5\n")
    entry = doc["entries"][0]
    assert entry["metric"] == "a, b" and entry["n"] == "5" and entry["control_id"] == "16"


def test_risks_and_inventory_lists():
    risks = P.parse_risks('version: v1\nowner: Sree\nrisks:\n  - risk_id: R-C16\n    statement: "runaway spend"\n')
    assert P.entries_by_id(risks)["R-C16"]["statement"] == "runaway spend"
    inv = P.parse_inventory("version: inv-1\ncomponents:\n  - component_id: ifabric-it\n    owner: Sree\n")
    assert inv["entries"][0]["owner"] == "Sree"


def test_register_validation_errors():
    doc = P.parse_register(BASE)
    errors = REG.validate_register(doc)
    assert any("control_ref: required" in e for e in errors)
    doc = P.parse_register(text().replace('version_date: "2026-10-06T03:52:10Z"', "version_date: 2026-10-06", 1))
    assert any("top.version_date" in e for e in REG.validate_register(doc))
    doc = P.parse_register(text().replace("threshold_version: C7-v1", "threshold_version: C16-v9"))
    assert any("start with the control_ref" in e for e in REG.validate_register(doc))
    doc = P.parse_register(text().replace("    cap_tier_high: 80000\n", "    cap_tier_high: lots\n"))
    assert any("cap_tier_high" in e for e in REG.validate_register(doc))
    doc = P.parse_register(text().replace("    max_tokens: 2048\n", "    max_tokens: 2048\n    surprise: 1\n"))
    assert any("unknown key" in e for e in REG.validate_register(doc))


def test_per_control_version_bumps():
    old = P.parse_register(text())
    same = P.parse_register(text())
    assert REG.check_version_bumps(old, same) == []
    changed = P.parse_register(text().replace("cap_tier_high: 80000", "cap_tier_high: 90000"))
    assert any(e.startswith("C16") for e in REG.check_version_bumps(old, changed))
    bumped = P.parse_register(text().replace("cap_tier_high: 80000", "cap_tier_high: 90000")
                              .replace("threshold_version: C16-v1", "threshold_version: C16-v2")
                              .replace('version_date: "2026-10-06T03:52:10Z"\n    enforcement_point: "EP-1',
                                       'version_date: "2026-10-06T07:00:00Z"\n    enforcement_point: "EP-1'))
    assert REG.check_version_bumps(old, bumped) == []
    only_version = P.parse_register(text().replace("threshold_version: C9-v1", "threshold_version: C9-v1.1"))
    assert any(e.startswith("C9") for e in REG.check_version_bumps(old, only_version))
