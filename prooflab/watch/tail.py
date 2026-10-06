"""`prooflab tail`: follow a run's records as they land. Stdlib, Python 3.9.

Polls the ledger by CID (never a full read) no faster than MIN_POLL_S, whatever interval is asked for.
With --feed it follows `live/events.jsonl` instead and touches no ledger at all.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from prooflab.watch import feed as _feed
from prooflab.watch.watcher import MIN_POLL_S


class Tail:
    def __init__(self, source, run_ids, out, interval_s=MIN_POLL_S, monotonic=time.monotonic, sleep=time.sleep):
        self.source = source
        self.run_ids = list(run_ids)
        self.out = out
        self.interval_s = max(float(interval_s), MIN_POLL_S)
        self.monotonic = monotonic
        self.sleep = sleep
        self._seen = set()
        self._last_poll = None

    def poll_once(self):
        """One pass over every run id; prints a line per new record that is a feed event. Returns the count."""
        self._last_poll = self.monotonic()
        written = 0
        for cid in self.run_ids:
            for rec in self.source.get_by_cid(cid):
                rid = rec.get("record_id")
                if rid in self._seen:
                    continue
                self._seen.add(rid)
                ev = _feed.event_from_record(rec, rec.get("ts") or "")
                if ev is None:
                    continue
                self.out.write("%s %-9s %s %s %s\n" % (ev["at"] or "-", ev["kind"], ev["run_id"] or "-",
                                                      ev["verdict"] or "-", ev["detail"] or ""))
                written += 1
        return written

    def run(self, max_polls=None):
        polls = 0
        while max_polls is None or polls < max_polls:
            if self._last_poll is not None:
                wait = self.interval_s - (self.monotonic() - self._last_poll)
                if wait > 0:
                    self.sleep(wait)
            self.poll_once()
            polls += 1
        return polls


def tail_feed(path, out, offset=0):
    """Print the feed lines past `offset`; returns the new offset (the caller sleeps and calls again)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            fh.seek(offset)
            for line in fh:
                out.write(line)
            return fh.tell()
    except OSError:
        return offset


def main(argv=None, source_factory=None, sleep=time.sleep, out=None):
    p = argparse.ArgumentParser(prog="prooflab tail", description="Follow the live index or a run's ledger records.")
    p.add_argument("--feed", help="follow this live/events.jsonl (no ledger access)")
    p.add_argument("--run-id", action="append", default=[], help="a run id (CID); repeatable")
    p.add_argument("--interval", type=float, default=MIN_POLL_S, help="seconds between polls (minimum %.0f)" % MIN_POLL_S)
    p.add_argument("--base-url")
    p.add_argument("--token-env", help="NAME of the environment variable holding the ledger token")
    p.add_argument("--polls", type=int, default=None, help="stop after N polls (default: until interrupted)")
    args = p.parse_args(argv)
    out = out or sys.stdout
    interval = max(args.interval, MIN_POLL_S)
    try:
        if args.feed:
            offset, n = 0, 0
            while args.polls is None or n < args.polls:
                offset = tail_feed(args.feed, out, offset)
                n += 1
                if args.polls is None or n < args.polls:
                    sleep(interval)
            return 0
        if not args.run_id:
            p.error("--run-id is required unless --feed is given")
        if source_factory is None:
            from prooflab.watch.cli import ledger_source
            source = ledger_source(args)
        else:
            source = source_factory(args)
        Tail(source, args.run_id, out, interval_s=interval, sleep=sleep).run(args.polls)
        return 0
    except KeyboardInterrupt:
        return 0
