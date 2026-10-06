"""PR-41: the optional C9 `named_run_treatments` register key (validated, parsed, preserved through freeze)."""
import os

import pytest

from prooflab.contract import register as R
from prooflab.registry import freeze as F
from prooflab.registry import parse as P
from prooflab.registry import pinned as PN

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DRAFT = os.path.join(ROOT, "register", "register.yaml")
V0 = os.path.join(ROOT, "register", "versions", "v0-pilot.yaml")
DECL = "N8:model-swap:ifabric-it:nemotron-super-120b:nemotron-nano-9b"


def _text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _with(text, value):
    old = '    declared_treatments: "model-swap:ifabric-it:nemotron-nano-9b"\n'
    assert old in text
    return text.replace(old, old + '    named_run_treatments: "%s"\n' % value)


def test_draft_register_declares_n8_and_validates():
    doc = P.parse_register(_text(DRAFT))
    assert R.validate_register(doc) == []
    got = R.named_run_treatments(R.controls_by_ref(doc)["C9"])
    assert got == [{"label": "N8", "kind": "model-swap", "agent": "ifabric-it",
                    "from_model": "nemotron-super-120b", "to_model": "nemotron-nano-9b"}]


@pytest.mark.parametrize("bad", ["N8:model-swap:ifabric-it:nemotron-super-120b",          # no to-model
                                 "N8:model-swap:ifabric-it:a:a",                          # swap to itself
                                 "X8:model-swap:ifabric-it:a:b",                          # not a named-run label
                                 "N8:pin-patch:ifabric-it:a:b",                           # not a model swap
                                 "N8:model-swap:it-resolution-agent:a:b",                 # not our agent
                                 "N8:model-swap:ifabric-it:a:b,N8:model-swap:ifabric-it:a:c"])  # duplicate
def test_malformed_declarations_are_refused(bad):
    doc = P.parse_register(_with(_text(V0), bad))
    errs = R.validate_register(doc)
    assert any("named_run_treatments" in e for e in errs), errs


def test_only_the_c9_entry_may_declare():
    text = _text(V0).replace("    control_ref: C7\n", "    control_ref: C7\n    named_run_treatments: \"%s\"\n" % DECL)
    errs = R.validate_register(P.parse_register(text))
    assert any("only the C9 entry" in e for e in errs)


def test_freeze_preserves_the_declaration_and_the_pin_stays_green(tmp_path):
    reg_text = _with(_text(V0), DECL).replace("version: v0-pilot", "version: v1-test", 1)
    risks = _text(os.path.join(ROOT, "register", "versions", "v0-pilot.risks.yaml")).replace(
        "version: v0-pilot", "version: v1-test", 1)
    rp, kp = tmp_path / "register.yaml", tmp_path / "risks.yaml"
    rp.write_text(reg_text, encoding="utf-8")
    kp.write_text(risks, encoding="utf-8")
    out = F.freeze("v1-test", str(rp), str(kp), str(tmp_path / "reg"))
    frozen = (tmp_path / "reg" / "versions" / "v1-test.yaml").read_bytes()
    assert frozen == reg_text.encode("utf-8") and out["register_sha256"]
    doc = P.parse_register(frozen.decode("utf-8"))
    assert R.named_run_treatments(R.controls_by_ref(doc)["C9"])[0]["label"] == "N8"
    env = PN.env_for(frozen, "observe")
    assert PN.check_pin(frozen, env["IFABRIC_PIN_JSON"], env["IFABRIC_PIN_SHA256"]) == []
