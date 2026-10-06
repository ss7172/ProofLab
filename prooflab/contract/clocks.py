"""Clocks and timestamps (ARCH §4.2 "Time"). Stdlib, Python 3.9.

Every record names the clock that stamped it (`emitted.clock` / `observed.clock`). Timestamps are
UTC ISO-8601 with a trailing "Z" and millisecond precision when we mint them; parsing accepts 0-6
fractional digits (Arth's console `utc` pattern).
"""
from __future__ import annotations

import datetime as _dt
import re

CLOCKS = (
    "agent-runtime", "script-host", "evaluator-host", "gateway", "pdp", "authz", "audit-store",
    "cloudwatch-ingest", "aws-cloudtrail", "servicenow", "s3",
)

UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$")


def is_utc(value) -> bool:
    """True for a full UTC timestamp string ending in Z (0-6 fractional digits)."""
    if not isinstance(value, str) or not UTC_RE.match(value):
        return False
    try:
        parse_utc(value)
    except ValueError:
        return False
    return True


def parse_utc(value: str) -> _dt.datetime:
    """Parse a contract timestamp into an aware UTC datetime. Raises ValueError."""
    if not isinstance(value, str) or not UTC_RE.match(value):
        raise ValueError("not a UTC timestamp: %r" % (value,))
    body = value[:-1]
    if "." in body:
        head, frac = body.split(".", 1)
        frac = (frac + "000000")[:6]
        body = head + "." + frac
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S"
    return _dt.datetime.strptime(body, fmt).replace(tzinfo=_dt.timezone.utc)


def format_utc(moment: _dt.datetime) -> str:
    """Aware or naive-UTC datetime -> 'YYYY-MM-DDTHH:MM:SS.mmmZ'."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (moment.microsecond // 1000)


def compact(value: str) -> str:
    """'2026-10-06T04:31:12.123Z' -> '20261006T043112123Z' (the record_id prefix)."""
    moment = parse_utc(value)
    return moment.strftime("%Y%m%dT%H%M%S") + "%03dZ" % (moment.microsecond // 1000)


def now_utc() -> str:
    """The current time as a contract timestamp. Never call this from an evaluator (they are pure)."""
    return format_utc(_dt.datetime.now(_dt.timezone.utc))
