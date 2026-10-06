"""Deterministic normalizer: raw platform captures -> `ifabric.evidence/1` records (ARCH §3.5, plan T4.3). Stdlib, 3.9.

Pure functions: the same raw text gives the same records, in the same order, with the same ids.
  * gateway pod logs (kubelet-prefixed) and span exports (flat JSON lines, same key names) -> `platform_decision`
    (refusals, an inferred guardrail block), `metric` (an llm call's tokens, the figure of record), `observation`
  * AWS `InvokeAgentRuntime` records (aict-invocations) -> `observation` carrying CID, session id, trace id, request id
Every record: authorship PLATFORM, record_id = observation_record_id(system, sha256 of the raw line) (so a re-pull
dedups), source.refs = raw file + line + sha256 of that line. Nothing here judges: no threshold, no verdict beyond
RECORDED, or the platform's own ALLOW/DENY on a platform_decision.
Run ids that are not a valid CID (the cockpit, `my-agent`, other parties) produce no record: they go to the
`sightings` list that the run catalogue reads. A line with no run id at all is kept only if the platform refused it
(its trace id becomes `unresolved:<trace>`, a link-gap for the stitcher); other no-run lines are background traffic,
counted and never a run (ARCH §3.6).
"""
from __future__ import annotations

import hashlib
import json
import re

from prooflab.contract import clocks as _clocks
from prooflab.contract import ids as _ids
from prooflab.contract import record as _rec

EMITTER = "prooflab.store.observations"
SYSTEM_GATEWAY = "gateway"
SYSTEM_AWS_INVOCATION = "aws-invocations"

_KV_RE = re.compile(r'([A-Za-z0-9_.:\-/]+)=("(?:[^"\\]|\\.)*"|\S*)')
_POD_RE = re.compile(r"^\[pod/(?P<pod>[^/\]]+)/(?P<ctr>[^\]]+)\] (?P<kts>\S+) (?P<rest>.*)$")
_TRACE_RE = re.compile(r"^[0-9a-f]{32}$")

REFUSAL_REAL = {403: "REFUSED_403", 404: "PAUSED_404", 405: "METHOD_405", 429: "CEILING_429"}
REFUSAL_EP = {403: "EP-6", 404: "EP-8"}
BAGGAGE_KEY = _ids.BAGGAGE_CID_KEY


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc6(value: str):
    """Trim a nanosecond UTC stamp to the 6 fractional digits the contract accepts; None if unparseable."""
    if not isinstance(value, str):
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?Z$", value)
    if not m:
        return None
    out = m.group(1) + ((m.group(2)[:7]) if m.group(2) else "") + "Z"
    return out if _clocks.is_utc(out) else None


def parse_kv(text: str) -> dict:
    out = {}
    for key, val in _KV_RE.findall(text):
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1]
        out[key] = val
    return out


def parse_gateway_line(line: str):
    """-> dict of the request's key=value pairs plus `_ts` (the gateway's own stamp), or None if not a request line."""
    m = _POD_RE.match(line.rstrip("\n"))
    if not m:
        return None
    parts = m.group("rest").split("\t")
    if len(parts) < 3 or not parts[2].startswith("request "):
        return None
    kv = parse_kv(parts[2][len("request "):])
    kv["_ts"] = _utc6(parts[0]) or _utc6(m.group("kts"))
    return kv


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def family_provenance(run_id: str) -> str:
    """The provenance a pulled record can honestly claim from the id alone (the run index refines it later)."""
    if run_id.startswith("fault-"):
        return "EXPLORATORY"
    if run_id.startswith("ifabric-test-"):
        return "AUTHORIZED_TEST"
    if run_id.startswith("ifabric-adv-"):
        return "AUTHORIZED_TEST"
    return "UNATTRIBUTED"


def _build(kind, rid, run_id, observed_at, clock, detail, provenance, refs, null_reason, **fields):
    rec = _rec.new_record(
        kind, null_reason,
        **dict({
            "record_id": rid, "run.id": run_id, "detail": detail, "verdict": "RECORDED",
            "observed.at": observed_at, "observed.clock": clock, "provenance": provenance,
            "authorship": "PLATFORM", "source.refs": refs, "emitter": EMITTER,
        }, **fields))
    return rec


