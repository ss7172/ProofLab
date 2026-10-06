"""C9's inputs from one snapshot (ARCH 5.3, EP-11; D3). Stdlib, Python 3.9. No threshold is held here.

THE FIGURE OF RECORD is M1: the AWS-written AgentCore invocation `Latency` statistic Maximum per runtime per 60 s
datapoint (`AWS/Bedrock-AgentCore`, dimensions Resource + Operation=InvokeAgentRuntime + Name=<rt>::DEFAULT), with
`Errors` Sum. It is read from the captures under raw/agentcore-metrics/ in either shape the lane produces:

  * the EP-11 collector (agentcore_metrics.pull): raw/agentcore-metrics/<runtime name>/<Metric>-<Stat>-<t>.json =
    `aws cloudwatch get-metric-statistics` stdout ({"Label", "Datapoints": [{"Timestamp", "<Stat>"}]}), with its
    .capture.json sidecar (scope: metric, statistic, period, start, end; captured_at);
  * `aws cloudwatch get-metric-data` stdout ({"MetricDataResults": [{"Label": "<agent> <Metric> <Stat>",
    "Timestamps", "Values"}]}) or the ops lane's measure.py form ({"window": [s, e], "results": {"<agent> <Metric>
    <Stat>": {"points": [[t, v]]}}}); period 60 unless the document says otherwise ("period"); "captured_at" if given.

The per-invocation duration the orchestrator itself measured (EP-5 `handoff.received ... duration_ms=`) is shown as
a DIAGNOSTIC beside it, never as the figure of record: it is our testimony, M1 is AWS-written. A window whose
datapoints are missing stays INDETERMINATE (the evaluator's monitoring-gap rule), never healthy.

W2, per run and runtime (ARCH 5.3): the 60 s datapoints whose minute overlaps [run.started, run.finished]; the window
closes at the end of the minute holding run.finished. A capture taken before that close cannot hold the last
datapoint (the publication delay, OC-20): the window is then "not yet present" (INDETERMINATE with a gap).
"""
from __future__ import annotations

import datetime as _dt
import glob
import json
import os
import re

METRIC_PERIOD_S = 60                    # AgentCore's metric resolution: the W2 datapoint (ARCH 5.3 M1), not a limit
LATENCY, ERRORS, INVOCATIONS = "Latency Maximum", "Errors Sum", "Invocations Sum"
SURFACE = "agentcore-metrics"
_UTC = _dt.timezone.utc


def utc(ts):
    """A datetime in UTC from '...Z', '+00:00', '-05:00' (CloudWatch prints the caller's local offset); None if bad."""
    if isinstance(ts, (int, float)):
        return _dt.datetime.fromtimestamp(ts, _UTC)
    if not isinstance(ts, str) or not ts:
        return None
    text = ts.strip().replace("Z", "+00:00")
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:\d{2})?$", text)
    if not m:
        return None
    frac = (m.group(2) or "")[:7]
    try:
        d = _dt.datetime.fromisoformat(m.group(1) + frac + (m.group(3) or "+00:00"))
    except ValueError:
        return None
    return d.astimezone(_UTC)


