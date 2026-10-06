"""EP-0 (D13) pin-only rule, creds-expiry fallback, secret hygiene, pin join without model-call fields."""
import copy
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from prooflab.adapters.orchestrator import common, preflight  # noqa: E402
from prooflab.evaluators.approval import check_versions  # noqa: E402

A = "ifabric-it"
DIG = "sha256:" + "ab" * 32
SECRET = "LEDGER-TOKEN-VALUE-XYZ"


def spec(pin="1" * 64, mode="observe", image=DIG, models=("m1",), tools=("t1",), reg="v0-pilot", extra=None):
    env = {"IFABRIC_PIN_JSON": "{...%s}" % pin[:4], "IFABRIC_PIN_SHA256": pin, "IFABRIC_REGISTER_SHA256": "2" * 64,
           "IFABRIC_REGISTER_VERSION": reg, "IFABRIC_RAILS_MODE": mode, "AUDIT_WRITE_TOKEN": SECRET}
    env.update(extra or {})
    return {"image_digest": image, "models": list(models), "tools": list(tools), "env": env}


def doc(live, approved="same", gen=2, agen=1, paused=False, approved_keys=None, model="m1"):
    if approved == "same":
        approved = spec()
    d = {"policy": "block-assessed",
         "approved": {A: approved_keys if approved_keys is not None else [DIG + "|" + model]},
         "running": {A: {"image_digest": live["image_digest"], "model": model, "paused": paused,
                         "generation": gen, "approved_generation": agen}},
         "specs": {A: {"live": live, "approved": approved}}}
    return d


def run(d, assessed=True):
    t = []
    steps, _ = preflight.ep0(d, assessed, [A], check_versions, treatments=t)
    return steps, t


def test_pin_only_patch_passes_and_is_recorded():
    steps, t = run(doc(spec(pin="3" * 64, mode="enforce", reg="v1")))
    assert steps[0]["ok"], steps
    assert len(t) == 1 and t[0]["kind"] == "declared_treatment" and t[0]["generation"] == 2
    assert t[0]["from_pin_sha256"] == "1" * 64 and t[0]["to_pin_sha256"] == "3" * 64
    assert (t[0]["from_rails_mode"], t[0]["to_rails_mode"]) == ("observe", "enforce")
    assert "declared treatment" in steps[0]["detail"]


def test_image_model_tool_other_env_block():
    cases = {
        "image": spec(image="sha256:" + "cd" * 32),
        "model": spec(models=("m2",)),
        "tools": spec(tools=("t1", "t2")),
        "env": spec(extra={"STEP_BASE": "9"}),
    }
    for name, live in cases.items():
        d = doc(live, model="m2" if name == "model" else "m1",
                approved_keys=[live["image_digest"] + "|" + ("m2" if name == "model" else "m1")] if name in ("image", "model") else None)
        steps, t = run(d)
        assert not steps[0]["ok"], name
        assert t == [], name


def test_paused_blocks_even_for_pin_only():
    steps, t = run(doc(spec(pin="3" * 64), paused=True))
    assert not steps[0]["ok"] and "paused" in steps[0]["detail"]


def test_no_approval_blocks():
    steps, _ = run(doc(spec(pin="3" * 64), approved_keys=[]))
    assert not steps[0]["ok"] and "no approved version" in steps[0]["detail"]


def test_approval_for_a_different_image_blocks():
    steps, _ = run(doc(spec(pin="3" * 64), approved_keys=["sha256:" + "ee" * 32 + "|m1"]))
    assert not steps[0]["ok"]


def test_record_only_policy_and_unassessed_runs_do_not_block():
    d = doc(spec(extra={"STEP_BASE": "9"}))
    steps, _ = run(d)
    assert not steps[0]["ok"]
    steps, _ = run(d, assessed=False)
    assert steps[0]["ok"] and "RECORDED (not gating)" in steps[0]["detail"]
    d["policy"] = "record-only"
    steps, _ = run(d)
    assert steps[0]["ok"] and "not gating" in steps[0]["detail"]


