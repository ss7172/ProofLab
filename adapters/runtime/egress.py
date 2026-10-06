"""RT-03 / EP-15: the runtime egress audit (guardrails/AGENT-GUARDRAILS.md §3.7). Stdlib, py3.9.

A PEP 578 audit hook (sys.addaudithook; it cannot be removed once installed), installed first thing in the
agent file. It watches socket.getaddrinfo and socket.connect and records a FLAG, once per host, for any
destination outside the declared allowlist: the hosts of OPENAI_BASE_URL, AGENTCORE_GATEWAY_MCP_URL and
AUDIT_URL plus the hosts learned in the smoke run (passed as `extra`). Observe only: it never refuses a
connection and never raises (record-only; enforce is P3). The sink is the emit client's enqueue.
"""
import hashlib, os, sys, threading
from urllib.parse import urlsplit

V = "1"
ENV_URLS = ("OPENAI_BASE_URL", "AGENTCORE_GATEWAY_MCP_URL", "AUDIT_URL")
_S = {"installed": False, "allow": frozenset(), "seen": set(), "flags": [], "sink": None, "agent": None}
_T = threading.local()


def allowlist(extra=()):
    hosts = set()
    for e in ENV_URLS:
        h = urlsplit(os.environ.get(e) or "").hostname
        if h:
            hosts.add(h.lower())
    return frozenset(hosts | {str(x).lower() for x in extra})


def _host(event, args):
    if event == "socket.getaddrinfo":
        h = args[0]
        return h.decode("ascii", "replace") if isinstance(h, bytes) else h
    a = args[1] if len(args) > 1 else None   # socket.connect: (socket, address)
    return a[0] if isinstance(a, tuple) and a and isinstance(a[0], str) else None


def _record(host, event):
    al = sorted(_S["allow"])
    return {"record_kind": "rail_decision", "phase": "ifabric.rail_decision", "control.ref": "RAIL",
            "control.id": "RAIL-RT-03", "threshold.version": "RT-03@" + V,
            "threshold.value": "sha256:" + hashlib.sha256(",".join(al).encode()).hexdigest(),
            "register.version": None, "verdict": "FLAG", "reason": "RT-03 FLAG: egress.unlisted x1 (%s)" % event,
            "inline.mode": "observe", "inline.action": "proceed", "rail.id": "RT-03", "rail.version": V,
            "rail.stage": "runtime", "rail.hook": "audit_hook", "rail.mechanism": "code",
            "rail.matches": {"egress.unlisted": 1}, "rail.values": [host], "ep.id": "EP-15", "actor.id": _S["agent"],
            "null_reasons": {"register.version": "not a register control: rail"}}


def _hook(event, args):
    if event not in ("socket.getaddrinfo", "socket.connect") or getattr(_T, "busy", False):
        return
    _T.busy = True   # the sink's own POST must not re-enter the hook
    try:
        host = _host(event, args)
        if host is None:
            return
        host = host.lower().strip("[]")
        ok = host in _S["allow"]
        if event == "socket.getaddrinfo":
            _T.last_ok = ok   # the connect that follows an allowed resolution is that host's connection
        elif getattr(_T, "last_ok", False):
            return
        if ok or host in _S["seen"]:
            return
        _S["seen"].add(host)
        r = _record(host, event)
        _S["flags"].append(r)
        if _S["sink"] is not None:
            _S["sink"](r)
    except Exception:
        pass   # never raise from an audit hook (it would break the caller's connection)
    finally:
        _T.busy = False


def install(agent=None, sink=None, extra=()):
    """Install once per process; later calls return the existing state unchanged (no reconfiguration)."""
    if not _S["installed"]:
        _S.update(installed=True, allow=allowlist(extra), sink=sink, agent=agent)
        sys.addaudithook(_hook)
    return _S


def flags():
    return list(_S["flags"])