def _gateway_record(kv: dict, raw_ref: str, lineno: int, line_sha: str, provenance_map, known_action_ids=None):
    """-> (record or None, sighting or None, reason or None).

    `known_action_ids`: action ids our own records name (e.g. the Assurance agent's ANALYSIS_* delivery-log lines).
    The ifabric-assure runtime's model call carries no baggage, so the gateway mints its own root trace and puts
    THAT 32-hex id in `modaas.run_id` (b6b, live 2026-10-06): such a span whose action id we know is kept as
    `unresolved:<trace>` for the stitcher to join by action id, never dropped as another party's traffic."""
    run_id = kv.get("modaas.run_id") or None
    trace = kv.get("modaas.trace_id") or kv.get("trace.id") or None
    status = _int(kv.get("http.status"))
    at = kv.get("_ts")
    if at is None:
        return None, None, "no usable timestamp"
    tokens_in = _int(kv.get("gen_ai.usage.input_tokens"))
    tokens_out = _int(kv.get("gen_ai.usage.output_tokens"))
    sighting = None
    if run_id:
        sighting = {"run_id": run_id, "source": "gateway", "ts": at, "tokens_in": tokens_in, "tokens_out": tokens_out}
    refused = status is not None and status >= 400
    if run_id and not _ids.is_valid_run_id(run_id):
        if known_action_ids and _TRACE_RE.match(run_id) and kv.get("modaas.action_id") in known_action_ids:
            run_id, sighting = _ids.unresolved_correlation_id(run_id), None   # joined by action id (stitcher)
        else:
            return None, sighting, None            # another party's id: catalogue only
    if not run_id:
        if not refused:
            return None, None, "background"
        if not (trace and _TRACE_RE.match(trace)):
            return None, None, "background"          # nothing to resolve it by: counted, raw capture keeps it
        run_id = _ids.unresolved_correlation_id(trace)
    prov = (provenance_map or {}).get(run_id) or ("UNATTRIBUTED" if run_id.startswith("unresolved:")
                                                  else family_provenance(run_id))
    refs = ["raw:" + raw_ref, "line:%d" % lineno, "sha256:" + line_sha]
    rid = _rec.observation_record_id(SYSTEM_GATEWAY, line_sha)
    route = kv.get("route", "")
    common = {"call.id": kv.get("modaas.action_id") or None, "trace.id": trace,
              "outcome.http_status": status}
    nr = "a gateway span carries no agent identity or control binding"
    if refused:
        real = REFUSAL_REAL.get(status, "ERROR_5XX" if status >= 500 else None)
        rec = _build("platform_decision", rid, run_id, at, "gateway",
                     "gateway answered http.status=%d on route %s" % (status, route), prov, refs, nr,
                     verdict="DENY", **dict(common, **{
                         "outcome.platform_decision": "DENY", "outcome.real": real,
                         "ep.id": REFUSAL_EP.get(status),
                         "reason": "http.status=%d" % status}))
        if rec.get("ep.id") is None:
            rec["null_reasons"]["ep.id"] = "the gateway status does not name an enforcement point"
        return rec, sighting, None
    if kv.get("protocol") == "llm":
        model = kv.get("gen_ai.request.model") or None
        if tokens_in == 0 and tokens_out == 0 and status == 200:
            rec = _build("platform_decision", rid, run_id, at, "gateway",
                         "model call answered 200 with 0/0 tokens (inferred guardrail block)", prov, refs, nr,
                         verdict="DENY", **dict(common, **{
                             "outcome.platform_decision": "DENY", "outcome.real": "BLOCKED_GUARDRAIL",
                             "ep.id": "EP-7", "model.id": model, "tokens.in": 0, "tokens.out": 0,
                             "reason": "inferred from http.status 200 with zero tokens; the raw finish reason is "
                                       "joined by action id, never read here"}))
            return rec, sighting, None
        if tokens_in is None or tokens_out is None:
            return None, sighting, "llm line without token counts"
        rec = _build("metric", rid, run_id, at, "gateway",
                     "gateway llm call: %d in, %d out tokens" % (tokens_in, tokens_out), prov, refs, nr,
                     **dict(common, **{
                         "model.id": model, "tokens.in": tokens_in, "tokens.out": tokens_out,
                         "measured.value": tokens_in + tokens_out, "measured.unit": "tokens",
                         "measured.source": "gateway-figure-of-record"}))
        return rec, sighting, None
    rec = _build("observation", rid, run_id, at, "gateway",
                 "gateway request %s %s status %s" % (kv.get("mcp.method.name") or kv.get("http.method", ""),
                                                      kv.get("http.path", ""), kv.get("http.status", "")),
                 prov, refs, nr, **common)
    return rec, sighting, None


