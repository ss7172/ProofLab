"""The kit cross-check (plan T4.7): the workshop kit's own `evaluate.py 16` run on a gateway-log built from OUR
store, next to our verdict. Stdlib, 3.9. Default-tier runs only (the kit knows nothing of tiers or risk).

`build_gateway_log(records, run_id)` -> `{"records": [...]}` in the kit's shape (`modaas.run_id`, `modaas.action_id`,
`gen_ai.usage.*_tokens`), model-call spans only (a gateway llm metric, or an inferred guardrail block carrying 0/0),
deduplicated by action id (the first record id in sort order wins; a span with no action id cannot be deduplicated and
is kept, and counted in `no_action_id`). `write(dir, run_id, log)` -> `<dir>/kit-crosscheck/<CID>/gateway-log.json`.
`run_kit` runs the kit's script on that folder (a subprocess; the register path is the caller's). `compare` puts the
kit's label next to our verdict: a disagreement is FLAGGED with both sides, never resolved.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from prooflab.contract import verdicts as _v
from prooflab.stitch import mon02 as _mon02

MODEL_CALL_KINDS = ("metric", "platform_decision")


def is_model_call_span(rec: dict) -> bool:
    return (rec.get("authorship") == "PLATFORM" and rec.get("observed.clock") == _mon02.GATEWAY_CLOCK
            and rec.get("record_kind") in MODEL_CALL_KINDS
            and rec.get("tokens.in") is not None and rec.get("tokens.out") is not None)


def build_gateway_log(records, run_id: str) -> dict:
    spans = sorted((r for r in records if (r.get("run.id") or r.get("correlation_id")) == run_id
                    and is_model_call_span(r)), key=lambda r: (r.get("observed.at") or "", r.get("record_id") or ""))
    seen, out, no_id = set(), [], 0
    for r in spans:
        call = r.get("call.id")
        if call:
            if call in seen:
                continue
            seen.add(call)
        else:
            no_id += 1
        row = {"modaas.run_id": run_id, "gen_ai.usage.input_tokens": r["tokens.in"],
               "gen_ai.usage.output_tokens": r["tokens.out"], "protocol": "llm"}
        if call:
            row["modaas.action_id"] = call
        if r.get("model.id"):
            row["gen_ai.request.model"] = r["model.id"]
        out.append(row)
    return {"records": out, "no_action_id": no_id}


def write(out_dir: str, run_id: str, log: dict) -> str:
    d = os.path.join(out_dir, "kit-crosscheck", run_id)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "gateway-log.json")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(log, sort_keys=True, indent=1) + "\n")
    return p


def run_kit(evaluate_py: str, evidence_dir: str, run_id: str, register: str, python=None, control="16") -> dict:
    """-> {exit_code, label, line}. The kit exits 0 / 1 / 2; the verdict line is the one that starts `<LABEL>:`."""
    proc = subprocess.run([python or sys.executable, evaluate_py, control, run_id, "--evidence-dir", evidence_dir,
                           "--register", register], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    lines = proc.stdout.strip().splitlines()
    label, line = None, (lines[0] if lines else "")
    for cand in lines:
        hit = [l for l in _v.KIT_LABEL_TO_VERDICT if cand.startswith(l + ":")]
        if hit:
            label, line = hit[0], cand
            break
    return {"exit_code": proc.returncode, "label": label, "line": line}


def compare(kit_label, our_verdict: str, run_id: str) -> dict:
    """Both sides stay in the result. `agree` is False on any difference, including a kit label we cannot read."""
    mapped = _v.KIT_LABEL_TO_VERDICT.get(kit_label)
    ours_label = _v.kit_label(our_verdict)
    agree = mapped is not None and mapped == our_verdict
    out = {"run_id": run_id, "kit_label": kit_label, "kit_as_verdict": mapped, "our_verdict": our_verdict,
           "our_kit_label": ours_label, "agree": agree}
    if not agree:
        out["flag"] = "DISAGREEMENT: shown, never resolved; neither side is overwritten"
    return out
