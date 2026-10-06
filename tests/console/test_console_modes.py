"""The data switch (T5.4 (a)), EPs from data (b), the panel embed (c), the catalogue (f), byte-identity and the no-verdict-JS rule."""
import filecmp
import json
import os
import re
import subprocess

import pytest

from prooflab.console import server as srv
from prooflab.console import sources as S
from prooflab.console.sources import ConsoleRefusal

import conftest as C

HANDOFF = os.path.join(C.ROOT, "handoffs", "ifabric-handoff-3")


def test_fixtures_banner_is_synthetic_amber(fixtures_client):
    m = fixtures_client.json("/api/v1/pack")[1]["meta"]["mode"]
    assert m["tone"] == "warn" and "SYNTHETIC" in m["banner"] and m["chip"].startswith("FIXTURES")


def test_pack_banner_by_source(pack_client):
    m = pack_client.json("/api/v1/pack")[1]["meta"]["mode"]
    assert m["tone"] == "real" and "MANIFEST VERIFIED" in m["banner"] and m["chip"].startswith("PACK")
    assert m["integrity_ok"] is True


def test_live_banner_by_source(pack):
    server = C.start(S.PackSource(pack, live=True))
    try:
        m = C.Client(server).login().json("/api/v1/pack")[1]["meta"]["mode"]
        assert m["chip"].startswith("LIVE") and "live index" in m["banner"]
    finally:
        server.shutdown(); server.server_close()


def test_pack_refuses_synthetic_pack_index():
    with pytest.raises(ConsoleRefusal) as ei:
        S.PackSource(C.PLAN.replace("evidence-console-plan", "evidence-console-plan/examples"))   # examples/ has pack-index.json
    assert "SYNTHETIC" in str(ei.value)


def test_pack_refuses_synthetic_document_even_if_index_is_clean(pack):
    path = os.path.join(pack, "answers", "C16_run_FM-B.json")
    doc = json.load(open(path))
    doc["provenance"] = "SYNTHETIC"
    json.dump(doc, open(path, "w"))
    C.write_manifest(pack)
    with pytest.raises(ConsoleRefusal):
        S.PackSource(pack)


def test_pack_refuses_synthetic_record(pack):
    path = os.path.join(pack, "records", "C16", "FM-A.jsonl")
    lines = open(path).read().split("\n")
    rec = json.loads(lines[0]); rec["provenance"] = "SYNTHETIC"
    lines[0] = json.dumps(rec)
    open(path, "w").write("\n".join(lines))
    with pytest.raises(ConsoleRefusal):
        S.PackSource(pack)


def test_pack_refuses_the_panels_fake_sample(pack):
    sample = json.load(open(os.path.join(HANDOFF, "code", "prooflab", "servicenow", "examples", "cases.sample-fake-data.json")))
    import hashlib
    idx_path = os.path.join(pack, "pack-index.json")
    idx = json.load(open(idx_path))
    rel = "servicenow/cases/sample.json"
    os.makedirs(os.path.join(pack, "servicenow", "cases"), exist_ok=True)
    blob = json.dumps(sample[0]).encode()
    open(os.path.join(pack, rel), "wb").write(blob)
    idx["cases"] = [{"finding_id": sample[0]["finding_id"], "incident": "INC0001000", "path": rel, "sha256": hashlib.sha256(blob).hexdigest()}]
    json.dump(idx, open(idx_path, "w"))
    C.write_manifest(pack)
    with pytest.raises(ConsoleRefusal) as ei:
        S.PackSource(pack)
    assert "fake sample" in str(ei.value)


def test_fake_digests_match_arths_sample():
    sample = json.load(open(os.path.join(HANDOFF, "code", "prooflab", "servicenow", "examples", "cases.sample-fake-data.json")))
    assert {S.case_digest(c) for c in sample} == set(S.FAKE_CASE_DIGESTS)


def test_main_pack_mode_refuses_synthetic_exit_2(tmp_path, capsys):
    ex = os.path.join(C.PLAN, "examples")
    clean = {k: v for k, v in os.environ.items() if not (k in srv.SECRET_ENV or k.startswith(srv.SECRET_ENV_PREFIXES))}
    old = dict(os.environ)
    os.environ.clear(); os.environ.update(clean)
    try:
        assert srv.main(["--data", "pack", "--pack", ex, "--port", "0"]) == 2
    finally:
        os.environ.clear(); os.environ.update(old)
    assert "SYNTHETIC" in capsys.readouterr().err


