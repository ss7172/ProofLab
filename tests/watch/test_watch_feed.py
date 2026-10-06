import datetime as dt
import json
import os

import pytest

from prooflab.contract import clocks, finding as cfinding
from prooflab.watch import cli, feed, rules, tail, watcher

HERE = os.path.dirname(__file__)
RUN = "ifabric-run-1791260000-ab12cd"
T0 = dt.datetime(2026, 10, 6, 5, 0, 0, tzinfo=dt.timezone.utc)


def load(name):
    with open(os.path.join(HERE, "fixtures", name)) as fh:
        return json.load(fh)


class Clock:
    def __init__(self, start=T0):
        self.t = start

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += dt.timedelta(seconds=s)

    def mono(self):
        return (self.t - T0).total_seconds()


class FakeLedger:
    """Only get_by_cid exists: a full read would be an AttributeError, so the tests prove it never happens."""

    def __init__(self, by_cid):
        self.by_cid = by_cid
        self.calls = []

    def get_by_cid(self, cid):
        self.calls.append(cid)
        return list(self.by_cid.get(cid, []))


def make(tmp_path, rows, **kw):
    clock = Clock()
    ledger = FakeLedger({RUN: rows})
    live = feed.LiveFeed(str(tmp_path / "live" / "events.jsonl"))
    w = watcher.Watcher(ledger, live, [RUN], now=clock.now, sleep=clock.sleep, **kw)
    return w, live, clock, ledger


def test_event_kinds_all_covered(tmp_path):
    """Every kind of T4.6 appears: record-driven ones from the fixture, heartbeat and stream-error from the watcher."""
    w, live, clock, _ = make(tmp_path, load("every_kind.json"))
    w.heartbeat()
    w.poll_once()
    w.source = type("Boom", (), {"get_by_cid": lambda s, c: (_ for _ in ()).throw(OSError("link down"))})()
    w.poll_once()
    kinds = {e["kind"] for e in feed.read_events(live.path)}
    assert kinds == set(feed.EVENT_KINDS)
    assert all(e["label"] == "live index" for e in feed.read_events(live.path))
    assert feed.classify({"record_kind": "observation"}) is None


def test_feed_has_each_record_once_across_restart(tmp_path):
    w, live, clock, _ = make(tmp_path, load("every_kind.json"))
    w.poll_once()
    first = len(feed.read_events(live.path))
    w.poll_once()
    w2, live2, _, _ = make(tmp_path, load("every_kind.json"))
    w2.poll_once()
    assert len(feed.read_events(live.path)) == first


def test_stopped_watcher_reads_stale_within_30s(tmp_path):
    w, live, clock, _ = make(tmp_path, [])
    w.heartbeat()
    assert feed.staleness(live.path, clock.now())["state"] == "LIVE"
    clock.sleep(feed.STALE_AFTER_S - 1)
    assert feed.staleness(live.path, clock.now())["state"] == "LIVE"
    clock.sleep(1)
    st = feed.staleness(live.path, clock.now())
    assert st["state"] == "STALE" and st["age_s"] == feed.STALE_AFTER_S
    assert feed.staleness(str(tmp_path / "none.jsonl"), clock.now())["state"] == "NO_FEED"


def test_running_watcher_stays_live_and_stopped_goes_stale(tmp_path):
    w, live, clock, _ = make(tmp_path, [], interval_s=120)
    w.run(max_cycles=2)               # a 120 s poll interval: heartbeats keep the feed LIVE in between
    assert feed.staleness(live.path, clock.now())["state"] == "LIVE"
    beats = [e for e in feed.read_events(live.path) if e["kind"] == "heartbeat"]
    gaps = [(clocks.parse_utc(b["written_at"]) - clocks.parse_utc(a["written_at"])).total_seconds()
            for a, b in zip(beats, beats[1:])]
    assert gaps and max(gaps) <= feed.STALE_AFTER_S
    clock.sleep(feed.STALE_AFTER_S)    # the watcher stops: nothing writes any more
    assert feed.staleness(live.path, clock.now())["state"] == "STALE"


def test_tail_never_faster_than_3s_and_never_full_read(tmp_path):
    clock = Clock()
    ledger = FakeLedger({RUN: load("every_kind.json")})
    stamps = []
    orig = ledger.get_by_cid
    ledger.get_by_cid = lambda cid: (stamps.append(clock.mono()), orig(cid))[1]
    out = []
    t = tail.Tail(ledger, [RUN], type("O", (), {"write": lambda s, x: out.append(x)})(), interval_s=0.1,
                  monotonic=clock.mono, sleep=clock.sleep)
    t.run(max_polls=5)
    assert len(stamps) == 5
    assert min(b - a for a, b in zip(stamps, stamps[1:])) >= 3.0
    assert not hasattr(ledger, "get_all")
    assert len(out) == 11              # each event record printed once; the plain observation is not an event


