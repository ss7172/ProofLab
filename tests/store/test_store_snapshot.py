import filecmp
import json
import os
import re
import shutil

from fake_ledger import TEST_CREDENTIAL, FakeLedger
from prooflab.store import snapshot

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _stage(tmp_path):
    root = tmp_path / "snap"
    (root / "raw" / "gateway").mkdir(parents=True)
    (root / "raw" / "aws-invocations").mkdir(parents=True)
    (root / "raw" / "ledger").mkdir(parents=True)
    shutil.copy(os.path.join(FIX, "gateway-fixture.log"), str(root / "raw" / "gateway"))
    shutil.copy(os.path.join(FIX, "invocations-fixture.jsonl"), str(root / "raw" / "aws-invocations"))
    shutil.copy(os.path.join(FIX, "ledger-fixture.jsonl"), str(root / "raw" / "ledger"))
    return str(root)


def _rows(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def test_refresh_twice_gives_identical_derived_dir(tmp_path):
    root = _stage(tmp_path)
    argv = ["--snapshot", root, "--as-of", "2026-10-06T05:00:00Z", "--run-ids", os.path.join(FIX, "run-ids.txt")]
    assert snapshot.main(argv) == 0
    first = tmp_path / "first"
    shutil.copytree(os.path.join(root, "derived"), str(first))
    shutil.copy(os.path.join(root, "SNAPSHOT.json"), str(tmp_path / "snap1.json"))
    assert snapshot.main(argv) == 0
    cmp = filecmp.dircmp(str(first), os.path.join(root, "derived"))
    assert not cmp.diff_files and not cmp.left_only and not cmp.right_only and cmp.common_files
    assert filecmp.cmp(str(tmp_path / "snap1.json"), os.path.join(root, "SNAPSHOT.json"), shallow=False)


def test_every_gateway_run_id_appears_once_in_catalogue_all_labelled_only_listed_assessed(tmp_path):
    root = _stage(tmp_path)
    assert snapshot.main(["--snapshot", root, "--run-ids", os.path.join(FIX, "run-ids.txt")]) == 0
    spans = set(re.findall(r'modaas\.run_id="([^"]+)"', open(os.path.join(FIX, "gateway-fixture.log")).read()))
    cat = _rows(os.path.join(root, "derived", "run-catalogue.jsonl"))
    seen = [r["run_id"] for r in cat]
    assert len(seen) == len(set(seen))
    assert spans <= set(seen)
    assert all(r["label"] for r in cat)
    assert [r["run_id"] for r in cat if r["assessed"]] == ["ifabric-run-1791300000-a1b2c3"]
    labels = dict((r["run_id"], r["label"]) for r in cat)
    assert labels["ifabric-test-ledger-smoke-1791252169"] == "test"
    assert labels["fault-1791300003-005ccd"] == "EXPLORATORY"
    assert any(l == "hackathon-helper" for l in labels.values()) and any(l == "my-agent" for l in labels.values())
    assert any(i.startswith("unattributed:") and l == "UNATTRIBUTED" for i, l in labels.items())
    assert not any(i.startswith("unresolved:") for i in seen)


def test_store_export_dedups_ledger_and_normalized_and_keeps_smoke_row(tmp_path):
    root = _stage(tmp_path)
    assert snapshot.main(["--snapshot", root]) == 0
    rows = _rows(os.path.join(root, "store", "records.jsonl"))
    assert any(r.get("correlation_id") == "ifabric-test-ledger-smoke-1791252169" for r in rows)
    ids = [r.get("record_id") for r in rows if r.get("record_id")]
    assert len(ids) == len(set(ids))
    rej = _rows(os.path.join(root, "derived", "rejects.jsonl"))
    assert rej == []


def test_live_steps_pull_per_cid_and_ingest_with_fake_ledger(tmp_path, monkeypatch):
    root = _stage(tmp_path)
    os.remove(os.path.join(root, "raw", "ledger", "ledger-fixture.jsonl"))
    with open(os.path.join(FIX, "ledger-fixture.jsonl")) as fh:
        seeded = [json.loads(l) for l in fh if l.strip()]
    monkeypatch.setenv("PL_TEST_TOKEN_VAR", TEST_CREDENTIAL)
    with FakeLedger(seeded) as led:
        argv = ["--snapshot", root, "--ledger-url", led.url, "--token-env", "PL_TEST_TOKEN_VAR",
                "--pull-ledger", "--ingest"]
        assert snapshot.main(argv) == 0
        gets = [p for m, p in led.log if m == "GET"]
        assert gets and all("cid=" in p for p in gets)           # per-CID only, never a full GET
        n = len(led.rows)
        assert n > len(seeded)
        assert not any(r["correlation_id"].startswith("fault-") and r.get("schema") for r in led.rows)
        assert snapshot.main(argv) == 0                          # re-ingest adds nothing
        assert len(led.rows) == n
    assert os.listdir(os.path.join(root, "raw", "ledger"))


def test_ingest_into_fallback_store(tmp_path):
    root = _stage(tmp_path)
    fb = str(tmp_path / "ifabric-store" / "records.jsonl")
    argv = ["--snapshot", root, "--ingest", "--fallback-store", fb]
    assert snapshot.main(argv) == 0
    n = len(open(fb).read().splitlines())
    assert n > 0
    assert snapshot.main(argv) == 0
    assert len(open(fb).read().splitlines()) == n


def test_token_never_on_argv_or_in_outputs(tmp_path, monkeypatch, capsys):
    root = _stage(tmp_path)
    monkeypatch.setenv("PL_TEST_TOKEN_VAR", TEST_CREDENTIAL)
    with FakeLedger([]) as led:
        snapshot.main(["--snapshot", root, "--ledger-url", led.url, "--token-env", "PL_TEST_TOKEN_VAR", "--pull-ledger"])
    assert TEST_CREDENTIAL not in capsys.readouterr().out
    for dp, _, fs in os.walk(root):
        for f in fs:
            assert TEST_CREDENTIAL not in open(os.path.join(dp, f), errors="replace").read()