def test_eps_come_from_pack_index_not_the_page(pack_client):
    eps = pack_client.json("/api/v1/pack")[1]["data"]["enforcement_points"]
    assert [e["id"] for e in eps][:2] == ["EP1", "EP2"] and all("status" in e for e in eps)
    text = open(os.path.join(srv.STATIC_DIR, "app.js"), encoding="utf-8").read() + open(os.path.join(srv.STATIC_DIR, "index.html")).read()
    assert not re.search(r"\bEP\s?\d", text), "no hard-coded EP label in the page"
    assert "P.enforcement_points" in text


def test_ep_status_is_rendered_as_recorded(pack):
    p = os.path.join(pack, "pack-index.json")
    idx = json.load(open(p))
    idx["enforcement_points"][0]["status"] = "NOT_BUILT"
    json.dump(idx, open(p, "w")); C.write_manifest(pack)
    server = C.start(S.PackSource(pack))
    try:
        eps = C.Client(server).login().json("/api/v1/pack")[1]["data"]["enforcement_points"]
        assert eps[0]["status"] == "NOT_BUILT"      # never upgraded
    finally:
        server.shutdown(); server.server_close()


def test_panel_js_and_css_byte_identical_to_arths():
    base = os.path.join(HANDOFF, "code", "prooflab", "servicenow", "panel")
    for name in ("ifabric-case-panel.js", "ifabric-case-panel.css"):
        assert filecmp.cmp(os.path.join(base, name), os.path.join(srv.PANEL_DIR, name), shallow=False), name
        out = subprocess.run(["cmp", os.path.join(base, name), os.path.join(srv.PANEL_DIR, name)])
        assert out.returncode == 0


def test_no_verdict_logic_in_js():
    out = subprocess.run(["grep", "-rnE", "SATISFIED|BREACHED", srv.STATIC_DIR], stdout=subprocess.PIPE)
    assert out.returncode == 1 and out.stdout == b""     # grep: no match


def test_panel_embed_uses_render_with_enveloped_data_never_poll():
    js = open(os.path.join(srv.STATIC_DIR, "app.js"), encoding="utf-8").read()
    assert "IFabricCasePanel.render(box, shown)" in js
    assert ".poll(" not in js
    assert 'api("/api/v1/cases")' in js and "10000" in js          # re-fetched every 10 s


def test_cases_only_listed_snapshots_sha_checked_unknown_keys_pass_through(pack):
    idx = json.load(open(os.path.join(pack, "pack-index.json")))
    listed = {e["finding_id"] for e in idx["cases"]}
    # an unlisted snapshot in the folder is never served
    open(os.path.join(pack, "servicenow", "cases", "stray.json"), "w").write(json.dumps({"finding_id": "stray", "extra_key": 1}))
    # a listed one gains an unknown key (and its sha in pack-index) -> passes through unchanged
    first = os.path.join(pack, idx["cases"][0]["path"])
    doc = json.load(open(first)); doc["future_key"] = {"a": [1]}
    blob = json.dumps(doc).encode(); open(first, "wb").write(blob)
    import hashlib
    idx["cases"][0]["sha256"] = hashlib.sha256(blob).hexdigest()
    json.dump(idx, open(os.path.join(pack, "pack-index.json"), "w")); C.write_manifest(pack)
    server = C.start(S.PackSource(pack))
    try:
        c = C.Client(server).login()
        j = c.json("/api/v1/cases")[1]
        assert {x["finding_id"] for x in j["data"]} == listed
        assert any(x.get("future_key") == {"a": [1]} for x in j["data"])
    finally:
        server.shutdown(); server.server_close()


def test_cases_refuse_a_snapshot_whose_sha_changed(pack):
    idx = json.load(open(os.path.join(pack, "pack-index.json")))
    second = os.path.join(pack, idx["cases"][1]["path"])
    doc = json.load(open(second)); doc["finding"]["summary"] = "edited after listing"
    open(second, "w").write(json.dumps(doc))
    C.write_manifest(pack)                         # manifest agrees, pack-index sha does not
    server = C.start(S.PackSource(pack))
    try:
        j = C.Client(server).login().json("/api/v1/cases")[1]
        assert len(j["data"]) == 1
        assert j["meta"]["refused"][0]["reason"] == "sha256 changed"
    finally:
        server.shutdown(); server.server_close()


def test_run_catalogue_lists_runs_with_provenance(pack_client, fixtures_client):
    rows = pack_client.json("/api/v1/runs")[1]["data"]
    assert {r["alias"] for r in rows} == {"FM-A", "FM-B"}
    assert all("provenance" in r and "source" in r for r in rows)
    assert len(fixtures_client.json("/api/v1/runs")[1]["data"]) == 5


