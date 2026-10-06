"""The ONE evidence record: schema `ifabric.evidence/1` (ARCH §4; guardrails G0.2 path A). Stdlib, 3.9.

One flat JSON object per record, dotted keys. Three field classes (ARCH §4.2):
  REQUIRED      on every record (plus one of the two time pairs, R*)
  TABLE_A       never left out: a value, or null with an entry in `null_reasons` (the null rule)
  OPTIONAL      may be absent
  DERIVED       stitch/query-time only: NEVER on an emitted or stored record

`validate_record(rec) -> list[str]` returns every error (empty list = valid); it never raises.
`new_record(...)` builds a record and fills every unset table-A field with null + a reason.
"""
from __future__ import annotations

import hashlib
import json
import re

from prooflab.contract import clocks as _clocks
from prooflab.contract import ids as _ids
from prooflab.contract import verdicts as _v

SCHEMA_ID = "ifabric.evidence/1"

# --- field classes ------------------------------------------------------------------------------

REQUIRED = (
    "schema", "record_id", "record_kind", "phase", "detail", "correlation_id", "run.id", "verdict",
    "ts", "provenance", "authorship", "source.refs", "emitter", "null_reasons",
)
TIME_PAIRS = (("emitted.at", "emitted.clock"), ("observed.at", "observed.clock"))

TABLE_A = (
    "call.id", "trace.id",
    "handoff.id", "handoff.from", "handoff.to", "handoff.payload_sha256", "handoff.data_classification",
    "control.ref", "control.id",
    "threshold.version", "threshold.value", "threshold.sha256", "threshold.tier",
    "register.version", "pin.sha256",
    "measured.value", "measured.unit", "measured.source",
    "reason", "outcome.platform_decision", "outcome.real",
    "evaluator.name", "evaluator.sha256",
    "inline.mode", "inline.limit_applied", "inline.limit_value", "inline.action", "inline.bound_basis",
    "actor.id", "actor.runtime_id", "actor.version", "on_behalf_of", "principal.platform",
    "ep.id", "ep.kind", "ep.transport", "ep.responsible", "control.owner",
)

RAIL_FIELDS = (
    "rail.id", "rail.version", "rail.stage", "rail.hook", "rail.mechanism", "rail.policy_sha256",
    "rail.subject", "rail.subject_sha256_in", "rail.subject_sha256_out", "rail.matches", "rail.values",
    "rail.evidence_id", "rail.llm_call_id", "rail.llm_outcome", "rail.latency_ms", "rail.error",
)
RAILS_COMPACT_FIELDS = ("rails.allow", "rails.policy_sha256", "rails.counts")

OPTIONAL = (
    "supersedes", "span.id", "seq.in_stream", "seq", "runtime.arn", "runtime.session_id", "aws.request_id",
    "finding.id", "assessment.id", "run.condition",
    "emitted.at", "emitted.clock", "observed.at", "observed.clock",
    "model.id", "tokens.in", "tokens.out", "outcome.http_status", "outcome.finish_reason",
    "tool.name", "tool.declared", "tool.args_sha256", "data_classification",
) + RAIL_FIELDS + RAILS_COMPACT_FIELDS

DERIVED = (
    "system.id", "system.risk_tier", "component.id", "component.owner", "component.approved_version",
    "component.approval", "inventory.version", "inventory.sha256", "inventory.match", "risk.refs",
)

# Assessment records carry the §3.2 Assessment fields flattened under `assessment.*` (optional group).
ASSESSMENT_PREFIX = "assessment."

KNOWN_FIELDS = frozenset(REQUIRED + TABLE_A + OPTIONAL)

# --- vocabularies -------------------------------------------------------------------------------

