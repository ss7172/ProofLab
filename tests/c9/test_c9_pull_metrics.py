"""PR-41: tools/c9_pull_metrics.py (ops lane) through a FAKE runner -> captures assess --snapshot reads (collector shape)."""
import importlib.util
import json
import os

import pytest

from prooflab.adapters.collectors import capture
from prooflab.query import assess_snapshot as A

import test_c9_assess as T

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("c9_pull_metrics", os.path.join(ROOT, "tools", "c9_pull_metrics.py"))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
ARNS = dict((a, "arn:aws:bedrock-agentcore:us-east-1:000000000000:runtime/%s-X" % a.replace("-", "_")) for a in T.AGENTS)


def fake_metrics(values):
    def runner(argv):
        name = [a for a in argv if a.startswith("Name=Name,")][0].split("Value=")[1].split("::")[0].replace("_", "-")
        metric = argv[argv.index("--metric-name") + 1]
        stat = argv[argv.index("--statistics") + 1]
        v = {"Latency": values[name], "Errors": 0.0, "Invocations": 2.0 if name == "ifabric-it" else 1.0}[metric]
        return 0, json.dumps({"Label": metric, "Datapoints": [{"Timestamp": "2026-10-06T08:19:00+00:00", stat: v}]}).encode(), b""
    return runner


def test_w2_is_minute_aligned():
    assert P.w2("2026-10-06T08:18:15.536Z", "2026-10-06T08:19:50.283Z") == ("2026-10-06T08:18:00Z", "2026-10-06T08:20:00Z")


def test_refuses_before_w2_closes(tmp_path):
    ctx = capture.Ctx(root=str(tmp_path), runner=fake_metrics(T.BASE), now=lambda: "2026-10-06T08:19:59Z")
    with pytest.raises(capture.CaptureError):
        P.pull(ctx, ARNS, "2026-10-06T08:18:15Z", "2026-10-06T08:19:50Z")
    assert ctx.calls == []


def test_pulled_captures_feed_assess_end_to_end(tmp_path):
    snap = T.snapshot(tmp_path, [(T.CID, T.run_records(T.CID, "08:18:15", "08:19:50"))])
    ctx = capture.Ctx(root=snap, runner=fake_metrics(T.BASE), now=lambda: "2026-10-06T08:21:00Z")
    res = P.pull(ctx, ARNS, "2026-10-06T08:18:15Z", "2026-10-06T08:19:50Z")
    assert len(res["captures"]) == 9 and all("--period" in c and c[c.index("--period") + 1] == "60" for c in ctx.calls)
    out = A.assess_snapshot(snap, controls=("C9",))
    assert out["written"][0][2] == "SATISFIED", out
    snap2 = T.snapshot(tmp_path / "b", [(T.CID, T.run_records(T.CID, "08:18:15", "08:19:50"))])
    ctx2 = capture.Ctx(root=snap2, runner=fake_metrics(dict(T.BASE, **{"ifabric-it": 2500.0})),
                       now=lambda: "2026-10-06T08:21:00Z")
    P.pull(ctx2, ARNS, "2026-10-06T08:18:15Z", "2026-10-06T08:19:50Z")
    assert A.assess_snapshot(snap2, controls=("C9",))["written"][0][2] == "BREACHED"
