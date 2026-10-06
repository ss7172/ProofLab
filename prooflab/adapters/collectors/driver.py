"""`python3 -m prooflab collect`: the live collect driver (M3). Stdlib, Python 3.9.

    prooflab collect --cid CID [--include-test] --surfaces aws_spans,agentcore_metrics,aict_invocations,ledger_export,runtime_logs
                     --runtimes runtimes.json --out WORKDIR [--start T --end T] [--wait] [--token-env NAME]
                     [--ledger-url URL] [--profile P] [--region R] [--aict-pad-s N] [--operator NAME]

A thin loop over the existing collector modules (it adds no pull logic): every call goes through the one subprocess
seam (`capture.default_runner`: `aws` / `kubectl` from the caller's environment; the ops lane runs the verb under
~/firstmate-homes/TrustworthyAI/workshop-local/bin/hk). Captures and their `.capture.json` sidecars land under
<out>/raw/<surface>/... exactly where `prooflab refresh --snapshot <out>` reads them.

Timing rules (a surface that is not due is recorded as `not-yet` with a retry time and the command to re-run; with
--wait the driver sleeps until it is due instead):
  ledger_export       any time; PER CID only (there is no full-GET path here or in the module)
  aws_spans           >= 60 s after the run end (b6b: Logs Insights lags)
  agentcore_metrics   >= 15.5 s after the run end (the OC-20 measured delay, b2d); a one-minute-period window
  aict_invocations    >= 600 s after the (padded) window end (the module's own MIN_AGE_S)
  runtime_logs        any time (the stdout witness)
The run window is --start/--end, else the first and last `ts` of the run's ledger rows (ledger_export first).
runtimes.json is {label: runtime ARN}; a runtime's id and name come from its ARN (`arn:...:runtime/<name>-<10 chars>`).
Test traffic (ifabric-test-*) is skipped for every surface unless --include-test.
Exit: 0 all captured, 5 some surface not yet due (nothing failed; re-run later), 1 a surface failed, 2 bad input.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

from prooflab.adapters.collectors import (agentcore_metrics, aict_invocations, aws_spans, capture, ledger_export,
                                          runtime_logs)
from prooflab.contract import clocks

DRIVEN = ("ledger_export", "aws_spans", "agentcore_metrics", "aict_invocations", "runtime_logs")   # ledger first
SPANS_MIN_AGE_S = 60.0
METRICS_DELAY_S = 15.5
METRICS_PERIOD_S = 60
MAX_WAIT_S = 1500.0
EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_NOT_YET = 0, 1, 2, 5


class UsageError(ValueError):
    pass


def _dt_of(value):
    return clocks.parse_utc(value)


def _fmt(moment):
    return clocks.format_utc(moment)


def load_runtimes(path):
    """{label: arn} -> [(label, arn, runtime id, runtime name)]."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as err:
        raise UsageError("cannot read --runtimes %s: %s" % (path, err))
    if not isinstance(doc, dict) or not doc:
        raise UsageError("--runtimes must be a JSON object {label: runtime ARN}")
    out = []
    for label in sorted(doc):
        arn = doc[label].get("arn") if isinstance(doc[label], dict) else doc[label]
        arn = str(arn or "")
        if not arn.startswith("arn:") or ":runtime/" not in arn:
            raise UsageError("runtime %r: %r is not a runtime ARN (arn:...:runtime/<name>-<id>)" % (label, arn))
        rid = arn.rsplit("/", 1)[-1]
        name = rid.rsplit("-", 1)[0] if "-" in rid else rid
        out.append((label, arn, rid, name))
    return out


def ledger_window(path):
    """(first ts, last ts) of a captured per-CID ledger file, or None."""
    times = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                ts = row.get("ts") or row.get("observed.at") if isinstance(row, dict) else None
                if isinstance(ts, str) and clocks.is_utc(ts):
                    times.append(_dt_of(ts))
    except OSError:
        return None
    return (_fmt(min(times)), _fmt(max(times))) if times else None


