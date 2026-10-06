"""Client for the platform ledger `audit-store` (ARCH §3.5, the S-1 path). Stdlib, Python 3.9.

Route that works from the laptop (B1 fact): kubectl proxy ->
  /api/v1/namespaces/components/services/audit-store:8080/proxy/records   with header X-Audit-Token.
The token is held in memory only: passed in by the caller (or read from an env var by `from_env`), never put
on argv, in a file, in an error message or in repr(). The server has no update or delete route and neither does
this client: it only appends (POST) and reads (GET). Reads are per CID; a full read is refused unless the caller
says it runs between runs (the server is single-threaded and parses the whole file on every GET).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

TOKEN_HEADER = "X-Audit-Token"
DEFAULT_TIMEOUT_S = 10.0


class LedgerError(Exception):
    """A ledger call failed. The message never carries the token."""


class LedgerClient:
    def __init__(self, base_url: str, token: str, timeout: float = DEFAULT_TIMEOUT_S, opener=None):
        if not token:
            raise LedgerError("no ledger write token supplied")
        self._base = base_url.rstrip("/")
        self._credential = token
        self._timeout = timeout
        self._open = opener or urllib.request.urlopen

    @classmethod
    def from_env(cls, base_url: str, env_name: str, **kw) -> "LedgerClient":
        value = os.environ.get(env_name)
        if not value:
            raise LedgerError("environment variable %s is not set" % env_name)
        return cls(base_url, value, **kw)

    def __repr__(self) -> str:
        return "LedgerClient(%s, credential=<hidden>)" % self._base

    # ---- plumbing -------------------------------------------------------------------------------
    def _call(self, method: str, path: str, body=None):
        data = None
        headers = {TOKEN_HEADER: self._credential, "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self._base + path, data=data, headers=headers, method=method)
        try:
            with self._open(req, timeout=self._timeout) as resp:
                return resp.getcode(), resp.read()
        except urllib.error.HTTPError as exc:
            raise LedgerError("%s %s -> HTTP %d" % (method, path.split("?")[0], exc.code))
        except (urllib.error.URLError, OSError) as exc:
            raise LedgerError("%s %s failed: %s" % (method, path.split("?")[0], type(exc).__name__))

    @staticmethod
    def _rows(raw: bytes) -> list:
        text = raw.decode("utf-8", "replace").strip()
        if not text:
            return []
        try:
            doc = json.loads(text)
        except ValueError:
            doc = [json.loads(line) for line in text.splitlines() if line.strip()]
        if isinstance(doc, dict):
            doc = doc.get("records", [doc])
        return [r for r in doc if isinstance(r, dict)]

    # ---- the only two verbs ---------------------------------------------------------------------
    def post(self, record: dict) -> int:
        """Append one record. Returns the HTTP status (2xx); raises LedgerError otherwise."""
        status, _ = self._call("POST", "/records", record)
        return status

    def get_by_cid(self, cid: str) -> list:
        """The ledger's records for one correlation id (`GET /records?cid=`)."""
        _, raw = self._call("GET", "/records?" + urllib.parse.urlencode({"cid": cid}))
        return self._rows(raw)

    def get_all(self, between_runs: bool = False) -> list:
        """A full read. Only between runs and at the final refresh: it can starve a live agent's emit."""
        if between_runs is not True:
            raise LedgerError("a full ledger read is only allowed between runs (pass between_runs=True)")
        _, raw = self._call("GET", "/records")
        return self._rows(raw)