def _flat(obj, prefix="", out=None):
    out = {} if out is None else out
    for k, v in obj.items():
        key = prefix + str(k)
        if isinstance(v, dict):
            _flat(v, key + ".", out)
        else:
            out[key] = v
    return out


def _insights_ts(row: dict, span: dict):
    """The span's own end time (ns epoch), else the Logs Insights @timestamp ('YYYY-MM-DD HH:MM:SS.mmm', UTC)."""
    import datetime
    nano = span.get("endTimeUnixNano") or span.get("startTimeUnixNano")
    try:
        t = datetime.datetime.fromtimestamp(int(nano) / 1e9, datetime.timezone.utc)
        return t.strftime("%Y-%m-%dT%H:%M:%S.") + "%06dZ" % t.microsecond
    except (TypeError, ValueError, OverflowError, OSError):
        pass
    stamp = str(row.get("@timestamp") or "").strip().replace(" ", "T")
    if stamp and not stamp.endswith("Z"):
        stamp += "Z"
    return stamp or None


def insights_row_to_flat(doc: dict) -> dict:
    """D3: one Logs Insights row (`@timestamp`, `@message` = the span as JSON) -> the flat span shape
    (`ts`, `protocol`, and the span's attributes as dotted keys) that the gateway normalizer reads. A row that is
    already flat is returned unchanged."""
    msg = doc.get("@message")
    if msg is None:
        return doc
    try:
        span = json.loads(msg) if isinstance(msg, str) else dict(msg)
    except ValueError:
        return {}
    if not isinstance(span, dict):
        return {}
    flat = dict(_flat(span.get("attributes") or {}))
    for k, v in _flat(dict((k, v) for k, v in span.items() if k != "attributes")).items():
        flat.setdefault(k, v)
    flat["ts"] = _insights_ts(doc, span)
    listener = flat.get("listener")
    if listener and "protocol" not in flat:
        flat["protocol"] = listener
    return flat


def normalize_gateway_text(text: str, raw_ref: str, provenance_map=None, insights=False, known_action_ids=None) -> dict:
    """Gateway pod log text (or span-export JSON lines) -> {records, sightings, rejects, background}.

    `raw_ref` is the capture's path inside the snapshot (`raw/gateway/<file>`); it goes into source.refs.
    `insights=True`: the lines are the aws-spans collector's Logs Insights rows (@message JSON, D3); each is
    flattened first, and the sha256 in source.refs is still the sha of the RAW line."""
    records, sightings, rejects, background = [], [], [], 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        s = line.strip()
        if s.startswith("{"):
            try:
                doc = json.loads(s)
            except ValueError:
                rejects.append({"ref": "%s:%d" % (raw_ref, lineno), "why": "not JSON"})
                continue
            if insights:
                doc = insights_row_to_flat(doc)
            kv = dict((k, str(v)) for k, v in doc.items() if v is not None)
            kv["_ts"] = _utc6(kv.get("ts") or kv.get("_ts") or "")
        else:
            kv = parse_gateway_line(line)
        if kv is None:
            continue
        rec, sighting, why = _gateway_record(kv, raw_ref, lineno, sha256_text(line.rstrip("\n")), provenance_map,
                                             known_action_ids)
        if sighting:
            sightings.append(sighting)
        if rec is None:
            if why == "background":
                background += 1
            elif why:
                rejects.append({"ref": "%s:%d" % (raw_ref, lineno), "why": why})
            continue
        errs = _rec.validate_record(rec)
        if errs:
            rejects.append({"ref": "%s:%d" % (raw_ref, lineno), "why": "; ".join(errs[:3])})
        else:
            records.append(rec)
    return {"records": records, "sightings": sightings, "rejects": rejects, "background": background}


