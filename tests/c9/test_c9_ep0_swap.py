"""PR-41: EP-0 passes a model change ONLY for the declared named run (N8) in the pinned register; all else blocks."""
import argparse
import hashlib
import os

from prooflab.adapters.orchestrator import conditions, preflight
from prooflab.adapters.orchestrator import run as R
from prooflab.evaluators.approval import check_versions

A = "ifabric-it"
DIG = "sha256:" + "ab" * 32
FROM, TO = "nemotron-super-120b", "nemotron-nano-9b"
DECL = [{"label": "N8", "kind": "model-swap", "agent": A, "from_model": FROM, "to_model": TO}]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def spec(models=(FROM,), pin="1" * 64, image=DIG):
    env = {"IFABRIC_PIN_JSON": "{}", "IFABRIC_PIN_SHA256": pin, "IFABRIC_REGISTER_SHA256": "2" * 64,
           "IFABRIC_REGISTER_VERSION": "v1", "IFABRIC_RAILS_MODE": "observe"}
    return {"image_digest": image, "models": list(models), "tools": ["runbook-lookup"], "env": env}


def versions(live_model=TO, approved_spec=True, gen=5, agen=4, live=None):
    live = live or spec(models=(live_model,))
    return {"policy": "block-assessed", "approved": {A: [DIG + "|" + FROM]},
            "running": {A: {"image_digest": live["image_digest"], "model": live_model, "paused": False,
                            "generation": gen, "approved_generation": agen}},
            "specs": {A: {"live": live, "approved": spec() if approved_spec else None}}}


def ep0(v, named_run, decl=DECL):
    t = []
    steps, decisions = preflight.ep0(v, True, [A], check_versions, treatments=t, named_run=named_run,
                                     declarations=decl)
    return steps, decisions, t


def test_declared_n8_swap_passes_for_n8_and_is_recorded_with_both_models():
    steps, decisions, t = ep0(versions(), "N8")
    assert steps[0]["ok"], steps
    assert decisions[0].verdict == "ALLOW" and decisions[0].action == "proceed"      # check_versions ALLOWs too
    assert len(t) == 1 and t[0]["verdict"] == "model-swap" and t[0]["kind"] == "declared_treatment"
    assert t[0]["model_swap"] == {"label": "N8", "from_model": FROM, "to_model": TO}
    assert "model-swap %s -> %s for named run N8" % (FROM, TO) in steps[0]["detail"]


def test_declared_swap_passes_on_the_attestation_fallback_too():
    steps, _, t = ep0(versions(approved_spec=False), "N8")
    assert steps[0]["ok"], steps
    assert t and t[0]["model_swap"]["to_model"] == TO


def test_declared_swap_when_the_swapped_generation_was_re_approved():
    steps, decisions, t = ep0(versions(gen=5, agen=5), "N8")      # no stale path: check_versions alone
    assert steps[0]["ok"] and decisions[0].verdict == "ALLOW"
    assert t and t[0]["basis"] == "declared-model-swap"


def test_the_same_swap_on_any_other_run_blocks():
    for label in (None, "N7", "N9", "n8"):
        steps, decisions, t = ep0(versions(), label)
        assert not steps[0]["ok"], label
        assert t == [], label


def test_an_undeclared_model_blocks_even_for_n8():
    steps, _, t = ep0(versions(live_model="nemotron-nano-3-30b"), "N8")
    assert not steps[0]["ok"] and t == []
    steps, _, _ = ep0(versions(), "N8", decl=[])                 # no declaration in the pinned register
    assert not steps[0]["ok"]


def test_swap_with_another_change_still_blocks():
    live = spec(models=(TO,), image="sha256:" + "cd" * 32)
    steps, _, t = ep0(versions(live=live), "N8")
    assert not steps[0]["ok"] and t == []
    live = spec(models=(TO,))
    live["env"]["STEP_BASE"] = "9"
    steps, _, _ = ep0(versions(live=live), "N8")
    assert not steps[0]["ok"]


def test_declaration_for_another_agent_does_not_cover_ifabric_it():
    decl = [dict(DECL[0], agent="ifabric-network")]
    steps, _, _ = ep0(versions(), "N8", decl=decl)
    assert not steps[0]["ok"]


def test_the_revert_after_n8_is_not_a_model_change_and_passes_as_pin_only():
    live = spec(models=(FROM,))
    steps, _, t = ep0(versions(live_model=FROM, live=live, gen=6, agen=4), "N9")
    assert steps[0]["ok"], steps
    assert t and t[0]["verdict"] == "pin-only" and not t[0].get("model_swap")


# ---- the orchestrator reads the declaration from the PINNED register only -----------------------------------------

def _args(tmp_path, named_run="N8", text=None, sha=None):
    reg = tmp_path / "v1.yaml"
    data = (text or open(os.path.join(ROOT, "register", "register.yaml"), encoding="utf-8").read()).encode("utf-8")
    reg.write_bytes(data)
    pin = {"register_version": "v1", "register_sha256": sha or hashlib.sha256(data).hexdigest()}
    return argparse.Namespace(named_run=named_run, register_file=str(reg)), pin


def test_named_run_reads_the_pinned_register(tmp_path):
    args, pin = _args(tmp_path)
    steps, decl = R.named_run_declarations(args, pin)
    assert steps[0]["ok"] and "ifabric-it %s -> %s" % (FROM, TO) in steps[0]["detail"]
    assert decl[0]["label"] == "N8"


def test_named_run_refuses_an_unpinned_register(tmp_path):
    args, pin = _args(tmp_path, sha="0" * 64)
    steps, decl = R.named_run_declarations(args, pin)
    assert not steps[0]["ok"] and decl == []
    steps, decl = R.named_run_declarations(argparse.Namespace(named_run="N8", register_file=None), {})
    assert not steps[0]["ok"]


def test_no_named_run_declares_nothing(tmp_path):
    args, pin = _args(tmp_path, named_run=None)
    assert R.named_run_declarations(args, pin) == ([], [])


def test_warm_up_is_a_text_free_exploratory_condition():
    c = conditions.load_condition("warm-up")
    assert c["text"] == "" and c["sha256"] is None
    ns = argparse.Namespace(provenance=None, condition="warm-up")
    assert R._provenance(ns, "run", False) == "EXPLORATORY"
