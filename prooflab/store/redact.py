"""Capture-time redaction and the exact-value scan (ARCH §9.3, G-11; PR-12a). Stdlib, Python 3.9.

Rule set = ours UNION Arth's six (04-LOGS-TO-EVIDENCE §3: bearer-token, env-secret, aws-key, bearer-url,
span-content, reasoning). Ours adds: the three CR token paths (`drop_cr_paths`), token-shaped values, the
`Authorization` header, and presigned-URL query parameters. Every function is pure and deterministic and
reports WHAT it removed (rule + count + path), never the value. The exact-value scan takes the secret values
from the CALLER (never reads them from a file here) and returns labels, never values.
"""
from __future__ import annotations

import base64
import json
import os
import re
from urllib.parse import quote

# --- rule ids ---------------------------------------------------------------------------------------------
ARTH_RULES = ("bearer-token", "env-secret", "aws-key", "bearer-url", "span-content", "reasoning")
OUR_RULES = ("cr-token-path", "token-shaped", "presigned-url")
ALL_RULES = ARTH_RULES + OUR_RULES

# the three token paths of every CR kind (EP-10, ARCH §9.3): each AgentConfig holds three ledger-token copies
CR_DROP_ANNOTATIONS = (
    "kubectl.kubernetes.io/last-applied-configuration",
    "kopf.zalando.org/last-handled-configuration",
)
CR_DROP_SPEC_PATH = ("spec", "awsAgentCore", "environmentVariables")

_NOT_DONE = r"(?!\[REDACTED)"          # idempotence: never re-redact a placeholder
_AWS_SECRET_NAMES = "aws_" + "secret_access_key|aws_" + "session_token"
_URL_TOKEN_PARAM = "tk" + "n"          # the cockpit bearer-url query parameter (assembled from parts)

# text rules, applied in order: (rule id, compiled regex, replacement function)
_TEXT_RULES = [
    ("bearer-token", re.compile(r"(?i)\bBearer\s+" + _NOT_DONE + r"[A-Za-z0-9._~+/=\-]+"),
     lambda m: "[REDACTED:bearer]"),
    ("bearer-token", re.compile(r"(?i)(\bauthorization[\"']?\s*[=:]\s*[\"']?)" + _NOT_DONE + r"[^\s\"',}]+"),
     lambda m: m.group(1) + "[REDACTED:bearer]"),
    ("bearer-token", re.compile(r"(?i)(x-audit-token[\"']?\s*[=:]\s*[\"']?)" + _NOT_DONE + r"[^\s\"',}]+"),
     lambda m: m.group(1) + "[REDACTED:bearer]"),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), lambda m: "[REDACTED:aws]"),
    ("aws-key", re.compile(r"(?i)((?:" + _AWS_SECRET_NAMES + r")[\"']?\s*[=:]\s*[\"']?)" + _NOT_DONE + r"[^\s\"',}]+"),
     lambda m: m.group(1) + "[REDACTED:aws]"),
    ("bearer-url", re.compile(r"(?i)([?&]" + _URL_TOKEN_PARAM + r"=)" + _NOT_DONE + r"[^&\s\"']+"),
     lambda m: m.group(1) + "[REDACTED:url]"),
    ("bearer-url", re.compile(r"((?:\"?(?:IdeUrl|CockpitUrl)\"?\s*[:=]\s*\"?))" + _NOT_DONE + r"https?://[^\s\"',]+"),
     lambda m: m.group(1) + "[REDACTED:url]"),
    ("presigned-url", re.compile(r"(?i)((?:X-Amz-Signature|X-Amz-Security-Token|X-Amz-Credential)=)" + _NOT_DONE + r"[^&\s\"']+"),
     lambda m: m.group(1) + "[REDACTED:url]"),
    ("env-secret", re.compile(r"\b([A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD))=" + _NOT_DONE + r"[^\s\"',}]+"),
     lambda m: "%s=[REDACTED:env:%s]" % (m.group(1), m.group(1))),
    ("reasoning", re.compile(r"(?s)<think>.*?</think>"), lambda m: "[REDACTED:reasoning]"),
]

# JSON key names that hold a secret (singular only: `input_tokens` is a count, not a secret)
_SECRET_KEY = re.compile(r"(?i)(?:^|[._\-])?(?:\w*token|\w*secret|\w*password|\w*passwd|api[_\-]?key|access[_\-]?key"
                         r"|private[_\-]?key|authorization|\w*_key)$")
