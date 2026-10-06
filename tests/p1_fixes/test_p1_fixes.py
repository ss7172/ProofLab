"""PR-38: the three agent defects pilot P1 found (ops-lane b3, ifabric-run-1791274694-7725ea), fixed and replayed.

(1) The J2 re-ask of customer and network was blocked by the platform guardrail (Bedrock PROMPT_ATTACK, LOW/MEDIUM;
    AWS-written aict records), so both fell back to escalate. Now: a plain closing instruction, a format-only re-ask,
    and a still-blocked re-ask is recorded (EP-7 observed) and the disposition derived in code (guardrail-blocked-reask).
(2) Network sent Gateway C an empty proposal. Now proposal_of never returns an empty resolution while the network
    answered, the orchestrator relays the answer for an empty one, and IT answers an empty proposal in code
    (gather-evidence, no model or tool call, the negotiation record still written).
(3) IT looped 28 calls inside Gateway C. PR-36's rail T-07 now proven inside the negotiate branch.
The pure part runs anywhere; the dynamic part runs the REAL app on the Strands 3.12 venv (skipped where absent).
All offline; SYNTHETIC data.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile

import pytest

from adapters.runtime import j2

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY312 = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-local/.venv-strands312/bin/python")
APP = os.path.join(REPO, "agents", "ifabric-customer", "ifabric_app.py")
# phrasing a prompt-attack classifier keys on: instruction override, role play, quoting the prior turn
INJECTION_LIKE = ("ignore", "instead", "you must", "only output", "system", "previous answer", "your last answer",
                  "exactly", "pretend", "act as", "role", "disregard", "override")
NONJSON = "- 3 accounts degraded at SITE-DEN-12 [EVIDENCE E1]\n- tell them a fix is under way"


def _suffix():
    for node in ast.parse(open(APP).read()).body:
        if isinstance(node, ast.Assign) and node.targets[0].id == "J2_SUFFIX":
            return ast.literal_eval(node.value)
    raise AssertionError("J2_SUFFIX not found")


# ---------------------------------------------------------------- (1) the prompt and the re-ask
def test_reask_is_plain_format_only_and_quotes_nothing():
    asked = []
    j2.judge("PRIOR-ANSWER-TEXT without json", lambda q: asked.append(q) or "")
    (p,) = asked
    assert p == j2.REASK and "PRIOR-ANSWER-TEXT" not in p and "must be" not in p
    low = p.lower()
    assert not [w for w in INJECTION_LIKE if w in low], p
    assert len(p) < 240
    for key in ("disposition", "deciding_evidence", "reversible_step", "reason"):
        assert key in p


def test_primary_instruction_is_one_plain_closing_instruction():
    s = _suffix()
    low = s.lower()
    assert not [w for w in INJECTION_LIKE if w in low], s
    assert low.count("json") == 1 and low.startswith(" end with one line of json")
    for key in ("disposition", "deciding_evidence", "reversible_step", "reason", "named_evidence_needed"):
        assert '"%s"' % key in s


def test_role_prompts_keep_the_role_marker_and_network_asks_for_the_proposal():
    for role in ("customer", "it", "network"):
        src = open(os.path.join(REPO, "agents", "ifabric-" + role, "role.py")).read()
        assert "(ifabric-%s)" % role in src   # drive_trio and the rails resolve the role by it
    net = open(os.path.join(REPO, "agents", "ifabric-network", "role.py")).read()
    assert "proposed_action" in net and "change_risk" in net and "Always state a proposed resolution" in net


def test_blocked_reask_is_derived_not_a_blind_escalate():
    asked = []
    j = j2.judge(NONJSON, lambda p: asked.append(p))   # None: the guardrail blocked the re-ask
    assert asked == [j2.REASK]
    assert j.disposition == "gather-evidence" and j.precedence_rule == "guardrail-blocked-reask"
    assert j.model_disposition is None and j.valid is False and j.reasked is True
    assert j.deciding_evidence == ["E1"] and "guardrail" in j.reason


def test_blocked_reask_keeps_the_precedence_rules_and_the_label():
    j = j2.judge(NONJSON, lambda p: None, constraints={"maintenance_freeze": True})
    assert j.disposition == "escalate" and j.precedence_rule == "guardrail-blocked-reask"
    assert "maintenance freeze" in j.reason and "guardrail blocked the re-ask" in j.reason
    j = j2.judge(NONJSON, lambda p: None, tool_evidence=["{}"], evidence_needed=["the runbook id"])
    assert j.disposition == "gather-evidence" and j.named_evidence_needed == ["the runbook id"]
    assert j.precedence_rule == "guardrail-blocked-reask"
    j = j2.judge("- we should escalate this to the NOC", lambda p: None)
    assert j.disposition == "escalate"   # the safest disposition word in the answer
    j = j2.judge("- auto-resolve: the runbook covers it", lambda p: None, tool_evidence=["INC-1 found"])
    assert j.disposition == "gather-evidence"   # never auto-resolve without a structured answer
    j = j2.judge("", lambda p: None)   # no answer at all (the first call blocked too, e.g. ADV-H-01): escalate
    assert j.disposition == "escalate" and j.precedence_rule == "guardrail-blocked-reask"


def test_a_served_but_invalid_reask_still_escalates_invalid():
    j = j2.judge("nope", lambda p: "still nope")
    assert j.disposition == "escalate" and j.precedence_rule == "invalid-structured-output"


# ---------------------------------------------------------------- (2) the proposal
NET = ("- Probable root cause: optic loss on eth-1/7 [EVIDENCE E1]\n- Proposed resolution: move the slice from eth-1/7 "
       "to eth-1/8.\n- Change risk: low; revert by moving it back.")


def test_proposal_from_the_answer_text_when_j2_is_invalid():
    f = j2.derived_judgment(NET).to_record_fields()
    p = j2.proposal_of(f, NET)
    assert "eth-1/8" in p["resolution"] and "low" in p["change_risk"] and not j2.proposal_empty(p)
    p = j2.proposal_of(j2.invalid_judgment(["x"]).to_record_fields(), "- the twin is degraded on the site")
    assert p["resolution"] == "the twin is degraded on the site"   # no resolution sentence: the whole answer


def test_proposal_prefers_the_structured_fields():
    text = NET + '\n{"disposition": "auto-resolve", "deciding_evidence": ["E1"], "reason": "r", ' \
                 '"proposed_action": "switch to eth-1/8", "change_risk": "low"}'
    p = j2.proposal_of(j2.parse(text).to_record_fields(), text)
    assert p["resolution"] == "switch to eth-1/8" and p["change_risk"] == "low"


@pytest.mark.parametrize("prop,empty", [(None, True), ("", True), ("  ", True), ({}, True),
                                        ({"resolution": ""}, True), ({"resolution": " ", "disposition": "x"}, True),
                                        ({"resolution": "switch"}, False), ("switch", False)])
def test_proposal_empty(prop, empty):
    assert j2.proposal_empty(prop) is empty


def test_no_proposal_judgment():
    j = j2.no_proposal_judgment()
    assert j.disposition == "gather-evidence" and j.precedence_rule == "no-proposal" and j.valid
    assert j.named_evidence_needed == ["the network team's proposed change and its risk"]
    assert j.reason.startswith("no proposal received")
    assert j2.no_proposal_judgment({"restricted_change": True}).disposition == "escalate"


def test_orchestrator_treats_an_empty_proposal_as_none():
    src = open(os.path.join(REPO, "prooflab", "adapters", "orchestrator", "run.py")).read()
    assert 'if not str(proposal.get("resolution") or "").strip():' in src


# ---------------------------------------------------------------- dynamic: the REAL app (Strands 3.12)
needs312 = pytest.mark.skipif(not os.path.exists(PY312), reason="the Strands 3.12 venv is absent")
_RUNS = {}


def _run(script, args):
    key = (script,) + tuple(args)
    if key not in _RUNS:
        out = os.path.join(tempfile.mkdtemp(prefix="pr38-"), "out.json")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for k in ("TOOL_MCP_URL", "AGENTCORE_GATEWAY_MCP_URL", "IFABRIC_RAILS_MODE", "AGENT_NAME"):
            env.pop(k, None)
        p = subprocess.run([PY312, os.path.join(REPO, "tests", script)] + list(args) + ["--out", out], cwd=REPO,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=240)
        assert p.returncode == 0, p.stdout.decode("utf-8", "replace")[-3000:]
        assert b"record-rejected" not in p.stdout, "a record failed the contract"
        with open(out) as fh:
            _RUNS[key] = json.load(fh)
    return _RUNS[key]


def loop(*args):
    return _run("it_loop/drive_loop.py", ["--mode", "enforce"] + list(args))


def trio(variant):
    return _run("negotiation/drive_trio.py", ["S1", "--variant", variant])


@needs312
def test_real_app_reask_blocked_is_recorded_and_derived():
    d = loop("--results", "h", "--nonjson", "--block-reask")
    assert d["model_calls"] == 3 and len(d["dispatched"]) == 1   # tool turn, answer, the one (blocked) re-ask
    assert d["prompts"][-1] == j2.REASK
    acts = [r for r in d["records"] if r.get("ep.id") == "EP-1" and r.get("record_kind") == "action"]
    assert [r["outcome.real"] for r in acts] == ["SERVED", "SERVED", "BLOCKED_GUARDRAIL"]
    (g,) = [r for r in d["records"] if r.get("ep.id") == "EP-7"]
    assert g["outcome.real"] == "BLOCKED_GUARDRAIL" and g["lifecycle.event"] == "guardrail-blocked"
    jf = d["result"]["judgment"]
    assert d["result"]["disposition"] == "gather-evidence" and jf["precedence_rule"] == "guardrail-blocked-reask"
    assert jf["model_disposition"] is None and jf["valid"] is False and jf["reasked"] is True


@needs312
def test_real_app_negotiate_loop_stops_after_k_lookups():
    d = loop("--results", "e" * 12, "--negotiate", "move the slice from eth-1/7 to eth-1/8")
    k = d["pin"]["c16"]["tool_no_evidence_limit"]
    assert len(d["dispatched"]) == k and d["model_calls"] == k   # P1: 28 calls here
    assert d["prompts"][0].startswith("NEGOTIATION (Gateway C)")
    res = d["result"]
    assert res["position"] == "gather-evidence" and res["halted"] is False and not res.get("error")
    assert res["judgment"]["precedence_rule"] == "tool-no-evidence-limit"
    assert len([r for r in d["records"] if r.get("rail.id") == "T-07"]) == 1
    assert [r for r in d["records"] if r.get("phase") == "negotiation"]


@needs312
def test_real_app_empty_proposal_answers_in_code():
    d = loop("--results", "e" * 12, "--negotiate", "")
    assert d["model_calls"] == 0 and d["dispatched"] == []   # no model call, no tool call
    res = d["result"]
    assert res["position"] == "gather-evidence" and res["disposition"] == "gather-evidence"
    assert res["judgment"]["precedence_rule"] == "no-proposal"
    (neg,) = [r for r in d["records"] if r.get("phase") == "negotiation"]
    assert "position=gather-evidence" in neg["detail"] and "proposed change and its risk" in neg["detail"]
    assert [r for r in d["records"] if r.get("phase") == "ifabric.judgment"]


def _by_call(d):
    return [(r["agent"], r["negotiate"], r["result"]) for r in d["results"]]


@needs312
def test_p1_replay_ends_sane_and_bounded():
    d = trio("p1")
    assert d["rc"] == 0
    (cu, _, c), (it, _, i1), (nw, _, n), (it2, neg, i3) = _by_call(d)
    assert (cu, it, nw, it2, neg) == ("ifabric-customer", "ifabric-it", "ifabric-network", "ifabric-it", True)
    for r in (c, n):
        assert r["disposition"] == "gather-evidence"
        assert r["judgment"]["precedence_rule"] == "guardrail-blocked-reask"
    assert i1["judgment"]["precedence_rule"] == "tool-no-evidence-limit"
    assert "eth-1/8" in n["proposal"]["resolution"] and "low" in n["proposal"]["change_risk"]
    assert i3["position"] == "gather-evidence" and i3["judgment"]["precedence_rule"] == "tool-no-evidence-limit"
    recs = d["records"]
    assert len([r for r in recs if r.get("ep.id") == "EP-7"]) == 2
    assert len([r for r in recs if r.get("rail.id") == "T-07"]) == 2
    assert [r for r in recs if r.get("phase") == "negotiation"]
    assert i3["tally_calls"] <= 15 and not any(r["halted"] for _, _, r in _by_call(d))   # P1: 41 calls, halted


@needs312
def test_p1_replay_with_an_empty_proposal():
    d = trio("p1-empty")
    (_, _, n), (_, neg, i3) = _by_call(d)[2:]
    assert neg and j2.proposal_empty(n["proposal"])
    assert n["disposition"] == "escalate"   # the network returned no text at all: its derived judgment escalates
    # IT answers in code (no-proposal reason), floored at the proposer's escalate (Gateway C: never less safe)
    assert i3["position"] == "escalate" and i3["judgment"]["precedence_rule"] == "proposal-disposition"
    assert "no proposal received" in i3["judgment"]["reason"]
    assert i3["tally_calls"] == n["tally_calls"]   # Gateway C made no model call
    h3 = [r for r in d["records"] if r.get("ep.id") == "EP-3" and str(r.get("handoff.id") or "").endswith(":h3")]
    assert h3 == []   # and no tool call
    assert [r for r in d["records"] if r.get("phase") == "negotiation"]


@needs312
@pytest.mark.parametrize("variant", ["p1", "p1-empty"])
def test_p1_replay_kit_negotiation_check_holds(variant):
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import kit_grade
    if not (os.path.exists(kit_grade.KIT_SCORE) and os.path.exists(kit_grade.KIT_INVENTORY)):
        pytest.skip("workshop kit score-run.py not present")
    d = trio(variant)
    out = kit_grade.grade(kit_grade.read_records("".join(json.dumps(r) + "\n" for r in d["records"])), d["cid"], "S1")
    assert out["checks"]["cross-domain negotiation recorded"][0], out["output"]
    assert out["checks"]["disposition recorded, not inferred"][0], out["output"]