def due_at(surface, end, aict_pad_s=0):
    """When `surface` may first be pulled for a run that ended at `end`; None = any time."""
    moment = _dt_of(end)
    delay = {"aws_spans": SPANS_MIN_AGE_S, "agentcore_metrics": METRICS_DELAY_S,
             "aict_invocations": aict_pad_s + aict_invocations.MIN_AGE_S}.get(surface)
    return None if delay is None else moment + _dt.timedelta(seconds=delay)


def _floor_min(moment):
    return moment.replace(second=0, microsecond=0)


def metric_window(start, end, now):
    """A whole-minute window around the run, its end clamped to `now`."""
    lo = _floor_min(_dt_of(start))
    hi = _floor_min(_dt_of(end))
    if hi < _dt_of(end):
        hi += _dt.timedelta(minutes=1)
    return _fmt(lo), _fmt(min(hi, _dt_of(now)))


def _files(*sidecars):
    return [s["path"] for s in sidecars if s]


def run(args, ctx, runtimes, fetch=None):
    """-> result dict. `ctx` is a capture.Ctx (its clock, sleep and runner are the test seams)."""
    cid = args.cid
    skipped = capture.skip_cid(cid, ctx)       # CaptureError for a non-run id
    surfaces = [s for s in DRIVEN if s in args.surfaces]
    results, start, end = [], args.start, args.end
    command = "python3 -m prooflab collect --cid %s --out %s --runtimes %s" % (cid, args.out, args.runtimes)
    if ctx.include_test:
        command += " --include-test"
    for surface in surfaces:
        row = {"surface": surface, "status": None, "files": []}
        results.append(row)
        if skipped:
            row.update(status="skipped", reason=skipped)
            continue
        try:
            if surface == "ledger_export":
                token = os.environ.get(args.token_env or "") if args.token_env else None
                if not token:
                    row.update(status="error", reason="ledger_export needs the ledger token: --token-env NAME of the "
                                                      "variable that holds it (kubectl proxy must be up)")
                    continue
                kw = {"fetch": fetch} if fetch else {}
                base = (args.ledger_url or ledger_export.PROXY_BASE).split("/api/v1/")[0]   # the runbook's $LEDGER is the full route
                side = ledger_export.pull(ctx, cid, token, base=base, **kw)
                row.update(status="captured", files=_files(side))
                win = ledger_window(os.path.join(ctx.root, side["path"])) if side else None
                row["rows"] = side["line_count"] if side else 0
                if win and not (start and end):
                    start, end = start or win[0], end or win[1]
                continue
            if not (start and end):
                row.update(status="error", reason="no run window: pass --start and --end, or pull ledger_export first")
                continue
            due = due_at(surface, end, args.aict_pad_s if surface == "aict_invocations" else 0)
            if due is not None and _dt_of(ctx.now()) < due:
                if args.wait:
                    wait_s = (due - _dt_of(ctx.now())).total_seconds()
                    if wait_s > MAX_WAIT_S:
                        raise capture.CaptureError("would wait %d s (> %d)" % (wait_s, MAX_WAIT_S))
                    ctx.sleep(wait_s + 0.5)
                else:
                    row.update(status="not-yet", retry_at=_fmt(due),
                               hint="re-run after %s: %s --surfaces %s --start %s --end %s" % (
                                   _fmt(due), command, surface, start, end))
                    continue
            if surface == "aws_spans":
                row.update(status="captured", files=_files(aws_spans.pull(ctx, cid, start, end)))
            elif surface == "aict_invocations":
                pad_end = _fmt(_dt_of(end) + _dt.timedelta(seconds=args.aict_pad_s))
                row.update(status="captured", window=[start, pad_end], files=_files(
                    aict_invocations.pull(ctx, [arn for _l, arn, _i, _n in runtimes], start, pad_end)))
            elif surface == "agentcore_metrics":
                lo, hi = metric_window(start, end, ctx.now())
                sides = [agentcore_metrics.pull(ctx, name, metric, stat, lo, hi, period=METRICS_PERIOD_S,
                                                resource_arn=arn)
                         for _label, arn, _rid, name in runtimes for metric, stat in agentcore_metrics.METRICS]
                row.update(status="captured", window=[lo, hi], files=_files(*sides))
            elif surface == "runtime_logs":
                row.update(status="captured", files=_files(*[runtime_logs.pull(ctx, rid, cid, start, end)
                                                             for _label, _arn, rid, _name in runtimes]))
        except capture.ExpiredTokenError as err:
            row.update(status="error", reason="AWS credentials expired: refresh them and re-run (%s)" % str(err)[:120])
        except (capture.CaptureError, OSError, ValueError, KeyError) as err:
            row.update(status="error", reason="%s: %s" % (type(err).__name__, str(err)[:300]))
    return {"cid": cid, "window": {"start": start, "end": end}, "include_test": bool(ctx.include_test),
            "out": args.out, "results": results}