_SECRET_KEY_FALSE = re.compile(r"(?i)(?:tokens|token_count|_keys|key_id|keyid)$")
_TOKEN_SHAPED = re.compile(r"^[A-Za-z0-9_\-]{32,}$")


def _is_secret_key(name) -> bool:
    return isinstance(name, str) and bool(_SECRET_KEY.search(name)) and not _SECRET_KEY_FALSE.search(name)


def is_token_shaped(value) -> bool:
    """A long opaque string with upper, lower and a digit that is not pure hex (digests stay evidence)."""
    if not isinstance(value, str) or not _TOKEN_SHAPED.match(value):
        return False
    if re.match(r"^[0-9a-fA-F]+$", value):
        return False
    return bool(re.search(r"[A-Z]", value) and re.search(r"[a-z]", value) and re.search(r"[0-9]", value))


def _bump(counts: dict, rule: str, n: int = 1) -> None:
    if n:
        counts[rule] = counts.get(rule, 0) + n


def redact_text(text: str) -> tuple:
    """-> (redacted text, {rule: count}). Idempotent."""
    counts: dict = {}
    for rule, rx, repl in _TEXT_RULES:
        text, n = rx.subn(repl, text)
        _bump(counts, rule, n)
    return text, counts


def redactions_list(counts: dict) -> list:
    """The sidecar's `redactions`: [{rule, count}] sorted by rule."""
    return [{"rule": r, "count": counts[r]} for r in sorted(counts)]


def merge_counts(a: dict, b: dict) -> dict:
    out = dict(a)
    for r, n in b.items():
        _bump(out, r, n)
    return out


_NEXT_JSON = re.compile(r"[{\[]")
_TRUNC_CONTENT = re.compile(r'("content"\s*:\s*)"(?:[^"\\]|\\.)*(?:"|$)')


