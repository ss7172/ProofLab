"""The watcher: C9's near-real-time loop host, MON-01, ExpiredToken supervision, the live feed (T4.6).

Stdlib, Python 3.9. Nothing here judges. Each cycle, per run id (never a full ledger read; the ledger server is
single-threaded and parses the whole file on a GET, so only `get_by_cid` is ever called):
  1. read the run's records, write a feed event for each new one (the feed dedupes by record id)
  2. run MON-01 over them; a finding not yet reported is written as a `finding` event and handed to `on_finding`
  3. run the injected hooks (the C9 window assessor and the response poller `check --cutoff` plug in here: they are
     other PRs' code, called with the same clock) and write the events they return
A heartbeat is written every `heartbeat_s` whatever the poll interval, so a stopped watcher reads STALE.
A source error naming ExpiredToken writes a `stream-error` event and a monitoring-gap finding and stops the loop:
it never fails silently (ARCH 7, D11).
"""
from __future__ import annotations

import datetime as _dt
import time

from prooflab.contract import clocks, finding as _finding
from prooflab.watch import feed as _feed
from prooflab.watch import rules
from prooflab.contract import verdicts as _V  # the one verdict vocabulary (ARCH §4.3)

MIN_POLL_S = 3.0
DEFAULT_INTERVAL_S = 30.0   # the OC-20 measurement sets the real value (--interval); this is only the fallback
EXPIRED_MARKERS = ("ExpiredToken", "ExpiredTokenException", "RequestExpired")


def is_expired(exc):
    text = "%s %s" % (type(exc).__name__, exc)
    return any(marker in text for marker in EXPIRED_MARKERS)


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc)


class Watcher:
    def __init__(self, source, live_feed, run_ids, now=utc_now, sleep=time.sleep, interval_s=DEFAULT_INTERVAL_S,
                 heartbeat_s=_feed.HEARTBEAT_S, on_finding=None, hooks=()):
        self.source = source
        self.feed = live_feed
        self._run_ids = run_ids
        self.now = now
        self.sleep = sleep
        self.interval_s = max(float(interval_s), MIN_POLL_S)
        self.heartbeat_s = float(heartbeat_s)
        self.on_finding = on_finding
        self.hooks = list(hooks)
        self.stopped = False
        self.findings = []
        self._reported = set()
        self._last_heartbeat = None

    # ---- helpers --------------------------------------------------------------------------------
    def _ts(self):
        return clocks.format_utc(self.now())

    def run_ids(self):
        ids = self._run_ids() if callable(self._run_ids) else self._run_ids
        return list(ids)

    def heartbeat(self):
        ts = self._ts()
        self.feed.append(_feed.synthetic_event("heartbeat", ts, detail="watcher alive",
                                               interval_s=self.interval_s, heartbeat_s=self.heartbeat_s))
        self._last_heartbeat = self.now()

    def _stream_error(self, exc, run_id=None):
        ts = self._ts()
        reason = "%s: %s" % (type(exc).__name__, str(exc)[:200])
        self.feed.append(_feed.synthetic_event("stream-error", ts, run_id=run_id, detail=reason))
        if is_expired(exc):
            gap = _finding.make_finding(
                "NONE", "WATCH-SUPERVISOR", "watch@1", "interval", "watch:" + ts, _V.INDETERMINATE,
                "monitoring gap: credentials expired, the watcher stopped (%s)" % reason, ts,
                evidence=[], kind="monitoring-gap")
            self._report(gap)
            self.stopped = True

    def _report(self, finding):
        key = (_finding.finding_id(finding), tuple(finding.get("evidence") or ()))
        if key in self._reported:
            return
        self._reported.add(key)
        self.findings.append(finding)
        self.feed.append(_feed.synthetic_event(
            "finding", self._ts(), run_id=finding.get("scope_id") if finding.get("scope_kind") == "run" else None,
            verdict=finding.get("verdict"), control=finding.get("control_ref"), detail=finding.get("summary"),
            finding_id=_finding.finding_id(finding), finding_kind=finding.get("kind")))
        if self.on_finding is not None:
            self.on_finding(finding)

    # ---- one cycle ------------------------------------------------------------------------------
    def poll_once(self):
        for cid in self.run_ids():
            if self.stopped:
                return
            try:
                rows = self.source.get_by_cid(cid)
            except Exception as exc:  # a failed read is an event, not a crash
                self._stream_error(exc, cid)
                continue
            written = self._ts()
            for rec in rows:
                ev = _feed.event_from_record(rec, written)
                if ev is not None:
                    self.feed.append(ev)
            for finding in rules.mon01(rows, written):
                self._report(finding)
        for hook in self.hooks:
            if self.stopped:
                return
            try:
                for ev in hook(self.now()) or ():
                    self.feed.append(ev)
            except Exception as exc:
                self._stream_error(exc)

    def _heartbeat_due(self):
        return self._last_heartbeat is None or \
            (self.now() - self._last_heartbeat).total_seconds() >= self.heartbeat_s

    def run(self, max_cycles=None):
        """Loop until stopped (expired credentials) or `max_cycles` polls. Sleeps in slices no longer than the
        heartbeat period, so the heartbeat never waits on the poll interval."""
        cycles = 0
        next_poll = self.now()
        while not self.stopped and (max_cycles is None or cycles < max_cycles):
            if self._heartbeat_due():
                self.heartbeat()
            if self.now() >= next_poll:
                self.poll_once()
                cycles += 1
                next_poll = self.now() + _dt.timedelta(seconds=self.interval_s)
                if max_cycles is not None and cycles >= max_cycles:
                    break
            if not self.stopped:
                self.sleep(min(self.heartbeat_s, self.interval_s))
        return cycles