def iso(d):
    return d.astimezone(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def runtime_key(name):
    """`ifabric_customer::DEFAULT` / `ifabric_customer` / `ifabric-customer` -> `ifabric-customer`."""
    return str(name or "").split("::")[0].replace("_", "-")


def _floor(d, period):
    return d - _dt.timedelta(seconds=(d.minute * 60 + d.second) % period, microseconds=d.microsecond)


class Metrics(object):
    """{runtime: {series: {minute(datetime): value}}} at `period` plus the captures that hold them."""

    def __init__(self):
        self.points = {}          # (runtime, series, period) -> {t: value}
        self.captures = []        # {path, runtime, series, period, start, end, captured_at}
        self.rejects = []

    def add(self, runtime, series, period, t, value, cap):
        d = utc(t)
        try:
            v = float(value)
        except (TypeError, ValueError):
            self.rejects.append({"ref": cap["path"], "why": "datapoint value not a number"})
            return
        if d is None:
            self.rejects.append({"ref": cap["path"], "why": "datapoint timestamp unreadable: %r" % (t,)})
            return
        slot = self.points.setdefault((runtime_key(runtime), series, int(period)), {})
        slot[d] = max(slot.get(d, v), v) if series == LATENCY else v      # one datapoint per runtime and minute

    def series(self, runtime, series, period):
        return self.points.get((runtime_key(runtime), series, int(period)), {})

    def covering(self, runtime, series, period, start, end):
        """Captures of this runtime/series/period whose query range covers [start, end]."""
        out = []
        for c in self.captures:
            if c["runtime"] != runtime_key(runtime) or c["series"] != series or c["period"] != int(period):
                continue
            if c["start"] is None or c["end"] is None or (c["start"] <= start and c["end"] >= end):
                out.append(c)
        return out


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return None


def _series_of(label):
    """'ifabric-it Latency Maximum' -> ('ifabric-it', 'Latency Maximum'); None if not one of ours."""
    parts = str(label or "").split()
    if len(parts) == 3 and parts[1] in ("Latency", "Errors", "Invocations"):
        return parts[0], "%s %s" % (parts[1], parts[2])
    return None


def read_metrics(root):
    """All AgentCore metric captures under <snapshot>/raw/agentcore-metrics/ -> Metrics."""
    m = Metrics()
    base = os.path.join(root, "raw", SURFACE)
    for path in sorted(glob.glob(os.path.join(base, "**", "*.json"), recursive=True)):
        if path.endswith(".capture.json"):
            continue
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        doc = _read_json(path)
        if not isinstance(doc, dict):
            m.rejects.append({"ref": rel, "why": "not a JSON object"})
            continue
        side = _read_json(path + ".capture.json") or {}
        captured = utc(side.get("captured_at") or doc.get("captured_at") or doc.get("measured_at_utc"))
        if "Datapoints" in doc:                                   # get-metric-statistics (the EP-11 collector)
            sc = side.get("scope") or {}
            metric, stat = sc.get("metric") or doc.get("Label"), sc.get("statistic")
            if not stat:
                stat = next((k for p in doc["Datapoints"] for k in ("Maximum", "Sum", "Average") if k in p), None)
            runtime = sc.get("runtime") or os.path.basename(os.path.dirname(path))
            series = "%s %s" % (metric, stat)
            cap = {"path": rel, "runtime": runtime_key(runtime), "series": series,
                   "period": int(sc.get("period") or doc.get("period") or METRIC_PERIOD_S),
                   "start": utc(sc.get("start")), "end": utc(sc.get("end")), "captured_at": captured}
            m.captures.append(cap)
            for p in doc["Datapoints"] or ():
                m.add(runtime, series, cap["period"], p.get("Timestamp"), p.get(stat), cap)
            continue
        rows = []
        if isinstance(doc.get("MetricDataResults"), list):        # get-metric-data stdout
            rows = [(r.get("Label"), list(zip(r.get("Timestamps") or [], r.get("Values") or [])))
                    for r in doc["MetricDataResults"]]
        elif isinstance(doc.get("results"), dict):               # the ops lane's measure.py form
            rows = [(label, [tuple(p) for p in (r or {}).get("points") or []]) for label, r in doc["results"].items()]
        else:
            m.rejects.append({"ref": rel, "why": "not an AgentCore metric capture shape"})
            continue
        win = doc.get("window") or [None, None]
        period = int(doc.get("period") or METRIC_PERIOD_S)
        for label, pts in rows:
            key = _series_of(label)
            if key is None:
                continue
            cap = {"path": rel, "runtime": runtime_key(key[0]), "series": key[1], "period": period,
                   "start": utc(win[0]) if len(win) > 0 else None, "end": utc(win[1]) if len(win) > 1 else None,
                   "captured_at": captured}
            m.captures.append(cap)
            for t, v in pts:
                m.add(key[0], key[1], period, t, v, cap)
    return m


# ---------------------------------------------------------------- the run's own facts (from its store records)

def _at(r):
    return r.get("emitted.at") or r.get("ts") or r.get("observed.at")


def run_window(recs):
    """(started, finished, scenario) from the orchestrator's run.started / run.finished records; None if absent."""
    st = [r for r in recs if r.get("phase") == "run.started" and r.get("actor.id") == "orchestrator"]
    fi = [r for r in recs if r.get("phase") == "run.finished" and r.get("actor.id") == "orchestrator"]
    start = min((utc(_at(r)) for r in st if utc(_at(r))), default=None)
    end = max((utc(_at(r)) for r in fi if utc(_at(r))), default=None)
    scen = None
    for r in st:
        mm = re.search(r"\bscenario (S[0-9]+)\b", str(r.get("detail") or ""))
        if mm:
            scen = mm.group(1)
    return start, end, scen


_RECV_RE = re.compile(r"^invocation of (\S+) returned status=(\S+)")
_ARN_RE = re.compile(r"runtime/([A-Za-z0-9_]+?)-[A-Za-z0-9]{10}$")


def _received_runtime(r):
    """The runtime a handoff.received record is about. The orchestrator's FIRST invocation (h0, the customer) has
    no handoff id (run.py plan_steps: n=0 -> None), so it records NO handoff.sent and its handoff.received carries
    no handoff.to/.id (real shape: b4 ledger export); the runtime is then in the detail text, else the runtime ARN."""
    to = r.get("handoff.to")
    if to:
        return runtime_key(to)
    mm = _RECV_RE.match(str(r.get("detail") or ""))
    if mm:
        return runtime_key(mm.group(1))
    am = _ARN_RE.search(str(r.get("runtime.arn") or ""))
    return runtime_key(am.group(1)) if am else None


def invocations(recs):
    """[(runtime, status or None)] one entry per agent invocation of the run, h0 included: the union of the EP-5
    handoff.sent records (keyed by handoff.id) and the handoff.received records (keyed by handoff.id; h0, which has
    none, by its session id). Only ifabric-* runtimes. An invocation never answered has status None."""
    seen = {}
    for r in recs:
        ph = r.get("phase")
        if ph == "handoff.sent":
            rt = runtime_key(r.get("handoff.to"))
            if rt.startswith("ifabric-"):
                seen.setdefault(r.get("handoff.id") or ("sent", r.get("runtime.session_id") or r.get("record_id")),
                                [rt, None])
        elif ph == "handoff.received":
            rt = _received_runtime(r)
            if rt and rt.startswith("ifabric-"):
                mm = _RECV_RE.match(str(r.get("detail") or ""))
                key = r.get("handoff.id") or ("recv", rt, r.get("runtime.session_id") or r.get("record_id"))
                seen.setdefault(key, [rt, None])[1] = mm.group(2) if mm else None
    return [tuple(v) for v in seen.values()]


def invocations_expected(recs):
    """{runtime: n} one per agent invocation of the run: customer h0, IT h1, network h2, IT h3 (Gateway C)."""
    out = {}
    for rt, _ in invocations(recs):
        out[rt] = out.get(rt, 0) + 1
    return out


def diagnostic_durations(recs):
    """{runtime: max duration_ms} the orchestrator measured per invocation (EP-5 testimony; a diagnostic only)."""
    out = {}
    for r in recs:
        if r.get("phase") != "handoff.received":
            continue
        mm = re.search(r"duration_ms=([0-9]+)", str(r.get("detail") or ""))
        rt = _received_runtime(r)
        if mm and rt:
            out[rt] = max(out.get(rt, 0), int(mm.group(1)))
    return out


_TREAT_RE = re.compile(r"^EP-0 declared treatment for (\S+?): .*?generation (\S+?)[ ,)]")
_PIN_RE = re.compile(r"\bpin \S+ -> (\S+?),")


def treatments(recs):
    """{agent: "<generation>[|<to-pin sha prefix>]"} from the run's ep0.declared_treatment records (a runtime update)."""
    out = {}
    for r in recs:
        if r.get("phase") == "ep0.declared_treatment":
            mm = _TREAT_RE.match(str(r.get("detail") or ""))
            if mm:
                pm = _PIN_RE.search(str(r.get("detail") or ""))
                out[mm.group(1)] = mm.group(2) + ("|" + pm.group(1) if pm else "")
    return out


def warm_up_index(by_run):
    """[(started, {agent: treatment}, agents warmed)] for every run recorded with run.condition warm-up. An agent is
    warmed when the warm-up run's invocation of it returned status=OK (a failed call warmed nothing). The warm-up
    run carries the same ep0.declared_treatment (generation and pin) as the next run on that pin, so `run_windows`
    matches on it: one '--condition warm-up' run satisfies C9's runtime-update rule for later runs at that
    generation and pin."""
    out = []
    for rid, recs in by_run.items():
        if not any(r.get("run.condition") == "warm-up" for r in recs):
            continue
        start, _, _ = run_window(recs)
        if start is not None:
            out.append((start, treatments(recs), set(rt for rt, st in invocations(recs) if st == "OK")))
    return out


def run_windows(recs, metrics, as_of, warmups=()):
    """{runtime: MetricWindow} for one run (the c9 evaluator's input) + facts for the assessment's measured block."""
    start, end, scen = run_window(recs)
    facts = {"scenario": scen, "started": iso(start), "finished": iso(end), "figure_of_record":
             "AWS/Bedrock-AgentCore Latency Maximum per runtime per 60 s (M1; AWS-written)",
             "diagnostic_invocation_ms": diagnostic_durations(recs), "captures": [], "gaps": []}
    expected = invocations_expected(recs)
    if start is None or end is None:
        facts["gaps"].append("no run.started/run.finished record: the run window W2 is unknown")
        return {}, facts
    lo, hi = _floor(start, METRIC_PERIOD_S), _floor(end, METRIC_PERIOD_S)
    closes = hi + _dt.timedelta(seconds=METRIC_PERIOD_S)
    facts["w2"] = [iso(lo), iso(closes)]
    asof = utc(as_of)
    updated = treatments(recs)
    windows = {}
    for rt in sorted(expected):
        w = {"invocations_expected": expected[rt], "condition": next(
            (r.get("run.condition") for r in recs if r.get("run.condition")), None)}
        caps = metrics.covering(rt, LATENCY, METRIC_PERIOD_S, lo, closes)
        lat = dict((t, v) for t, v in metrics.series(rt, LATENCY, METRIC_PERIOD_S).items() if lo <= t <= hi)
        err = dict((t, v) for t, v in metrics.series(rt, ERRORS, METRIC_PERIOD_S).items() if lo <= t <= hi)
        late = [c for c in caps if c["captured_at"] is not None and c["captured_at"] < closes]
        on_time = [c for c in caps if c not in late]
        facts["captures"] += sorted(set(c["path"] for c in caps))
        inv = dict((t, v) for t, v in metrics.series(rt, INVOCATIONS, METRIC_PERIOD_S).items() if lo <= t <= hi)
        if lat and caps and not on_time:
            facts["gaps"].append("%s: datapoints not yet complete: every capture was taken before W2 closed (%s; "
                                 "publication delay OC-20); the window is not judged on a partial read" % (rt, iso(closes)))
            lat = {}
        elif lat and inv and sum(inv.values()) < expected[rt]:
            facts["gaps"].append("%s: the metric counts %d invocation(s) in W2, the run made %d: a datapoint is missing"
                                 % (rt, int(sum(inv.values())), expected[rt]))
            lat = {}
        if lat:
            w["latency_max"] = max(lat.values())
            w["datapoints"] = len(lat)
            w["errors"] = int(sum(err.values())) if err else None
            w["datapoint_minutes"] = [iso(t) for t in sorted(lat)]
        else:
            w["latency_max"], w["datapoints"], w["errors"] = None, 0, None
            if any(g.startswith(rt + ": ") for g in facts["gaps"]):
                pass
            elif not caps:
                facts["gaps"].append("%s: no AgentCore metric capture at 60 s covers W2 %s..%s" % (rt, iso(lo), iso(closes)))
            elif not on_time:
                facts["gaps"].append("%s: datapoints not yet present: every capture was taken before the window closed "
                                     "(%s; publication delay OC-20)" % (rt, iso(closes)))
            elif asof is not None and asof < closes:
                facts["gaps"].append("%s: W2 has not closed at as_of %s" % (rt, iso(asof)))
        if lat and not err:
            facts["gaps"].append("%s: no Errors datapoint captured for W2 (Errors not assessed)" % rt)
        if rt in updated:
            w["runtime_updated"] = True
            w["warmed_up"] = any(ws < start and wt.get(rt) == updated[rt] and rt in inv for ws, wt, inv in warmups)
        windows[rt] = w
    facts["captures"] = sorted(set(facts["captures"]))
    return windows, facts


def baseline_pin(entry, scenario, runtimes):
    """The C9 pin values for one run from the register entry (values only from there; never a literal):
    baseline_value_<runtime>_<scenario> (ARCH 3.3) or baseline_value_<runtime>, mapped to the evaluator's
    baseline_value_<runtime>; the limits stay in observation_limit as k=v (c9 reads them)."""
    out = {}
    for rt in runtimes:
        v = entry.get("baseline_value_%s_%s" % (rt, scenario)) if scenario else None
        if v in (None, ""):
            v = entry.get("baseline_value_%s" % rt)
        if v not in (None, ""):
            out["baseline_value_%s" % rt] = v
    return out


def hour_of(d):
    return d.replace(minute=0, second=0, microsecond=0)
