"""PR-53: 'show me control 16 for run <RUN> between <T1> and <T2>' over an N1-shaped pack (stdlib, offline)."""
import contextlib
import io
import json
import os
import threading

import pytest

from prooflab.query import answer as A
from prooflab.query import cli
from prooflab.query import engine as E
from prooflab.query import grammar as G
from prooflab.query import run_window as RW

CID = "ifabric-run-1791300000-aa11bb"
DAY = "2026-10-06T"
# four served calls of 1,100 tokens each (one gateway span duplicated), an EP-1 decision before each, then a DENY
CALLS = [("c1", "10:00:10.500000Z"), ("c2", "10:00:20.500000Z"), ("c3", "10:00:30.500000Z"), ("c4", "10:00:40.500000Z")]


def _rec(rid, kind, at, **kw):
    r = {"record_id": rid, "record_kind": kind, "run.id": CID, "correlation_id": CID, "ts": DAY + at,
         "schema": "ifabric.evidence/1", "provenance": "LIVE_SUBJECT"}
    r.update(kw)
    return r


def _records():
    out = [_rec("life-start", "lifecycle", "10:00:00.000Z", authorship="TESTIMONY", phase="run.started",
                **{"emitted.at": DAY + "10:00:00.000Z"})]
    committed = 0
    for i, (cid, at) in enumerate(CALLS):
        dt = "10:00:%02d.000Z" % (9 + 10 * i)
        out.append(_rec("ep1-%s" % cid, "decision", dt, authorship="TESTIMONY", verdict="ALLOW", **{
            "ep.id": "EP-1", "control.ref": "C16", "call.id": cid, "emitted.at": DAY + dt, "inline.action": "proceed",
            "inline.mode": "enforce", "inline.bound_basis": "projected", "inline.limit_value": 5000,
            "measured.value": committed + 1200, "actor.id": "ifabric-it",
            "detail": "C16 inline ALLOW [committed=%d reserved=0 bound=1200 max_retries=0]" % committed}))
        span = _rec("obs-%s" % cid, "metric", at, authorship="PLATFORM", verdict="RECORDED", **{
            "observed.clock": "gateway", "observed.at": DAY + at, "call.id": cid, "tokens.in": 1000, "tokens.out": 100,
            "outcome.http_status": 200, "model.id": "m",
            "source.refs": ["raw:raw/aws-spans/%s/spans.jsonl" % CID, "line:%d" % (i + 1), "sha256:" + "0" * 64]})
        out.append(span)
        if cid == "c2":                       # the same span ingested twice: counted once (dedup by action id)
            out.append(dict(span, record_id="obs-c2-dup"))
        out.append(_rec("act-%s" % cid, "action", at, authorship="TESTIMONY", **{
            "ep.id": "EP-1", "call.id": cid, "emitted.at": DAY + at, "tokens.in": 1000, "tokens.out": 100}))
        committed += 1100
    out.append(_rec("ep1-deny", "decision", "10:00:45.000Z", authorship="TESTIMONY", verdict="DENY", **{
        "ep.id": "EP-1", "control.ref": "C16", "call.id": None, "emitted.at": DAY + "10:00:45.000Z", "inline.action": "halt",
        "inline.mode": "enforce", "inline.bound_basis": "projected", "inline.limit_value": 5000, "measured.value": 5600,
        "actor.id": "ifabric-it", "detail": "C16 inline DENY [committed=4400 reserved=0 bound=1200 max_retries=0]"}))
    out.append(_rec("life-end", "lifecycle", "10:00:50.000Z", authorship="TESTIMONY", phase="run.finished",
                    **{"emitted.at": DAY + "10:00:50.000Z"}))
    out.append(_rec("ep2-c1", "decision", "12:00:00Z", authorship="ASSURANCE", verdict="ALLOW", **{
        "ep.id": "EP-2", "control.ref": "C16", "call.id": "c1", "emitted.at": DAY + "12:00:00Z"}))
    return out


