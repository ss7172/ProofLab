"""J2 tests. All answers are SYNTHETIC, shaped like the reference agents' free-text replies."""
import importlib.util
import os

_p = os.path.join(os.path.dirname(__file__), "..", "..", "adapters", "runtime", "j2.py")
_s = importlib.util.spec_from_file_location("j2", _p)
j2 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(j2)

OBJ = ('{"disposition": "%s", "deciding_evidence": ["E1", "rec-7"], "reversible_step": "restart port",'
       ' "reason": "latency matches link flap"}')
FENCED = "Summary of findings (synthetic).\n```json\n" + OBJ % "gather-evidence" + "\n```\n"


def test_fenced_and_bare():
    assert j2.parse(FENCED).disposition == "gather-evidence"
    assert j2.parse("Done. " + OBJ % "escalate").disposition == "escalate"


def test_resolve_alias_and_think_tags():
    t = "<think>maybe {\"disposition\": \"escalate\"}</think>" + OBJ % "resolve"
    j = j2.parse(t)
    assert j.valid and j.disposition == "auto-resolve"
    assert j2.parse("reasoning {\"disposition\":\"escalate\"} </think> " + OBJ % "gather-evidence").disposition == "gather-evidence"


def test_last_valid_wins():
    t = OBJ % "escalate" + "\nCorrection:\n" + OBJ % "gather-evidence"
    assert j2.parse(t).disposition == "gather-evidence"
    # last object invalid -> earlier valid one is used
    t2 = OBJ % "escalate" + ' {"disposition": "dunno", "reason": "x"}'
    assert j2.parse(t2).disposition == "escalate"


def test_malformed():
    for t in ["", "no json here", '{"disposition": "escalate", ', '{"disposition": "bogus", "reason": "r", "deciding_evidence": []}',
              '{"disposition": "escalate", "reason": "", "deciding_evidence": []}',
              '{"disposition": "escalate", "reason": "r"}',
              '{"disposition": "resolve", "reason": "r", "deciding_evidence": []}']:
        j = j2.parse(t)
        assert not j.valid and j.errors and j.disposition == "escalate", t


def test_precedence_freeze_escalates():
    j = j2.apply_precedence(j2.parse(OBJ % "resolve"), {"maintenance_freeze": True}, ["data"])
    assert j.disposition == "escalate" and j.precedence_rule == "freeze-or-restricted"
    j = j2.apply_precedence(j2.parse(OBJ % "gather-evidence"), {"restricted_change": True})
    assert j.disposition == "escalate"


def test_precedence_empty_evidence_names_it():
    for ev in ([], ["no twin data"], ["{}", ""]):
        j = j2.apply_precedence(j2.parse(OBJ % "resolve"), None, ev, ["twin data for site S1"])
        assert j.disposition == "gather-evidence" and j.named_evidence_needed == ["twin data for site S1"]
        assert j.precedence_rule == "empty-evidence"
    j = j2.apply_precedence(j2.parse(OBJ % "resolve"), None, ["latency 40ms"])
    assert j.disposition == "auto-resolve" and j.precedence_rule == ""


def test_never_moves_toward_less_safe():
    j = j2.apply_precedence(j2.parse(OBJ % "escalate"), None, [])
    assert j.disposition == "escalate" and j.precedence_rule == ""


def test_freeze_beats_empty():
    j = j2.apply_precedence(j2.parse(OBJ % "resolve"), {"maintenance_freeze": True}, [])
    assert j.precedence_rule == "freeze-or-restricted"


def test_site_ids():
    assert j2.resolve_site_ids(["e1", "e2", "e3"], {"e1": "S1", "e2": "S1"}) == (["S1"], ["e3"])


def test_reask_path():
    calls = []

    def ask(p):
        calls.append(p)
        return OBJ % "gather-evidence"
    j = j2.judge("rambling answer without json", ask)
    assert len(calls) == 1 and "disposition" in calls[0]
    assert j.valid and j.reasked and j.disposition == "gather-evidence"


def test_reask_not_called_when_valid():
    j = j2.judge(FENCED, lambda p: 1 / 0)
    assert j.valid and not j.reasked


def test_second_failure_escalates_invalid():
    calls = []
    j = j2.judge("nope", lambda p: calls.append(p) or "still nope")
    assert len(calls) == 1
    assert j.disposition == "escalate" and j.reason == "invalid-structured-output" and not j.valid


def test_halted_and_record_fields():
    h = j2.halted_judgment()
    assert h.disposition == "escalate" and h.reason == "c16-budget-halt"
    f = j2.parse(FENCED).to_record_fields()
    assert {"disposition", "deciding_evidence", "reversible_step", "precedence_rule", "reason"} <= set(f)


def test_never_structured_output():
    src = open(_p).read()
    assert "structured_output(" not in src.replace("Strands structured_output()", "")
