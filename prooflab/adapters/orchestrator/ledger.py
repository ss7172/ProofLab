"""Ledger write token handling (ARCH 7.2 credentials). The token exists only in memory.

`read_token` runs kubectl through a subprocess pipe and decodes the Secret in this process; it never goes on
argv, in a child's env, in a log line or on disk. `LedgerSink.post` sends it only as the X-Audit-Token header.
A ledger POST from the laptop is untested (spike S-1): the spool file is the always-on record.
"""
from __future__ import annotations

import base64
import json
import subprocess
import urllib.request


def read_token(namespace: str, secret: str, key: str, runner=subprocess.run) -> str:
    argv = ["kubectl", "-n", namespace, "get", "secret", secret, "-o", "jsonpath={.data.%s}" % key]
    proc = runner(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("could not read the ledger secret (exit %s)" % proc.returncode)
    raw = proc.stdout if isinstance(proc.stdout, bytes) else proc.stdout.encode()
    return base64.b64decode(raw.strip()).decode("utf-8").strip()


class LedgerSink:
    """POSTs records to `<base_url>/records`. The token is held privately and never rendered."""

    def __init__(self, base_url: str, token: str, timeout: float = 5.0):
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def __repr__(self):
        return "LedgerSink(%s, token=<withheld>)" % self._base

    def post(self, records) -> int:
        body = json.dumps(list(records)).encode("utf-8")
        req = urllib.request.Request(self._base + "/records", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "X-Audit-Token": self._token})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return resp.status
