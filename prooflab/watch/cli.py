"""`prooflab watch`: the live feed, MON-01 and the poll hooks. Stdlib, Python 3.9.

  watch --run-id CID [--run-id ...] [--feed live/events.jsonl] [--interval S] [--once]
        [--base-url URL --token-env NAME]      the ledger token is read from the named variable, never argv
  watch --status [--feed PATH]                 LIVE | STALE | NO_FEED; exit 0 / 1 / 1
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from prooflab.watch import feed as _feed
from prooflab.watch import watcher as _watcher

DEFAULT_FEED = "live/events.jsonl"


def ledger_source(args):
    """The live ledger client (imported lazily: PR-13a). Used only by the real CLI; tests pass fakes."""
    if not args.base_url or not args.token_env:
        raise SystemExit("--base-url and --token-env are required to read the ledger")
    from prooflab.store.ledger_client import LedgerClient
    return LedgerClient.from_env(args.base_url, args.token_env)


def main(argv=None, source_factory=None, now=_watcher.utc_now, sleep=time.sleep, hooks=(), out=None):
    p = argparse.ArgumentParser(prog="prooflab watch", description="Write the live index and run MON-01.")
    p.add_argument("--feed", default=DEFAULT_FEED)
    p.add_argument("--run-id", action="append", default=[])
    p.add_argument("--run-ids-file", help="one run id per line, re-read each cycle")
    p.add_argument("--interval", type=float, default=_watcher.DEFAULT_INTERVAL_S,
                   help="seconds between polls (OC-20 sets it; minimum %.0f)" % _watcher.MIN_POLL_S)
    p.add_argument("--once", action="store_true", help="one cycle and exit")
    p.add_argument("--status", action="store_true", help="print the feed's LIVE/STALE state and exit")
    p.add_argument("--base-url")
    p.add_argument("--token-env")
    args = p.parse_args(argv)
    out = out or sys.stdout
    if args.status:
        st = _feed.staleness(args.feed, now())
        out.write(json.dumps(st, sort_keys=True) + "\n")
        return 0 if st["state"] == "LIVE" else 1

    def run_ids():
        ids = list(args.run_id)
        if args.run_ids_file:
            try:
                with open(args.run_ids_file, "r", encoding="utf-8") as fh:
                    ids += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
            except OSError:
                pass
        return ids

    if not run_ids() and not args.run_ids_file:
        p.error("give --run-id or --run-ids-file")
    source = source_factory(args) if source_factory else ledger_source(args)

    def show(finding):
        out.write("finding %s %s\n" % (finding["control_ref"], finding["summary"]))

    w = _watcher.Watcher(source, _feed.LiveFeed(args.feed), run_ids, now=now, sleep=sleep, interval_s=args.interval,
                         on_finding=show, hooks=hooks)
    try:
        w.heartbeat()
        w.run(max_cycles=1 if args.once else None)
    except KeyboardInterrupt:
        return 0
    return 4 if w.stopped else 0
