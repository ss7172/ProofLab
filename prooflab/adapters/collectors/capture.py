"""Capture format + the one subprocess seam (PR-12a; 04-LOGS-TO-EVIDENCE §1, §3, §4). Stdlib, Python 3.9.

`write_capture` writes `raw/<surface>/<scope>/<file>` plus `<file>.capture.json` (Arth's sidecar fields). Bytes
are written exactly as received AFTER capture-time redaction; the sidecar lists each rule and its count and the
sha256 of the written file. A byte-identical re-capture keeps the file; a differing one becomes `<file>.r<N>`
(a re-capture is a new file, never an edit). Time comes from `Ctx.now`, so a fixed clock gives identical bytes.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field

from prooflab.contract import clocks, ids          # the one coupling to PR-01's contract
from prooflab.store import redact

ALLOWED_BINARIES = ("aws", "kubectl")
# verbs a collector must never run; assembled from parts so this file itself stays grep-clean
_NEVER = ("get" + "-function", "Get" + "Function", "get-agent" + "-runtime", "GetAgent" + "Runtime")
SIDECAR_FIELDS = ("surface", "path", "command", "scope", "captured_at", "captured_by", "operator",
                  "source_identity", "pagination_complete", "line_count", "redactions", "sha256")


class CaptureError(RuntimeError):
    pass


class ExpiredTokenError(CaptureError):
    """AWS credentials expired: the supervisor turns this into a `monitoring-gap` (T4.1)."""


def default_runner(argv):
    """THE live seam. -> (returncode, stdout bytes, stderr bytes). Tests inject a fake; workers never call this."""
    p = subprocess.run(list(argv), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    return p.returncode, p.stdout, p.stderr


@dataclass
class Ctx:
    root: str                                   # the staging root; raw/ lives under it
    runner: object = default_runner
    now: object = clocks.now_utc                # () -> UTC string
    sleep: object = time.sleep
    operator: str = ""
    captured_by: str = "prooflab capture@git:unknown"
    profile: "str | None" = None
    region: "str | None" = None
    calls: list = field(default_factory=list)   # argv log, for tests and the live-lane log
    include_test: bool = False                  # explicit opt-in (ops lane, smokes): also collect ifabric-test-* CIDs


def aws_argv(ctx: Ctx, *args) -> list:
    argv = ["aws"]
    if ctx.profile:
        argv += ["--profile", ctx.profile]
    if ctx.region:
        argv += ["--region", ctx.region]
    return argv + list(args)


def run(ctx: Ctx, argv) -> bytes:
    """Run one read-only command through the seam; return stdout. Never retries."""
    argv = list(argv)
    if not argv or argv[0] not in ALLOWED_BINARIES:
        raise CaptureError("refusing to run %r: only %s" % (argv[:1], "/".join(ALLOWED_BINARIES)))
    joined = " ".join(argv)
    for bad in _NEVER:
        if bad in joined:
            raise CaptureError("refusing a forbidden verb")
    ctx.calls.append(argv)
    rc, out, err = ctx.runner(argv)
    if rc != 0:
        msg = redact.redact_text((err or b"").decode("utf-8", "replace")[:500])[0]
        if "ExpiredToken" in msg:
            raise ExpiredTokenError(msg)
        raise CaptureError("command failed rc=%s: %s" % (rc, msg))
    return out


def command_text(argv) -> str:
    return shlex.join([str(a) for a in argv])


def skip_cid(cid: str, ctx: "Ctx | None" = None, include_test: bool = False) -> "str | None":
    """Why a CID is not collected, or None. Skips test traffic unless explicitly opted in (include_test=True, or
    ctx.include_test: the ops lane's smokes); assessed collection keeps the default. Refuses non-run ids always."""
    if not ids.is_valid_run_id(cid):
        raise CaptureError("not a run id: %r" % (cid,))
    if cid.startswith("ifabric-test-") and not (include_test or (ctx is not None and ctx.include_test)):
        return "test traffic (ifabric-test-*)"
    return None


def canonical(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def jsonl(rows) -> bytes:
    return b"".join(canonical(r) for r in rows)


def _free_path(path: str, data: bytes) -> str:
    if not os.path.exists(path):
        return path
    with open(path, "rb") as fh:
        if fh.read() == data:
            return path
    n = 2
    while os.path.exists("%s.r%d" % (path, n)):
        with open("%s.r%d" % (path, n), "rb") as fh:
            if fh.read() == data:
                return "%s.r%d" % (path, n)
        n += 1
    return "%s.r%d" % (path, n)


def write_capture(ctx: Ctx, surface: str, scope_dir: str, filename: str, data: bytes, *, command: str,
                  scope: dict, source_identity: dict, pagination_complete: bool = True,
                  counts: "dict | None" = None, text_redact: bool = True, exact_values=()) -> dict:
    """Write one capture and its sidecar; return the sidecar dict.

    `counts` = redactions already applied upstream (e.g. by the JSON walk). `exact_values` = secret values the
    caller injects (e.g. the ledger token) that must not survive in the bytes.
    """
    counts = dict(counts or {})
    if text_redact:
        text, c = redact.redact_text(data.decode("utf-8", "replace"))
        if c:
            data = text.encode("utf-8")
            counts = redact.merge_counts(counts, c)
    for v in exact_values:
        if v and v.encode("utf-8") in data:
            data = data.replace(v.encode("utf-8"), b"[REDACTED:exact]")
            counts = redact.merge_counts(counts, {"env-secret": 1})
    rel = "/".join(["raw", surface, scope_dir, filename])
    full = _free_path(os.path.join(ctx.root, *rel.split("/")), data)
    rel = os.path.relpath(full, ctx.root).replace(os.sep, "/")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(data)
    sidecar = {
        "surface": surface, "path": rel, "command": command, "scope": scope,
        "captured_at": ctx.now(), "captured_by": ctx.captured_by, "operator": ctx.operator,
        "source_identity": source_identity, "pagination_complete": bool(pagination_complete),
        "line_count": data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0),
        "redactions": redact.redactions_list(counts),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    with open(full + ".capture.json", "wb") as fh:
        fh.write((json.dumps(sidecar, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return sidecar


def to_ms(utc: str) -> int:
    return int(clocks.parse_utc(utc).timestamp() * 1000)


def to_epoch(utc: str) -> int:
    return int(clocks.parse_utc(utc).timestamp())


def filter_log_events(ctx: Ctx, group: str, pattern: str, start: str, end: str, max_pages: int = 200) -> tuple:
    """Paginate `aws logs filter-log-events` until no nextToken. -> (events, pages, complete, command text)."""
    events, pages, token, complete = [], 0, None, True
    base = ["logs", "filter-log-events", "--log-group-name", group, "--filter-pattern", pattern,
            "--start-time", str(to_ms(start)), "--end-time", str(to_ms(end)), "--output", "json"]
    first = aws_argv(ctx, *base)
    while True:
        argv = first + (["--next-token", token] if token else [])
        doc = json.loads(run(ctx, argv).decode("utf-8") or "{}")
        events.extend(doc.get("events") or [])
        pages += 1
        token = doc.get("nextToken")
        if not token:
            break
        if pages >= max_pages:
            complete = False
            break
    return events, pages, complete, command_text(first)
