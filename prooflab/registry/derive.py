"""Threshold derivation from the pilots (ARCH §5.4 step 5; DC-11). Stdlib, Python 3.9.

    items = derive_all(records, rules, rules_sha256)

`records` come from `register/experiments/experiments.jsonl`, one JSON object per line:
  {"run_id": "...", "scenario": "S1|S2|S3", "provenance": "PILOT|BASELINE", "condition": "none|...", "mode": "observe",
   "measured": {"c16_tokens": N, "c7_gap_ms_max": N, "c9_latency_max_ms": {"<runtime>": N}}}
`rules` is the pre-registered rule file (JSON, frozen with v0-pilot; its sha256 is cited in every derived value). The
NUMBERS (headroom, rounding, the owner's appetite) live in that file, never in this code. Each derived item carries:
the value, the pilot run ids it cites, the rule id and the rules-file sha256 ("it is what we achieved" is not an answer).

Refusals:
  * a C16 cap from S2 (or any run carrying a condition): the cap is never derived to force a breach (DeriveError);
  * halted, failed (incl. FAILED-UPSTREAM) and not-derivation-eligible runs feed no control; --use restricts all controls;
  * a normal need above the owner's appetite is NOT a reason to raise the cap: the item comes back with
    status NORMAL_NEED_ABOVE_APPETITE and no value (a finding about the agents, raised to the owner).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys


class DeriveError(ValueError):
    """A derivation the protocol refuses."""


def load_records(path: str) -> list:
    out = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError as exc:
                    raise DeriveError("experiments line %d: %s" % (n, exc))
    return out


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def exclusion_reason(r, rules):
    """Why a run may not feed any derivation, or None when it may. Halted, failed (incl. FAILED-UPSTREAM) and
    not-derivation-eligible runs are refused for EVERY control; scenario/provenance/condition follow the rules file."""
    if r.get("halted") is True:
        return "halted"
    if r.get("failed") is True or any("FAIL" in str(r.get(k) or "").upper() for k in ("status", "outcome", "result", "verdict")):
        return "failed (incl. FAILED-UPSTREAM)"
    if r.get("derivation_eligible") is False:
        return "not derivation-eligible"
    if r.get("scenario") not in set(rules.get("eligible_scenarios") or []):
        return "scenario %s is not eligible" % r.get("scenario")
    if r.get("provenance") not in ("PILOT", "BASELINE"):
        return "provenance %s is not PILOT/BASELINE" % r.get("provenance")
    if (r.get("condition") or "none") != "none":
        return "carries condition %s" % r.get("condition")
    return None


def partition(records, rules, cited_ids=None):
    """(used, excluded[(run_id, reason)]); with cited_ids only the cited runs can be used."""
    used, excluded = [], []
    cited = set(cited_ids or [])
    for r in records:
        why = exclusion_reason(r, rules)
        if why is None and cited_ids and r.get("run_id") not in cited:
            why = "not named by --use"
        if why:
            excluded.append((r.get("run_id"), why))
        else:
            used.append(r)
    return used, excluded


def _eligible(records, rules, label, cited_ids=None):
    if not (rules.get("eligible_scenarios") or []):
        raise DeriveError("%s: rules name no eligible_scenarios" % label)
    known = set(r.get("run_id") for r in records)
    for rid in cited_ids or []:
        if rid not in known:
            raise DeriveError("%s: --use names %s, which is not in the experiments file" % (label, rid))
    use, excluded = partition(records, rules, cited_ids)
    for rid, why in excluded:
        if cited_ids and rid in cited_ids:
            raise DeriveError("%s: --use names %s, which is refused (%s)" % (label, rid, why))
    if not use:
        raise DeriveError("%s: no eligible pilot run (excluded: %s)"
                          % (label, "; ".join("%s: %s" % x for x in excluded) or "none"))
    return use


def refuse_s2(records, rules, cited_ids=None):
    """Raise if a C16 cap would rest on a run outside the eligible set (S2, or any condition run)."""
    ok = set(rules.get("eligible_scenarios") or [])
    by_id = dict((r["run_id"], r) for r in records)
    for rid in cited_ids or []:
        r = by_id.get(rid)
        if r is None or r.get("scenario") not in ok or (r.get("condition") or "none") != "none":
            raise DeriveError("a C16 cap is never derived from %s (scenario %s, condition %s): only %s runs without a condition"
                              % (rid, (r or {}).get("scenario"), (r or {}).get("condition"), sorted(ok)))


def _scale(value: int, headroom_pct: int, step: int) -> int:
    scaled = _ceil_div(value * (100 + headroom_pct), 100)
    return _ceil_div(scaled, step) * step


def derive_c16(records, rules, rules_sha256, cited_ids=None) -> dict:
    refuse_s2(records, rules, cited_ids)
    use = [r for r in _eligible(records, rules, "C16", cited_ids)
           if isinstance((r.get("measured") or {}).get("c16_tokens"), int)]
    if not use:
        raise DeriveError("C16: no eligible run carries measured.c16_tokens")
    need = max(r["measured"]["c16_tokens"] for r in use)
    item = {"control_ref": "C16", "rule_id": rules["c16_rule_id"], "rules_sha256": rules_sha256,
            "normal_need_tokens": need, "cites": sorted(r["run_id"] for r in use)}
    cap = _scale(need, rules["c16_headroom_pct"], rules["c16_round_up_to"])
    appetite = rules.get("appetite_tokens")
    if appetite is not None and cap > appetite:
        item.update(status="NORMAL_NEED_ABOVE_APPETITE", value=None,
                    note="normal need with headroom exceeds the owner's appetite: a finding about the agents; the cap is not raised")
    else:
        item.update(status="DERIVED", value=cap)
    return item


def derive_c7_gap(records, rules, rules_sha256, cited_ids=None) -> dict:
    use = [r for r in _eligible(records, rules, "C7", cited_ids)
           if isinstance((r.get("measured") or {}).get("c7_gap_ms_max"), int)]
    if not use:
        raise DeriveError("C7: no eligible run carries measured.c7_gap_ms_max")
    need = max(r["measured"]["c7_gap_ms_max"] for r in use)
    return {"control_ref": "C7", "rule_id": rules["c7_rule_id"], "rules_sha256": rules_sha256, "status": "DERIVED",
            "normal_need_ms": need, "value": _scale(need, rules["c7_headroom_pct"], rules["c7_round_up_to"]),
            "cites": sorted(r["run_id"] for r in use)}


def derive_c9_baseline(records, rules, rules_sha256, cited_ids=None) -> dict:
    """Largest Maximum per (runtime, scenario) over the declared baseline-eligible runs (DC-11)."""
    use = _eligible(records, rules, "C9", cited_ids)
    values, cites = {}, set()
    for r in use:
        for runtime, ms in ((r.get("measured") or {}).get("c9_latency_max_ms") or {}).items():
            key = "%s_%s" % (runtime, r["scenario"])
            if key not in values or ms > values[key][0]:
                values[key] = (ms, r["run_id"])
            cites.add(r["run_id"])
    if not values:
        raise DeriveError("C9: no eligible run carries measured.c9_latency_max_ms")
    return {"control_ref": "C9", "rule_id": rules["c9_rule_id"], "rules_sha256": rules_sha256, "status": "DERIVED",
            "baseline_values": dict((k, v[0]) for k, v in sorted(values.items())),
            "max_run": dict((k, v[1]) for k, v in sorted(values.items())), "cites": sorted(cites)}


def derive_all(records, rules, rules_sha256, cited_ids=None) -> list:
    """cited_ids (--use) restricts ALL controls (C16, C7, C9), not only C16."""
    return [derive_c16(records, rules, rules_sha256, cited_ids), derive_c7_gap(records, rules, rules_sha256, cited_ids),
            derive_c9_baseline(records, rules, rules_sha256, cited_ids)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab register derive")
    ap.add_argument("--experiments", default="register/experiments/experiments.jsonl")
    ap.add_argument("--rules", required=True, help="the pre-registered rules file (JSON); its sha256 is cited")
    ap.add_argument("--use", help="comma-joined run ids every control (C16, C7, C9) may cite; halted, failed, ineligible, S2 or condition runs are refused")
    ns = ap.parse_args(argv)
    try:
        with open(ns.rules, "rb") as fh:
            raw = fh.read()
        rules, digest = json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
        records = load_records(ns.experiments)
        cited = [x for x in (ns.use or "").split(",") if x] or None
        used, excluded = partition(records, rules, cited)
        print("derive: used runs: %s" % (", ".join(r["run_id"] for r in used) or "none"), file=sys.stderr)
        for rid, why in excluded:
            print("derive: excluded %s: %s" % (rid, why), file=sys.stderr)
        items = derive_all(records, rules, digest, cited)
    except (DeriveError, OSError, ValueError, KeyError) as exc:
        print("derive refused: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(items, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
