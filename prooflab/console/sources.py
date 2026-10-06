"""Data sources for the Evidence Console (T5.4 (a)): `fixtures`, `pack`, `live`.

Stdlib only, Python 3.9. A source only READS and serves what the pack declares; it computes no verdicts.
- FixturesSource: Arth's synthetic demo data (SYNTHETIC, amber banner).
- PackSource: a real Evidence Pack directory (pack-index.json is the table of contents and the allow-list).
  It REFUSES synthetic data and the panel's fake sample (ConsoleRefusal), so a judge never sees demo data as evidence.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import time

MANIFEST_NAME = "MANIFEST.json"
RAW_CAP_BYTES = 2 * 1024 * 1024

# canonical-JSON sha256 of each case in Arth's examples/cases.sample-fake-data.json (the panel's fake sample).
FAKE_CASE_DIGESTS = frozenset([
    "8a847633dae51a4e82f78ebe0102503636ff2622ebd5f7f9d1d516e86e4fad2d",
    "269c8f15a5b645e1d38f25cc13d5af4ab9201cdbd3084fb7e5dc4f5c6ef56897",
    "38d9990cbc4b10b9888ad069455722299d6a0109f2d1658bee5dd33ca4765463",
    "8fd641aadc6672b9531e44a812ba5ad6b09a2f4639bc6d1779610fafd7a35f51",
])


class ConsoleRefusal(Exception):
    """The console refuses to start or to serve (synthetic data in PACK mode, a secret in the env, ...)."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_text(text):
    return sha256_bytes(text.encode("utf-8"))


def case_digest(case):
    return sha256_text(json.dumps(case, sort_keys=True))


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    return rows


def safe_join(root, rel):
    """Resolve rel under root: no absolute path, no '..', no backslash/NUL, no symlink component. None if unsafe."""
    if not isinstance(rel, str) or not rel or "\x00" in rel or "\\" in rel or rel.startswith("/"):
        return None
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    cur = root
    for part in parts:
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            return None
    real_root = os.path.realpath(root)
    real = os.path.realpath(cur)
    if real != real_root and not real.startswith(real_root + os.sep):
        return None
    return cur


def sidecar_for(raw_path):
    """raw/gateway/<cid>/gateway-stdout.log -> raw/gateway/<cid>/gateway-stdout.capture.json"""
    head, name = os.path.split(raw_path)
    stem = name.split(".", 1)[0]
    return (head + "/" if head else "") + stem + ".capture.json"


def parse_raw_ref(ref):
    """raw:<path>#L<n> -> (path, n); raw:<path> (no line) -> (path, 1); else None."""
    m = re.match(r"^raw:([^#]+)(?:#L(\d+))?$", ref or "")
    if not m or (m.group(2) is not None and int(m.group(2)) < 1):
        return None
    return m.group(1), int(m.group(2) or 1)


def manifest_paths_sha(root):
    data = read_json(os.path.join(root, MANIFEST_NAME))
    return {e["path"]: e["sha256"] for e in data.get("files", [])}


def verify_manifest(root):
    """Same semantics as tools/manifest.py verify: changed / missing / unlisted. Status VERIFIED|MODIFIED|NO_MANIFEST."""
    mpath = os.path.join(root, MANIFEST_NAME)
    if not os.path.isfile(mpath):
        return {"status": "NO_MANIFEST", "changed": [], "missing": [], "unlisted": [], "files": 0,
                "manifest_sha256": None}
    listed = manifest_paths_sha(root)
    present = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel == MANIFEST_NAME or os.path.islink(full):
                continue
            with open(full, "rb") as handle:
                present[rel] = sha256_bytes(handle.read())
    changed = sorted(p for p in listed if p in present and present[p] != listed[p])
    missing = sorted(p for p in listed if p not in present)
    unlisted = sorted(p for p in present if p not in listed)
    with open(mpath, "rb") as handle:
        msha = sha256_bytes(handle.read())
    ok = not (changed or missing or unlisted)
    return {"status": "VERIFIED" if ok else "MODIFIED", "changed": changed, "missing": missing,
            "unlisted": unlisted, "files": len(listed), "manifest_sha256": msha}


