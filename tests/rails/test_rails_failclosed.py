"""AGENT-GUARDRAILS §2 principle 10: rails fail closed. An exception inside a rail -> BLOCK in enforce, FLAG in
observe, reason rail-error:<id>; enforce returns the refusing result, observe passes the subject through (DG-1)."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _railpath  # noqa: F401,E402
from adapters.runtime import rails as R  # noqa: E402


def boom(*a, **k):
    raise RuntimeError("forced")


class Patch(object):
    """Replace one module attribute for the duration of a with-block (no pytest fixture needed)."""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.old = getattr(R, self.name)
        setattr(R, self.name, boom)

    def __exit__(self, *a):
        setattr(R, self.name, self.old)


def err(r, rail):
    d = [x for x in r.records if x["rail.id"] == rail and x["rail.matches"] == {"rail-error": 1}]
    assert len(d) == 1, r.records
    return d[0]


def check(rail, mode, d):
    assert d["reason"] == "rail-error:" + rail
    assert d["verdict"] == ("BLOCK" if mode == "enforce" else "FLAG")
    assert d["inline.action"] == ("block" if mode == "enforce" else "proceed")


def test_ingress_fails_closed():
    for mode in ("enforce", "observe"):
        r = R.Rails("ifabric-it", mode=mode)
        p = {"context": b"x", "ifabric": {}}   # bytes context: crashes the JSON size check
        out, blocked = r.ingress(p)
        assert blocked is (mode == "enforce") and out is p
        check("I-01", mode, err(r, "I-01"))


def test_tools_fails_closed():
    for mode in ("enforce", "observe"):
        r = R.Rails("ifabric-it", mode=mode)
        ts = ["runbook-lookup___lookup", "cr-author___patch_cr"]
        out = r.tools(ts, boom)   # the name accessor raises inside the rail
        assert out == ([] if mode == "enforce" else ts)
        check("X-01", mode, err(r, "X-01"))


def test_before_tool_fails_closed():
    for mode in ("enforce", "observe"):
        r = R.Rails("ifabric-network", mode=mode)
        args = {"site": "DU-DEN-12-A"}
        with Patch("sha"):
            msg, a = r.before_tool("network-twin___predict_rsrp", args)
        assert a is args and (msg.startswith("denied by rail X-02") if mode == "enforce" else msg is None)
        check("X-02", mode, err(r, "X-02"))


def test_after_tool_fails_closed_and_still_envelopes():
    for mode in ("enforce", "observe"):
        r = R.Rails("ifabric-it", mode=mode)
        with Patch("scan"):
            out = r.after_tool("runbook-lookup___lookup", "plain text")
        assert out.startswith("[EVIDENCE") and "UNTRUSTED DATA" in out and "plain text" in out
        check("T-03", mode, err(r, "T-03"))


def test_after_tool_none_does_not_raise():
    for mode in ("enforce", "observe"):
        r = R.Rails("ifabric-it", mode=mode)
        out = r.after_tool("runbook-lookup___lookup", None)
        assert isinstance(out, str) and out.startswith("[EVIDENCE")


def test_output_fails_closed():
    for mode in ("enforce", "observe"):
        r = R.Rails("ifabric-it", mode=mode)
        assert r.output(None) == ("" if mode == "enforce" else None)
        check("O-04", mode, err(r, "O-04"))


def test_ground_fails_closed():
    for mode in ("enforce", "observe"):
        r = R.Rails("ifabric-it", mode=mode)
        j = r.ground(["x"])
        assert j == ({"disposition": "escalate"} if mode == "enforce" else ["x"])
        check("O-03", mode, err(r, "O-03"))


def test_ground_crash_on_dict_escalates_in_enforce():
    r = R.Rails("ifabric-it", mode="enforce")
    with Patch("IDS"):   # IDS.findall -> AttributeError inside ground
        j = r.ground({"disposition": "auto-resolve", "deciding_evidence": []})
    assert j["disposition"] == "escalate"
    check("O-03", "enforce", err(r, "O-03"))


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
