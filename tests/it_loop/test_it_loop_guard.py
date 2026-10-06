"""PR-36: rail T-07, the no-evidence tool-loop guard, in the REAL IT role + shared app + Strands 1.57.2 Agent.

Live finding (ops-lane b2d S-4): the IT smoke made 12 model calls, every one a runbook-lookup (9 T-02 no-evidence
FLAGs, longest consecutive streak 8) until the C16 ceiling halted it as escalate. T-02 only FLAGs; nothing acted.

Here the fake model always calls runbook-lookup and the fake tool always returns no evidence. With the limit K
from the pin (register C16 tool_no_evidence_limit) the run stops after exactly K lookups and K model calls, with one
RAIL-T-07 decision, a gather-evidence judgment (precedence tool-no-evidence-limit) naming the evidence needed, and no
halt. A normal run (a hit) and a streak that a hit resets are unaffected; observe only records; no pinned limit = off.
Runs tests/it_loop/drive_loop.py on the Strands 3.12 venv in a subprocess (skipped where that venv is absent).
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY312 = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-local/.venv-strands312/bin/python")
LOOKUP = "runbook-lookup___lookup"

pytestmark = pytest.mark.skipif(not os.path.exists(PY312), reason="the Strands 3.12 venv is absent")

_CACHE = {}


def drive(results, mode="enforce", *flags):
    key = (results, mode) + flags
    if key not in _CACHE:
        out = os.path.join(tempfile.mkdtemp(prefix="pr36-loop-"), "out.json")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for k in ("TOOL_MCP_URL", "AGENTCORE_GATEWAY_MCP_URL", "IFABRIC_RAILS_MODE", "AGENT_NAME"):
            env.pop(k, None)
        p = subprocess.run([PY312, os.path.join(HERE, "drive_loop.py"), "--mode", mode, "--results", results,
                            "--out", out] + list(flags),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=180)
        assert p.returncode == 0, p.stdout.decode("utf-8", "replace")[-3000:]
        assert b"record-rejected" not in p.stdout, "a record failed the contract"
        with open(out) as fh:
            _CACHE[key] = json.load(fh)
    return _CACHE[key]


def limit(d):
    return d["pin"]["c16"].get("tool_no_evidence_limit")


def t07(d):
    return [r for r in d["records"] if r.get("record_kind") == "rail_decision" and r.get("rail.id") == "T-07"]


def judgment(d):
    j = [r for r in d["records"] if r.get("record_kind") == "judgment"]
    assert len(j) == 1, j
    return j[0]


def model_actions(d):
    return [r for r in d["records"] if r.get("record_kind") == "action" and r.get("ep.id") == "EP-1"]


def test_register_pins_a_positive_limit():
    sys.path.insert(0, REPO)
    from prooflab.registry import pinned
    with open(os.path.join(REPO, "register", "register.yaml"), "rb") as fh:
        pin = json.loads(pinned.env_for(fh.read(), "observe")["IFABRIC_PIN_JSON"])
    k = pin["c16"]["tool_no_evidence_limit"]
    assert isinstance(k, int) and k >= 1


def test_no_evidence_loop_stops_after_k_lookups():
    d = drive("e" * 12)   # the S-4 shape: the model would keep looking up forever
    k = limit(d)
    assert len(d["dispatched"]) == k                 # exactly K lookups ran, not K+1
    assert d["model_calls"] == k                     # no model call after the stop (no re-ask either)
    assert len(model_actions(d)) == k
    (r,) = t07(d)
    assert r["verdict"] == "BLOCK" and r["inline.action"] == "block" and r["inline.mode"] == "enforce"
    assert r["rail.matches"] == {"no-evidence-streak": k} and r["threshold.value"] == k
    assert r["threshold.sha256"] == r["pin.sha256"] and r["tool.name"] == LOOKUP
    res = d["result"]
    assert res["disposition"] == "gather-evidence" and res["halted"] is False and not res.get("error")
    jf = res["judgment"]
    assert jf["precedence_rule"] == "tool-no-evidence-limit" and jf["model_disposition"] is None
    assert jf["valid"] is True and jf["reasked"] is False and jf["named_evidence_needed"]
    assert "incident id" in jf["named_evidence_needed"][0]   # the IT role names what is missing
    assert "rail T-07" in res["answer"]
    j = judgment(d)
    assert "gather-evidence" in j["detail"] and "incident id" in j["detail"]
    assert res["rails"]["rails.counts"]["T-07"]["BLOCK"] == 1


def test_freeze_still_escalates_when_the_loop_is_stopped():
    d = drive("e" * 12, "enforce", "--freeze")
    assert len(d["dispatched"]) == limit(d) and len(t07(d)) == 1
    assert d["result"]["disposition"] == "escalate"
    assert d["result"]["judgment"]["precedence_rule"] == "freeze-or-restricted"


def test_normal_run_is_unaffected():
    d = drive("h")
    assert len(d["dispatched"]) == 1 and d["model_calls"] == 2
    assert t07(d) == []
    jf = d["result"]["judgment"]
    assert d["result"]["disposition"] == "auto-resolve" and jf["precedence_rule"] == ""
    assert jf["model_disposition"] == "auto-resolve"


def test_a_hit_resets_the_streak():
    k = limit(drive("h"))
    pattern = "e" * (k - 1) + "h" + "e" * (k - 1)    # never K empties in a row
    d = drive(pattern)
    assert len(d["dispatched"]) == len(pattern) and t07(d) == []
    assert d["result"]["judgment"]["precedence_rule"] != "tool-no-evidence-limit"


def test_observe_records_the_intended_block_and_does_not_stop():
    k = limit(drive("h"))
    d = drive("e" * (k + 2), "observe")
    assert len(d["dispatched"]) == k + 2            # observe: the loop is not stopped
    (r,) = t07(d)                                    # recorded once, not on every later empty result
    assert r["verdict"] == "BLOCK" and r["inline.action"] == "proceed" and r["rail.intended_action"] == "block"
    assert d["result"]["judgment"]["precedence_rule"] != "tool-no-evidence-limit"


def test_no_pinned_limit_means_no_guard():
    d = drive("e" * 5, "enforce", "--no-limit")
    assert limit(d) is None
    assert len(d["dispatched"]) == 5 and t07(d) == []
