"""Run ids (CIDs), runtime session ids and W3C propagation (ARCH §3.2, §4.2 run.id, §7.2). Stdlib, 3.9.

The run id IS the CID (`run.id` == `correlation_id`). Families:

  ifabric-run-<epoch>-<hex>          every run of our trio (subject, pilot, baseline)
  ifabric-test-<epoch>-<hex>         test traffic
  ifabric-adv-<epoch>-<hex>          adversarial runs
  ifabric-assure-<epoch>-<hex>       reserved for the Assurance agent (G-03)
  ifabric-unenveloped-<epoch>-<hex>  minted by an agent invoked with no envelope (derived, §7.1)
  unattributed:<runtime>:<eventTime> pseudo-CID for an invocation no handoff.sent matches (derived)
  fault-...                          the reference trio's earlier, unassessed runs (never ours)
  unresolved:<trace id>              correlation_id when the run is unknown

Propagation on every invocation (§7.2): baggage `modaas-correlation-id=<CID>`, one run `traceparent`,
and `runtimeSessionId` = `<CID>-<32 hex>`. Handoff ids are `<CID>:h<n>`.
"""
from __future__ import annotations

import binascii
import os
import re
from urllib.parse import quote, unquote

CID_FAMILIES = ("ifabric-run", "ifabric-test", "ifabric-adv", "ifabric-assure", "ifabric-unenveloped")
MINTABLE_FAMILIES = ("ifabric-run", "ifabric-test", "ifabric-adv", "ifabric-assure")
BAGGAGE_CID_KEY = "modaas-correlation-id"
CID_HEX_LEN = 6

_CID_RE = re.compile(r"^(ifabric-(?:run|test|adv|assure|unenveloped))-([0-9]{9,11})-([0-9a-f]{4,32})$")
_UNATTRIBUTED_RE = re.compile(r"^unattributed:[A-Za-z0-9_.\-]+:\S+$")
_FAULT_RE = re.compile(r"^fault-\S+$")
_UNRESOLVED_RE = re.compile(r"^unresolved:[0-9a-f]{32}$")
_SESSION_RE = re.compile(r"^(?P<cid>.+)-(?P<hex>[0-9a-f]{32})$")
_TRACEPARENT_RE = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
_HANDOFF_RE = re.compile(r"^(?P<cid>.+):h(?P<n>[0-9]+)$")


def _hex(nbytes: int) -> str:
    return binascii.hexlify(os.urandom(nbytes)).decode("ascii")