def exit_code(result):
    states = [r["status"] for r in result["results"]]
    if "error" in states:
        return EXIT_ERROR
    return EXIT_NOT_YET if "not-yet" in states else EXIT_OK


def parser():
    ap = argparse.ArgumentParser(prog="prooflab collect", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="Timing rules and exit codes:\n" + __doc__.split("Timing rules", 1)[1])
    ap.add_argument("--cid", help="the run id (CID)")
    ap.add_argument("--include-test", action="store_true", help="also collect an ifabric-test-* CID (smokes)")
    ap.add_argument("--surfaces", default=",".join(DRIVEN),
                    help="comma list of: %s (default: all)" % ", ".join(DRIVEN))
    ap.add_argument("--runtimes", help="JSON {label: runtime ARN}")
    ap.add_argument("--out", help="work directory (raw/<surface>/... is written under it)")
    ap.add_argument("--start", help="run start, UTC (default: first ledger row)")
    ap.add_argument("--end", help="run end, UTC (default: last ledger row)")
    ap.add_argument("--wait", action="store_true", help="sleep until a surface is due instead of recording not-yet")
    ap.add_argument("--token-env", help="NAME of the environment variable holding the ledger token (never the value)")
    ap.add_argument("--ledger-url", help="kubectl proxy base (default %s)" % ledger_export.PROXY_BASE)
    ap.add_argument("--aict-pad-s", type=float, default=0.0,
                    help="seconds added to the aict window end (records land up to ~330 s late); default 0")
    ap.add_argument("--profile")
    ap.add_argument("--region", help="default: $AWS_REGION")
    ap.add_argument("--operator", default="")
    ap.add_argument("--list", action="store_true", help="list every collector surface and exit")
    return ap


def main(argv=None, ctx=None, fetch=None):
    ap = parser()
    args = ap.parse_args(argv)
    try:
        if args.list:
            from prooflab.adapters import collectors
            print("collectors: " + ", ".join(collectors.SURFACES))
            return EXIT_OK
        for need in ("cid", "runtimes", "out"):
            if not getattr(args, need):
                raise UsageError("--%s is required" % need)
        wanted = [s.strip() for s in args.surfaces.split(",") if s.strip()]
        bad = [s for s in wanted if s not in DRIVEN]
        if bad or not wanted:
            raise UsageError("--surfaces: %s not driven here (one of %s)" % (bad or "empty", ", ".join(DRIVEN)))
        args.surfaces = wanted
        for name in ("start", "end"):
            if getattr(args, name) and not clocks.is_utc(getattr(args, name)):
                raise UsageError("--%s must be a UTC timestamp like 2026-10-06T07:36:00Z" % name)
        runtimes = load_runtimes(args.runtimes)
        if ctx is None:
            ctx = capture.Ctx(root=args.out, profile=args.profile, region=args.region or os.environ.get("AWS_REGION") or None,
                              operator=args.operator, captured_by="prooflab collect", include_test=args.include_test)
        result = run(args, ctx, runtimes, fetch)
    except (UsageError, capture.CaptureError) as err:
        print("error: %s" % err, file=sys.stderr)
        return EXIT_USAGE
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
