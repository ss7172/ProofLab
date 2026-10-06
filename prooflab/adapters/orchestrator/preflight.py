"""The preflight = the budget guard (IMPLEMENTATION-PLAN 5.1) + EP-0 + the pin echo (ARCH 7.2 step 1).

The preflight holds no control verdict logic: EP-0 acts only on `action` from approval.check_versions; the
budget guard compares the ops lane's own limits (budget.json), not a control threshold.
"""
from __future__ import annotations

import datetime as _dt
import importlib
import json
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


def ep0(versions, assessed, agents, check_versions=None, meta=None):
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
    decisions = list(fn(running, approved, versions.get("policy"), assessed, meta) if meta is not None
                     else fn(running, approved, versions.get("policy"), assessed))
    steps = []
    for d in decisions:
        action = _field(d, "action")
        steps.append(step("ep0.%s" % _agent_of(d, agents), action == "proceed",
                          "action=%s verdict=%s reason=%s" % (action, _field(d, "verdict"), _field(d, "reason"))))
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
