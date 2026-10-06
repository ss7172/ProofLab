"""EP-2: the post-run replay of the c16 core (ARCH 3.1 EP-2, 3.4, 11.1; I-21). Stdlib, Python 3.9.

After a run, the run's model-call spans (an aws/spans capture, read from a file: no AWS call here) are put in
gateway order. For each call ONE C16Question is built (committed = the actual tokens of the calls before it,
reserved = 0, bound = this call's actual input + output, bound_basis "actual") and answered by the SAME
`c16_core.decide_inline` that EP-1 calls inline, with the run's pin. Each answer becomes a `decision` record
(ep.id EP-2, ep.transport pull). Records only: nothing is executed, blocked or halted here (`inline.action` is
the core's answer, recorded as such). This module never imports `evaluate` (only adapters/runtime/model_call.py
may) and holds no threshold: every limit comes from the pin.

Verb: `python3 -m prooflab postrun --cid <CID> --spans <file> --pin <file>` (PR-01's dispatcher routes to main).
Span capture formats read (all tolerant): JSON array, JSON object with rows/results/spans, or JSON lines; a row
is a flat dict with dotted `attributes.*` keys, a nested {"attributes": {...}} dict, or a Logs Insights row
[{"field": ..., "value": ...}, ...].
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys

# The one coupling site to the contract and the core (PR-01, PR-02).
from prooflab.contract import clocks as _clocks
from prooflab.contract import record as _rec
from prooflab.contract.c16_hook import decision_record as _decision_record
from prooflab.evaluators import c16_core as _core

EMITTER_NAME = "adapters.postrun.c16_replay"
EMITTER_VERSION = "1.0"
EP_ID = "EP-2"
EP_KIND = "managed gateway log, after the run (spend adapter over aws/spans)"
EP_RESPONSIBLE = "team iFabric"
DEFAULT_SHA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))), "register", "c16_core.sha256")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

_IN = ("attributes.gen_ai.usage.input_tokens", "gen_ai.usage.input_tokens")
_OUT = ("attributes.gen_ai.usage.output_tokens", "gen_ai.usage.output_tokens")
_ACTION = ("attributes.modaas.action_id", "modaas.action_id")
_RUN = ("attributes.modaas.run_id", "modaas.run_id")
_LISTENER = ("attributes.listener", "listener")
_STATUS = ("attributes.http.status", "http.status")
_START = ("startTimeUnixNano", "attributes.startTimeUnixNano")
_END = ("endTimeUnixNano", "attributes.endTimeUnixNano")
_TRACE = ("traceId", "trace_id", "attributes.modaas.trace_id", "modaas.trace_id")
_SPAN = ("spanId", "span_id", "span.id")


class ReplayError(ValueError):
    """The capture, pin or core hash cannot be used; nothing is recorded (fail closed)."""


# --- reading the capture ------------------------------------------------------------------------

def _flatten(obj, prefix="", out=None):
    out = {} if out is None else out
    for k, v in obj.items():
        key = prefix + str(k)
        if isinstance(v, dict):
            _flatten(v, key + ".", out)
        else:
            out[key] = v
    return out


def _row(raw):
    if isinstance(raw, dict):
        msg = raw.get("@message")
        if isinstance(msg, str):       # D3: a Logs Insights row; the span is the JSON in @message
            try:
                span = json.loads(msg)
            except ValueError:
                span = None
            if isinstance(span, dict):
                raw = dict((k, v) for k, v in raw.items() if k != "@message")
                raw.update(span)
        flat = _flatten(raw)
        # also expose nested {"attributes": {"modaas.run_id": ...}} as dotted keys either way
        return flat
    if isinstance(raw, list) and all(isinstance(c, dict) and "field" in c for c in raw):
        return dict((c["field"], c.get("value")) for c in raw)
    raise ReplayError("unreadable span row")


def load_rows(text):
    """The rows of a capture file's text (JSON array / object with rows / JSON lines)."""
    text = text.strip()
    if not text:
        return []
    try:
        doc = json.loads(text)
    except ValueError:
        doc = [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(doc, dict):
        for key in ("rows", "results", "spans"):
            if isinstance(doc.get(key), list):
                doc = doc[key]
                break
        else:
            doc = [doc]
    if not isinstance(doc, list):
        raise ReplayError("capture is not a list of rows")
    return [_row(r) for r in doc]


def _first(row, keys):
    for k in keys:
        v = row.get(k)
        if v is not None and v != "":
            return v
    return None


def _int(v):
    try:
        if isinstance(v, bool):
            return None
        f = float(v)
        return int(f) if f == int(f) and f >= 0 else None
    except (TypeError, ValueError):
        return None


def model_call_spans(rows, cid):
    """One dict per model call of run `cid`, in gateway order, deduplicated by action id.

    A row counts when its listener is llm (or absent while it carries gen_ai usage) and its run id is `cid`
    (or absent). A model-call row without readable tokens is an error: the replay cannot be complete.
    """
    calls, seen = [], set()
    for i, row in enumerate(rows):
        listener = _first(row, _LISTENER)
        has_usage = _first(row, _IN) is not None or _first(row, _OUT) is not None
        if listener is not None and listener != "llm":
            continue
        if listener is None and not has_usage:
            continue
        run = _first(row, _RUN)
        if run is not None and run != cid:
            continue
        action = _first(row, _ACTION)
        if action is None:
            raise ReplayError("model-call span %d has no action id" % i)
        if action in seen:
            continue
        seen.add(action)
        t_in, t_out = _int(_first(row, _IN)), _int(_first(row, _OUT))
        if t_in is None or t_out is None:
            raise ReplayError("model-call span %s has no readable token counts" % action)
        start, end = _int(_first(row, _START)), _int(_first(row, _END))
        stamp = _first(row, ("@timestamp",))
        calls.append({"action_id": str(action), "tokens_in": t_in, "tokens_out": t_out, "start": start,
                      "end": end, "stamp": stamp, "trace_id": _first(row, _TRACE), "span_id": _first(row, _SPAN),
                      "http_status": _int(_first(row, _STATUS)), "order": i})
    calls.sort(key=lambda c: (c["start"] if c["start"] is not None else float("inf"), str(c["stamp"] or ""),
                              c["order"]))
    return calls


# --- pin and core hash --------------------------------------------------------------------------

def load_pin(text, expected_sha256=None):
    """(PinnedC16, pin_sha256) from the pin's canonical JSON text; sha256 over the text without trailing newline."""
    raw = text.strip().encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and sha != expected_sha256.strip().lower():
        raise ReplayError("pin sha256 mismatch")
    try:
        return _core.PinnedC16.from_dict(json.loads(raw.decode("utf-8")), sha), sha
    except (ValueError, TypeError) as exc:
        raise ReplayError("invalid pin: %s" % exc)


def read_core_sha(path=DEFAULT_SHA_FILE):
    """The register's recorded sha256 of c16_core.py (the content of register/c16_core.sha256)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            token = fh.read().split()[0].lower()
    except (OSError, IndexError):
        raise ReplayError("cannot read the core sha256 file: %s" % path)
    if not _SHA_RE.match(token):
        raise ReplayError("core sha256 file does not hold a sha256")
    return token


def loaded_core_sha():
    with open(_core.__file__, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# --- the replay ---------------------------------------------------------------------------------

def _ms_stamp(nanos):
    if nanos is None:
        return None
    return _clocks.format_utc(_dt.datetime.fromtimestamp(nanos // 1000000 / 1000.0, _dt.timezone.utc))


def replay(cid, calls, pin, core_sha256, now=None, tier=None, provenance="REPLAY", owner=None):
    """The EP-2 `decision` records, one per call in `calls`, from `decide_inline` (never executed)."""
    now = now or _clocks.now_utc()
    tier = tier or pin.default_tier
    records, committed = [], 0
    for seq, call in enumerate(calls):
        bound = call["tokens_in"] + call["tokens_out"]
        q = _core.C16Question(cid, tier, committed, 0, bound, "actual")
        decision = _core.decide_inline(q, pin, core_sha256)
        digest = hashlib.sha256(("%s|%s|%d" % (cid, call["action_id"], seq)).encode("utf-8")).hexdigest()
        observed = _ms_stamp(call["end"] if call["end"] is not None else call["start"])
        ctx = {
            "run.id": cid, "call.id": call["action_id"], "trace.id": call["trace_id"], "seq.in_stream": seq,
            "ep.id": EP_ID, "ep.kind": EP_KIND, "ep.transport": "pull", "ep.responsible": EP_RESPONSIBLE,
            "control.owner": owner, "emitted.at": now, "emitted.clock": "evaluator-host",
            "provenance": provenance, "authorship": "ASSURANCE",
            "emitter": "%s@%s+%s" % (EMITTER_NAME, EMITTER_VERSION, core_sha256[:7]),
            "record_id": _rec.emitted_record_id(now, "ep2", digest[:8]),
            "measured.source": "gateway-figure-of-record",
            "tokens.in": call["tokens_in"], "tokens.out": call["tokens_out"],
            "source.refs": ["gateway-span:%s" % call["action_id"], "pin:sha256-%s" % pin.pin_sha256],
            "detail": "EP-2 replay: action %s (not executed: post-run placement)" % decision.action,
            "outcome.real": None,
            "null_reasons": {"outcome.real": "post-run placement: not executed",
                             "outcome.platform_decision": "no gateway request was made by this record",
                             "actor.id": "the gateway span names no agent",
                             "control.owner": "not set for this replay"},
        }
        if observed:
            ctx["observed.at"], ctx["observed.clock"] = observed, "gateway"
        if call["http_status"] is not None:
            ctx["outcome.http_status"] = call["http_status"]
        if owner is not None:
            ctx["null_reasons"].pop("control.owner")
        ctx = dict((k, v) for k, v in ctx.items() if v is not None or k in ("trace.id",))
        if ctx.get("trace.id") is None:
            ctx["null_reasons"]["trace.id"] = "the span row carries no trace id"
        rec = _decision_record(decision, ctx)
        errors = _rec.validate_record(rec)
        if errors:
            raise ReplayError("record for %s invalid: %s" % (call["action_id"], "; ".join(errors)))
        records.append(rec)
        committed += bound
    return records


def main(argv=None, out=None):
    ap = argparse.ArgumentParser(prog="prooflab postrun", description="EP-2: replay the c16 core over a run's spans")
    ap.add_argument("--cid", required=True)
    ap.add_argument("--spans", required=True, help="aws/spans capture file (JSON, rows object or JSON lines)")
    ap.add_argument("--pin", required=True, help="the run's ifabric.pin/1 canonical JSON file")
    ap.add_argument("--pin-sha256", help="expected sha256 of the pin (IFABRIC_PIN_SHA256)")
    ap.add_argument("--sha-file", default=DEFAULT_SHA_FILE, help="register/c16_core.sha256")
    ap.add_argument("--tier", help="tier of the run (default: the pin's default tier)")
    ap.add_argument("--provenance", default="REPLAY")
    ap.add_argument("--owner")
    ap.add_argument("--out", help="write JSON lines here (default stdout)")
    args = ap.parse_args(argv)
    try:
        with open(args.spans, "r", encoding="utf-8") as fh:
            calls = model_call_spans(load_rows(fh.read()), args.cid)
        with open(args.pin, "r", encoding="utf-8") as fh:
            pin, _ = load_pin(fh.read(), args.pin_sha256)
        sha = read_core_sha(args.sha_file)
        if sha != loaded_core_sha():
            raise ReplayError("c16_core.py does not match register/c16_core.sha256")
        if not calls:
            raise ReplayError("no model-call spans for %s: INDETERMINATE (monitoring gap), nothing recorded"
                              % args.cid)
        records = replay(args.cid, calls, pin, sha, tier=args.tier, provenance=args.provenance, owner=args.owner)
    except (ReplayError, OSError, ValueError) as exc:
        sys.stderr.write("postrun: %s\n" % exc)
        return 2
    lines = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(lines)
    else:
        (out or sys.stdout).write(lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