@pytest.fixture()
def pack_dir(tmp_path):
    root = tmp_path / "pack"
    (root / "store").mkdir(parents=True)
    (root / "assessments" / "C16").mkdir(parents=True)
    (root / "store" / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in _records()))
    (root / "assessments" / "C16" / ("%s.json" % CID)).write_text(json.dumps({
        "assessment_id": "C16:C16-v1:run:%s:r1" % CID, "control_ref": "C16", "threshold_version": "C16-v1",
        "scope_kind": "run", "scope_id": CID, "scope_start": DAY + "10:00:10.500Z", "scope_end": DAY + "10:00:40.500Z",
        "requirement_verdict": "SATISFIED", "measured": {"total_tokens": 4400, "cap": 5000}}))
    (root / "pack-index.json").write_text(json.dumps({"answers": [], "runs": []}))
    return str(root)


@pytest.fixture()
def pack(pack_dir):
    return E.Pack(pack_dir)


def _w(t1, t2):
    return DAY + t1, DAY + t2


def test_window_inside_the_run(pack):
    a = RW.compose(pack, "C16", CID, *_w("10:00:15Z", "10:00:35Z"))
    s = a["slice"]
    assert a["verdict"] == "SATISFIED" and a["verdict_scope"] == "run" and "WHOLE run" in a["verdict_note"]
    assert a["overlap"] == "inside-run"
    assert [c["action_id"] for c in s["calls"]] == ["c2", "c3"] and s["tokens"] == 2200
    assert s["committed_at_t1"] == 1100 and s["committed_at_t2"] == 3300 and s["headroom_at_t2"] == 1700
    assert [d["record_id"] for d in s["decisions"]] == ["ep1-c2", "ep1-c3"]
    c2 = s["calls"][0]
    assert c2["span_record_ids"] == ["obs-c2", "obs-c2-dup"] and c2["adapter_record_ids"] == ["act-c2"]
    assert c2["raw_ref"].startswith("raw:raw/aws-spans/")
    text = "\n".join(RW.render(a))
    assert "by 2026-10-06T10:00:35Z the run had committed 3,300 of 5,000" in text


def test_window_covering_the_whole_run_equals_the_run_total(pack):
    a = RW.compose(pack, "C16", CID, *_w("09:00:00Z", "11:00:00Z"))
    assert a["overlap"] == "covers-run"
    assert a["slice"]["tokens"] == a["run_total_from_calls"] == 4400 and a["slice"]["call_count"] == a["run_calls"] == 4
    assert a["slice"]["committed_at_t2"] == 4400 and not a["gaps"]
    assert a["ep2_replay_decisions"] == 1 and all(d["record_id"] != "ep2-c1" for d in a["slice"]["decisions"])


@pytest.mark.parametrize("t1,t2", [("09:00:00Z", "09:30:00Z"), ("10:01:00Z", "10:30:00Z")])
def test_window_before_or_after_the_run(pack, t1, t2):
    a = RW.compose(pack, "C16", CID, *_w(t1, t2))
    assert a["overlap"] == "none" and a["slice"]["call_count"] == 0 and a["verdict"] == "SATISFIED"
    assert "does not overlap run %s (run 2026-10-06T10:00:00.000Z .. 2026-10-06T10:00:50.000Z)" % CID in a["message"]


def test_deny_inside_the_window(pack):
    a = RW.compose(pack, "C16", CID, *_w("10:00:41Z", "10:00:50Z"))
    d = a["slice"]["decisions"]
    assert a["slice"]["deny"] == 1 and d[0]["verdict"] == "DENY" and d[0]["action"] == "halt"
    assert (d[0]["committed"], d[0]["bound"], d[0]["projected"], d[0]["cap"]) == (4400, 1200, 5600, 5000)
    assert "DENY halt" in "\n".join(RW.render(a)) and "halted before a call" in "\n".join(RW.render(a))


def test_c7_c9_say_run_window_is_c16_only(pack):
    a = RW.compose(pack, "C7", CID, *_w("10:00:15Z", "10:00:35Z"))
    assert a["kind"] == "error" and a["message"] == RW.NOT_DEFINED


@pytest.mark.parametrize("text", [
    "show me control 16 for run %s between 2026-10-06T10:00:15Z and 2026-10-06T10:00:35Z" % CID,
    "Show me control 16 for run %s between 10:00:15Z and 10:00:35Z?" % CID,
    "control 16 for run %s from 2026-10-06T10:00:15Z to 2026-10-06T10:00:35Z" % CID,
    "controltest 16 --run %s --window 2026-10-06T10:00:15Z..2026-10-06T10:00:35Z" % CID,
])
def test_grammar_phrases(pack, text):
    p = G.parse(text, pack)
    assert p["ok"] and p["kind"] == "controltest-run-window" and p["run"] == CID and p["control"] == "C16"
    assert (p["t1"], p["t2"]) == _w("10:00:15Z", "10:00:35Z")
    assert p["normalized"] == "controltest 16 --run %s --window %s..%s" % ((CID,) + _w("10:00:15Z", "10:00:35Z"))


