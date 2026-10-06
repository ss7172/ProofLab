"""B-G5 offline part: RT-03's audit hook. No network: events are raised with sys.audit, never by real DNS."""
import os, socket, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _railpath  # noqa: F401,E402
from adapters.runtime import egress  # noqa: E402

SINK = []
os.environ.setdefault("AUDIT_URL", "http://audit-store.components.svc:8080/records")
STATE = egress.install(agent="ifabric-it", sink=SINK.append, extra=("localhost",))


def test_install_once_and_allowlist_from_env():
    assert egress.install(agent="other", sink=None) is STATE and STATE["agent"] == "ifabric-it"
    assert "localhost" in STATE["allow"]
    assert egress.urlsplit(os.environ["AUDIT_URL"]).hostname.lower() in STATE["allow"]


def test_one_flag_per_unlisted_host_dedup():
    n = len(SINK)
    sys.audit("socket.getaddrinfo", "example.invalid", 80, 0, 0, 0)   # an injected urlopen's first event
    sys.audit("socket.connect", None, ("192.0.2.7", 80))
    sys.audit("socket.getaddrinfo", "example.invalid", 443, 0, 0, 0)
    new = SINK[n:]
    hosts = [r["rail.values"][0] for r in new]
    assert hosts.count("example.invalid") == 1
    r = [x for x in new if x["rail.values"] == ["example.invalid"]][0]
    assert r["verdict"] == "FLAG" and r["inline.action"] == "proceed" and r["ep.id"] == "EP-15" and r["rail.id"] == "RT-03"


def test_allowed_host_and_its_connect_are_not_flagged():
    n = len(SINK)
    socket.getaddrinfo("localhost", 80)   # local resolution only (hosts file)
    sys.audit("socket.connect", None, ("127.0.0.1", 80))
    assert SINK[n:] == []


def test_raw_ip_connect_without_allowed_resolution_is_flagged():
    n = len(SINK)
    sys.audit("socket.getaddrinfo", "203.0.113.9", 80, 0, 0, 0)   # not allowed: last_ok False
    sys.audit("socket.connect", None, ("198.51.100.4", 443))
    hosts = [r["rail.values"][0] for r in SINK[n:]]
    assert "198.51.100.4" in hosts and "203.0.113.9" in hosts


def test_hook_never_raises_on_odd_args():
    sys.audit("socket.connect", None, "/tmp/unix.sock")
    sys.audit("socket.getaddrinfo", None, 80, 0, 0, 0)
    sys.audit("socket.connect")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
