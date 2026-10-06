import json
import os

import pytest

from fake_ledger import TEST_CREDENTIAL, FakeLedger
from prooflab.contract import record as R
from prooflab.store import ingest, observations
from prooflab.store.ledger_client import LedgerClient, LedgerError

HERE = os.path.dirname(__file__)
FIX = os.path.join(HERE, "fixtures")


def _norm():
    with open(os.path.join(FIX, "gateway-fixture.log")) as fh:
        return observations.normalize_gateway_text(fh.read(), "raw/gateway/gateway-fixture.log")


def test_client_posts_and_gets_per_cid_and_never_leaks_token():
    with FakeLedger() as led:
        c = LedgerClient(led.url, TEST_CREDENTIAL)
        assert TEST_CREDENTIAL not in repr(c)
        assert c.post({"correlation_id": "x-1", "phase": "p"}) == 201
        assert c.post({"correlation_id": "x-2", "phase": "p"}) == 201
        assert [r["correlation_id"] for r in c.get_by_cid("x-1")] == ["x-1"]
        assert ("GET", "/records?cid=x-1") in led.log
        with pytest.raises(LedgerError):
            c.get_all()                                  # a full read needs between_runs=True
        assert len(c.get_all(between_runs=True)) == 2


def test_client_error_message_has_no_token():
    with FakeLedger() as led:
        bad = LedgerClient(led.url, "wrong-" + "value")
        with pytest.raises(LedgerError) as ei:
            bad.get_by_cid("x")
        assert "401" in str(ei.value) and "wrong-" not in str(ei.value)


def test_from_env_reads_named_variable(monkeypatch):
    monkeypatch.delenv("PL_TEST_LEDGER_ENV", raising=False)
    with pytest.raises(LedgerError):
        LedgerClient.from_env("http://127.0.0.1:1", "PL_TEST_LEDGER_ENV")
    monkeypatch.setenv("PL_TEST_LEDGER_ENV", TEST_CREDENTIAL)
    assert LedgerClient.from_env("http://127.0.0.1:1", "PL_TEST_LEDGER_ENV")


def test_reingest_deduplicates_against_fake_ledger():
    recs = _norm()["records"]
    assert recs
    with FakeLedger() as led:
        store = ingest.LedgerStore(LedgerClient(led.url, TEST_CREDENTIAL))
        # the ledger rows carry correlation_id; our records do too (new_record sets it)
        first = ingest.ingest(recs, store)
        assert first["appended"] == len(recs) and first["skipped"] == 0 and not first["rejected"]
        n = len(led.rows)
        second = ingest.ingest(recs, store)
        assert second["appended"] == 0 and second["skipped"] == len(recs)
        assert len(led.rows) == n                        # nothing was added by the re-pull
        posts = [e for e in led.log if e[0] == "POST"]
        assert len(posts) == n


def test_ingest_rejects_non_ifabric_and_invalid_records_without_crashing():
    smoke = {"correlation_id": "ifabric-test-ledger-smoke-1791252169", "phase": "smoke", "ts": "2026-10-06T01:20:00Z"}
    bad = R.new_record("observation", "x", **{"run.id": "not a cid"})
    with FakeLedger() as led:
        store = ingest.LedgerStore(LedgerClient(led.url, TEST_CREDENTIAL))
        out = ingest.ingest([smoke, bad, None], store)
        assert out["appended"] == 0 and len(out["rejected"]) == 3 and not led.rows


def test_ingest_scope_limits_what_is_written():
    recs = _norm()["records"]
    with FakeLedger() as led:
        store = ingest.LedgerStore(LedgerClient(led.url, TEST_CREDENTIAL))
        out = ingest.ingest(recs, store, scope=lambda cid: cid.startswith("ifabric-"))
        assert out["out_of_scope"] > 0
        assert led.rows and all(r["correlation_id"].startswith("ifabric-") for r in led.rows)


def test_ingest_stops_after_consecutive_failures():
    recs = _norm()["records"]

    class Broken:
        def known_ids(self, cid):
            return set()

        def append(self, rec):
            raise OSError("down")

    out = ingest.ingest(recs, Broken())
    assert out["appended"] == 0 and len(out["failed"]) == ingest.MAX_CONSECUTIVE_FAILURES


def test_file_store_fallback_appends_dedups_and_copies_ledger_verbatim(tmp_path):
    path = str(tmp_path / "ifabric-store" / "records.jsonl")
    fs = ingest.FileStore(path)
    recs = _norm()["records"]
    a = ingest.ingest(recs, fs)
    b = ingest.ingest(recs, fs)
    assert a["appended"] == len(recs) and b["appended"] == 0
    assert len(open(path).read().splitlines()) == len(recs)
    with open(os.path.join(FIX, "ledger-fixture.jsonl")) as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    with FakeLedger(rows) as led:
        client = LedgerClient(led.url, TEST_CREDENTIAL)
        cids = ["ifabric-test-ledger-smoke-1791252169", "fault-1791300003-005ccd"]
        one = ingest.copy_ledger_into_file_store(client, fs, cids)
        two = ingest.copy_ledger_into_file_store(client, fs, cids)
        assert one["appended"] == 4 and two["appended"] == 0 and two["skipped"] == 4


def test_no_update_or_delete_path_in_store_code():
    root = os.path.join(HERE, "..", "..", "prooflab", "store")
    import re
    pat = re.compile(r'def (update|delete)|"(PUT|DELETE|PATCH)"')
    for name in os.listdir(root):
        if name.endswith(".py"):
            assert not pat.search(open(os.path.join(root, name)).read()), name