def test_hhmmz_resolves_like_resolve_times(pack, pack_dir):
    p = G.parse("show me control 16 for run %s between 10:00Z and 10:01Z" % CID, pack)
    assert (p["t1"], p["t2"]) == _w("10:00:00Z", "10:01:00Z")
    with open(os.path.join(pack_dir, "window.json"), "w") as f:      # a declared window wins over the run anchor
        json.dump({"start": DAY + "09:00:00Z", "end": DAY + "12:00:00Z"}, f)
    p2 = G.parse("show me control 16 for run %s between 10:00Z and 10:01Z" % CID, E.Pack(pack_dir))
    assert (p2["t1"], p2["t2"]) == G.resolve_times(E.Pack(pack_dir), "10:00Z", "10:01Z")[:2]
    assert G.parse("control 16 for run FM-X between 10:00Z and 10:01Z", pack)["ok"] is False   # no run, no anchor


def test_ask_route(pack):
    res = A.ask(pack, "show me control 16 for run %s between 10:00:15Z and 10:00:35Z" % CID)
    assert res["kind"] == RW.KIND and res["doc"]["slice"]["tokens"] == 2200
    assert res["doc"]["text"][0].startswith("CONTROL C16  RUN %s" % CID)


def _cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(argv)
    return code, buf.getvalue()


def test_cli_run_and_window_together(pack_dir):
    code, out = _cli(["--pack", pack_dir, "--control", "C16", "--run", CID, "--window", "10:00:15Z..10:00:35Z"])
    assert code == 0 and "RUN VERDICT (whole run, stored): SATISFIED" in out and "2 model call(s), 2,200 tokens" in out
    code, out = _cli(["--pack", pack_dir, "--control", "C16", "--run", CID, "--window",
                      "%s..%s" % _w("09:00:00Z", "11:00:00Z"), "--json"])
    doc = json.loads(out)
    assert doc["slice"]["tokens"] == 4400 and doc["slice"]["call_count"] == 4


def test_window_only_lists_a_run_the_window_cuts_through(pack_dir):
    code, out = _cli(["--pack", pack_dir, "--control", "C16", "--window", "%s..%s" % _w("10:00:15Z", "10:00:35Z")])
    assert code == 2 and "no run in scope" in out
    assert "listed, not counted: %s (overlaps the window but is not wholly inside it" % CID in out
    assert "its run verdict is SATISFIED; ask for run+window" in out


def test_console_ask_route(pack_dir):
    from prooflab.console import server as srv, sources as S
    import http.client
    server = srv.make_server("127.0.0.1", 0, S.PackSource(pack_dir))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        def req(method, path, body=None, cookie=None):
            c = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
            h = {"Host": "127.0.0.1:%d" % server.port, "Content-Type": "application/json"}
            if cookie:
                h["Cookie"] = cookie
            c.request(method, path, body=json.dumps(body) if body else None, headers=h)
            r = c.getresponse()
            out = (r.status, dict((k.lower(), v) for k, v in r.getheaders()), r.read())
            c.close()
            return out
        st, hd, _ = req("POST", "/api/v1/session", {"token": server.token})
        assert st == 200
        cookie = hd["set-cookie"].split(";")[0]
        from urllib.parse import quote
        q = "show me control 16 for run %s between 10:00:15Z and 10:00:35Z" % CID
        st, _, raw = req("GET", "/api/v1/ask?q=" + quote(q), cookie=cookie)
        j = json.loads(raw)
        assert st == 200, raw
        assert j["data"]["kind"] == RW.KIND and j["data"]["slice"]["committed_at_t2"] == 3300
        assert j["meta"]["normalized"].startswith("controltest 16 --run %s --window" % CID) and j["meta"]["render"] == "text"
        assert any("RUN VERDICT" in line for line in j["data"]["text"])
    finally:
        server.shutdown()
        server.server_close()