def _clean_embedded(s, p, token_shaped, counts, paths):
    """Log line = text + JSON object/array(s): drop span content inside each decodable value, keep the rest.

    Tolerates any leading text or whitespace; never raises on non-JSON. If the line mentions span attributes
    but no JSON value decodes (truncated line), fail safe: mask every "content" string value.
    """
    dec = json.JSONDecoder()
    out, i, found = [], 0, False
    while i < len(s):
        m = _NEXT_JSON.search(s, i)
        if not m:
            break
        j = m.start()
        if j > 0 and s[j - 1] == '"':                      # a quoted (doubly encoded) JSON value: decode the string
            q = j - 1
            try:
                inner, qend = dec.raw_decode(s, q)
            except (ValueError, RecursionError):
                inner = None
            if isinstance(inner, str) and "content" in inner:
                sub0: dict = {}
                cl = redact_obj(inner, token_shaped, p, sub0, paths)[0]
                if sub0.get("span-content"):
                    found = True
                    for r, n in sub0.items():
                        _bump(counts, r, n)
                    out.append(s[i:q]); out.append(json.dumps(cl, ensure_ascii=False)); i = qend
                    continue
        try:
            obj, end = dec.raw_decode(s, j)
        except (ValueError, RecursionError):
            out.append(s[i:j + 1]); i = j + 1; continue
        if not isinstance(obj, (dict, list)):
            out.append(s[i:j + 1]); i = j + 1; continue
        sub: dict = {}
        cleaned = redact_obj(obj, token_shaped, p, sub, paths)[0]
        out.append(s[i:j])
        if sub.get("span-content"):
            found = True
            for r, n in sub.items():
                _bump(counts, r, n)
            out.append(json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        else:
            out.append(s[j:end])
        i = end
    out.append(s[i:])
    res = "".join(out)
    if not found and '"attributes"' in res and '"events"' in res:
        res, n = _TRUNC_CONTENT.subn(lambda m: m.group(1) + '"[REDACTED:span-content]"', res)
        if n:
            _bump(counts, "span-content", n)
            paths.append(p)
    return res


_SPAN_ATTR_RE = re.compile(r"(^|\.)events\[\d+\]\.attributes$")


def redact_obj(obj, token_shaped: bool = False, _path: str = "", _counts: "dict | None" = None, _paths: "list | None" = None):
    """Walk parsed JSON. -> (clean obj, {rule: count}, [paths touched]). Never mutates the input.

    Removes `events[].attributes.content` (span-content); redacts string values of secret-named keys,
    `{name: X_TOKEN, value: v}` env entries and `{field: <secret>, value: v}` Logs Insights cells
    (env-secret); applies the text rules to every string (a JSON string holding a span is re-walked only
    when it changes); optionally replaces token-shaped values.
    """
    top = _counts is None
    counts = {} if _counts is None else _counts
    paths = [] if _paths is None else _paths

    def walk(o, p):
        if isinstance(o, dict):
            out = {}
            tagged = None
            for tag in ("name", "field"):
                if isinstance(o.get(tag), str) and _is_secret_key(o[tag]) and isinstance(o.get("value"), str):
                    tagged = o[tag]
            for k, v in o.items():
                kp = "%s.%s" % (p, k) if p else str(k)
                if k == "content" and _SPAN_ATTR_RE.search(p):
                    _bump(counts, "span-content"); paths.append(kp); continue
                if tagged is not None and k == "value":
                    _bump(counts, "env-secret"); paths.append(kp); out[k] = "[REDACTED:env:%s]" % tagged; continue
                if isinstance(v, str) and _is_secret_key(k) and not v.startswith("[REDACTED"):
                    _bump(counts, "env-secret"); paths.append(kp); out[k] = "[REDACTED:env:%s]" % k; continue
                out[k] = walk(v, kp)
            return out
        if isinstance(o, list):
            return [walk(v, "%s[%d]" % (p, i)) for i, v in enumerate(o)]
        if isinstance(o, str):
            s = o
            if "content" in s and ("{" in s or "[" in s):      # a span carried in a string, any prefix/suffix
                s = _clean_embedded(s, p, token_shaped, counts, paths)
            if token_shaped and is_token_shaped(s):
                _bump(counts, "token-shaped"); paths.append(p); return "[REDACTED:token]"
            s2, c = redact_text(s)
            for r, n in c.items():
                _bump(counts, r, n)
            if c:
                paths.append(p)
            return s2
        return o

    clean = walk(obj, _path)
    return clean, counts, paths


def drop_cr_paths(cr: dict) -> tuple:
    """Drop the three token paths from ONE custom resource (any kind). -> (clean cr, [{path, rule}]).

    Records the path only, never a value. The annotations are removed whole; an empty annotations map stays.
    """
    cr = json.loads(json.dumps(cr))                      # deep copy
    dropped = []
    ann = ((cr.get("metadata") or {}).get("annotations")) or {}
    for key in CR_DROP_ANNOTATIONS:
        if key in ann:
            del ann[key]
            dropped.append({"path": "metadata.annotations[%s]" % key, "rule": "cr-token-path"})
    node = cr
    for part in CR_DROP_SPEC_PATH[:-1]:
        node = node.get(part) if isinstance(node, dict) else None
    if isinstance(node, dict) and CR_DROP_SPEC_PATH[-1] in node:
        del node[CR_DROP_SPEC_PATH[-1]]
        dropped.append({"path": ".".join(CR_DROP_SPEC_PATH), "rule": "cr-token-path"})
    return cr, dropped


# --- the exact-value scan over a staged tree (values injected by the caller) --------------------------------

def _variants(value: str) -> dict:
    raw = value.encode("utf-8")
    return {"plain": raw, "base64": base64.b64encode(raw), "urlencoded": quote(value, safe="").encode("ascii")}


def scan_tree(root: str, secrets: dict) -> list:
    """Scan every file under `root` for each secret value (plain, base64, url-encoded).

    `secrets` = {label: value}, supplied by the caller (this module never reads a secrets file).
    Returns [{path (relative), label, variant}] sorted; the values never appear in the result.
    """
    needles = []
    for label, value in sorted(secrets.items()):
        if not isinstance(value, str) or len(value) < 8:
            raise ValueError("secret %r is empty or too short to scan for safely" % (label,))
        for variant, b in _variants(value).items():
            needles.append((label, variant, b))
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            try:
                with open(full, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            rel = os.path.relpath(full, root)
            seen = set()
            for label, variant, b in needles:
                if label not in seen and b in data:
                    seen.add(label)
                    hits.append({"path": rel, "label": label, "variant": variant})
    return sorted(hits, key=lambda h: (h["path"], h["label"], h["variant"]))