# ---- AWS InvokeAgentRuntime records -------------------------------------------------------------

def _baggage_cid(baggage: str):
    from urllib.parse import unquote
    for part in (baggage or "").split(","):
        key, _, val = part.strip().partition("=")
        if key.strip() == BAGGAGE_KEY:
            return unquote(val.split(";")[0].strip())
    return None


def normalize_invocation_text(text: str, raw_ref: str, provenance_map=None) -> dict:
    """aict-invocations JSON lines (a bare event, or a CloudWatch row whose `message` is the event JSON)."""
    records, sightings, rejects = [], [], []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
            if isinstance(ev, dict) and isinstance(ev.get("message"), str):
                ev = json.loads(ev["message"])
        except ValueError:
            rejects.append({"ref": "%s:%d" % (raw_ref, lineno), "why": "not JSON"})
            continue
        if not isinstance(ev, dict) or ev.get("eventName") != "InvokeAgentRuntime":
            continue
        resp = ev.get("responseElements") or {}
        at = _utc6(ev.get("eventTime") or "")
        arn = ((ev.get("resources") or [{}])[0] or {}).get("ARN")
        if at is None:
            rejects.append({"ref": "%s:%d" % (raw_ref, lineno), "why": "no usable eventTime"})
            continue
        session = resp.get("runtimeSessionId") or None
        cid = _baggage_cid(resp.get("baggage") or "")
        if not cid and session:
            try:
                cid = _ids.session_cid(session)
            except ValueError:
                cid = None
        trace = None
        try:
            trace = _ids.parse_traceparent(resp.get("traceParent") or "")["trace_id"]
        except (ValueError, KeyError, TypeError):
            trace = None
        runtime = (arn or "runtime").rsplit("/", 1)[-1] or "runtime"
        if not cid or not _ids.is_valid_run_id(cid):
            if cid and not _ids.is_valid_run_id(cid):
                sightings.append({"run_id": cid, "source": "aws-invocation", "ts": at,
                                  "tokens_in": None, "tokens_out": None})
                continue
            cid = _ids.unattributed_cid(runtime, at)
        sightings.append({"run_id": cid, "source": "aws-invocation", "ts": at, "tokens_in": None, "tokens_out": None})
        line_sha = sha256_text(line.rstrip("\n"))
        key = ev.get("requestID") or line_sha
        prov = (provenance_map or {}).get(cid) or ("UNATTRIBUTED" if cid.startswith("unattributed:")
                                                   else family_provenance(cid))
        rec = _build("observation", _rec.observation_record_id(SYSTEM_AWS_INVOCATION, key), cid, at,
                     "aws-cloudtrail",
                     "AWS InvokeAgentRuntime record; eventTime is the end of the call, status %s"
                     % (resp.get("statusCode"),),
                     prov, ["raw:" + raw_ref, "line:%d" % lineno, "sha256:" + line_sha],
                     "an AWS invocation record carries no control binding",
                     **{"trace.id": trace, "runtime.arn": arn, "runtime.session_id": session,
                        "aws.request_id": ev.get("requestID"), "outcome.http_status": _int(resp.get("statusCode"))})
        errs = _rec.validate_record(rec)
        if errs:
            rejects.append({"ref": "%s:%d" % (raw_ref, lineno), "why": "; ".join(errs[:3])})
        else:
            records.append(rec)
    return {"records": records, "sightings": sightings, "rejects": rejects, "background": 0}


def sort_records(records) -> list:
    """Stable order: observed/emitted time, then record id."""
    return sorted(records, key=lambda r: (r.get("ts") or "", r.get("record_id") or ""))
