"""The in-path pin format `ifabric.pin/1` (ARCH §3.3 step 5; I-04, B4). Stdlib, 3.9.

The pin is a canonical JSON extract (sorted keys, no spaces) of every value the runtime uses, derived
from the frozen register's bytes by `derive_pin` (a pure function, so the post-run pin check can re-derive
it and compare byte for byte). Shape:

  {"schema": "ifabric.pin/1",
   "register": {"version": "v1", "sha256": "<64 hex of the frozen file>"},
   "c16": {"control_id": "ACN-COST-001", "threshold_version": "C16-v1", "version_date": "<UTC>",
           "tiers": ["high", "standard"], "default_tier": "standard", "caps": {"high": N, "standard": M},
           "safety_ceiling": S, "modes": ["enforce", "observe"], "mode": "enforce",
           "bound": {"inline_bound_margin_pct": P, "inline_bound_fallback_tokens": F, "max_tokens": T}},
   "c7": {"declared_faults": ["suppress-record:ifabric-it:tool.call:1", ...]}}

The env block (the only way in-path values are set): IFABRIC_PIN_JSON, IFABRIC_PIN_SHA256,
IFABRIC_REGISTER_VERSION, IFABRIC_REGISTER_SHA256. PinnedC16.from_env (PR-02, c16_core) parses the same
JSON; `load_pin_env` here is the reference reader and fails closed.
"""
from __future__ import annotations

import hashlib
import json

from prooflab.contract import register as _reg

PIN_SCHEMA = "ifabric.pin/1"
ENV_PIN_JSON = "IFABRIC_PIN_JSON"
ENV_PIN_SHA256 = "IFABRIC_PIN_SHA256"
ENV_REGISTER_VERSION = "IFABRIC_REGISTER_VERSION"
ENV_REGISTER_SHA256 = "IFABRIC_REGISTER_SHA256"
ENV_KEYS = (ENV_PIN_JSON, ENV_PIN_SHA256, ENV_REGISTER_VERSION, ENV_REGISTER_SHA256)
ENV_VALUE_MAX = 5000            # operator cap per env value [05 AR-14]
BOUND_KEYS = ("inline_bound_margin_pct", "inline_bound_fallback_tokens", "max_tokens")


class PinError(ValueError):
    """A pin that must not be used: the runtime refuses to start (fail closed)."""


