"""The deterministic query grammar (Arth's 06-UI-UX-SPEC section 6; ARCH 3.7). Stdlib only, Python 3.9.

parse(text, pack=None) -> a plain dict:
    ok, kind, normalized, control, run, t1, t2, error, examples, candidates
kind: controltest-run | controltest-window | controltest-run-window (PR-53) | auditor | trail | who | told | unparsed
No LLM, no guessing: unknown input -> "I can't parse that" plus the example list; an ambiguous run -> candidates.
Rules: RUN is an alias (FM-B) or a CID; times are ISO UTC or HH:MMZ (resolved inside the pack's event window);
C16 = 16 = "spend cap", C7 = 7 = "event recording", C9 = 9 = "drift".
"""
from __future__ import annotations

import datetime
import re

from prooflab.query import engine as E

GRAMMAR_VERSION = "g1"
VERBS = ("controltest", "ask", "auditor", "trail")      # CLI verbs (aliases of the grammar's normalized forms)
EXAMPLES = (
    "Show me control 16 for run FM-B",
    "Was control 9 satisfied for run FM-B?",
    "Was control 9 satisfied between 23:00Z and 09:00Z?",
    "control 9 for window 2026-10-06T00",
    "controltest 16 --run FM-B",
    "show me control 16 for run FM-B between 13:56Z and 13:57Z",
    "six questions for INC0090216",
    "reconstruct run FM-B",
    "who acted in FM-B",
    "who was told for FM-B",
)

_CTL = r"(c?\d+|spend cap|event recording|drift)"
_UTC = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z"
_TIME = r"(%s|\d\d:\d\d(?::\d\d)?Z)" % _UTC
_SHORT = re.compile(r"^(\d\d):(\d\d)(?::(\d\d))?Z$")
_PATTERNS = (
    ("run-window", re.compile(r"^(?:show me |was )?control %s (?:satisfied )?for run (\S+) (?:between|from) %s (?:and|to) %s$" % (_CTL, _TIME, _TIME), re.I)),
    ("cli-run-window", re.compile(r"^controltest %s --run (\S+) --window (\S+)\.\.(\S+)$" % _CTL, re.I)),
    ("run", re.compile(r"^(?:show me |was )?control %s (?:satisfied )?for run (\S+)$" % _CTL, re.I)),
    ("between", re.compile(r"^(?:show me |was )?control %s (?:satisfied )?(?:between|from) %s (?:and|to) %s$" % (_CTL, _TIME, _TIME), re.I)),
    ("hour", re.compile(r"^(?:show me |was )?control %s (?:satisfied )?for window (\d{4}-\d\d-\d\dT\d\d)$" % _CTL, re.I)),
    ("cli-run", re.compile(r"^controltest %s --run (\S+)$" % _CTL, re.I)),
    ("cli-range", re.compile(r"^controltest %s --from %s --to %s$" % (_CTL, _TIME, _TIME), re.I)),
    ("cli-window", re.compile(r"^controltest %s --window (\S+)$" % _CTL, re.I)),
    ("auditor", re.compile(r"^(?:six questions(?: for)?|auditor) (\S+)$", re.I)),
    ("trail", re.compile(r"^(?:reconstruct run|trail) (\S+)$", re.I)),
    ("who", re.compile(r"^who acted in (\S+)$", re.I)),
    ("told", re.compile(r"^who was told for (\S+)$", re.I)),
)
_SYNONYMS = {"spend cap": "C16", "event recording": "C7", "drift": "C9"}


def control_of(word):
    w = str(word).strip().lower()
    if w in _SYNONYMS:
        return _SYNONYMS[w]
    ref = E.norm_control(w)
    return ref if ref in E.CONTROLS else None


def _fail(text, error, **extra):
    out = {"ok": False, "kind": "unparsed", "text": text, "normalized": None, "error": error,
           "examples": list(EXAMPLES), "candidates": []}
    out.update(extra)
    return out


