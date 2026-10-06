"""PR-41: tools/c9_model_swap.py generates (never applies) the N8 swap and its exact revert. Offline."""
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("c9_model_swap", os.path.join(ROOT, "tools", "c9_model_swap.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def cr(models=("nemotron-super-120b",), model_ref=None, name="ifabric-it"):
    spec_ = {"dependsOn": {"models": list(models), "tools": ["runbook-lookup"]}, "paused": False}
    if model_ref is not None:
        spec_["modelRef"] = model_ref
    return {"metadata": {"name": name, "namespace": "components"}, "spec": spec_}


def test_swap_sets_both_fields_and_revert_deletes_an_absent_model_ref(tmp_path):
    doc = S.plan("ifabric-it", "nemotron-nano-9b", cr(), out_dir=str(tmp_path))
    assert doc["swap_patch"] == {"spec": {"modelRef": "nemotron-nano-9b", "dependsOn": {"models": ["nemotron-nano-9b"]}}}
    assert doc["revert_patch"] == {"spec": {"modelRef": None, "dependsOn": {"models": ["nemotron-super-120b"]}}}
    assert "tools" not in doc["swap_patch"]["spec"]["dependsOn"]          # merge patch keeps the tools list
    assert doc["register_declaration"] == "N8:model-swap:ifabric-it:nemotron-super-120b:nemotron-nano-9b"
    assert doc["notes"] == []


def test_revert_restores_a_present_model_ref_exactly(tmp_path):
    doc = S.plan("ifabric-it", "nemotron-nano-9b", cr(model_ref="nemotron-super-120b"), out_dir=str(tmp_path))
    assert doc["revert_patch"]["spec"]["modelRef"] == "nemotron-super-120b" and doc["pre_swap_modelRef_present"]


def test_filtered_status_view_is_accepted(tmp_path):
    view = {"name": "ifabric-it", "dependsOn": {"models": ["nemotron-super-120b"], "tools": ["runbook-lookup"]}}
    doc = S.plan("ifabric-it", "nemotron-nano-9b", view, out_dir=str(tmp_path))
    assert doc["from_model"] == "nemotron-super-120b"


def test_refusals():
    with pytest.raises(S.SwapError):
        S.plan("ifabric-it", "nemotron-super-120b", cr())                      # already on the target
    with pytest.raises(S.SwapError):
        S.plan("ifabric-it", "nemotron-nano-9b", cr(model_ref="nemotron-nano-3-30b"))   # modelRef != models[0]
    with pytest.raises(S.SwapError):
        S.plan("ifabric-it", "nemotron-nano-9b", cr(name="ifabric-network"))
    with pytest.raises(S.SwapError):
        S.plan("ifabric-it", "nemotron-nano-9b", {"spec": {"dependsOn": {"models": []}}})


def test_commands_are_hk_server_dry_run_and_never_run(tmp_path, monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("the tool must never run a command"))
    src = tmp_path / "cr.json"
    src.write_text(json.dumps(cr()), encoding="utf-8")
    assert S.main(["patches", "--current", str(src), "--out-dir", str(tmp_path / "out")]) == 0
    swap = json.loads((tmp_path / "out" / "ifabric-it-swap-nemotron-nano-9b.json").read_text())
    revert = json.loads((tmp_path / "out" / "ifabric-it-revert-nemotron-super-120b.json").read_text())
    assert swap["spec"]["modelRef"] == "nemotron-nano-9b" and revert["spec"]["modelRef"] is None
    doc = S.plan("ifabric-it", "nemotron-nano-9b", cr(), out_dir=str(tmp_path / "out"))
    assert doc["swap"]["dry_run"].startswith(S.HK + " 'kubectl patch agentconfig ifabric-it -n components --type merge")
    assert doc["swap"]["dry_run"].endswith("--dry-run=server -o json'")
    assert "--dry-run" not in doc["swap"]["apply"]
    assert doc["precheck"] == S.HK + " 'kubectl get modelconfig nemotron-nano-9b -n components -o json'"
    assert os.path.isabs(doc["swap_file"])


def test_no_current_assumes_and_says_so(tmp_path):
    doc = S.plan("ifabric-it", "nemotron-nano-9b", None, out_dir=str(tmp_path))
    assert doc["revert_patch"]["spec"] == {"modelRef": None, "dependsOn": {"models": ["nemotron-super-120b"]}}
    assert doc["notes"] and "ASSUMES" in doc["notes"][0]


def mc(phase="Approved", paused=False, reg="APPROVED"):
    return {"metadata": {"name": "nemotron-nano-9b"}, "spec": {"paused": paused},
            "status": {"phase": phase, "registryApprovalStatus": reg}}


def test_precheck_approved_and_not_paused():
    assert S.precheck(mc())[0] is True
    assert S.precheck(mc(phase="Reviewing"))[0] is False
    assert S.precheck(mc(paused=True))[0] is False
    assert S.precheck(mc(reg="PENDING"))[0] is False
    with pytest.raises(S.SwapError):
        S.precheck({"status": {}})
