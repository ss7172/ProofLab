"""The preflight = the budget guard (IMPLEMENTATION-PLAN 5.1) + EP-0 + the pin echo (ARCH 7.2 step 1).

The preflight holds no control verdict logic: EP-0 acts only on `action` from approval.check_versions; the
budget guard compares the ops lane's own limits (budget.json), not a control threshold.
"""
from __future__ import annotations

import datetime as _dt
import importlib
import hashlib
import json
import os
import subprocess
import time

from prooflab.adapters.orchestrator import common


class PreflightRefused(Exception):
    def __init__(self, steps):
        self.steps = steps
        super().__init__("; ".join("%s: %s" % (s["name"], s["detail"]) for s in steps if not s["ok"]))


def step(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": detail}


# --- bounds and the guard ------------------------------------------------------------------------------------

def bound_for(budget, scenario, mode, only=None, adversarial=False, override=None, gateway_c=False):
    """(bound tokens, class name) for this run. `override` is an explicit --bound (e.g. the pilots' CAP).
    gateway_c: a trio run that also makes Gateway C's one extra IT call adds bounds.gateway_c_extra."""
    bounds = budget["bounds"]
    if only:
        cls = "adversarial_single" if adversarial else "smoke_single"
    else:
        cls = budget["scenario_class"].get(scenario)
        if cls is None:
            raise ValueError("unknown scenario %r" % (scenario,))
        if cls == "s2":
            cls = "observe_s2" if mode == "observe" else "enforce_s2"
    if override is not None:
        return int(override), cls
    if gateway_c and not only:
        return int(bounds[cls]) + int(bounds["gateway_c_extra"]), cls + "+gateway_c"
    return int(bounds[cls]), cls


def is_observe_s2(scenario, mode, only=None):
    return scenario == "S2" and mode == "observe" and not only


def rolling(entries, now, budget):
    """Index entries (live runs that started) inside the rolling window ending at `now`."""
    start = now - _dt.timedelta(minutes=int(budget["rolling_window_minutes"]))
    out = []
    for e in entries:
        if e.get("dry_run") or not e.get("started_at") or e.get("event") in ("run.finished", "run.refused"):
            continue
        t = common.parse_utc(e["started_at"])
        if start <= t <= now:
            out.append((t, e))
    return out


def budget_guard(budget, now, tokens_in_window, bound, observe_s2_run, index_entries):
    """Returns a list of steps. `tokens_in_window` None (unknown) fails closed."""
    steps = []
    limit = int(budget["tokens_per_rolling_window"])
    if tokens_in_window is None:
        steps.append(step("budget.tokens", False, "tokens in the last rolling window unknown (fail closed)"))
    else:
        total = int(tokens_in_window) + int(bound)
        steps.append(step("budget.tokens", total <= limit,
                          "in window %d + this run's bound %d = %d vs limit %d" % (tokens_in_window, bound, total, limit)))
    recent = rolling(index_entries, now, budget)
    if observe_s2_run:
        n = sum(1 for _, e in recent if e.get("scenario") == "S2" and e.get("mode") == "observe" and not e.get("only"))
        cap = int(budget["observe_s2_runs_per_rolling_window"])
        steps.append(step("budget.observe_s2", n + 1 <= cap,
                          "%d observe S2 run(s) in the window, this would be %d of at most %d" % (n, n + 1, cap)))
    if recent:
        last = max(t for t, _ in recent)
        gap = (now - last).total_seconds()
        need = int(budget["min_spacing_seconds"])
        steps.append(step("budget.spacing", gap >= need, "%d s since the last run start, need %d" % (gap, need)))
    return steps


# --- identity, credentials, live headroom (all through one runner seam; fakes in tests) -------------------------

def check_identity(runner, budget):
    proc = runner(["aws", "sts", "get-caller-identity", "--query", "Arn", "--output", "text"],
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    arn = (proc.stdout or "").strip()
    ok = proc.returncode == 0 and budget["required_role"] in arn
    return step("identity", ok, "caller role matches %s" % budget["required_role"] if ok else "caller is not %s" % budget["required_role"])


def credential_expiry(runner):
    """Expiration of the current credentials as a datetime (only that field is read; the rest is dropped)."""
    proc = runner(["aws", "configure", "export-credentials", "--format", "process"],
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if proc.returncode != 0:
        return None
    try:
        doc = json.loads(proc.stdout)
        return common.parse_utc(doc["Expiration"].replace("+00:00", "").replace("Z", ""))
    except (ValueError, KeyError, TypeError):
        return None


CREDS_EXPIRY_FILE = os.path.join("~", "firstmate-homes", "TrustworthyAI", "ops-lane", "creds-expiry.txt")


def credential_expiry_file(path=None):
    """Fallback when the profile has no Expiration: a one-line ISO UTC timestamp the ops lane writes (from
    CloudTrail AssumeRole). None if the file is absent or unparseable (the caller then fails closed)."""
    try:
        with open(os.path.expanduser(path or CREDS_EXPIRY_FILE)) as fh:
            text = fh.readline().strip()
        return common.parse_utc(text.replace("+00:00", "").replace("Z", "")) if text else None
    except (OSError, ValueError, TypeError):
        return None


def resolve_expiry(runner, explicit=None, path=None):
    """--creds-expiry, else the CLI's Expiration, else the ops lane's creds-expiry.txt, else None (fail closed)."""
    if explicit:
        return common.parse_utc(explicit)
    return credential_expiry(runner) or credential_expiry_file(path)


def check_credentials(expiry, now, budget):
    if expiry is None:
        return step("credentials", False, "expiry unknown (fail closed)")
    minutes = (expiry - now).total_seconds() / 60.0
    need = int(budget["credential_min_remaining_minutes"])
    return step("credentials", minutes >= need, "%.0f min remaining, need %d (expires %sZ)" % (minutes, need, expiry.isoformat()))


HEADROOM_QUERY = ("filter attributes.listener = 'llm' | stats sum(attributes.gen_ai.usage.input_tokens) as tin, "
                  "sum(attributes.gen_ai.usage.output_tokens) as tout")


def tokens_in_window(runner, now, budget, sleep=time.sleep, polls=20):
    """Logs Insights on aws/spans (listener=llm, gen_ai.usage.*) over the rolling window. None if unavailable.
    UNVERIFIED offline: the field names follow the B1 fact; confirm in the ops lane's first headroom read."""
    end = int((now - _dt.datetime(1970, 1, 1)).total_seconds())
    start = end - int(budget["rolling_window_minutes"]) * 60
    p = runner(["aws", "logs", "start-query", "--log-group-name", "aws/spans", "--start-time", str(start),
                "--end-time", str(end), "--query-string", HEADROOM_QUERY, "--query", "queryId", "--output", "text"],
               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode != 0:
        return None
    qid = p.stdout.strip()
    for _ in range(polls):
        r = runner(["aws", "logs", "get-query-results", "--query-id", qid, "--output", "json"],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if r.returncode != 0:
            return None
        doc = json.loads(r.stdout or "{}")
        if doc.get("status") == "Complete":
            rows = doc.get("results") or []
            if not rows:
                return 0
            vals = {c["field"]: c["value"] for c in rows[0]}
            try:
                return int(float(vals.get("tin") or 0)) + int(float(vals.get("tout") or 0))
            except ValueError:
                return None
        sleep(2)
    return None


# --- EP-0 and the pin echo ---------------------------------------------------------------------------------------

def load_check_versions():
    """Lazy import: PR-09a may merge after this PR. A clear error if it is absent."""
    try:
        return importlib.import_module("prooflab.evaluators.approval").check_versions
    except (ImportError, AttributeError) as exc:
        raise RuntimeError("EP-0 needs prooflab.evaluators.approval.check_versions (PR-09a), not importable: %s" % exc)


def _field(decision, name):
    return decision.get(name) if isinstance(decision, dict) else getattr(decision, name, None)


def _agent_of(decision, agents):
    """Decision has no actor_id; approval.check_versions puts '<agent>: <why>' in `reason`. Fall back to a field."""
    named = _field(decision, "actor_id") or _field(decision, "agent")
    if named:
        return named
    reason = _field(decision, "reason") or ""
    for a in agents:
        if reason.startswith(a + ":"):
            return a
    return "agent"


def _normalise_running(rv):
    """Accept the legacy key `digest` as `image_digest`; everything else passes through unchanged."""
    rv = dict(rv)
    if "image_digest" not in rv and "digest" in rv:
        rv["image_digest"] = rv.pop("digest")
    return rv


# --- EP-0: declared pin treatments (D13 kept) --------------------------------------------------------------------

PIN_ENV_KEYS = ("IFABRIC_PIN_JSON", "IFABRIC_PIN_SHA256", "IFABRIC_REGISTER_SHA256", "IFABRIC_REGISTER_VERSION",
                "IFABRIC_RAILS_MODE")
SHA_KEYS = ("IFABRIC_PIN_SHA256", "IFABRIC_REGISTER_SHA256")      # the only env values a record may carry


def _vh(value):
    """Comparable fingerprint of an env value; the value itself is never kept."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _spec_view(spec):
    """Reduce a spec to {image, models, tools, env_fp:{key: fingerprint}}; env values are fingerprinted at once."""
    spec = spec or {}
    env = spec.get("env") or {}
    return {"image": spec.get("image_digest"), "models": sorted(spec.get("models") or []),
            "tools": sorted(spec.get("tools") or []), "env_fp": {k: _vh(v) for k, v in env.items()},
            "pins": {k: env.get(k) for k in SHA_KEYS if k in env},
            "mode": env.get("IFABRIC_RAILS_MODE"), "has_env": "env" in spec}


def pin_treatment(agent, live, approved, generation, approved_generation, approved_keys=None):
    """Compare the LIVE spec with the spec at the APPROVED generation.

    Returns (verdict, record): verdict "pin-only" (PASS, a declared treatment), "unchanged", or "block" with the
    reasons; `record` holds only digests, key names and the pin sha values (never other env values).
    live/approved = {"image_digest", "models", "tools", "env"}; `approved` None = the approved spec cannot be
    reconstructed: fall back to the attestation (same image digest + model as an approved key; tools if known)."""
    keys = set(PIN_ENV_KEYS)      # fixed by ARCH; never extended from runtime input
    lv = _spec_view(live)
    rec = {"agent": agent, "generation": generation, "approved_generation": approved_generation}
    reasons = []
    if approved:
        av = _spec_view(approved)
        rec["basis"] = "approved-spec"
        if lv["image"] != av["image"]:
            reasons.append("image digest differs from the approved generation")
        if lv["models"] != av["models"]:
            reasons.append("model differs from the approved generation")
        if lv["tools"] != av["tools"]:
            reasons.append("tools differ from the approved generation")
        changed = sorted(k for k in set(lv["env_fp"]) | set(av["env_fp"]) if lv["env_fp"].get(k) != av["env_fp"].get(k))
        other = [k for k in changed if k not in keys]
        if other:
            reasons.append("env key(s) outside the declared pin keys changed: %s" % ", ".join(other))
        rec["pin_keys_changed"] = [k for k in changed if k in keys]
        rec["from_pin_sha256"] = av["pins"].get("IFABRIC_PIN_SHA256")
        rec["to_pin_sha256"] = lv["pins"].get("IFABRIC_PIN_SHA256")
        rec["from_rails_mode"], rec["to_rails_mode"] = av["mode"], lv["mode"]
    else:
        rec["basis"] = ("attestation-fallback: the approved generation's spec could not be reconstructed; "
                        "compared the approval's image digest + model; tools and other env not verifiable")
        digest = live.get("image_digest") if live else None
        model = (live.get("models") or [None])[0] if live else None
        have = approved_keys or []
        if not (digest and any(k.split("|")[0] == digest for k in have)):
            reasons.append("live image digest is not the approval's image")
        if model and have and not any(k.split("|", 1)[-1] == model for k in have if k.split("|")[0] == digest):
            reasons.append("live model is not the approval's model")
        rec["pin_keys_changed"] = [k for k in sorted(keys) if k in lv["env_fp"]]
        rec["to_pin_sha256"] = lv["pins"].get("IFABRIC_PIN_SHA256")
        rec["from_pin_sha256"] = None
        rec["to_rails_mode"] = lv["mode"]
    if reasons:
        rec["reasons"] = reasons
        return "block", rec
    if rec["pin_keys_changed"] or generation != approved_generation:
        return "pin-only", rec
    return "unchanged", rec


def _apply_pin_rule(versions, running, agents, treatments):
    """For a stale generation, replace the blanket stale rule by the spec comparison. Returns blocks {agent: reason}."""
    blocks = {}
    specs = versions.get("specs") or {}
    approved_keys = versions.get("approved") or {}
    for a in agents:
        rv = running[a]
        try:
            gen, agen = int(rv.get("generation")), int(rv.get("approved_generation"))
        except (TypeError, ValueError):
            continue
        if gen <= agen:
            continue
        sp = specs.get(a) or {}
        if not sp.get("live"):
            blocks[a] = "stale approval: approved at generation %d, running generation %d (no live spec to compare)" % (agen, gen)
            continue
        verdict, rec = pin_treatment(a, sp["live"], sp.get("approved"), gen, agen, approved_keys.get(a))
        if verdict == "block":
            blocks[a] = "stale approval and not a pin-only change: " + "; ".join(rec["reasons"])
        else:
            rv["approved_generation"] = gen          # the approval covers it: only declared pin keys moved
            treatments.append(dict(rec, verdict=verdict, kind="declared_treatment"))
    return blocks


def ep0(versions, assessed, agents, check_versions=None, meta=None, treatments=None):
    """EP-0 input contract (matches PR-09a approval.check_versions(running, approved, policy, assessed, meta)):

        versions = {"running":  {agent: {"image_digest": str, "model": str, "paused": bool,
                                         "generation": int, "approved_generation": int}},
                    "approved": {agent: ["<image_digest>|<model>", ...]},
                    "policy":   "block-assessed" | "record-only"}

    captured by the ops lane through filtered reads (never env values). `meta` (e.g. register_version, pin_sha256)
    is stamped on each Decision. Returns (steps, decisions); one step per agent, named ep0.<agent>."""
    try:
        fn = check_versions or load_check_versions()
    except RuntimeError as exc:
        return [step("ep0", False, str(exc))], []
    if not versions:
        return [step("ep0", False, "no versions document supplied (--versions-file); EP-0 cannot run")], []
    running = {a: _normalise_running(versions["running"][a]) for a in agents if a in versions.get("running", {})}
    missing = [a for a in agents if a not in running]
    if missing:
        return [step("ep0", False, "no running-version read for %s" % ", ".join(missing))], []
    approved = {a: list(versions.get("approved", {}).get(a, [])) for a in agents}
    treatments = treatments if treatments is not None else []
    blocks = _apply_pin_rule(versions, running, agents, treatments)
    decisions = list(fn(running, approved, versions.get("policy"), assessed, meta) if meta is not None
                     else fn(running, approved, versions.get("policy"), assessed))
    steps = []
    for d in decisions:
        action = _field(d, "action")
        agent = _agent_of(d, agents)
        gating = bool(assessed) and versions.get("policy") != "record-only"     # D13: record-only otherwise
        ok = action == "proceed" and not (agent in blocks and gating)
        detail = "action=%s verdict=%s reason=%s" % (action, _field(d, "verdict"), _field(d, "reason"))
        if agent in blocks:
            detail += ("; BLOCK: " if gating else "; RECORDED (not gating): ") + blocks[agent]
        t = [x for x in treatments if x["agent"] == agent]
        if ok and t:
            detail += "; declared treatment: pin %s -> %s (generation %s)" % (
                (t[0].get("from_pin_sha256") or "unknown")[:12], (t[0].get("to_pin_sha256") or "unknown")[:12], t[0]["generation"])
            if t[0]["basis"].startswith("attestation-fallback"):
                detail += " [basis: attestation fallback, approved spec not reconstructable]"
        steps.append(step("ep0.%s" % agent, ok, detail))
    treatments[:] = [t for t in treatments if t["agent"] not in blocks]
    if not steps:
        steps.append(step("ep0", False, "check_versions returned no decision (fail closed)"))
    return steps, decisions


def pin_echo(expected_sha, echoed, agents):
    """Each agent's last echoed pin sha256 must equal the pin this run is meant for."""
    if not expected_sha:
        return [step("pin.echo", True, "no pin supplied; echo check skipped (record-only)")]
    bad = [a for a in agents if echoed.get(a) not in (None, expected_sha)]
    unseen = [a for a in agents if echoed.get(a) is None]
    detail = "expected %s" % expected_sha[:12]
    if unseen:
        detail += "; not yet echoed: %s" % ", ".join(unseen)
    if bad:
        detail += "; MISMATCH: %s" % ", ".join(bad)
    return [step("pin.echo", not bad, detail)]


def run_preflight(budget, now, *, bound, observe_s2_run, index_entries, tokens, expiry, identity_step,
                  ep0_steps, pin_steps):
    """Combine the pieces; raise PreflightRefused if any step failed. Returns the steps on success."""
    steps = [identity_step, check_credentials(expiry, now, budget)]
    steps += budget_guard(budget, now, tokens, bound, observe_s2_run, index_entries)
    steps += ep0_steps + pin_steps
    if not all(s["ok"] for s in steps):
        raise PreflightRefused(steps)
    return steps


# --- pin join tolerant of missing model-call fields (gap: model_call records lack pin.sha256 / runtime.session_id) ---

def pin_by_run(records):
    """{run.id: pin sha256} from the run's start-up record or a response pin echo (`pin.sha256`,
    `ifabric.pin_sha256` or `pin_sha256`). Model-call records do not carry it; join through the run id."""
    out = {}
    for r in records or []:
        rid = r.get("run.id") or r.get("correlation_id")
        sha = r.get("pin.sha256") or r.get("ifabric.pin_sha256") or r.get("pin_sha256")
        if rid and sha and r.get("record_kind") != "model_call":
            out.setdefault(rid, sha)
    return out


def pin_of(record, by_run):
    """The record's own pin if present, else the run's (start-up/echo); None if neither (never raises)."""
    return record.get("pin.sha256") or (by_run or {}).get(record.get("run.id") or record.get("correlation_id"))
