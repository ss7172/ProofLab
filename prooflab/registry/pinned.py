"""In-path pins from a frozen register (ARCH §3.3 steps 5-6; I-04, B4; DC-8). Stdlib, Python 3.9.

    pin = pin_from_register(register_bytes, mode)        # pure; the pin the runtime hashes
    env = env_for(register_bytes, mode)                  # IFABRIC_PIN_JSON/_SHA256, IFABRIC_REGISTER_VERSION/_SHA256
    write_pins(version, register_bytes, pins_dir)        # register/pins/<v>-<mode>.json + .sha256, one per declared mode
    check_pin(register_bytes, pin_json, pin_sha256)      # the post-run pin check: errors list, empty = OK
    check_decisions(register_bytes, decisions)           # every decision's threshold value against the file, per tier
    smoke_register(text, ...)                            # the v0-smoke variant (low cap, EXPLORATORY, local only)

The declared faults `suppress-record` and `inject-tool-output` must be inside the pin (DC-8): a register whose
C7 entry lacks either is refused here, so no run-time env patch is ever needed for ADV-H-02 or N4.
The pin format and its derivation are PR-01's (`prooflab.contract.pin.derive_pin`); this module adds no values.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from prooflab.contract import pin as _pin
from prooflab.contract import register as _reg
from prooflab.registry import parse as _parse

REQUIRED_FAULT_KINDS = ("suppress-record", "inject-tool-output")
EXPLORATORY_VERSIONS = ("v0-smoke", "v0-pilot")


def _text(data) -> str:
    return data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data


def _bytes(data) -> bytes:
    return bytes(data) if isinstance(data, (bytes, bytearray)) else data.encode("utf-8")


def declared_modes(doc: dict) -> list:
    c16 = _reg.controls_by_ref(doc).get("C16") or {}
    return _reg.as_list(c16.get("inline_modes", ""))


def missing_fault_kinds(doc: dict) -> list:
    c7 = _reg.controls_by_ref(doc).get("C7") or {}
    kinds = [f.split(":", 1)[0] for f in _reg.as_list(c7.get("declared_faults", ""))]
    return [k for k in REQUIRED_FAULT_KINDS if k not in kinds]


def pin_from_register(data, mode: str) -> dict:
    """The pin for one mode. Raises PinError on a register that cannot be pinned (fail closed)."""
    raw = _bytes(data)
    try:
        doc = _parse.parse_register(_text(raw))
    except ValueError as exc:
        raise _pin.PinError("register does not parse: %s" % exc)
    errors = _reg.validate_register(doc)
    if errors:
        raise _pin.PinError("register invalid: " + "; ".join(errors))
    missing = missing_fault_kinds(doc)
    if missing:
        raise _pin.PinError("declared faults missing from C7 (DC-8): %s" % ", ".join(missing))
    if mode not in declared_modes(doc):
        raise _pin.PinError("mode %r is not declared in inline_modes %s" % (mode, declared_modes(doc)))
    return _pin.derive_pin(doc, _reg.register_sha256(raw), mode)


def env_for(data, mode: str) -> dict:
    return _pin.env_block(pin_from_register(data, mode))


def write_pins(version: str, data, pins_dir: str) -> list:
    """Write <v>-<mode>.json + .sha256 for every declared mode; refuse to overwrite. Returns the paths."""
    raw = _bytes(data)
    doc = _parse.parse_register(_text(raw))
    os.makedirs(pins_dir, exist_ok=True)
    written = []
    for mode in declared_modes(doc):
        text = _pin.dumps(pin_from_register(raw, mode))
        base = os.path.join(pins_dir, "%s-%s" % (version, mode))
        with open(base + ".json", "xb") as fh:
            fh.write(text.encode("utf-8"))
        with open(base + ".sha256", "xb") as fh:
            fh.write(("%s  %s-%s.json\n" % (_pin.sha256_of(text), version, mode)).encode("utf-8"))
        written.extend([base + ".json", base + ".sha256"])
    return written


def check_pin(data, pin_json: str, pin_sha256: str) -> list:
    """Post-run pin check: the pin a run carried must be the byte-for-byte re-derivation from the frozen file."""
    try:
        pin = _pin.loads(pin_json, pin_sha256)
    except _pin.PinError as exc:
        return ["pin unusable: %s" % exc]
    try:
        expected = _pin.dumps(pin_from_register(data, pin["c16"]["mode"]))
    except _pin.PinError as exc:
        return ["cannot re-derive the pin: %s" % exc]
    if expected != pin_json:
        return ["pin differs from the re-derivation of the frozen register"]
    return []


def check_decisions(data, decisions) -> list:
    """Every decision's threshold value must equal the file's cap for its tier (one error per mismatch)."""
    doc = _parse.parse_register(_text(_bytes(data)))
    caps = _reg.tier_caps(_reg.controls_by_ref(doc)["C16"])
    errors = []
    for i, d in enumerate(decisions):
        tier = d.get("tier")
        if tier not in caps:
            errors.append("decision %d: tier %r not in the register" % (i, tier))
        elif d.get("threshold_value") != caps[tier]:
            errors.append("decision %d: threshold_value %r != register cap %r for tier %s"
                          % (i, d.get("threshold_value"), caps[tier], tier))
    return errors


def smoke_register(text: str, cap_tokens: int, ceiling_tokens: int, version: str = "v0-smoke") -> str:
    """The v0-smoke register: the working file with a low cap for every tier, a low ceiling, both modes, EXPLORATORY.
    Local only: it is never uploaded or used for an assessment. The caps are the caller's (a test or the S-3 halt proof)."""
    out = []
    for line in text.splitlines():
        key = line.split(":", 1)[0].lstrip("- ").strip()
        indent = line[:len(line) - len(line.lstrip())]
        if re.match(r"^version:", line):
            line = "version: %s" % version
        elif re.match(r"^status:", line):
            line = "status: EXPLORATORY"
        elif key.startswith("cap_tier_"):
            line = "%s%s: %d" % (indent, key, cap_tokens)
        elif key == "safety_ceiling":
            line = "%s%s: %d" % (indent, key, ceiling_tokens)
        elif key == "inline_modes":
            line = "%s%s: enforce,observe" % (indent, key)
        out.append(line)
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab register pin")
    ap.add_argument("--register", required=True, help="the frozen register file (its bytes are hashed)")
    ap.add_argument("--mode", required=True)
    ap.add_argument("--env", action="store_true", help="print the four env values as JSON")
    ns = ap.parse_args(argv)
    with open(ns.register, "rb") as fh:
        data = fh.read()
    try:
        block = env_for(data, ns.mode)
    except _pin.PinError as exc:
        print("pin refused: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(block if ns.env else json.loads(block[_pin.ENV_PIN_JSON]), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