def dumps(pin: dict) -> str:
    """The canonical pin string: sorted keys, no spaces, ASCII."""
    return json.dumps(pin, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_of(pin_json: str) -> str:
    return hashlib.sha256(pin_json.encode("utf-8")).hexdigest()


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def validate_pin(pin) -> list:
    errors = []
    if not isinstance(pin, dict):
        return ["pin must be an object"]
    if pin.get("schema") != PIN_SCHEMA:
        errors.append("schema: must be %r" % PIN_SCHEMA)
    reg = pin.get("register") or {}
    if not isinstance(reg.get("version"), str) or not reg.get("version"):
        errors.append("register.version: required")
    if not (isinstance(reg.get("sha256"), str) and len(reg["sha256"]) == 64):
        errors.append("register.sha256: 64 hex required")
    c16 = pin.get("c16")
    if not isinstance(c16, dict):
        errors.append("c16: required")
        c16 = {}
    for k in ("control_id", "threshold_version", "version_date", "default_tier", "mode"):
        if not isinstance(c16.get(k), str) or not c16.get(k):
            errors.append("c16.%s: required string" % k)
    tiers, caps = c16.get("tiers"), c16.get("caps")
    if not isinstance(tiers, list) or not tiers:
        errors.append("c16.tiers: non-empty list required")
        tiers = []
    if not isinstance(caps, dict) or sorted(caps) != sorted(tiers) or not all(_is_int(v) and v > 0 for v in caps.values()):
        errors.append("c16.caps: one positive integer per tier")
    if c16.get("default_tier") not in tiers:
        errors.append("c16.default_tier: must be one of the tiers")
    if not _is_int(c16.get("safety_ceiling")) or c16.get("safety_ceiling", 0) <= 0:
        errors.append("c16.safety_ceiling: positive integer required")
    modes = c16.get("modes")
    if not isinstance(modes, list) or not modes or not set(modes) <= {"enforce", "observe"}:
        errors.append("c16.modes: subset of enforce|observe required")
        modes = []
    if c16.get("mode") not in modes:
        errors.append("c16.mode: must be one of the declared modes")
    bound = c16.get("bound")
    if not isinstance(bound, dict) or sorted(bound) != sorted(BOUND_KEYS):
        errors.append("c16.bound: exactly %s" % list(BOUND_KEYS))
    else:
        if not (_is_int(bound["inline_bound_fallback_tokens"]) and _is_int(bound["max_tokens"])):
            errors.append("c16.bound: fallback and max_tokens must be integers")
        m = bound["inline_bound_margin_pct"]
        if isinstance(m, bool) or not isinstance(m, (int, float)) or m < 0:
            errors.append("c16.bound.inline_bound_margin_pct: non-negative number")
    c7 = pin.get("c7")
    if not isinstance(c7, dict) or not isinstance(c7.get("declared_faults"), list) or \
            not all(isinstance(f, str) for f in c7["declared_faults"]):
        errors.append("c7.declared_faults: list of strings required")
    extra = set(pin) - {"schema", "register", "c16", "c7"}
    if extra:
        errors.append("unknown top-level keys: %s" % sorted(extra))
    return errors


def loads(pin_json: str, expected_sha256: "str | None" = None) -> dict:
    """Parse and validate a pin string. With expected_sha256, the bytes must hash to it. Raises PinError."""
    if expected_sha256 is not None and sha256_of(pin_json) != expected_sha256:
        raise PinError("pin sha256 mismatch")
    try:
        pin = json.loads(pin_json)
    except ValueError as exc:
        raise PinError("pin is not JSON: %s" % exc)
    errors = validate_pin(pin)
    if errors:
        raise PinError("invalid pin: " + "; ".join(errors))
    if dumps(pin) != pin_json:
        raise PinError("pin is not in canonical form")
    return pin


def derive_pin(doc: dict, register_sha256: str, mode: str) -> dict:
    """The pin for one mode, from a parsed frozen register (prooflab.registry.parse.parse_register) and the
    sha256 of its bytes. Pure; raises PinError if the register lacks a value the runtime needs."""
    top = doc.get("top") or {}
    c16 = _reg.controls_by_ref(doc).get("C16")
    c7 = _reg.controls_by_ref(doc).get("C7") or {}
    if c16 is None:
        raise PinError("register has no C16 entry")
    try:
        caps = _reg.tier_caps(c16)
        modes = _reg.as_list(c16["inline_modes"])
        pin = {
            "schema": PIN_SCHEMA,
            "register": {"version": top["version"], "sha256": register_sha256},
            "c16": {
                "control_id": c16["library_id"],
                "threshold_version": c16["threshold_version"],
                "version_date": c16["version_date"],
                "tiers": sorted(caps),
                "default_tier": c16["default_tier"],
                "caps": caps,
                "safety_ceiling": _reg.as_int(c16["safety_ceiling"]),
                "modes": modes,
                "mode": mode,
                "bound": {
                    "inline_bound_margin_pct": _reg.as_number(c16["inline_bound_margin_pct"]),
                    "inline_bound_fallback_tokens": _reg.as_int(c16["inline_bound_fallback_tokens"]),
                    "max_tokens": _reg.as_int(c16["max_tokens"]),
                },
            },
            "c7": {"declared_faults": _reg.as_list(c7.get("declared_faults", ""))},
        }
    except (KeyError, ValueError) as exc:
        raise PinError("register cannot be pinned: %s" % exc)
    errors = validate_pin(pin)
    if errors:
        raise PinError("derived pin invalid: " + "; ".join(errors))
    return pin


def env_block(pin: dict) -> dict:
    """The four env values the live lane patches into an AgentConfig."""
    text = dumps(pin)
    if len(text) > ENV_VALUE_MAX:
        raise PinError("pin is %d chars; the operator caps an env value at %d" % (len(text), ENV_VALUE_MAX))
    return {
        ENV_PIN_JSON: text,
        ENV_PIN_SHA256: sha256_of(text),
        ENV_REGISTER_VERSION: pin["register"]["version"],
        ENV_REGISTER_SHA256: pin["register"]["sha256"],
    }


def load_pin_env(environ) -> dict:
    """Reference fail-closed reader: every key present, the hash matches, the register ids agree."""
    missing = [k for k in ENV_KEYS if not environ.get(k)]
    if missing:
        raise PinError("missing env: %s" % ", ".join(missing))
    pin = loads(environ[ENV_PIN_JSON], environ[ENV_PIN_SHA256])
    if pin["register"]["version"] != environ[ENV_REGISTER_VERSION] or \
            pin["register"]["sha256"] != environ[ENV_REGISTER_SHA256]:
        raise PinError("register version/sha256 in env disagree with the pin")
    return pin
