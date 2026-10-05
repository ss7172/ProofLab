"""Minimal ServiceNow REST client: OAuth client-credentials + Table API.

Standard library only so it runs unchanged in the workshop IDE.
Credentials come from the environment, never from code or files:
  SNOW_INSTANCE, SNOW_CLIENT_ID, SNOW_CLIENT_SECRET
HTTPS only (plain http is allowed for localhost test fakes), redirects are
never followed, so the bearer token and client secret cannot be forwarded.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPException
from typing import Callable, List, Optional

TIMEOUT_SECONDS = 15
TOKEN_REFRESH_MARGIN_SECONDS = 60
_QUERY_UNSAFE = ("^", "\n", "\r")
_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


class ServiceNowError(Exception):
    """A ServiceNow call failed. status is None when no usable HTTP answer arrived."""

    def __init__(self, status: Optional[int], message: str) -> None:
        super().__init__(f"ServiceNow {status if status is not None else 'unreachable'}: {message}")
        self.status = status

    @property
    def outcome_unknown(self) -> bool:
        """True when a write may have been applied even though we got no clean answer."""
        return self.status is None or self.status >= 500 or self.status == 408


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None  # surface 3xx as an HTTPError instead of following it


_OPENER = urllib.request.build_opener(_NoRedirect)


def check_query_value(value: str) -> str:
    """Reject characters that would change a ServiceNow encoded query."""
    if any(ch in value for ch in _QUERY_UNSAFE):
        raise ValueError(f"unsafe characters in query value: {value!r}")
    return value


def _require_https(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme == "https":
        return base_url
    if parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS:
        return base_url
    raise ValueError(f"ServiceNow base_url must use https://, got {base_url!r}")


class ServiceNowClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str,
                 clock: Callable[[], float] = time.time) -> None:
        if not (base_url and client_id and client_secret):
            raise ValueError("base_url, client_id and client_secret are required")
        self.base_url = _require_https(base_url.rstrip("/"))
        self._client_id = client_id
        self._client_secret = client_secret
        self._clock = clock
        self._token: Optional[str] = None
        self._token_expires_at = 0.0

    @classmethod
    def from_env(cls) -> "ServiceNowClient":
        missing = [name for name in ("SNOW_INSTANCE", "SNOW_CLIENT_ID", "SNOW_CLIENT_SECRET")
                   if not os.environ.get(name)]
        if missing:
            raise ValueError(f"set environment variables: {', '.join(missing)}")
        instance = os.environ["SNOW_INSTANCE"].strip()
        base = instance if instance.startswith(("https://", "http://")) else f"https://{instance}"
        return cls(base, os.environ["SNOW_CLIENT_ID"], os.environ["SNOW_CLIENT_SECRET"])

    # ------------------------------------------------------------ transport
    def _send(self, request: urllib.request.Request) -> dict:
        try:
            with _OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read().decode(errors="replace") or "{}"
        except urllib.error.HTTPError as err:
            detail = err.read().decode(errors="replace")[:300]
            raise ServiceNowError(err.code, detail) from err
        except (urllib.error.URLError, socket.timeout, ConnectionError, HTTPException) as err:
            raise ServiceNowError(None, str(err)) from err
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as err:
            raise ServiceNowError(None, f"unparseable response: {raw[:80]!r}") from err
        if not isinstance(payload, dict):
            raise ServiceNowError(None, "unexpected response shape")
        return payload

    def _access_token(self) -> str:
        if self._token and self._clock() < self._token_expires_at - TOKEN_REFRESH_MARGIN_SECONDS:
            return self._token
        form = urllib.parse.urlencode({"grant_type": "client_credentials",
                                       "client_id": self._client_id,
                                       "client_secret": self._client_secret}).encode()
        request = urllib.request.Request(f"{self.base_url}/oauth_token.do", data=form, method="POST",
                                         headers={"Content-Type": "application/x-www-form-urlencoded",
                                                  "Accept": "application/json"})
        payload = self._send(request)
        token = payload.get("access_token")
        if not token:
            reason = f"{payload.get('error', 'no_token')}: {payload.get('error_description', '')}"
            raise ServiceNowError(401, f"OAuth token not issued ({reason})")
        self._token = token
        self._token_expires_at = self._clock() + float(payload.get("expires_in", 1800))
        return token

    def _api(self, method: str, path: str, params: Optional[dict] = None,
             body: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self._access_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        payload = self._send(request)
        if "result" not in payload:
            raise ServiceNowError(None, "response has no 'result'")
        return payload

    # ------------------------------------------------------------ table API
    def find_user_sys_id(self, user_name: str) -> str:
        rows = self._api("GET", "/api/now/table/sys_user", {
            "sysparm_query": f"user_name={check_query_value(user_name)}^active=true",
            "sysparm_fields": "sys_id,user_name", "sysparm_limit": "1"})["result"]
        if not rows:
            raise ServiceNowError(404, f"active user {user_name!r} not found")
        return rows[0]["sys_id"]

    def find_incidents(self, correlation_id: str, created_by: str) -> List[dict]:
        """Our incidents for this correlation id, oldest first (other teams' are excluded)."""
        query = (f"correlation_id={check_query_value(correlation_id)}"
                 f"^sys_created_by={check_query_value(created_by)}^ORDERBYsys_created_on")
        return self._api("GET", "/api/now/table/incident",
                         {"sysparm_query": query, "sysparm_limit": "5"})["result"]

    def create_incident(self, payload: dict) -> dict:
        return self._api("POST", "/api/now/table/incident", body=payload)["result"]

    def get_incident(self, sys_id: str) -> dict:
        return self._api("GET", f"/api/now/table/incident/{urllib.parse.quote(sys_id)}")["result"]

    def get_incident_notes_text(self, sys_id: str) -> dict:
        """Work notes / comments as display text. Readable by itil even when
        sys_journal_field rows are hidden by ACLs."""
        return self._api("GET", f"/api/now/table/incident/{urllib.parse.quote(sys_id)}", {
            "sysparm_fields": "work_notes,comments", "sysparm_display_value": "true"})["result"]

    def list_work_notes(self, sys_id: str) -> List[dict]:
        """Journal entries (comments/work notes) on an incident, oldest first."""
        return self._api("GET", "/api/now/table/sys_journal_field", {
            "sysparm_query": f"element_id={check_query_value(sys_id)}^ORDERBYsys_created_on",
            "sysparm_fields": "element,value,sys_created_by,sys_created_on"})["result"]