def test_fallback_when_approved_spec_missing_is_declared():
    d = doc(spec(pin="3" * 64), approved=None)
    steps, t = run(d)
    assert steps[0]["ok"], steps
    assert t[0]["basis"].startswith("attestation-fallback") and "attestation fallback" in steps[0]["detail"]
    d = doc(spec(pin="3" * 64, image="sha256:" + "cd" * 32), approved=None)
    steps, _ = run(d)
    assert not steps[0]["ok"]


def test_no_live_spec_with_stale_generation_blocks():
    d = doc(spec())
    d["specs"] = {}
    steps, _ = run(d)
    assert not steps[0]["ok"] and "stale" in steps[0]["detail"]


def test_same_generation_is_unchanged_pass_and_not_a_treatment():
    steps, t = run(doc(spec(), gen=2, agen=2))
    assert steps[0]["ok"] and t == []


def test_secrets_never_in_records():
    steps, t = run(doc(spec(pin="3" * 64, mode="enforce")))
    blob = json.dumps([steps, t])
    assert SECRET not in blob and "AUDIT_WRITE_TOKEN" not in blob and "{...3333}" not in blob
    # a changed secret env value blocks, and its value is not echoed either, only the key name
    live = spec(extra={"AUDIT_WRITE_TOKEN2": SECRET + "2"})
    steps, t = run(doc(live))
    assert not steps[0]["ok"] and SECRET not in json.dumps([steps, t])


# --- credentials expiry -----------------------------------------------------------------------------------------

class _Proc:
    def __init__(self, rc=1, out=""):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def _no_exp(argv, **kw):
    return _Proc(0, json.dumps({"AccessKeyId": "x", "SecretAccessKey": "y"}))   # no Expiration


def test_creds_fallback_file(tmp_path):
    f = tmp_path / "creds-expiry.txt"
    f.write_text("2026-10-06T13:52:47Z\n")
    exp = preflight.resolve_expiry(_no_exp, path=str(f))
    assert exp == dt.datetime(2026, 10, 6, 13, 52, 47)
    assert preflight.resolve_expiry(_no_exp, explicit="2026-10-06T10:00:00Z", path=str(f)) == dt.datetime(2026, 10, 6, 10)


def test_creds_fail_closed_without_any_source(tmp_path):
    exp = preflight.resolve_expiry(_no_exp, path=str(tmp_path / "missing.txt"))
    assert exp is None
    bad = tmp_path / "bad.txt"
    bad.write_text("not a time")
    assert preflight.resolve_expiry(_no_exp, path=str(bad)) is None
    assert not preflight.check_credentials(None, dt.datetime(2026, 10, 6), common.load_budget())["ok"]


# --- the pin join without model-call fields ------------------------------------------------------------------------

def test_pin_join_tolerates_missing_model_call_fields():
    recs = [{"record_kind": "lifecycle", "run.id": "c1", "pin.sha256": "p" * 64},
            {"record_kind": "model_call", "run.id": "c1"},                 # no pin.sha256, no runtime.session_id
            {"record_kind": "model_call", "run.id": "c2"},
            {"record_kind": "handoff", "run.id": "c3", "ifabric.pin_sha256": "q" * 64}]
    by = preflight.pin_by_run(recs)
    assert preflight.pin_of(recs[1], by) == "p" * 64
    assert preflight.pin_of(recs[2], by) is None
    assert preflight.pin_of({"record_kind": "model_call", "run.id": "c3"}, by) == "q" * 64
    assert preflight.pin_of({}, by) is None


def test_runtime_extra_pin_keys_cannot_widen_the_declared_set():
    d = doc(spec(extra={"OTHER": "changed"}), approved=spec(extra={"OTHER": "orig"}))
    d["extra_pin_keys"] = ["OTHER"]
    steps, t = run(d)
    assert not steps[0]["ok"] and t == []