def _utc(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(text):
    key = E._utc_key(text)
    if not key:
        return None
    return datetime.datetime.strptime(key[:19], "%Y-%m-%dT%H:%M:%S")


def resolve_times(pack, t1, t2, anchor=None):
    """(T1, T2, error): full UTC stamps. HH:MMZ resolves forward from the pack's declared window start; with no declared
    window, from `anchor` (PR-53: the run's start minus 12 hours, so a run+window question resolves near its run)."""
    short = [t for t in (t1, t2) if _SHORT.match(t)]
    start = None
    if short:
        win = (getattr(pack, "window", None) or {}) if pack is not None else {}
        start = _parse_utc(win.get("start") or "")
        if start is None and anchor:
            start = _parse_utc(anchor)
            start = start - datetime.timedelta(hours=12) if start else None
        if start is None:
            return None, None, "a time like %s needs the pack's event window (window.json): none declared" % short[0]
    cur, out = start, []
    for t in (t1, t2):
        sm = _SHORT.match(t)
        if sm:
            hh, mm, ss = int(sm.group(1)), int(sm.group(2)), int(sm.group(3) or 0)
            if hh > 23 or mm > 59 or ss > 59:
                return None, None, "not a time: %s" % t
            base = cur or start
            cand = base.replace(hour=hh, minute=mm, second=ss, microsecond=0)
            if cand <= base and out:       # the second time rolls over midnight
                cand += datetime.timedelta(days=1)
            elif cand < base:
                cand += datetime.timedelta(days=1)
            cur = cand
            out.append(_utc(cand))
        else:
            if _parse_utc(t) is None:
                return None, None, "not a UTC time: %s" % t
            cur = _parse_utc(t)
            out.append(t if len(t) == 20 else _utc(cur))
    if not E._utc_key(out[0]) < E._utc_key(out[1]):
        return None, None, "T1 must be before T2 (%s .. %s)" % tuple(out)
    return out[0], out[1], None


def run_anchor(pack, cid):
    """The run's first record time (UTC text) for resolving HH:MMZ when the pack declares no window, else None."""
    if pack is None:
        return None
    recs = [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment" and r.get("authorship") != "ASSURANCE"]
    keys = sorted(k for k in (E._utc_key(r.get("emitted.at") or r.get("ts")) for r in recs) if k)
    return (keys[0][:19] + "Z") if keys else None


def resolve_run(pack, token):
    """(cid, candidates): exact CID, then an alias/label, then a unique case-insensitive fragment of a CID."""
    if pack is None:
        return token, []
    if E.run_known(pack, token):
        return token, []
    low = token.lower()
    rows = list(pack.run_index) + list(pack.catalogue)
    hits = []
    for r in rows:
        cid = E._cid(r)
        if cid and low in (str(r.get("alias") or "").lower(), str(r.get("run_alias") or "").lower(), str(r.get("label") or "").lower()):
            hits.append(cid)
    for a in pack.assessments:
        if a["scope_kind"] == "run" and low == str(a["scope_id"]).lower():
            hits.append(a["scope_id"])
    hits = sorted(set(hits))
    if not hits:
        known = set(list(pack.by_cid) + list(pack.index_by_cid) + list(pack.catalogue_by_cid))
        hits = sorted(c for c in known if low in c.lower())
    if len(hits) == 1:
        return hits[0], []
    return None, hits


def parse(text, pack=None):
    raw = " ".join(str(text or "").strip().split())
    t = raw.rstrip("?.! ").strip()
    if not t:
        return _fail(raw, "I can't parse that: empty question")
    for name, rx in _PATTERNS:
        m = rx.match(t)
        if not m:
            continue
        g = m.groups()
        out = {"ok": True, "text": raw, "examples": [], "candidates": [], "error": None, "grammar_version": GRAMMAR_VERSION,
               "control": None, "run": None, "t1": None, "t2": None, "alias": None}
        if name in ("auditor",):
            out.update(kind="auditor", incident=g[0], normalized="auditor %s" % g[0])
            return out
        if name in ("trail", "who", "told"):
            cid, cands = resolve_run(pack, g[0])
            if cid is None and cands:
                return _fail(raw, "ambiguous run %r" % g[0], candidates=cands)
            kind = {"trail": "trail", "who": "who", "told": "told"}[name]
            out.update(kind=kind, run=cid or g[0], alias=g[0],
                       normalized={"trail": "trail %s", "who": "auditor %s --question who", "told": "auditor %s --question told"}[name] % (cid or g[0]))
            return out
        ctl = control_of(g[0])
        if ctl is None:
            return _fail(raw, "I can't parse that: unknown control %r (C7, C9, C16)" % g[0])
        out["control"] = ctl
        num = ctl[1:]
        if name in ("run-window", "cli-run-window"):
            cid, cands = resolve_run(pack, g[1])
            if cid is None and cands:
                return _fail(raw, "ambiguous run %r: %d candidates" % (g[1], len(cands)), candidates=cands)
            t1, t2, err = resolve_times(pack, g[2], g[3], anchor=run_anchor(pack, cid or g[1]))
            if err:
                return _fail(raw, err)
            out.update(kind="controltest-run-window", run=cid or g[1], alias=g[1], t1=t1, t2=t2,
                       normalized="controltest %s --run %s --window %s..%s" % (num, cid or g[1], t1, t2))
            return out
        if name in ("run", "cli-run"):
            cid, cands = resolve_run(pack, g[1])
            if cid is None and cands:
                return _fail(raw, "ambiguous run %r: %d candidates" % (g[1], len(cands)), candidates=cands)
            out.update(kind="controltest-run", run=cid or g[1], alias=g[1], normalized="controltest %s --run %s" % (num, g[1]))
            return out
        if name in ("between", "cli-range"):
            t1, t2, err = resolve_times(pack, g[1], g[2])
            if err:
                return _fail(raw, err)
            out.update(kind="controltest-window", t1=t1, t2=t2, normalized="controltest %s --from %s --to %s" % (num, g[1], g[2]))
            return out
        if name == "hour":
            hour = g[1]
            try:
                d = datetime.datetime.strptime(hour, "%Y-%m-%dT%H")
            except ValueError:
                return _fail(raw, "not an hour window: %s" % hour)
            out.update(kind="controltest-window", t1=_utc(d), t2=_utc(d + datetime.timedelta(hours=1)),
                       normalized="controltest %s --window %s" % (num, hour))
            return out
        if name == "cli-window":
            if re.match(r"^\d{4}-\d\d-\d\dT\d\d$", g[1]):
                d = datetime.datetime.strptime(g[1], "%Y-%m-%dT%H")
                out.update(kind="controltest-window", t1=_utc(d), t2=_utc(d + datetime.timedelta(hours=1)),
                           normalized="controltest %s --window %s" % (num, g[1]))
                return out
            w = E.parse_window(g[1])
            if not w:
                return _fail(raw, "--window needs <T1>..<T2> in full UTC")
            out.update(kind="controltest-window", t1=w[0], t2=w[1], normalized="controltest %s --window %s" % (num, g[1]))
            return out
    return _fail(raw, "I can't parse that")
