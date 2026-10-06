"""gap-list.md -> pack-index gaps[] (`ifabric.gap/v1`). Stdlib, Python 3.9. Read-only over the staged gap list.

A gap starts at a heading the gap list uses: `**A1. Title**`, `### 3. Title` or `## B12. Title`. Its fields come from
the labelled lines under it (What / What's missing, Why, Affects, Impact, Next / If you had one more day, Status).
A field the entry does not state stays as the text "not stated in gap-list.md": nothing is invented.
"""
import re

NOT_STATED = "not stated in gap-list.md"
_HEAD = (re.compile(r"^\*\*([A-Z]\d+)\.\s+(.+?)\*\*\s*$"),           # **A1. AICT discovery scope**
         re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$"),                   # ### 1. A governed answer ...
         re.compile(r"^##\s+([A-Z]\d+)\.\s+(.+?)\s*$"))               # ## B12. Design gaps ...
_SECTION = re.compile(r"^##\s+([AB])\.\s")
_FIELD = re.compile(r"^(?:-\s*)?\*\*([A-Za-z' ]+?):\*\*\s*(.*)$")
_KEYS = {"what": "what", "what's missing": "what", "why": "why", "affects": "affects", "impact": "impact",
         "next": "next", "if you had one more day": "next", "status": "status"}
_LEVELS = re.compile(r"\bL([123])\b")
_CONTROLS = re.compile(r"\bC(16|7|9)\b")
_QUESTIONS = ("WHO", "WHAT", "AUTHORIZED", "APPROVED", "INTEGRITY", "RECONSTRUCT")


def _clean(text):
    return re.sub(r"\s+", " ", text.replace("`", "")).strip()


def parse(text):
    gaps, cur, field, section = [], None, None, "A"
    for line in (text or "").splitlines():
        m = _SECTION.match(line)
        if m:
            section = m.group(1)
        head = None
        for rx in _HEAD:
            head = rx.match(line)
            if head:
                break
        if head:
            gid = head.group(1)
            if gid.isdigit():
                gid = "B%s" % gid
            cur = {"gap_id": gid, "section": "B" if gid.startswith("B") else section, "title": _clean(head.group(2)),
                   "_f": {}}
            gaps.append(cur)
            field = None
            continue
        if cur is None:
            continue
        if line.startswith("## ") or line.strip() == "---":
            field = None
            continue
        f = _FIELD.match(line.strip())
        if f and f.group(1).strip().lower() in _KEYS:
            field = _KEYS[f.group(1).strip().lower()]
            cur["_f"][field] = cur["_f"].get(field, "") + " " + f.group(2)
            continue
        if field and line.strip():
            cur["_f"][field] = cur["_f"].get(field, "") + " " + line.strip().lstrip("-* ")
    out = []
    for g in gaps:
        f = dict((k, _clean(v)) for k, v in g.pop("_f").items())
        body = " ".join(f.values()) + " " + g["title"]
        status = f.get("status", "").upper()
        aff = f.get("affects") or ""
        out.append({
            "schema": "ifabric.gap/v1", "gap_id": g["gap_id"], "section": g["section"], "title": g["title"],
            "what": f.get("what") or NOT_STATED, "why": f.get("why") or NOT_STATED,
            "affects": {"controls": sorted(set("C" + c for c in _CONTROLS.findall(aff or body))),
                        "levels": sorted(set("L" + x for x in _LEVELS.findall(aff))),
                        "auditor_questions": [q for q in _QUESTIONS if re.search(r"\b%s\b" % q, g["title"] + " " + aff)]},
            "impact": f.get("impact") or NOT_STATED, "next": f.get("next") or NOT_STATED,
            "status": "CLOSED" if "CLOSED" in status else "MITIGATED" if "MITIGATED" in status else "OPEN",
            "source": "gap-list.md#%s" % g["gap_id"],
        })
    return out