def test_run_catalogue_prefers_derived_catalogue_and_labels_unknowns(pack):
    os.makedirs(os.path.join(pack, "derived"), exist_ok=True)
    rows = [{"cid": "fault-1-aaaaaa", "provenance": "EXPLORATORY", "source": "gateway", "assessed": False, "label": "reference"},
            {"cid": "fault-2-bbbbbb", "provenance": "ASSESSED", "source": "orchestrator", "assessed": True}]
    open(os.path.join(pack, "derived", "run-catalogue.jsonl"), "w").write("\n".join(json.dumps(r) for r in rows) + "\n")
    C.write_manifest(pack)
    server = C.start(S.PackSource(pack))
    try:
        got = C.Client(server).login().json("/api/v1/runs")[1]["data"]
        assert [r["cid"] for r in got][:2] == ["fault-1-aaaaaa", "fault-2-bbbbbb"]     # catalogue rows first
        assert all(r["source"].startswith("pack-index") for r in got[2:])      # PR-56: then every other pack-index run, none hidden
        assert got[0]["in_window"] is None and got[0]["assessed"] is False     # unknown stays unknown, not green
    finally:
        server.shutdown(); server.server_close()


def test_runs_and_records_endpoints(pack_client):
    c = pack_client
    r = c.json("/api/v1/runs/FM-B")[1]["data"]
    assert r["run_alias"] == "FM-B" and c.json("/api/v1/runs/" + r["cid"])[0] == 200
    assert c.get("/api/v1/runs/FM-Z")[0] == 404
    j = c.json("/api/v1/records?run=FM-B&control=C16&verdict=SATISFIED")[1]
    assert j["data"] and all(x["verdict"] == "SATISFIED" and x["control.ref"] == "C16" for x in j["data"])
    assert j["meta"]["next_cursor"] == ""


def test_records_paging_cursor(pack):
    path = os.path.join(pack, "records", "C16", "FM-B.jsonl")
    rec = json.loads(open(path).readline())
    with open(path, "w") as h:
        for i in range(450):
            r = dict(rec); r["evidence_id"] = "ev:%d" % i
            h.write(json.dumps(r) + "\n")
    C.write_manifest(pack)
    server = C.start(S.PackSource(pack))
    try:
        c = C.Client(server).login()
        j1 = c.json("/api/v1/records?run=FM-B")[1]
        assert len(j1["data"]) == 200 and j1["meta"]["next_cursor"] == "200" and j1["meta"]["total"] == 450
        j3 = c.json("/api/v1/records?run=FM-B&cursor=400")[1]
        assert len(j3["data"]) == 50 and j3["meta"]["next_cursor"] == ""
    finally:
        server.shutdown(); server.server_close()


def test_integrity_cached_60s(pack):
    src = S.PackSource(pack)
    first = src.integrity()["verified_at"]
    open(os.path.join(pack, "extra.txt"), "w").write("x")
    assert src.integrity()["status"] == "VERIFIED"           # cached
    assert src.integrity(max_age=0)["status"] == "MODIFIED"  # re-verified on demand


def test_api_envelope_shape(fixtures_client):
    j = fixtures_client.json("/api/v1/integrity")[1]
    assert set(j) == {"ok", "data", "error", "meta"} and j["ok"] is True and j["error"] is None
    st, bad = fixtures_client.json("/api/v1/answer?key=nope")
    assert st == 404 and bad["ok"] is False and bad["error"]["code"] == "no-such-answer"


def test_vocab_supplied_by_server_not_js(fixtures_client):
    v = fixtures_client.json("/api/v1/pack")[1]["meta"]["vocab"]
    assert v["BREACHED"]["label"] == "NOT SATISFIED" and v["INDETERMINATE"]["tone"] == "unknown"


def test_dispatcher_verb_target_exists():
    assert srv.main.__module__ == "prooflab.console.server"


def test_node_syntax_of_app_js():
    node = subprocess.run(["which", "node"], stdout=subprocess.PIPE).stdout.strip()
    if not node:
        pytest.skip("node not installed")
    out = subprocess.run([node.decode(), "--check", os.path.join(srv.STATIC_DIR, "app.js")])
    assert out.returncode == 0


def test_panel_is_served_and_only_arths_files_live_outside_static(fixtures_client):
    for name in ("ifabric-case-panel.js", "ifabric-case-panel.css"):
        st, hd, body = fixtures_client.get("/static/panel/" + name, cookie=False)
        assert st == 200 and body == open(os.path.join(srv.PANEL_DIR, name), "rb").read()
    assert sorted(os.listdir(srv.PANEL_DIR)) == sorted(srv.PANEL_FILES)
    assert fixtures_client.get("/static/panel/other.js", cookie=False)[0] == 404
