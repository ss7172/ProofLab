"""CID families, session ids, handoff ids, W3C baggage + traceparent (ARCH §3.2, §4.2, §7.2)."""
import pytest

from prooflab.contract import ids as I

CID = "ifabric-run-1791260000-ab12cd"


def test_mint_and_parse():
    assert I.mint_cid("ifabric-run", 1791260000, "ab12cd") == CID
    assert I.parse_cid(CID) == {"family": "ifabric-run", "epoch": 1791260000, "hex": "ab12cd"}
    minted = I.mint_cid("ifabric-adv", 1791260000)
    assert I.cid_family(minted) == "ifabric-adv" and len(minted.rsplit("-", 1)[1]) == 6
    with pytest.raises(ValueError):
        I.mint_cid("fault", 1)


@pytest.mark.parametrize("value,family", [
    (CID, "ifabric-run"), ("ifabric-test-1791260000-0f0f0f", "ifabric-test"),
    ("ifabric-assure-1791260000-0f0f0f", "ifabric-assure"),
    ("ifabric-unenveloped-1791260000-0f0f0f", "ifabric-unenveloped"),
    ("unattributed:ifabric_it-abc:2026-10-06T04:00:00Z", "unattributed"),
    ("fault-s2-1", "fault"), ("unresolved:" + "a" * 32, "unresolved"),
])
def test_families(value, family):
    assert I.cid_family(value) == family


@pytest.mark.parametrize("bad", ["", "run-1", "ifabric-run-12-ab", "ifabric-run-1791260000-XYZ", None])
def test_invalid(bad):
    assert not I.is_valid_run_id(bad)


def test_only_ours_are_ours():
    assert I.is_ours(CID) and not I.is_ours("fault-s2-1")


def test_session_id():
    sid = I.mint_session_id(CID, "0123456789abcdef0123456789abcdef")
    assert sid == CID + "-0123456789abcdef0123456789abcdef"
    assert I.session_cid(sid) == CID
    assert len(I.mint_session_id(CID)) >= 33  # AgentCore's minimum session id length
    with pytest.raises(ValueError):
        I.session_cid(CID)


def test_handoff_id():
    assert I.handoff_id(CID, 2) == CID + ":h2"
    assert I.parse_handoff_id(CID + ":h2") == (CID, 2)
    with pytest.raises(ValueError):
        I.handoff_id(CID, 0)


def test_baggage_roundtrip():
    assert I.cid_baggage(CID) == "modaas-correlation-id=" + CID
    assert I.cid_from_baggage("other=1;p=2, modaas-correlation-id=%s;prop" % CID) == CID
    assert I.cid_from_baggage("modaas-correlation-id=junk") is None
    items = {"a": "x y,z", "b": "1"}
    assert I.parse_baggage(I.format_baggage(items)) == items


def test_traceparent():
    tp = I.mint_traceparent("4bf92f3577b34da6a3ce929d0e0e4736", "00f067aa0ba902b7")
    assert tp == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert I.parse_traceparent(tp)["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    for bad in ("00-" + "0" * 32 + "-00f067aa0ba902b7-01", "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                "00-xyz-00f067aa0ba902b7-01"):
        with pytest.raises(ValueError):
            I.parse_traceparent(bad)
    headers = I.propagation_headers(CID, tp)
    assert headers == {"baggage": "modaas-correlation-id=" + CID, "traceparent": tp}
