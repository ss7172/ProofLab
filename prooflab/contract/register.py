"""The register schema (ARCH §3.3, §5.1-§5.3): per-control versions, kit fields, extended flat keys. Stdlib, 3.9.

Input is the output of prooflab.registry.parse.parse_register(text) (all values are strings, as the kit's
fallback parser returns them). `validate_register(doc) -> list[str]`; typed accessors convert on read.
The register's sha256 is always taken over the frozen FILE BYTES (`register_sha256(data)`), never a re-dump.
"""
from __future__ import annotations

import hashlib
import json
import re

from prooflab.contract import clocks as _clocks

TOP_REQUIRED = ("version", "version_date")
TOP_KNOWN = TOP_REQUIRED + (
    "supersedes", "claim_id", "register_owner", "pre_run_gate", "join_tolerance_s",
    # G-14 (handoff-3 boundary keys)
    "register_version", "status", "frozen_at", "builder", "assurance", "retention", "owner", "owner_name",
)

KIT_FIELDS = (
    "control_id", "name", "metric", "observation_limit", "exception_tolerance", "measurement_basis", "owner",
    "version_date", "enforcement_point",
)
CONTROL_REQUIRED = KIT_FIELDS + ("control_ref", "library_id", "threshold_version")

CONTROL_KNOWN = CONTROL_REQUIRED + (
    "mode", "in_claim", "objective", "risk", "risk_ref", "scope", "applies_to",
    "metric_unit", "calculation", "exception_denominator",
    "why_metric", "why_value", "measured_on", "stops_holding_when",
    "missing_data_rule", "late_data_rule", "duplicate_rule", "invalid_data_rule",
    "transport_inline", "transport_postrun", "evaluator_module", "evaluator_sha256",
    "alert_recipient", "alert_volume_bound", "owner_name",
    # C16
    "tier_rule", "default_tier", "inline_modes", "safety_ceiling", "inline_bound_margin_pct",
    "inline_bound_fallback_tokens", "max_tokens", "declared_conditions", "breach_protocol",
    # C7
    "expected_sources", "workflow_events", "workflow_events_after_stop", "gap_clock", "declared_faults",
    # C9
    "metric_namespace", "statistic", "window_rule", "baseline_procedure", "limit_direction", "comparability",
    "declared_treatments",
)
CONTROL_KEY_PREFIXES = ("cap_tier_", "handoff_class_", "baseline_value_")

CONTROL_MODES = ("static", "scheduled", "event-driven", "in-transaction", "continuous")
PRE_RUN_GATES = ("block-assessed", "record-only")
THRESHOLD_VERSION_RE = re.compile(r"^(C16|C7|C9|INV|APPROVAL|ESC)-v[0-9]+(\.[0-9]+)*$")
REGISTER_VERSION_RE = re.compile(r"^v[0-9]+(\.[0-9]+)*(-[a-z0-9-]+)?$")
INT_RE = re.compile(r"^-?[0-9]+$")
NUM_RE = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")


def register_sha256(data: bytes) -> str:
    """sha256 of the frozen file's bytes (what threshold.sha256 and the pin carry)."""
    return hashlib.sha256(data).hexdigest()


def as_int(value: str) -> int:
    if not isinstance(value, str) or not INT_RE.match(value.strip()):
        raise ValueError("not an integer: %r" % (value,))
    return int(value)


def as_number(value: str):
    if not isinstance(value, str) or not NUM_RE.match(value.strip()):
        raise ValueError("not a number: %r" % (value,))
    return int(value) if INT_RE.match(value.strip()) else float(value)


def as_list(value: str) -> list:
    """Comma-joined string -> list (empty string -> [])."""
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def as_bool(value: str) -> bool:
    if value not in ("true", "false"):
        raise ValueError("not true|false: %r" % (value,))
    return value == "true"


def tier_caps(control: dict) -> dict:
    """{tier: cap} from the C16 entry's cap_tier_<name> keys."""
    return dict((k[len("cap_tier_"):], as_int(v)) for k, v in sorted(control.items()) if k.startswith("cap_tier_"))


def controls_by_ref(doc: dict) -> dict:
    return dict((e.get("control_ref"), e) for e in doc["entries"])


def control_versions(doc: dict) -> dict:
    """{control_ref: (threshold_version, version_date)}: the control's own version and date (E-05)."""
    return dict((e.get("control_ref"), (e.get("threshold_version"), e.get("version_date"))) for e in doc["entries"])


