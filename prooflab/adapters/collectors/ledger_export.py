"""Ledger export, PER CID ONLY (ARCH §3.1; B1): kubectl proxy -> audit-store `/records?cid=<cid>` with the
X-Audit-Token header. There is no full-GET path in this module. The token is injected by the caller, never
logged, never written (the response is scrubbed of it too). `fetch` is the seam (tests inject a fake)."""
from __future__ import annotations

from urllib.parse import quote
from urllib.request import Request, urlopen

from prooflab.adapters.collectors import capture

SURFACE = "ledger"
PROXY_BASE = "http://127.0.0.1:8001"
ROUTE = "/api/v1/namespaces/components/services/audit-store:8080/proxy/records"
TOKEN_HEADER = "X-Audit-Token"


def records_url(cid: str, base: str = PROXY_BASE) -> str:
    if not cid:
        raise capture.CaptureError("a ledger pull needs a cid (no full GET)")
    return "%s%s?cid=%s" % (base.rstrip("/"), ROUTE, quote(cid, safe=""))


def urllib_fetch(url: str, headers: dict) -> tuple:
    """The live fetch (never called by tests or workers)."""
    with urlopen(Request(url, headers=headers), timeout=30) as resp:
        return resp.status, resp.read()


def pull(ctx: capture.Ctx, cid: str, token: str, fetch=urllib_fetch, base: str = PROXY_BASE) -> "dict | None":
    if capture.skip_cid(cid, ctx):
        return None
    url = records_url(cid, base)
    if "?cid=" not in url:
        raise capture.CaptureError("refusing a ledger URL without ?cid=")
    status, body = fetch(url, {TOKEN_HEADER: token})
    if status != 200:
        raise capture.CaptureError("ledger returned HTTP %s" % (status,))
    return capture.write_capture(
        ctx, SURFACE, cid, "records.jsonl", body,
        command="GET %s (header %s: [REDACTED:bearer])" % (url, TOKEN_HEADER),
        scope={"cid": cid}, source_identity={"service": "components/audit-store:8080", "route": "records"},
        pagination_complete=True, exact_values=(token,))