def test_watcher_poll_interval_floor(tmp_path):
    w, _, _, _ = make(tmp_path, [], interval_s=0.5)
    assert w.interval_s == watcher.MIN_POLL_S


def test_mon01_block_in_assessed_run_is_a_finding(tmp_path):
    seen = []
    w, live, clock, ledger = make(tmp_path, load("assessed_run_block.json"), on_finding=seen.append)
    w.poll_once()
    w.poll_once()
    assert len(seen) == 1             # reported once across polls
    f = seen[0]
    assert (f["control_ref"], f["verdict"], f["scope_kind"], f["scope_id"]) == ("RAIL", "ESCALATED", "run", RUN)
    assert "X-02" in f["summary"] and f["evidence"] and cfinding.validate_finding(f) == []
    assert any(e["kind"] == "finding" and e["finding_id"] for e in feed.read_events(live.path))
    assert ledger.calls == [RUN, RUN]


def test_mon01_not_assessed_run_no_finding():
    rows = [dict(r, provenance="AUTHORIZED_TEST") for r in load("assessed_run_block.json")]
    assert rules.mon01(rows, "2026-10-06T05:00:00.000Z") == []


def test_mon01_egress_flag_and_quarantine():
    base = load("assessed_run_block.json")[0]
    flag = dict(base, record_id="x-flag", verdict="FLAG", **{"rail.id": "RT-03", "rail.version": "1",
                                                              "provenance": "AUTHORIZED_TEST"})
    quar = dict(base, record_id="x-quar", verdict="FLAG", **{"rail.id": "X-05", "inline.action": "quarantine"})
    out = rules.rail_findings([flag, quar], "2026-10-06T05:00:00.000Z")
    assert sorted(f["control_id"] for f in out) == ["RAIL-RT-03", "RAIL-X-05"]


def test_mon01_counts_mismatch_is_monitoring_gap():
    rows = load("assessed_run_block.json")
    rows = [r for r in rows if r["record_kind"] != "rail_decision"]   # the BLOCK record never arrived
    out = rules.counts_gaps(rows, "2026-10-06T05:00:00.000Z")
    assert len(out) == 1 and out[0]["kind"] == "monitoring-gap" and out[0]["verdict"] == "INDETERMINATE"
    assert rules.counts_gaps(load("assessed_run_block.json"), "2026-10-06T05:00:00.000Z") == []


def test_expired_token_stops_with_gap_and_stream_error(tmp_path):
    seen = []

    class Expired:
        def get_by_cid(self, cid):
            raise RuntimeError("ExpiredToken: the security token is expired")

    clock = Clock()
    live = feed.LiveFeed(str(tmp_path / "e.jsonl"))
    w = watcher.Watcher(Expired(), live, [RUN], now=clock.now, sleep=clock.sleep, on_finding=seen.append)
    assert w.run() == 1 and w.stopped
    kinds = [e["kind"] for e in feed.read_events(live.path)]
    assert "stream-error" in kinds and "finding" in kinds
    assert seen[0]["kind"] == "monitoring-gap"


def test_hook_events_are_written_and_hook_errors_do_not_crash(tmp_path):
    ok = lambda now: [feed.synthetic_event("window", clocks.format_utc(now), detail="c9 window")]
    bad = lambda now: 1 / 0
    w, live, _, _ = make(tmp_path, [], hooks=[ok, bad])
    w.poll_once()
    kinds = [e["kind"] for e in feed.read_events(live.path)]
    assert "window" in kinds and "stream-error" in kinds


def test_cli_once_and_status(tmp_path, capsys):
    clock = Clock()
    path = str(tmp_path / "live" / "events.jsonl")
    rc = cli.main(["--feed", path, "--run-id", RUN, "--once"],
                  source_factory=lambda a: FakeLedger({RUN: load("assessed_run_block.json")}),
                  now=clock.now, sleep=clock.sleep)
    assert rc == 0
    assert "finding RAIL" in capsys.readouterr().out
    assert cli.main(["--status", "--feed", path], now=clock.now) == 0
    clock.sleep(31)
    assert cli.main(["--status", "--feed", path], now=clock.now) == 1
    assert '"STALE"' in capsys.readouterr().out


def test_no_threshold_literals_or_secrets_in_watch_code():
    root = os.path.join(HERE, "..", "..", "prooflab", "watch")
    for name in os.listdir(root):
        if name.endswith(".py"):
            text = open(os.path.join(root, name)).read()
            assert "get_all" not in text.replace("never a full ledger read", "")
            for bad in ("cap_tier", "safety_ceiling", "300000", "X-Audit-Token"):
                assert bad not in text, (name, bad)
