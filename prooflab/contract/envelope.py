"""The run envelope `ifabric.run/1` (ARCH §7.2): the ids and tally the script hands each agent. Stdlib, 3.9.

The orchestrating script (EP-5, PR-08a) puts it in the invocation payload under `payload["ifabric"]`;
the agents (PR-04 start-up, PR-05 rails, PR-06 apps) read it with `read_envelope` and echo the ids back.

  {"ifabric": {"envelope": "ifabric.run/1", "run_id": "ifabric-run-<epoch>-<hex>", "handoff_id": "<run_id>:h2",
    "from": "ifabric-customer", "to": "ifabric-it", "tier": "<tier>", "tally_tokens": 0, "tally_calls": 0,
    "register_version": "v1", "register_sha256": "<sha>", "provenance": "LIVE_SUBJECT", "condition": "none"}}

No envelope (`read_envelope` -> None) is the unenveloped path (ARCH §7.1): the agent mints an
`ifabric-unenveloped-…` CID, stamps UNATTRIBUTED and starts its tally at 0. Never a cap in the envelope.
"""
from __future__ import annotations

import re

from prooflab.contract import ids as _ids
from prooflab.contract import record as _rec

ENVELOPE_SCHEMA = "ifabric.run/1"
PAYLOAD_KEY = "ifabric"
ENVELOPE_KEYS = (
    "envelope", "run_id", "handoff_id", "from", "to", "tier", "tally_tokens", "tally_calls",
    "register_version", "register_sha256", "provenance", "condition",
)
# Optional keys the script may add (PR-08a): the pin echo, mode, condition digest, scenario, a declared fault.
ENVELOPE_OPTIONAL = ("pin_sha256", "mode", "condition_sha256", "scenario", "fault")
MODES = ("enforce", "observe")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def build_envelope(run_id, handoff_id, from_agent, to_agent, tier, tally_tokens, tally_calls,
                   register_version, register_sha256, provenance, condition="none", **optional) -> dict:
    """The envelope dict (put it at payload[PAYLOAD_KEY]). Raises ValueError if it does not validate."""
    env = {
        "envelope": ENVELOPE_SCHEMA, "run_id": run_id, "handoff_id": handoff_id, "from": from_agent,
        "to": to_agent, "tier": tier, "tally_tokens": tally_tokens, "tally_calls": tally_calls,
        "register_version": register_version, "register_sha256": register_sha256, "provenance": provenance,
        "condition": condition,
    }
    for key, value in optional.items():
        if key not in ENVELOPE_OPTIONAL:
            raise ValueError("unknown envelope key: %r" % (key,))
        if value is not None:
            env[key] = value
    errors = validate_envelope(env)
    if errors:
        raise ValueError("invalid envelope: " + "; ".join(errors))
    return env


def wrap(payload: dict, env: dict) -> dict:
    """A copy of `payload` with the envelope under PAYLOAD_KEY."""
    out = dict(payload or {})
    out[PAYLOAD_KEY] = env
    return out


def read_envelope(payload) -> "dict | None":
    """payload["ifabric"] when it is an `ifabric.run/1` object, else None (the unenveloped path). Never raises.
    It does not validate: call validate_envelope() and treat a non-empty list as untrusted ids."""
    try:
        if not isinstance(payload, dict):
            return None
        env = payload.get(PAYLOAD_KEY)
        if not isinstance(env, dict) or env.get("envelope") != ENVELOPE_SCHEMA:
            return None
        return dict(env)
    except Exception:  # noqa: BLE001 - a malformed payload is the unenveloped path, never a crash
        return None


def _nonneg_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_envelope(env) -> list:
    """Every error in `env` (empty list = valid). Never raises."""
    try:
        return _validate(env)
    except Exception as exc:  # noqa: BLE001
        return ["envelope is malformed: %s: %s" % (type(exc).__name__, exc)]


def _validate(env):
    if not isinstance(env, dict):
        return ["envelope must be an object"]
    errors = []
    for key in ENVELOPE_KEYS:
        if key not in env:
            errors.append("%s: required" % key)
    for key in env:
        if key not in ENVELOPE_KEYS and key not in ENVELOPE_OPTIONAL:
            errors.append("%s: unknown envelope key" % key)
    if env.get("envelope") != ENVELOPE_SCHEMA:
        errors.append("envelope: must be %r" % ENVELOPE_SCHEMA)
    run_id = env.get("run_id")
    try:
        _ids.parse_cid(run_id)
    except (ValueError, TypeError):
        errors.append("run_id: not an ifabric CID")
        run_id = None
    try:
        hcid, _n = _ids.parse_handoff_id(env.get("handoff_id"))
        if run_id is not None and hcid != run_id:
            errors.append("handoff_id: CID %r differs from run_id" % (hcid,))
    except (ValueError, TypeError):
        errors.append("handoff_id: not <run_id>:h<n>")
    for key in ("from", "to", "tier", "register_version", "condition"):
        if key == "tier" and env.get(key) is None:
            continue                       # no tier decision (ARCH §7.2 step 3 "if tiers"): the pin's default
        if key in env and not (isinstance(env[key], str) and env[key].strip()):
            errors.append("%s: must be a non-empty string" % key)
    for key in ("tally_tokens", "tally_calls"):
        if key in env and not _nonneg_int(env[key]):
            errors.append("%s: must be an int >= 0" % key)
    for key in ("register_sha256", "pin_sha256", "condition_sha256"):
        if key in env and not (isinstance(env[key], str) and _SHA256_RE.match(env[key])):
            if key == "register_sha256" or env[key] is not None:
                errors.append("%s: not a lowercase sha256 hex" % key)
    if "provenance" in env and env["provenance"] not in _rec.PROVENANCE:
        errors.append("provenance: %r not in %s" % (env["provenance"], list(_rec.PROVENANCE)))
    if env.get("mode") is not None and env["mode"] not in MODES:
        errors.append("mode: must be enforce|observe")
    for key, value in env.items():
        if isinstance(value, str) and _rec.secret_shaped(value):
            errors.append("%s: secret-shaped value refused" % key)
    return errors


def echo(env: dict) -> dict:
    """The ids an agent echoes back in its response (ARCH §7.2)."""
    return dict((k, env.get(k)) for k in ("envelope", "run_id", "handoff_id", "to"))