RECORD_KINDS = (
    "decision", "action", "platform_decision", "observation", "handoff", "lifecycle", "judgment",
    "approval", "notification", "metric", "assessment", "finding", "reconciliation", "adversarial",
    "link-gap", "rail_decision",
)
CONTROL_REFS = ("C16", "C7", "C9", "ESC", "APPROVAL", "INV", "PLATFORM", "NONE", "RAIL")
CONTROL_LIBRARY_IDS = {
    "C16": "ACN-COST-001", "C7": "AIA-LOG-001", "C9": "AIA-ARC-006",
    "APPROVAL": "IFABRIC-APPROVAL-001", "INV": "AIA-INV-001.01", "ESC": "AGENT-ESCALATION",
}
EP_IDS = tuple("EP-%d" % n for n in range(0, 17))
EP_TRANSPORTS = ("evaluate", "emit", "callback", "pull")
PROVENANCE = (
    "EXPLORATORY", "PILOT", "BASELINE", "LIVE_SUBJECT", "AUTHORIZED_TEST", "FAULT_INJECTION", "REPLAY",
    "COUNTERFACTUAL_EXPORT", "SYNTHETIC", "UNATTRIBUTED",
)
AUTHORSHIP = ("TESTIMONY", "PLATFORM", "ASSURANCE", "HUMAN")
OUTCOME_REAL = (
    "SERVED", "BLOCKED_GUARDRAIL", "REFUSED_403", "PAUSED_404", "METHOD_405", "CEILING_429", "ERROR_5XX",
    "CANCELLED_C16", "CANCELLED_RAIL", "TIMEOUT",
)
MEASURED_SOURCES = ("adapter-tally", "gateway-figure-of-record", "cloudwatch", "pdp", "ledger")  # open list
RAIL_STAGES = ("input", "execution", "retrieval", "model", "output", "runtime")
RAIL_HOOKS = (
    "entrypoint", "discovery", "before_tool_call", "after_tool_call", "before_model_call",
    "after_model_call", "after_invocation", "startup", "audit_hook",
)
RAIL_MECHANISMS = ("code", "llm-self-check", "platform-guardrail-observed")