def mint_cid(family: str, epoch: int, hex_part: "str | None" = None) -> str:
    """Mint a CID. `epoch` is passed in (no hidden clock); `hex_part` defaults to 6 random hex."""
    if family not in MINTABLE_FAMILIES and family != "ifabric-unenveloped":
        raise ValueError("unknown CID family: %r" % (family,))
    if hex_part is None:
        hex_part = _hex(CID_HEX_LEN // 2)
    cid = "%s-%d-%s" % (family, int(epoch), hex_part)
    if not _CID_RE.match(cid):
        raise ValueError("malformed CID: %r" % (cid,))
    return cid


def parse_cid(cid: str) -> dict:
    """Split an ifabric CID into {family, epoch, hex}. Raises ValueError for any other id."""
    m = _CID_RE.match(cid or "")
    if not m:
        raise ValueError("not an ifabric CID: %r" % (cid,))
    return {"family": m.group(1), "epoch": int(m.group(2)), "hex": m.group(3)}


def cid_family(run_id: str) -> str:
    """The family of any valid run id: an ifabric family, 'unattributed', 'fault' or 'unresolved'."""
    if _CID_RE.match(run_id or ""):
        return _CID_RE.match(run_id).group(1)
    if _UNATTRIBUTED_RE.match(run_id or ""):
        return "unattributed"
    if _FAULT_RE.match(run_id or ""):
        return "fault"
    if _UNRESOLVED_RE.match(run_id or ""):
        return "unresolved"
    raise ValueError("not a valid run id: %r" % (run_id,))


def is_valid_run_id(run_id) -> bool:
    try:
        cid_family(run_id)
    except (ValueError, TypeError):
        return False
    return True


def is_ours(run_id: str) -> bool:
    """True for our trio's / tools' CIDs (never a reference-trio `fault-` run)."""
    return bool(_CID_RE.match(run_id or ""))


def unattributed_cid(runtime: str, event_time: str) -> str:
    cid = "unattributed:%s:%s" % (runtime, event_time)
    if not _UNATTRIBUTED_RE.match(cid):
        raise ValueError("malformed unattributed pseudo-CID: %r" % (cid,))
    return cid


def unresolved_correlation_id(trace_id: str) -> str:
    cid = "unresolved:%s" % (trace_id,)
    if not _UNRESOLVED_RE.match(cid):
        raise ValueError("trace id must be 32 lowercase hex: %r" % (trace_id,))
    return cid


# --- runtime session id -------------------------------------------------------------------------

def mint_session_id(cid: str, hex32: "str | None" = None) -> str:
    """`runtimeSessionId` = `<CID>-<32 hex>` (§7.2)."""
    parse_cid(cid)
    hex32 = hex32 if hex32 is not None else _hex(16)
    if not re.match(r"^[0-9a-f]{32}$", hex32):
        raise ValueError("session suffix must be 32 lowercase hex")
    return "%s-%s" % (cid, hex32)


def session_cid(session_id: str) -> str:
    """The CID a runtime session id was minted from (exact join key 5, §3.6)."""
    m = _SESSION_RE.match(session_id or "")
    if not m:
        raise ValueError("not a runtime session id: %r" % (session_id,))
    parse_cid(m.group("cid"))
    return m.group("cid")


# --- handoff ids --------------------------------------------------------------------------------

def handoff_id(cid: str, n: int) -> str:
    """`<CID>:h<n>`, n >= 1 (the envelope's handoff_id)."""
    if int(n) < 1:
        raise ValueError("handoff number starts at 1")
    cid_family(cid)
    return "%s:h%d" % (cid, int(n))


def parse_handoff_id(value: str) -> "tuple":
    m = _HANDOFF_RE.match(value or "")
    if not m:
        raise ValueError("not a handoff id: %r" % (value,))
    cid_family(m.group("cid"))
    return m.group("cid"), int(m.group("n"))


# --- W3C trace context --------------------------------------------------------------------------

def mint_traceparent(trace_id: "str | None" = None, span_id: "str | None" = None, sampled: bool = True) -> str:
    trace_id = trace_id or _hex(16)
    span_id = span_id or _hex(8)
    value = "00-%s-%s-%s" % (trace_id, span_id, "01" if sampled else "00")
    parse_traceparent(value)
    return value


def parse_traceparent(value: str) -> dict:
    """W3C traceparent -> {version, trace_id, span_id, flags}. Rejects all-zero ids and version ff."""
    m = _TRACEPARENT_RE.match((value or "").strip())
    if not m:
        raise ValueError("malformed traceparent: %r" % (value,))
    version, trace_id, span_id, flags = m.groups()
    if version == "ff" or trace_id == "0" * 32 or span_id == "0" * 16:
        raise ValueError("invalid traceparent: %r" % (value,))
    return {"version": version, "trace_id": trace_id, "span_id": span_id, "flags": flags}


# --- W3C baggage --------------------------------------------------------------------------------

def format_baggage(items: dict) -> str:
    """{key: value} -> 'k1=v1,k2=v2' (keys sorted, values percent-encoded)."""
    parts = []
    for key in sorted(items):
        if not re.match(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$", key):
            raise ValueError("invalid baggage key: %r" % (key,))
        parts.append("%s=%s" % (key, quote(str(items[key]), safe="")))
    return ",".join(parts)


def parse_baggage(header: str) -> dict:
    """'k=v;prop,k2=v2' -> {k: v, k2: v2}. Properties after ';' are dropped; malformed members skipped."""
    out = {}
    for member in (header or "").split(","):
        member = member.split(";", 1)[0].strip()
        if "=" not in member:
            continue
        key, value = member.split("=", 1)
        key = key.strip()
        if key:
            out[key] = unquote(value.strip())
    return out


def cid_baggage(cid: str) -> str:
    """The baggage our script always sends: `modaas-correlation-id=<CID>`."""
    cid_family(cid)
    return format_baggage({BAGGAGE_CID_KEY: cid})


def cid_from_baggage(header: str) -> "str | None":
    value = parse_baggage(header).get(BAGGAGE_CID_KEY)
    return value if value and is_valid_run_id(value) else None


def propagation_headers(cid: str, traceparent: str) -> dict:
    """The headers one invocation carries: baggage + traceparent (§7.2)."""
    parse_traceparent(traceparent)
    return {"baggage": cid_baggage(cid), "traceparent": traceparent}