def _has_synthetic(obj):
    if isinstance(obj, dict):
        if obj.get("provenance") == "SYNTHETIC" or obj.get("synthetic") is True:
            return True
        return any(_has_synthetic(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_synthetic(v) for v in obj)
    return False


def answer_key(answer):
    q = answer.get("query") or {}
    scope = q.get("scope") or answer.get("scope") or {}
    ref = q.get("control_ref") or (answer.get("control") or {}).get("ref")
    kind = scope.get("kind", "run")
    ident = scope.get("alias") or scope.get("id") or "W"
    return "%s|%s|%s" % (ref, kind, ident)


class _Base(object):
    name = "base"

    def __init__(self):
        self.started = time.time()
        self._integrity_cache = None

    # filled by subclasses -------------------------------------------------
    def pack_index(self): raise NotImplementedError
    def answer(self, key): raise NotImplementedError
    def auditor(self, ident): raise NotImplementedError
    def run(self, ident): raise NotImplementedError
    def run_catalogue(self): raise NotImplementedError
    def records(self): raise NotImplementedError
    def raw(self, ref): raise NotImplementedError
    def cases(self): raise NotImplementedError
    def integrity(self): raise NotImplementedError
    def replay(self, ident): return None

    def mode_info(self):
        raise NotImplementedError

    # shared ---------------------------------------------------------------
    def answers_index(self):
        return list(self.pack_index().get("answers", []))

    def _interval_covers(self, key, asked):
        a = self.answer(key) or {}
        sc = (a.get("query") or {}).get("scope") or a.get("scope") or {}
        start, end = sc.get("start"), sc.get("end")
        if not (start and end) and ".." in key.split("|")[-1]:
            start, end = key.split("|")[-1].split("..", 1)
        return _covers(start, end, asked)

    def find_answer(self, control_ref, kind, scope_id=None, params=None):
        """Locate a stored answer by control + scope (no computation)."""
        params = params or {}
        hits = []
        for entry in self.answers_index():
            k = entry.get("key", "")
            parts = k.split("|")
            if len(parts) != 3 or parts[0] != control_ref or parts[1] != kind:
                continue
            if kind == "interval" and scope_id is not None and ".." in str(scope_id):
                if parts[2].upper() == str(scope_id).upper() or self._interval_covers(entry["key"], str(scope_id)):
                    hits.append(entry["key"])
                continue        # PR-54: an interval question never falls back to another window
            if scope_id is not None and parts[2].upper() != str(scope_id).upper():
                continue
            hits.append(entry["key"])
        if kind == "interval" and params:
            narrowed = []
            for key in hits:
                a = self.answer(key) or {}
                scope = (a.get("query") or {}).get("scope") or a.get("scope") or {}
                if all(str(scope.get(p)) == str(v) for p, v in params.items() if p in scope):
                    narrowed.append(key)
            hits = narrowed or hits
        return hits[0] if hits else None


def _ts(text):
    import datetime as _dt
    try:
        return _dt.datetime.strptime(str(text)[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _covers(start, end, asked):
    """True when the stored window [start, end] contains the asked one. Asked times may be time of day only
    ('13:50:00Z'): they are placed on the stored window's dates (an end before its start means the next day)."""
    import datetime as _dt
    s, e = _ts(start), _ts(end)
    if s is None or e is None:
        return False
    a1, a2 = [x.strip() for x in asked.split("..", 1)]
    if "T" in a1 and "T" in a2:
        t1, t2 = _ts(a1), _ts(a2)
    else:
        try:
            h1 = _dt.datetime.strptime(a1.split("T")[-1][:8], "%H:%M:%S").time()
            h2 = _dt.datetime.strptime(a2.split("T")[-1][:8], "%H:%M:%S").time()
        except ValueError:
            return False
        t1 = _dt.datetime.combine(s.date(), h1)
        if t1 < s:
            t1 += _dt.timedelta(days=1)
        t2 = _dt.datetime.combine(t1.date(), h2)
        if t2 <= t1:
            t2 += _dt.timedelta(days=1)
    return t1 is not None and t2 is not None and s <= t1 < t2 <= e


class FixturesSource(_Base):
    """Arth's demo data (demo-data.js + the assurance-panel cases.js), parsed as data, never executed."""
    name = "fixtures"

    def __init__(self, plan_dir):
        super().__init__()
        self.plan_dir = plan_dir
        demo = os.path.join(plan_dir, "demo")
        self.D = self._load_js(os.path.join(demo, "demo-data.js"))
        cases_js = os.path.join(demo, "assurance-panel", "cases.js")
        self._cases = self._load_js(cases_js) if os.path.isfile(cases_js) else self.D.get("cases", [])

    @staticmethod
    def _load_js(path):
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        start = min(i for i in (text.find("{"), text.find("[")) if i >= 0)
        # "window.X = <json>;"  ->  <json>
        end = max(text.rfind("}"), text.rfind("]")) + 1
        return json.loads(text[start:end])

    def pack_index(self):
        return self.D["pack"]

    def answer(self, key):
        return self.D["answers"].get(key)

    def auditor(self, ident):
        return self.D["auditor"].get(ident)

    def run(self, ident):
        for alias, run in self.D["runs"].items():
            if ident in (alias, run.get("cid")):
                return run
        return None

    def run_catalogue(self):
        rows = []
        for entry in self.pack_index().get("runs", []):
            rows.append({"alias": entry.get("alias"), "cid": entry.get("cid"), "provenance": entry.get("provenance"),
                         "source": "fixtures", "assessed": True, "in_window": None, "label": entry.get("purpose")})
        return rows

    def records(self):
        out = []
        for alias, recs in self.D["records"].items():
            out.extend(recs)
        return out

    def raw(self, ref):
        parsed = parse_raw_ref(ref)
        if not parsed or ref not in self.D["raw"]:
            return None
        line = self.D["raw"][ref]
        cap = self.D["captures"].get("capture:" + sidecar_for(parsed[0]))
        return {"line": line, "sha256": sha256_text(line), "capture": cap}

    def cases(self):
        return list(self._cases)

    def integrity(self):
        i = dict(self.pack_index().get("integrity", {}))
        i.setdefault("status", "VERIFIED")
        i["verified_at"] = i.get("verified_at")
        return i

    def mode_info(self):
        i = self.integrity()
        return {"data": "fixtures", "chip": "FIXTURES · read-only", "tone": "warn",
                "banner": "SYNTHETIC FIXTURES (Arth's handoff demo data): illustrative values, not evidence",
                "integrity_ok": False, "integrity_text": "synthetic (%s files)" % i.get("files", "?"),
                "synthetic": True}


class PackSource(_Base):
    """A real Evidence Pack on disk. pack-index.json is the allow-list; MANIFEST.json gates integrity."""
    name = "pack"

    def __init__(self, root, live=False, allow_synthetic=False):
        super().__init__()
        self.root = os.path.abspath(root)
        self.live = live
        index_path = os.path.join(self.root, "pack-index.json")
        if not os.path.isfile(index_path):
            raise ConsoleRefusal("no pack-index.json in %s (the console's only entry point)" % self.root)
        self.index = read_json(index_path)
        if not allow_synthetic and _has_synthetic(self.index):
            raise ConsoleRefusal("PACK mode refuses SYNTHETIC data: pack-index.json carries provenance SYNTHETIC")
        self._integrity = verify_manifest(self.root)
        self._integrity_at = time.time()
        self._manifest = manifest_paths_sha(self.root) if self._integrity["status"] != "NO_MANIFEST" else None
        self._answers = {}
        self._auditors = {}
        self._runs = {}
        self._records = []
        self._load(allow_synthetic)

    # ---- loading ----------------------------------------------------------
    def _check(self, obj, what, allow_synthetic):
        if not allow_synthetic and _has_synthetic(obj):
            raise ConsoleRefusal("PACK mode refuses SYNTHETIC data (%s)" % what)

    def _glob(self, pattern):
        return sorted(glob.glob(os.path.join(self.root, pattern)))

    def _load(self, allow_synthetic):
        by_id = {e.get("answer_id"): e.get("key") for e in self.index.get("answers", [])}
        for path in self._glob("answers/*.json"):
            if os.path.islink(path):
                continue
            doc = read_json(path)
            self._check(doc, os.path.relpath(path, self.root), allow_synthetic)
            key = by_id.get(doc.get("answer_id")) or answer_key(doc)
            self._answers[key] = doc
        for path in self._glob("auditor/*.json"):
            if os.path.islink(path):
                continue
            doc = read_json(path)
            self._check(doc, os.path.relpath(path, self.root), allow_synthetic)
            ident = (doc.get("scope") or {}).get("id") or os.path.splitext(os.path.basename(path))[0]
            self._auditors[ident] = doc
        for path in self._glob("runs/*/run.json"):
            if os.path.islink(path):
                continue
            doc = read_json(path)
            self._check(doc, os.path.relpath(path, self.root), allow_synthetic)
            self._runs[doc.get("run_alias") or doc.get("cid")] = doc
        for path in self._glob("records/*/*.jsonl"):
            if os.path.islink(path):
                continue
            for rec in read_jsonl(path):
                self._check(rec, os.path.relpath(path, self.root), allow_synthetic)
                self._records.append(rec)
        for path in self._glob("records/*/*.json"):      # the projector writes one document per record
            if os.path.islink(path):
                continue
            rec = read_json(path)
            self._check(rec, os.path.relpath(path, self.root), allow_synthetic)
            self._records.append(rec)
        self._case_docs = []
        self._case_refused = []
        for entry in self.index.get("cases", []):
            self._load_case(entry, allow_synthetic)

    def _load_case(self, entry, allow_synthetic):
        path = safe_join(self.root, entry.get("path"))
        if path is None or not os.path.isfile(path):
            self._case_refused.append({"finding_id": entry.get("finding_id"), "reason": "path not found or unsafe"})
            return
        if self._manifest is not None and entry["path"] not in self._manifest:
            self._case_refused.append({"finding_id": entry.get("finding_id"), "reason": "not listed in MANIFEST"})
            return
        with open(path, "rb") as handle:
            blob = handle.read()
        if sha256_bytes(blob) != entry.get("sha256"):
            self._case_refused.append({"finding_id": entry.get("finding_id"), "reason": "sha256 changed"})
            return
        doc = json.loads(blob.decode("utf-8"))
        if not allow_synthetic:
            if case_digest(doc) in FAKE_CASE_DIGESTS or "fake-data" in blob.decode("utf-8").lower():
                raise ConsoleRefusal("PACK mode refuses the panel's fake sample case (%s)" % entry.get("finding_id"))
            self._check(doc, entry["path"], allow_synthetic)
        self._case_docs.append(doc)

    # ---- source API --------------------------------------------------------
    def pack_index(self):
        return self.index

    def answer(self, key):
        return self._answers.get(key)

    def auditor(self, ident):
        return self._auditors.get(ident)

    def run(self, ident):
        low = str(ident or "").lower()
        for alias, run in self._runs.items():
            if low in (str(alias).lower(), str(run.get("cid") or "").lower()):
                return run
        for entry in self.index.get("runs", []):      # PR-54: no runs/*/run.json in the pack -> the pack-index entry
            if low in (str(entry.get("alias") or "").lower(), str(entry.get("cid") or "").lower()):
                return dict(entry, source="pack-index runs[]")
        return None

    def declared_window(self):
        """window.json as declared in the pack ({start, end, note} or None); the console shows it, never edits it."""
        path = os.path.join(self.root, "window.json")
        if os.path.isfile(path) and not os.path.islink(path):
            try:
                w = read_json(path)
            except ValueError:
                return None
            w = w.get("event_window") if isinstance(w.get("event_window"), dict) else w
            return {"start": w.get("start"), "end": w.get("end"), "note": w.get("note")}
        ew = (self.index.get("pack") or {}).get("event_window")   # PR-54: the pack's own event window (pack-index)
        if isinstance(ew, dict) and ew.get("start") and ew.get("end"):
            return {"start": ew.get("start"), "end": ew.get("end"), "note": "pack-index pack.event_window"}
        return None

    def run_catalogue(self):
        """The run catalogue with its honesty fields, from the same engine as `query --runs` (one label source)."""
        from prooflab.query import engine as E
        res = E.runs_list(E.Pack(self.root))
        win = self.declared_window() or {}
        aliases = dict((e.get("cid"), e.get("alias")) for e in self.index.get("runs", []))
        ientry = dict((e.get("cid"), e) for e in self.index.get("runs", []))
        rows = []
        for r in res["rows"]:
            start = r.get("start") or (ientry.get(r["cid"]) or {}).get("started_at")
            inside = None
            if start and win.get("start") and win.get("end"):
                inside = E._utc_key(win["start"]) <= E._utc_key(start) <= E._utc_key(win["end"])
            rows.append({"alias": aliases.get(r["cid"]), "cid": r["cid"],
                         "provenance": (ientry.get(r["cid"]) or {}).get("provenance") or r.get("provenance"),
                         "source": res["source"], "assessed": r.get("assessed"), "in_window": inside,
                         "label": r.get("label"), "first_seen": start})
        seen = set(x["cid"] for x in rows)
        for e in self.index.get("runs", []):     # PR-56: every pack-index run (21), not only the catalogue's rows
            if e.get("cid") in seen:
                continue
            start = e.get("started_at")
            inside = None
            if start and win.get("start") and win.get("end"):
                inside = E._utc_key(win["start"]) <= E._utc_key(start) <= E._utc_key(win["end"])
            rows.append({"alias": e.get("alias"), "cid": e.get("cid"), "provenance": e.get("provenance"),
                         "source": "pack-index" + (" (" + ", ".join(e.get("sources") or []) + ")" if e.get("sources") else ""),
                         "assessed": bool(e.get("verdicts")), "in_window": inside, "label": e.get("label") or e.get("purpose"),
                         "first_seen": start})
        for x in rows:                           # pack-index label NOT COUNTED and its reason win over the catalogue label
            e = ientry.get(x["cid"]) or {}
            if e.get("label") == "NOT COUNTED":
                x["label"] = "NOT COUNTED"
                x["failure_class"] = e.get("failure_class") or e.get("state")
                x["reason"] = e.get("purpose")
        if rows:
            return rows
        rows = []
        for entry in self.index.get("runs", []):
            rows.append({"alias": entry.get("alias"), "cid": entry.get("cid"), "provenance": entry.get("provenance"),
                         "source": "pack-index", "assessed": None, "in_window": None, "label": entry.get("purpose")})
        return rows

    def records(self):
        return self._records

    def _raw_allowed(self, rel):
        if not rel.startswith("raw/"):
            return False
        if self._manifest is not None:
            return rel in self._manifest
        return any((parse_raw_ref((r.get("source") or {}).get("raw_ref")) or ("",))[0] == rel for r in self._records)

    def _store_line(self, rid):
        """record:<record_id> -> the exact line in store/records.jsonl (only when MANIFEST lists that file)."""
        rel = "store/records.jsonl"
        if self._manifest is None or rel not in self._manifest:
            return None
        if getattr(self, "_store_index", None) is None:
            self._store_index = {}
            path = safe_join(self.root, rel)
            if path and os.path.isfile(path) and os.path.getsize(path) <= RAW_CAP_BYTES * 8:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    for n, line in enumerate(handle.read().split("\n"), 1):
                        try:
                            key = json.loads(line).get("record_id")
                        except (ValueError, AttributeError):
                            continue
                        if key and key not in self._store_index:
                            self._store_index[key] = (n, line)
        hit = self._store_index.get(rid)
        if hit is None:
            return None
        return {"line": hit[1], "sha256": sha256_text(hit[1]), "capture": None, "path": rel, "line_no": hit[0]}

    def _pack_file(self, ref):
        """register:/manifest:/assessment-file refs (<scheme>:<path in the pack>[#section]) -> the file as sealed,
        with the sha256 of its bytes, so the inspector shows it instead of 'unresolved'. Only MANIFEST-listed files."""
        scheme, _, rest = (ref or "").partition(":")
        rel = rest.split("#", 1)[0]
        if scheme not in ("register", "manifest", "file") or not rel or self._manifest is None or (rel not in self._manifest and rel != "MANIFEST.json"):
            return None
        path = safe_join(self.root, rel)
        if path is None or not os.path.isfile(path) or os.path.getsize(path) > RAW_CAP_BYTES:
            return None
        with open(path, "rb") as handle:
            data = handle.read()
        return {"line": data.decode("utf-8", errors="replace"), "sha256": sha256_bytes(data), "path": rel,
                "capture": {"note": "whole file as sealed in the pack; sha256 is of the file bytes (= its MANIFEST entry)"}}

    def raw(self, ref):
        if (ref or "").startswith("record:"):
            return self._store_line(ref[len("record:"):])
        got = self._pack_file(ref)
        if got is not None:
            return got
        parsed = parse_raw_ref(ref)
        if not parsed:
            return None
        rel, n = parsed
        if not self._raw_allowed(rel):
            return None
        path = safe_join(self.root, rel)
        if path is None or not os.path.isfile(path) or os.path.getsize(path) > RAW_CAP_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().split("\n")
        if n > len(lines) or (n == len(lines) and lines[-1] == ""):
            return None
        line = lines[n - 1]
        cap = None
        side = sidecar_for(rel)
        if self._raw_allowed(side):
            spath = safe_join(self.root, side)
            if spath and os.path.isfile(spath):
                try:
                    cap = read_json(spath)
                except ValueError:
                    cap = None
        return {"line": line, "sha256": sha256_text(line), "capture": cap}

    def cases(self):
        return list(self._case_docs)

    def refused_cases(self):
        return list(self._case_refused)

    def integrity(self, max_age=60):
        if time.time() - self._integrity_at > max_age:
            self._integrity = verify_manifest(self.root)
            self._integrity_at = time.time()
        i = dict(self._integrity)
        i["verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._integrity_at))
        sub = (self.index.get("integrity") or {}).get("submission")
        i["submission"] = sub
        return i

    def replay(self, ident):
        path = os.path.join(self.root, "live", "events.jsonl")
        if not os.path.isfile(path) or os.path.islink(path):
            return None
        run = self.run(ident)
        keys = set([ident] + ([run.get("cid"), run.get("run_alias")] if run else []))
        return [e for e in read_jsonl(path) if e.get("run") in keys or e.get("cid") in keys or e.get("run_id") in keys]

    def mode_info(self):
        i = self.integrity()
        st = i["status"]
        if self.live:
            chip, head = "LIVE · read-only", "live index"
        else:
            chip, head = "PACK · read-only", "PACK"
        if st == "VERIFIED":
            banner, tone, text = "%s · MANIFEST VERIFIED · %d files listed" % (head, i["files"]), "real", "✓ %d/%d" % (i["files"], i["files"])
        elif st == "MODIFIED":
            names = ", ".join(i["changed"] + i["missing"] + i["unlisted"])
            banner, tone, text = "PACK MODIFIED since sealing: %s. Answers are UNVERIFIED." % names, "bad", "✗ MODIFIED"
        else:
            banner, tone, text = "%s · no MANIFEST.json: integrity unknown, answers are UNVERIFIED" % head, "warn", "? none"
        return {"data": "live" if self.live else "pack", "chip": chip, "tone": tone, "banner": banner,
                "integrity_ok": st == "VERIFIED", "integrity_text": text, "synthetic": False}