EMITTED_RECORD_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{9}Z-[a-z0-9][a-z0-9.\-]{0,31}-[0-9a-f]{8}$")
OBS_RECORD_ID_RE = re.compile(r"^obs-[0-9a-f]{32}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RAIL_TAG_RE = re.compile(r"^[A-Z]{1,3}-[0-9]{2}@[0-9]+$")
SOURCE_REF_RE = re.compile(r"^[a-z][a-z0-9-]*:\S.*$")

# --- the secret guard (schema-level; the exact-value scan of §9.3 is the real check) -------------
# Patterns are assembled from parts so this file never holds a literal the repo's secret scan flags.
_SECRET_VALUE_RES = (
    re.compile("(" + "AK" + "IA" + "|" + "AS" + "IA" + ")[A-Z0-9]{16}"),
    re.compile("-----BEGIN [A-Z ]*" + "PRIV" + "ATE KEY-----"),
    re.compile("gh" + "p_[A-Za-z0-9]{20,}"),
    re.compile("git" + "hub_" + "pat_"),
    re.compile("s" + "k-[A-Za-z0-9]{20,}"),
    re.compile("xo" + "x[bap]-[A-Za-z0-9-]{10,}"),
    re.compile("Bear" + "er [A-Za-z0-9._~+/=-]{20,}"),
    re.compile("[?&]" + "tk" + "n" + "="),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\."),            # a JWT
    re.compile(r"(?i)\b(aws_" + "secret" + "_access_key|aws_" + "session" + "_token)\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]*(TOKEN|SECRET|PASSWORD|API_KEY)[A-Z0-9_]*=\S"),  # env-value-shaped
)
_SECRET_KEY_RE = re.compile(r"(?i)(secret|password|passwd|api[_-]?key|private[_-]?key|credential|_token$|^token$|"
                            r"authorization|cookie)")


def secret_shaped(value) -> bool:
    """True if a string looks like a credential or an env assignment of one."""
    if not isinstance(value, str):
        return False
    return any(rx.search(value) for rx in _SECRET_VALUE_RES)


def _walk_strings(value, path):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield path + "." + str(k), str(k)
            for item in _walk_strings(v, path + "." + str(k)):
                yield item
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            for item in _walk_strings(v, "%s[%d]" % (path, i)):
                yield item


# --- ids ----------------------------------------------------------------------------------------

def emitted_record_id(emitted_at: str, emitter_short: str, hex8: str) -> str:
    """`<emitted.at compact>-<emitter short>-<8 hex>`; the caller supplies the 8 hex (random or a digest)."""
    rid = "%s-%s-%s" % (_clocks.compact(emitted_at), emitter_short, hex8)
    if not EMITTED_RECORD_ID_RE.match(rid):
        raise ValueError("malformed record id: %r" % (rid,))
    return rid


def observation_record_id(source_system: str, source_ref: str) -> str:
    """`obs-` + sha256(source.system + "|" + source.ref)[:32]: deterministic, so a re-pull deduplicates."""
    digest = hashlib.sha256((source_system + "|" + source_ref).encode("utf-8")).hexdigest()
    return "obs-" + digest[:32]


def rail_tag(rail_id: str, version) -> str:
    """The compact-ALLOW tag: 'X-02@1' (rails §5.3)."""
    tag = "%s@%s" % (rail_id, version)
    if not RAIL_TAG_RE.match(tag):
        raise ValueError("malformed rail tag: %r" % (tag,))
    return tag


def empty_rail_counts(rail_ids) -> dict:
    """{rail: {ALLOW: 0, BLOCK: 0, MODIFY: 0, FLAG: 0}} for the lifecycle record's `rails.counts`."""
    return {rid: dict((v, 0) for v in _v.RAIL_VERDICTS) for rid in rail_ids}


# --- constructor --------------------------------------------------------------------------------

def new_record(record_kind: str, null_reason: str = "not applicable", **fields) -> dict:
    """Build a record. Pass dotted keys through a dict: new_record("decision", **{"run.id": cid, ...}).

    `schema`, `phase` (`ifabric.<kind>`), `correlation_id` (= run.id), `ts` (= emitted.at or observed.at),
    `source.refs` ([]) and `null_reasons` ({}) are defaulted. Every table-A field left unset becomes null
    with `null_reason` (an explicit `null_reasons` entry from the caller wins). It does not validate:
    call validate_record() on the result.
    """
    rec = dict(fields)
    rec["schema"] = SCHEMA_ID
    rec["record_kind"] = record_kind
    rec.setdefault("phase", "ifabric." + record_kind)
    if "run.id" in rec:
        rec.setdefault("correlation_id", rec["run.id"])
    rec.setdefault("ts", rec.get("emitted.at") or rec.get("observed.at"))
    rec.setdefault("source.refs", [])
    reasons = dict(rec.get("null_reasons") or {})
    for name in TABLE_A:
        if name not in rec:
            rec[name] = None
        if rec[name] is None and name not in reasons:
            reasons[name] = null_reason
    rec["null_reasons"] = reasons
    return rec


def complete_nulls(rec: dict, null_reason: str) -> dict:
    """A copy of `rec` with every missing table-A field set to null with `null_reason`."""
    out = dict(rec)
    reasons = dict(out.get("null_reasons") or {})
    for name in TABLE_A:
        if name not in out:
            out[name] = None
        if out[name] is None and name not in reasons:
            reasons[name] = null_reason
    out["null_reasons"] = reasons
    return out


def canonical_json(rec: dict) -> str:
    """Sorted keys, no spaces, UTF-8 safe: the bytes a digest is taken over."""
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# --- validator ----------------------------------------------------------------------------------

def _enum(errors, rec, field, allowed, nullable=True):
    value = rec.get(field)
    if value is None:
        if not nullable and field in rec:
            errors.append("%s: must not be null" % field)
        return
    if value not in allowed:
        errors.append("%s: %r not in %s" % (field, value, list(allowed)))


def _sha(errors, rec, field):
    value = rec.get(field)
    if value is not None and not (isinstance(value, str) and SHA256_RE.match(value)):
        errors.append("%s: not a lowercase sha256 hex" % field)


def validate_record(rec, require_table_a: bool = True) -> list:
    """Every schema error in `rec` (empty list = valid). Never raises.

    require_table_a=False skips only the null-rule completeness check (for reading partial shapes);
    stored and emitted records are always checked with the default True.
    """
    try:
        return _validate(rec, require_table_a)
    except Exception as exc:  # noqa: BLE001 - a malformed record is an error, never a crash
        return ["record is malformed: %s: %s" % (type(exc).__name__, exc)]


def _validate(rec, require_table_a):
    errors = []
    if not isinstance(rec, dict):
        return ["record must be a JSON object"]

    # required + time pair
    for name in REQUIRED:
        if name not in rec:
            errors.append("%s: required field missing" % name)
        elif rec[name] is None or rec[name] == "":
            errors.append("%s: required field is null/empty" % name)
    if not any(rec.get(a) and rec.get(c) for a, c in TIME_PAIRS):
        errors.append("emitted.at/emitted.clock or observed.at/observed.clock: one pair is required")
    if rec.get("schema") not in (None, SCHEMA_ID):
        errors.append("schema: must be %r" % SCHEMA_ID)

    # unknown and derived keys
    for key in rec:
        if key in DERIVED:
            errors.append("%s: derived field (stitch/query time only), never on a stored record" % key)
        elif key not in KNOWN_FIELDS and not key.startswith(ASSESSMENT_PREFIX):
            errors.append("%s: unknown field" % key)

    # null rule
    reasons = rec.get("null_reasons")
    if not isinstance(reasons, dict):
        errors.append("null_reasons: must be an object")
        reasons = {}
    if require_table_a:
        for name in TABLE_A:
            if name not in rec:
                errors.append("%s: table-A field missing (use null with a null_reasons entry)" % name)
    for name in TABLE_A + OPTIONAL:
        if name in rec and rec[name] is None and name in TABLE_A:
            if not str(reasons.get(name) or "").strip():
                errors.append("%s: null without a null_reasons entry" % name)
    for name in reasons:
        if name not in KNOWN_FIELDS and not name.startswith(ASSESSMENT_PREFIX):
            errors.append("null_reasons.%s: names an unknown field" % name)
        elif rec.get(name) is not None:
            errors.append("null_reasons.%s: field is not null" % name)

    # vocabularies
    kind = rec.get("record_kind")
    if not isinstance(kind, str):
        kind = None
    _enum(errors, rec, "record_kind", RECORD_KINDS)
    _enum(errors, rec, "control.ref", CONTROL_REFS)
    _enum(errors, rec, "ep.id", EP_IDS)
    _enum(errors, rec, "ep.transport", EP_TRANSPORTS)
    _enum(errors, rec, "provenance", PROVENANCE)
    _enum(errors, rec, "authorship", AUTHORSHIP)
    _enum(errors, rec, "outcome.real", OUTCOME_REAL)
    _enum(errors, rec, "outcome.platform_decision", _v.DECISION_VERDICTS)
    _enum(errors, rec, "emitted.clock", _clocks.CLOCKS)
    _enum(errors, rec, "observed.clock", _clocks.CLOCKS)
    _enum(errors, rec, "inline.mode", _v.INLINE_MODES)
    _enum(errors, rec, "inline.action", _v.INLINE_ACTIONS)
    _enum(errors, rec, "inline.limit_applied", _v.LIMITS_APPLIED)
    _enum(errors, rec, "inline.bound_basis", _v.BOUND_BASES)
    _enum(errors, rec, "rail.stage", RAIL_STAGES)
    _enum(errors, rec, "rail.hook", RAIL_HOOKS)
    _enum(errors, rec, "rail.mechanism", RAIL_MECHANISMS)
    verdict = rec.get("verdict")
    if kind in _v.VERDICTS_BY_KIND and verdict is not None and not _v.is_verdict_allowed(kind, verdict):
        errors.append("verdict: %r is not a %s verdict (allowed %s)" % (verdict, kind, list(_v.VERDICTS_BY_KIND[kind])))
    if verdict in _v.RISK_STATES:
        errors.append("verdict: risk states never appear in a verdict field")

    # timestamps
    for name in ("emitted.at", "observed.at", "ts"):
        if rec.get(name) is not None and not _clocks.is_utc(rec[name]):
            errors.append("%s: not a UTC timestamp ending in Z" % name)
    if rec.get("ts") and rec.get("emitted.at") and rec["ts"] != rec["emitted.at"]:
        errors.append("ts: must equal emitted.at")

    # ids
    run_id = rec.get("run.id")
    if run_id is not None and not _ids.is_valid_run_id(run_id):
        errors.append("run.id: not a valid CID")
    cid = rec.get("correlation_id")
    if cid is not None and cid != run_id and not str(cid).startswith("unresolved:"):
        errors.append("correlation_id: must equal run.id (or unresolved:<trace id>)")
    rid = rec.get("record_id")
    if isinstance(rid, str) and kind != "assessment":
        if not (EMITTED_RECORD_ID_RE.match(rid) or OBS_RECORD_ID_RE.match(rid)):
            errors.append("record_id: neither <compact time>-<emitter>-<8 hex> nor obs-<32 hex>")
    if kind in ("observation", "platform_decision", "metric") and rec.get("authorship") == "PLATFORM":
        if isinstance(rid, str) and not OBS_RECORD_ID_RE.match(rid):
            errors.append("record_id: a pulled platform record needs the deterministic obs- id")
    for name in ("handoff.payload_sha256", "evaluator.sha256", "pin.sha256", "threshold.sha256",
                 "tool.args_sha256", "rail.policy_sha256", "rails.policy_sha256",
                 "rail.subject_sha256_in", "rail.subject_sha256_out"):
        _sha(errors, rec, name)
    refs = rec.get("source.refs")
    if refs is not None:
        if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
            errors.append("source.refs: must be a list of strings")
        else:
            for r in refs:
                if not SOURCE_REF_RE.match(r):
                    errors.append("source.refs: %r is not prefix:value" % r)

    # record-kind rules
    ref = rec.get("control.ref")
    if ref == "RAIL" and kind != "rail_decision":
        errors.append("control.ref: RAIL only on rail_decision records")
    if kind == "rail_decision":
        errors.extend(_rail_errors(rec))
    elif any(k in rec for k in RAIL_FIELDS):
        errors.append("rail.*: only on rail_decision records (compact ALLOWs use rails.allow)")
    if kind == "assessment" and (any(k in rec for k in RAIL_FIELDS + RAILS_COMPACT_FIELDS) or ref == "RAIL"):
        errors.append("assessment: rail fields or verdicts never enter an assessment")
    if kind == "handoff" and rec.get("ep.id") not in (None, "EP-5"):
        errors.append("ep.id: handoff records come from EP-5")
    errors.extend(_compact_rails_errors(rec))

    # secret guard
    for path, text in _walk_strings(rec, "$"):
        if secret_shaped(text):
            errors.append("%s: secret-shaped value refused" % path)
    for key in rec:
        if _SECRET_KEY_RE.search(key.split(".")[-1]) and key not in ("tokens.in", "tokens.out"):
            errors.append("%s: key names a secret" % key)
    return errors


def _rail_errors(rec) -> list:
    errors = []
    for name in ("rail.id", "rail.version", "rail.stage", "rail.policy_sha256"):
        if not rec.get(name):
            errors.append("%s: required on a rail_decision" % name)
    if rec.get("control.ref") != "RAIL":
        errors.append("control.ref: a rail_decision carries RAIL")
    if rec.get("rail.id") and rec.get("control.id") not in (None, "RAIL-" + str(rec["rail.id"])):
        errors.append("control.id: must be RAIL-<rail.id>")
    if rec.get("register.version") is not None:
        errors.append("register.version: a rail is not a register control (null with a reason)")
    mode, action = rec.get("inline.mode"), rec.get("inline.action")
    if mode not in (None,) + _v.C16_MODES:
        errors.append("inline.mode: a rail runs in enforce|observe")
    if action is not None and action not in _v.RAIL_ACTIONS:
        errors.append("inline.action: %r is not a rail action" % (action,))
    if mode == "observe" and action not in (None, "proceed"):
        errors.append("inline.action: in observe a rail always proceeds")
    if rec.get("ep.id") not in (None, "EP-14", "EP-1", "EP-3", "EP-4", "EP-15"):
        errors.append("ep.id: a rail decides at EP-14, EP-1, EP-3, EP-4 or EP-15")
    run_id = str(rec.get("run.id") or "")
    if not rec.get("handoff.id") and run_id.startswith("ifabric-") and not run_id.startswith("ifabric-unenveloped"):
        errors.append("handoff.id: every rail record sets the invocation's handoff id (duplicate key)")
    return errors


def _compact_rails_errors(rec) -> list:
    errors = []
    allow = rec.get("rails.allow")
    if allow is not None:
        if not isinstance(allow, list) or not all(isinstance(t, str) and RAIL_TAG_RE.match(t) for t in allow):
            errors.append("rails.allow: must be a list of '<rail id>@<n>' tags")
        if not rec.get("rails.policy_sha256"):
            errors.append("rails.policy_sha256: required with rails.allow")
    counts = rec.get("rails.counts")
    if counts is not None:
        ok = isinstance(counts, dict) and all(
            isinstance(c, dict) and set(c) <= set(_v.RAIL_VERDICTS)
            and all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in c.values())
            for c in counts.values())
        if not ok:
            errors.append("rails.counts: must be {rail: {ALLOW|BLOCK|MODIFY|FLAG: int >= 0}}")
        if rec.get("record_kind") != "lifecycle":
            errors.append("rails.counts: only on the invocation's lifecycle record")
    return errors


