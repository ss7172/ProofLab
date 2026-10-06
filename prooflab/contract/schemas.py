"""JSON Schema documents for the contract's other shapes, generated from the code (a test keeps the committed
files in prooflab/contract/schema/ equal to these). Stdlib, 3.9. The Python validators stay the authority:
record.validate_record, register.validate_register, pin.validate_pin, transports.Assessment.

  assessment-1.json     the §3.2 Assessment (transports.Assessment fields)
  register-1.json       the register: TOP_REQUIRED/TOP_KNOWN, CONTROL_REQUIRED/CONTROL_KNOWN + key prefixes
  pin-1.json            ifabric.pin/1
  evidence-record-1.json  record.json_schema() (unchanged location)
  app-contracts-v1.schema.json  Arth's handoff-3 console contracts (pack-index, answer, ...), a byte copy

Regenerate: python3 -m prooflab.contract.schemas  (writes every generated file).
"""
from __future__ import annotations

import dataclasses
import json
import os

from prooflab.contract import pin as _pin
from prooflab.contract import record as _rec
from prooflab.contract import register as _reg
from prooflab.contract import transports as _t
from prooflab.contract import verdicts as _v

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema")
APP_CONTRACTS_FILE = "app-contracts-v1.schema.json"
APP_CONTRACTS_SOURCE = os.path.join("handoffs", "ifabric-handoff-3", "evidence-console-plan", "schemas",
                                    "contracts.schema.json")
_DRAFT = "https://json-schema.org/draft/2020-12/schema"


def assessment_schema() -> dict:
    fields = [f.name for f in dataclasses.fields(_t.Assessment)]
    required = [f.name for f in dataclasses.fields(_t.Assessment)
                if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING]
    props = dict((name, {}) for name in fields)
    props["requirement_verdict"] = {"enum": list(_v.ASSESSMENT_VERDICTS)}
    props["control_ref"] = {"enum": list(_rec.CONTROL_REFS)}
    props["scope_kind"] = {"enum": ["run", "window", "interval", "escalation"]}
    for name in ("measured", "denominators", "completeness"):
        props[name] = {"type": "object"}
    for name in ("exceptions", "evidence_refs", "gaps"):
        props[name] = {"type": "array"}
    props["finding"] = {"type": ["object", "null"]}
    return {
        "$schema": _DRAFT, "$id": "ifabric.assessment/1",
        "title": "ProofLab assessment (ARCH §3.2; transports.Assessment)",
        "description": "As a record: record_kind assessment with these fields flattened under assessment.*.",
        "type": "object", "required": required, "properties": props, "additionalProperties": False,
        "x-assessment-id": "<control_ref>:<threshold_version>:<scope_kind>:<scope_id>:r<n>",
    }


def register_schema() -> dict:
    control_props = dict((name, {"type": "string"}) for name in _reg.CONTROL_KNOWN)
    control_props["mode"] = {"enum": list(_reg.CONTROL_MODES)}
    control_props["threshold_version"] = {"type": "string", "pattern": _reg.THRESHOLD_VERSION_RE.pattern}
    top_props = dict((name, {"type": "string"}) for name in _reg.TOP_KNOWN)
    top_props["pre_run_gate"] = {"enum": list(_reg.PRE_RUN_GATES)}
    top_props["version"] = {"type": "string", "pattern": _reg.REGISTER_VERSION_RE.pattern}
    props = dict(top_props)
    props["controls"] = {"type": "array", "items": {
        "type": "object", "required": list(_reg.CONTROL_REQUIRED), "properties": control_props,
        "patternProperties": dict(("^" + p, {"type": "string"}) for p in _reg.CONTROL_KEY_PREFIXES),
        "additionalProperties": False}}
    return {
        "$schema": _DRAFT, "$id": "ifabric.register/1",
        "title": "ProofLab control register: the flat-YAML file read as JSON (top keys + a controls list)",
        "description": "Scalars are strings in the strict flat-YAML subset (registry/parse.py); the typed "
                       "accessors in register.py convert them. register.validate_register is the authority.",
        "type": "object", "required": list(_reg.TOP_REQUIRED) + ["controls"], "properties": props,
        "additionalProperties": False,
        "x-kit-fields": list(_reg.KIT_FIELDS),
    }


def pin_schema() -> dict:
    integer = {"type": "integer"}
    return {
        "$schema": _DRAFT, "$id": _pin.PIN_SCHEMA,
        "title": "ProofLab in-path pin (pin.validate_pin is the authority)",
        "type": "object", "required": ["schema", "register", "c16", "c7"], "additionalProperties": False,
        "properties": {
            "schema": {"const": _pin.PIN_SCHEMA},
            "register": {"type": "object", "required": ["version", "sha256"], "properties": {
                "version": {"type": "string"}, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}},
            "c16": {"type": "object", "required": [
                "control_id", "threshold_version", "version_date", "tiers", "default_tier", "caps",
                "safety_ceiling", "modes", "mode", "bound"], "properties": {
                "control_id": {"type": "string"}, "threshold_version": {"type": "string"},
                "version_date": {"type": "string"}, "tiers": {"type": "array", "items": {"type": "string"}},
                "default_tier": {"type": "string"},
                "caps": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 1}},
                "safety_ceiling": {"type": "integer", "minimum": 1},
                "modes": {"type": "array", "items": {"enum": list(_v.C16_MODES)}},
                "mode": {"enum": list(_v.C16_MODES)},
                "bound": {"type": "object", "required": list(_pin.BOUND_KEYS), "additionalProperties": False,
                          "properties": {"inline_bound_margin_pct": {"type": "number", "minimum": 0},
                                         "inline_bound_fallback_tokens": integer, "max_tokens": integer}},
                "tool_no_evidence_limit": {"type": "integer", "minimum": 1}}},
            "c7": {"type": "object", "required": ["declared_faults"], "properties": {
                "declared_faults": {"type": "array", "items": {"type": "string"}}}},
        },
        "x-env-keys": list(_pin.ENV_KEYS),
    }


GENERATED = {
    "evidence-record-1.json": _rec.json_schema,
    "assessment-1.json": assessment_schema,
    "register-1.json": register_schema,
    "pin-1.json": pin_schema,
}


def write_all(directory: str = SCHEMA_DIR) -> list:
    written = []
    for name, maker in sorted(GENERATED.items()):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(maker(), handle, indent=1, ensure_ascii=False)
            handle.write("\n")
        written.append(path)
    return written


if __name__ == "__main__":
    for p in write_all():
        print(p)