def entry_digest(entry: dict) -> str:
    """Canonical digest of one control entry (key order independent)."""
    return hashlib.sha256(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def check_version_bumps(old: dict, new: dict) -> list:
    """Per-control versioning (§3.3), both directions, between a superseded and a new parsed register:
    an unchanged entry keeps its threshold_version and version_date; any changed key bumps both."""
    errors = []
    olds = controls_by_ref(old)
    for ref, entry in controls_by_ref(new).items():
        prev = olds.get(ref)
        if prev is None:
            continue
        strip = lambda e: dict((k, v) for k, v in e.items() if k not in ("threshold_version", "version_date"))
        changed = strip(prev) != strip(entry)
        same_version = prev.get("threshold_version") == entry.get("threshold_version")
        same_date = prev.get("version_date") == entry.get("version_date")
        if changed and (same_version or same_date):
            errors.append("%s: values changed but threshold_version/version_date not both bumped" % ref)
        if not changed and not (same_version and same_date):
            errors.append("%s: values unchanged but threshold_version/version_date changed" % ref)
    return errors


def validate_register(doc: dict) -> list:
    """Schema errors in a parsed register (empty list = valid)."""
    errors = []
    top = doc.get("top") or {}
    for k in TOP_REQUIRED:
        if not top.get(k):
            errors.append("top.%s: required" % k)
    for k in top:
        if k not in TOP_KNOWN:
            errors.append("top.%s: unknown top-level key" % k)
    if top.get("version") and not REGISTER_VERSION_RE.match(top["version"]):
        errors.append("top.version: %r is not v<n>[.<m>][-label]" % top["version"])
    if top.get("version_date") and not _clocks.is_utc(top["version_date"]):
        errors.append("top.version_date: must be a quoted full UTC time (rule 7)")
    if top.get("pre_run_gate") and top["pre_run_gate"] not in PRE_RUN_GATES:
        errors.append("top.pre_run_gate: not in %s" % list(PRE_RUN_GATES))
    if doc.get("list_key") != "controls":
        errors.append("list key must be 'controls'")
    refs = set()
    for entry in doc.get("entries") or []:
        ref = entry.get("control_ref") or entry.get("control_id")
        where = "control %s" % ref
        for k in CONTROL_REQUIRED:
            if not entry.get(k):
                errors.append("%s.%s: required" % (where, k))
        for k in entry:
            if k not in CONTROL_KNOWN and not k.startswith(CONTROL_KEY_PREFIXES):
                errors.append("%s.%s: unknown key (extending the register is a contract change)" % (where, k))
        if ref in refs:
            errors.append("%s: duplicate control_ref" % where)
        refs.add(ref)
        tv = entry.get("threshold_version")
        if tv and not THRESHOLD_VERSION_RE.match(tv):
            errors.append("%s.threshold_version: %r is not <REF>-v<n>[.<m>]" % (where, tv))
        if tv and entry.get("control_ref") and not tv.startswith(entry["control_ref"] + "-"):
            errors.append("%s.threshold_version: must start with the control_ref" % where)
        if entry.get("version_date") and not _clocks.is_utc(entry["version_date"]):
            errors.append("%s.version_date: must be a quoted full UTC time (rule 7)" % where)
        if entry.get("mode") and entry["mode"] not in CONTROL_MODES:
            errors.append("%s.mode: not in %s" % (where, list(CONTROL_MODES)))
        if entry.get("in_claim") and entry["in_claim"] not in ("true", "false"):
            errors.append("%s.in_claim: true|false" % where)
        for k, v in entry.items():
            if k.startswith("cap_tier_") or k in ("safety_ceiling", "inline_bound_fallback_tokens", "max_tokens"):
                if not INT_RE.match(v):
                    errors.append("%s.%s: must be an integer" % (where, k))
            if k == "inline_bound_margin_pct" and not NUM_RE.match(v):
                errors.append("%s.%s: must be a number" % (where, k))
        if entry.get("control_ref") == "C16":
            for k in ("default_tier", "inline_modes", "safety_ceiling", "inline_bound_margin_pct",
                      "inline_bound_fallback_tokens", "max_tokens"):
                if not entry.get(k):
                    errors.append("%s.%s: required on C16 (the pin needs it)" % (where, k))
            caps = [k for k in entry if k.startswith("cap_tier_")]
            if not caps:
                errors.append("%s: C16 needs at least one cap_tier_<name>" % where)
            if entry.get("default_tier") and "cap_tier_" + entry["default_tier"] not in entry:
                errors.append("%s.default_tier: no cap_tier_%s" % (where, entry["default_tier"]))
            for mode in as_list(entry.get("inline_modes", "")):
                if mode not in ("enforce", "observe"):
                    errors.append("%s.inline_modes: %r not enforce|observe" % (where, mode))
    return errors