def is_valid(rec) -> bool:
    return not validate_record(rec)


def json_schema() -> dict:
    """The JSON Schema document committed as schema/evidence-record-1.json (a test keeps them equal).
    The Python validator is the authority; the JSON file is for other tools and readers."""
    nullable = lambda t: {"type": [t, "null"]}
    props = {}
    for name in REQUIRED + TABLE_A + OPTIONAL:
        props[name] = {}
    props["schema"] = {"const": SCHEMA_ID}
    props["record_kind"] = {"enum": list(RECORD_KINDS)}
    props["verdict"] = {"enum": list(_v.ALL_RECORD_VERDICTS)}
    props["provenance"] = {"enum": list(PROVENANCE)}
    props["authorship"] = {"enum": list(AUTHORSHIP)}
    props["control.ref"] = {"enum": list(CONTROL_REFS) + [None]}
    props["ep.id"] = {"enum": list(EP_IDS) + [None]}
    props["ep.transport"] = {"enum": list(EP_TRANSPORTS) + [None]}
    props["outcome.real"] = {"enum": list(OUTCOME_REAL) + [None]}
    props["emitted.clock"] = {"enum": list(_clocks.CLOCKS)}
    props["observed.clock"] = {"enum": list(_clocks.CLOCKS)}
    props["rail.stage"] = {"enum": list(RAIL_STAGES)}
    props["rail.hook"] = {"enum": list(RAIL_HOOKS)}
    props["rail.mechanism"] = {"enum": list(RAIL_MECHANISMS)}
    props["source.refs"] = {"type": "array", "items": {"type": "string"}}
    props["null_reasons"] = {"type": "object", "additionalProperties": {"type": "string"}}
    props["rails.allow"] = {"type": "array", "items": {"type": "string", "pattern": RAIL_TAG_RE.pattern}}
    props["rails.counts"] = {"type": "object"}
    for name in ("emitted.at", "observed.at", "ts"):
        props[name] = {"type": "string", "pattern": _clocks.UTC_RE.pattern}
    for name in ("seq.in_stream", "seq", "tokens.in", "tokens.out", "outcome.http_status", "rail.latency_ms"):
        props[name] = nullable("integer")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "ifabric.evidence/1",
        "title": "ProofLab evidence record (team iFabric)",
        "description": "One flat record, dotted keys (ARCH §4). Table-A fields are present as a value or null "
                       "with a null_reasons entry. prooflab/contract/record.py validate_record is the authority.",
        "type": "object",
        "required": list(REQUIRED) + list(TABLE_A),
        "properties": props,
        "patternProperties": {"^assessment\\.": {}},
        "additionalProperties": False,
        "x-table-a": list(TABLE_A),
        "x-derived-never-stored": list(DERIVED),
        "x-time-pairs": [list(p) for p in TIME_PAIRS],
    }
