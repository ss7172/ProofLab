"""The strict flat-YAML subset parser (ARCH §3.3 schema rules 1-7). Stdlib, Python 3.9.

One parser for `register.yaml`, `risks.yaml` and `inventory.yaml`. The accepted subset is exactly what
the kit's no-PyYAML fallback (`starter/evaluate.py::_load_register`) reads the same way, so the judged
register parses identically in both. Anything the kit would silently misread is an error here:

  1. top-level `key: value` lines come before the list key (`controls:`, `risks:`, `components:`);
  2. each entry is flat `key: value`, starting `- <id key>: value`; no nested maps or lists;
  3. nothing follows the last entry at column 0;
  4. no `#` inside a value (only whole-line comments or ` # ...` after a complete value);
  5. (the kit fields are checked by prooflab.contract.register, not here);
  6. one line per value: no `|`, `>`, flow collections or continuation lines;
  7. values are strings exactly as the kit fallback returns them (quotes stripped, never typed).

    doc = parse_text(text)                 # {"top": {...}, "list_key": "controls", "entries": [{...}, ...]}
    controls = kit_view(text)              # {"16": {...}, "7": {...}} = the kit fallback's result
"""
from __future__ import annotations

import re

LIST_KEYS = {"controls": "control_id", "risks": "risk_id", "components": "component_id"}

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")


class RegisterParseError(ValueError):
    """A line the strict subset refuses; the message starts with 'line <n>:'."""


def _strip_comment(raw: str, lineno: int) -> str:
    if "#" not in raw:
        return raw.rstrip()
    head = raw.split("#", 1)[0]
    if head.strip() and not head[-1:].isspace():
        raise RegisterParseError("line %d: '#' inside a value (rule 4)" % lineno)
    value = head.split(":", 1)[-1].strip() if ":" in head else ""
    if value[:1] in ("'", '"') and (len(value) < 2 or value[-1] != value[0]):
        raise RegisterParseError("line %d: '#' inside a quoted value (rule 4)" % lineno)
    return head.rstrip()


def _value(text: str, lineno: int) -> str:
    v = text.strip()
    if v == "":
        raise RegisterParseError("line %d: empty value: nested maps and lists are not allowed (rule 2)" % lineno)
    if v[0] in "|>":
        raise RegisterParseError("line %d: block scalars are not allowed (rule 6)" % lineno)
    if v[0] in "[{":
        raise RegisterParseError("line %d: flow collections are not allowed; comma-join lists (rule 2)" % lineno)
    if v[0] in "\"'":
        if len(v) < 2 or v[-1] != v[0]:
            raise RegisterParseError("line %d: unterminated quoted value" % lineno)
        inner = v[1:-1]
        if inner[:1] in ("'", '"') or inner[-1:] in ("'", '"'):
            raise RegisterParseError("line %d: a quote at the edge of a quoted value (the kit strips it)" % lineno)
        return inner
    if v[-1] in "\"'":
        raise RegisterParseError("line %d: stray quote at the end of a value" % lineno)
    if ": " in v:
        raise RegisterParseError("line %d: unquoted value contains ': ' (quote it)" % lineno)
    if v.startswith(("&", "*", "!", "%", "@", "`")):
        raise RegisterParseError("line %d: YAML anchors, aliases and tags are not allowed" % lineno)
    return v


def _key(text: str, lineno: int) -> str:
    if text != text.rstrip():
        raise RegisterParseError("line %d: whitespace before ':' (the kit would keep it in the key)" % lineno)
    k = text.strip()
    if not _KEY_RE.match(k):
        raise RegisterParseError("line %d: invalid key %r" % (lineno, k))
    return k


def parse_text(text: str, list_key: "str | None" = None) -> dict:
    """Parse one file. `list_key` defaults to the first of controls/risks/components that appears."""
    if "\t" in text:
        raise RegisterParseError("tabs are not allowed")
    top, entries, cur = {}, [], None
    found_list, id_key = None, None
    for lineno, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("#") or not raw.strip():
            continue
        line = _strip_comment(raw, lineno)
        if not line.strip():
            continue
        indented = line[:1].isspace()
        body = line.strip()
        if found_list is None:
            if indented:
                raise RegisterParseError("line %d: indented line before the list key (rule 1)" % lineno)
            if ":" not in body:
                raise RegisterParseError("line %d: not a 'key: value' line" % lineno)
            k, v = body.split(":", 1)
            k = _key(k, lineno)
            if v.strip() == "" and (k == list_key or (list_key is None and k in LIST_KEYS)):
                found_list, id_key = k, LIST_KEYS.get(k, "id")
                continue
            if k in top:
                raise RegisterParseError("line %d: duplicate top-level key %r" % (lineno, k))
            top[k] = _value(v, lineno)
            continue
        if not indented:
            raise RegisterParseError("line %d: nothing may follow the last entry at column 0 (rule 3)" % lineno)
        if body.startswith("-"):
            item = body[2:]
            if not body.startswith("- " + id_key + ":"):
                raise RegisterParseError("line %d: a list item must start '- %s:' (rule 2)" % (lineno, id_key))
            if cur is not None:
                entries.append(cur)
            cur = {id_key: _value(item.split(":", 1)[1], lineno)}
            continue
        if cur is None:
            raise RegisterParseError("line %d: key before the first '- %s:' entry" % (lineno, id_key))
        if ":" not in body:
            raise RegisterParseError("line %d: continuation lines are not allowed (rule 6)" % lineno)
        k, v = body.split(":", 1)
        k = _key(k, lineno)
        if k in cur:
            raise RegisterParseError("line %d: duplicate key %r in one entry" % (lineno, k))
        cur[k] = _value(v, lineno)
    if cur is not None:
        entries.append(cur)
    if found_list is None:
        raise RegisterParseError("no list key (%s) found" % ", ".join(sorted(LIST_KEYS)))
    seen = set()
    for entry in entries:
        if entry[id_key] in seen:
            raise RegisterParseError("duplicate %s %r" % (id_key, entry[id_key]))
        seen.add(entry[id_key])
    return {"top": top, "list_key": found_list, "id_key": id_key, "entries": entries}


def parse_file(path, list_key: "str | None" = None) -> dict:
    with open(str(path), "rb") as handle:
        data = handle.read()
    return parse_text(data.decode("utf-8"), list_key)


def entries_by_id(doc: dict) -> dict:
    return dict((e[doc["id_key"]], e) for e in doc["entries"])


def kit_view(text: str) -> dict:
    """{control_id: {key: str}} exactly as the kit's fallback `_load_register` returns it, after a strict parse."""
    doc = parse_text(text, "controls")
    return dict((str(e["control_id"]), dict(e)) for e in doc["entries"])


def parse_register(text: str) -> dict:
    return parse_text(text, "controls")


def parse_risks(text: str) -> dict:
    return parse_text(text, "risks")


def parse_inventory(text: str) -> dict:
    return parse_text(text, "components")
