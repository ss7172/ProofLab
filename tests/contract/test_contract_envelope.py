"""The run envelope ifabric.run/1 (ARCH §7.2): golden, round trip, refusals (PR-01 fix round 1)."""
import json

import pytest

from prooflab.contract import envelope as E
from prooflab.contract import ids

CID = "ifabric-run-1791260000-ab12cd"
SHA = "a" * 64

# The ARCH §7.2 printed example, with real-shaped values.
GOLDEN = {"ifabric": {"envelope": "ifabric.run/1", "run_id": CID, "handoff_id": CID + ":h2",
                      "from": "ifabric-customer", "to": "ifabric-it", "tier": "standard", "tally_tokens": 0,
                      "tally_calls": 0, "register_version": "v1", "register_sha256": SHA,
                      "provenance": "LIVE_SUBJECT", "condition": "none"}}


def test_constants():
    assert E.ENVELOPE_SCHEMA == "ifabric.run/1" and E.PAYLOAD_KEY == "ifabric"
    assert set(GOLDEN["ifabric"]) == set(E.ENVELOPE_KEYS)


def test_golden_reads_and_validates():
    env = E.read_envelope(GOLDEN)
    assert env == GOLDEN["ifabric"] and E.validate_envelope(env) == []


def test_build_round_trip():
    env = E.build_envelope(CID, ids.handoff_id(CID, 2), "ifabric-customer", "ifabric-it", "standard", 0, 0,
                           "v1", SHA, "LIVE_SUBJECT")
    assert env == GOLDEN["ifabric"]
    payload = E.wrap({"prompt": "hello"}, env)
    back = E.read_envelope(json.loads(json.dumps(payload)))
    assert back == env and payload["prompt"] == "hello"
    assert E.echo(back)["run_id"] == CID


def test_build_with_the_scripts_optional_keys():
    env = E.build_envelope(CID, CID + ":h1", "orchestrator", "ifabric-customer", None, 10, 1, "v1", SHA,
                           "PILOT", pin_sha256="b" * 64, mode="observe", condition_sha256="c" * 64,
                           scenario="S2", fault={"agent": "ifabric-it"})
    assert E.validate_envelope(env) == [] and env["tier"] is None
    with pytest.raises(ValueError):
        E.build_envelope(CID, CID + ":h1", "a", "b", "standard", 0, 0, "v1", SHA, "PILOT", cap=50000)


@pytest.mark.parametrize("payload", [None, "x", [], {}, {"ifabric": None}, {"ifabric": "x"},
                                     {"ifabric": {"envelope": "other/1"}}, {"envelope": {"run_id": CID}}])
def test_unenveloped_path_is_none(payload):
    assert E.read_envelope(payload) is None


@pytest.mark.parametrize("change", [
    {"run_id": "fault-xyz"}, {"handoff_id": "ifabric-run-1791260000-ffffff:h2"}, {"handoff_id": "h2"},
    {"tally_tokens": -1}, {"tally_calls": True}, {"tally_tokens": "0"}, {"register_sha256": "ABC"},
    {"provenance": "LIVE"}, {"envelope": "ifabric.run/2"}, {"to": ""}, {"mode": "audit"}, {"cap_tier_standard": 1},
])
def test_refusals(change):
    env = dict(GOLDEN["ifabric"], **change)
    assert E.validate_envelope(env) != []


def test_missing_key_and_never_raises():
    env = dict(GOLDEN["ifabric"])
    del env["tally_calls"]
    assert "tally_calls: required" in E.validate_envelope(env)
    assert E.validate_envelope(None) == ["envelope must be an object"]
