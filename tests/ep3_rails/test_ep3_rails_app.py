"""PR-31: EP-3 tool rails follow DG-1 in the REAL app (ifabric_app + real Strands 1.57.2 Agent, a scripted model).

- enforce: an undeclared tool is CANCELLED by X-02 through cancel_tool: the tool never executes, a rail_decision
  BLOCK (outcome.real CANCELLED_RAIL) is emitted, and no EP-3 action record exists for it (no actual call);
- observe: the same call is only RECORDED: the tool executes, the rail_decision BLOCK carries
  rail.intended_action block and inline.action proceed, and EP-3 records the actual call (declared false);
- ADV-R-01 leg 2: the customer agent's declared tool on SITE-ADV-99 in enforce is NOT blocked or rewritten by our
  rails, so the platform PDP (the DG-4 Cedar forbid) is the layer that decides.

Runs tests/ep3_rails/drive_ep3.py on the Strands 3.12 venv in a subprocess (skipped where that venv is absent).
IFABRIC_EP3_SRC_ROOTS (os.pathsep-separated) adds other trees to drive, e.g. a concurrent PR's worktree.
"""
import json
import os
import subprocess
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY312 = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-local/.venv-strands312/bin/python")
LOOKUP = "customer-records___customer_lookup"
SRCS = [REPO] + [p for p in os.environ.get("IFABRIC_EP3_SRC_ROOTS", "").split(os.pathsep) if p]

pytestmark = pytest.mark.skipif(not os.path.exists(PY312), reason="the Strands 3.12 venv is absent")

_CACHE = {}


def drive(src, agent, mode, tool=LOOKUP, site="SITE-ADV-99"):
    key = (src, agent, mode, tool, site)
    if key not in _CACHE:
        out = os.path.join(tempfile.mkdtemp(prefix="pr31-ep3-"), "out.json")
        env = dict(os.environ, IFABRIC_SRC_ROOT=src, PYTHONDONTWRITEBYTECODE="1")   # another tree stays untouched
        for k in ("TOOL_MCP_URL", "AGENTCORE_GATEWAY_MCP_URL", "IFABRIC_RAILS_MODE", "AGENT_NAME"):
            env.pop(k, None)
        p = subprocess.run([PY312, os.path.join(HERE, "drive_ep3.py"), "--agent", agent, "--mode", mode,
                            "--tool", tool, "--site", site, "--out", out],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=180)
        assert p.returncode == 0, p.stdout.decode("utf-8", "replace")[-3000:]
        assert b"record-rejected" not in p.stdout, "a record failed the contract"
        with open(out) as fh:
            _CACHE[key] = json.load(fh)
    return _CACHE[key]


def rails(d, rail):
    return [r for r in d["records"] if r.get("record_kind") == "rail_decision" and r.get("rail.id") == rail]


def ep3_actions(d, tool=LOOKUP):
    return [r for r in d["records"] if r.get("record_kind") == "action" and r.get("ep.id") == "EP-3"
            and r.get("tool.name") == tool]


@pytest.mark.parametrize("src", SRCS)
def test_enforce_undeclared_tool_is_cancelled_and_recorded(src):
    d = drive(src, "ifabric-network", "enforce")
    assert d["src"] == os.path.abspath(src)
    assert d["dispatched"] == []                                   # the tool never executed
    assert all(LOOKUP not in names for names in d["model_tools"])  # X-01 withheld it at discovery
    (x02,) = rails(d, "X-02")
    assert (x02["verdict"], x02["inline.mode"], x02["inline.action"]) == ("BLOCK", "enforce", "block")
    assert x02["ep.id"] == "EP-3" and x02["control.ref"] == "RAIL" and x02["phase"] == "ifabric.rail_decision"
    assert x02["tool.name"] == LOOKUP and x02["tool.declared"] is False
    assert x02["outcome.real"] == "CANCELLED_RAIL" and "rail.intended_action" not in x02
    assert ep3_actions(d) == []                                    # no actual call: no EP-3 action record
    (x01,) = rails(d, "X-01")
    assert x01["verdict"] == "MODIFY" and x01["inline.action"] == "modify"
    assert d["result"]["rails"]["rails.mode"] == "enforce" and "error" not in d["result"]


@pytest.mark.parametrize("src", SRCS)
def test_observe_undeclared_tool_is_only_recorded(src):
    d = drive(src, "ifabric-network", "observe")
    assert d["dispatched"] == [{"tool": LOOKUP, "site": "SITE-ADV-99"}]   # the tool executed
    assert all(LOOKUP in names for names in d["model_tools"])            # X-01 observe: every tool offered
    (x02,) = rails(d, "X-02")
    assert (x02["verdict"], x02["inline.mode"], x02["inline.action"]) == ("BLOCK", "observe", "proceed")
    assert x02["rail.intended_action"] == "block" and x02["tool.declared"] is False
    assert x02.get("outcome.real") != "CANCELLED_RAIL"
    acts = ep3_actions(d)
    assert sorted(a["tool.phase"] for a in acts) == ["after", "before"]
    assert all(a["tool.declared"] is False for a in acts)
    assert [a["outcome.real"] for a in acts if a["tool.phase"] == "after"] == ["SERVED"]
    assert d["result"]["rails"]["rails.mode"] == "observe"


@pytest.mark.parametrize("src", SRCS)
def test_adv_r01_leg2_site_adv_99_passes_our_rails_in_enforce(src):
    d = drive(src, "ifabric-customer", "enforce")
    assert d["dispatched"] == [{"tool": LOOKUP, "site": "SITE-ADV-99"}]   # out to the platform, argument intact
    assert not [r for r in d["records"] if r.get("record_kind") == "rail_decision"
                and r.get("verdict") == "BLOCK"]
    assert rails(d, "X-02") == [] and rails(d, "X-03") == []              # ALLOWs are compact (DG-3)
    counts = d["result"]["rails"]["rails.counts"]
    assert counts["X-02"] == {"ALLOW": 1, "BLOCK": 0, "MODIFY": 0, "FLAG": 0}
    assert counts["X-03"] == {"ALLOW": 1, "BLOCK": 0, "MODIFY": 0, "FLAG": 0}
    acts = ep3_actions(d)
    assert sorted(a["tool.phase"] for a in acts) == ["after", "before"] and all(a["tool.declared"] for a in acts)
