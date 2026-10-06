"""The in-path pin ifabric.pin/1: derive, canonical round trip, sha256, env block, fail-closed load."""
import json
import os

import pytest

from prooflab.contract import pin as PIN
from prooflab.contract import register as REG
from prooflab.registry import parse as P

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def frozen():
    with open(os.path.join(FIX, "register.synthetic.yaml"), "rb") as handle:
        data = handle.read()
    return P.parse_register(data.decode("utf-8")), REG.register_sha256(data)


def test_derive_and_round_trip_byte_for_byte():
    doc, sha = frozen()
    pin = PIN.derive_pin(doc, sha, "enforce")
    text = PIN.dumps(pin)
    assert PIN.loads(text, PIN.sha256_of(text)) == pin
    assert PIN.dumps(PIN.loads(text)) == text
    assert pin["c16"]["caps"] == {"high": 80000, "standard": 50000}
    assert pin["c16"]["bound"] == {"inline_bound_margin_pct": 10, "inline_bound_fallback_tokens": 6000,
                                   "max_tokens": 2048}
    assert pin["c7"]["declared_faults"] == ["suppress-record:ifabric-it:tool.call:1"]
    assert pin["register"] == {"version": "v0-smoke", "sha256": sha}
    assert " " not in text and len(text) < PIN.ENV_VALUE_MAX


def test_modes_give_two_pins_from_one_file():
    doc, sha = frozen()
    enforce, observe = PIN.derive_pin(doc, sha, "enforce"), PIN.derive_pin(doc, sha, "observe")
    assert PIN.sha256_of(PIN.dumps(enforce)) != PIN.sha256_of(PIN.dumps(observe))
    with pytest.raises(PIN.PinError):
        PIN.derive_pin(doc, sha, "advisory")


def test_derivation_is_pure_and_repeatable():
    doc, sha = frozen()
    assert PIN.dumps(PIN.derive_pin(doc, sha, "enforce")) == PIN.dumps(PIN.derive_pin(frozen()[0], sha, "enforce"))


def test_loads_fails_closed():
    doc, sha = frozen()
    text = PIN.dumps(PIN.derive_pin(doc, sha, "enforce"))
    with pytest.raises(PIN.PinError):
        PIN.loads(text, "0" * 64)
    with pytest.raises(PIN.PinError):
        PIN.loads(json.dumps(json.loads(text), indent=1))  # not canonical
    bad = json.loads(text)
    del bad["c16"]["caps"]["high"]
    with pytest.raises(PIN.PinError):
        PIN.loads(PIN.dumps(bad))
    with pytest.raises(PIN.PinError):
        PIN.loads("not json")


def test_env_block_and_reader():
    doc, sha = frozen()
    env = PIN.env_block(PIN.derive_pin(doc, sha, "observe"))
    assert sorted(env) == sorted(PIN.ENV_KEYS)
    assert PIN.load_pin_env(env)["c16"]["mode"] == "observe"
    for key in PIN.ENV_KEYS:
        broken = dict(env)
        del broken[key]
        with pytest.raises(PIN.PinError):
            PIN.load_pin_env(broken)
    wrong = dict(env, IFABRIC_REGISTER_VERSION="v9")
    with pytest.raises(PIN.PinError):
        PIN.load_pin_env(wrong)


def test_register_without_c16_cannot_be_pinned():
    doc, sha = frozen()
    doc["entries"] = [e for e in doc["entries"] if e["control_ref"] != "C16"]
    with pytest.raises(PIN.PinError):
        PIN.derive_pin(doc, sha, "enforce")
