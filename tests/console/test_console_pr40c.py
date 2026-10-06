"""PR-40c: console round 3 (one boot request, serve-time auditor integrity, findings with delivery, one label for a
declared fault, C7 answers carry C7 evidence, 'headroom' sign)."""
import json
import os
import re
import shutil
from urllib.parse import quote

import pytest

from prooflab.console import sources as S
from prooflab.pack import build as B
from prooflab.pack import projector as PJ
from prooflab.query import answer as A
from prooflab.query import engine as E

import conftest as C

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "tests", "query", "fixtures", "pack")
C7_BREACH = "ifabric-run-1791261000-cd34ef"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("built40c") / "pack")
    assert B.main(["build", "--out", out, "--src", SRC, "--strict-readme"]) == 0
    return out


def _serve(root):
    server = C.start(S.PackSource(root))
    return server, C.Client(server).login()


def test_first_load_is_two_requests_and_never_429(built):
    js = open(os.path.join(REPO, "prooflab", "console", "static", "app.js")).read()
    boot = js[js.index("async function loadAll"):]
    assert "/api/v1/boot" in boot and "/api/v1/pack" in boot
    assert "/api/v1/answer?key" not in boot and "/api/v1/auditor/" not in boot and "/api/v1/records?run" not in boot
    server, c = _serve(built)
    try:
        for _ in range(3):                      # the page's whole first load, several times over, inside one second
            st, pack = c.json("/api/v1/pack")
            st2, bj = c.json("/api/v1/boot")
            assert st == 200 and st2 == 200
        idx = pack["data"]
        assert set(bj["data"]["answers"]) == set(a["key"] for a in idx["answers"])
        assert set(bj["data"]["auditor"]) == set(a["id"] for a in idx["auditor"])
        assert set(bj["data"]["records"]) == set(r["alias"] for r in idx["runs"])
    finally:
        server.shutdown(); server.server_close()


def test_auditor_integrity_question_agrees_with_the_banner(built):
    server, c = _serve(built)
    try:
        st, integ = c.json("/api/v1/integrity")
        assert integ["data"]["status"] == "VERIFIED"
        st, idx = c.json("/api/v1/pack")
        for a in idx["data"]["auditor"]:
            for url in ("/api/v1/auditor/" + quote(a["id"]), None):
                if url is None:
                    break
                st, doc = c.json(url)
                q = doc["data"]["questions"]["integrity"]
                assert "missing (gap)" not in q["answer"]
                assert "MANIFEST.json VERIFIED (%d files" % integ["data"]["files"] in q["answer"]
                assert q["facts"][0]["flag"] == "OK"
        st, boot = c.json("/api/v1/boot")          # the batched path states the same thing
        assert all("VERIFIED" in d["questions"]["integrity"]["answer"] for d in boot["data"]["auditor"].values())
    finally:
        server.shutdown(); server.server_close()


def test_display_summary_headroom_sign():
    assert PJ.display_summary("tokens 16450, cap 40000 (tier default), headroom -23550; complete") == \
        "tokens 16450, cap 40000 (tier default), under cap by 23550; complete"
    assert "over cap by 12" in PJ.display_summary("headroom 12")
    assert PJ.display_summary("78800 tokens over cap 40000 by 38800") == "78800 tokens over cap 40000 by 38800"


def test_delivery_log_projects_into_findings(tmp_path):
    src = tmp_path / "s"
    (src / "servicenow").mkdir(parents=True)
    rows = [{"finding_id": "f1", "state": "INTENT"}, {"finding_id": "f1", "state": "SENT", "number": "INC0001000"},
            {"finding_id": "f1", "state": "DELIVERED", "number": "INC0001000"}, "not json"]
    (src / "servicenow" / "delivery-log.jsonl").write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows))
    d = PJ.delivery_by_finding(str(src))
    assert d["f1"]["state"] == "DELIVERED" and d["f1"]["number"] == "INC0001000"
    assert PJ.delivery_by_finding(str(tmp_path / "none")) == {}


def test_loop_view_lists_findings_and_states_the_case_gap():
    js = open(os.path.join(REPO, "prooflab", "console", "static", "app.js")).read()
    assert "P.findings" in js and "No ServiceNow case snapshots are listed" in js
    vend = os.path.join(REPO, "prooflab", "console", "panel_vendor")
    assert os.path.isfile(os.path.join(vend, "ifabric-case-panel.js"))     # vendored panel left alone


class _Pins(object):
    def __init__(self, files):
        self.files = files

    def list_file(self, pattern):
        return self.files


def test_fault_injection_run_is_labelled_with_its_declared_fault(tmp_path):
    pin = tmp_path / "v1-observe.json"
    pin.write_text(json.dumps({"c7": {"declared_faults": ["suppress-record:ifabric-it:tool.call:1"]}}))
    pack = _Pins([str(pin)])
    assert E.run_label(pack, "x", "OURS-ROLE-UNDECLARED", "FAULT_INJECTION") == "declared fault: suppress-record"
    assert E.run_label(pack, "x", "LIVE_SUBJECT", "LIVE_SUBJECT") == "LIVE_SUBJECT"
    assert E.run_label(pack, "x", "OURS-ROLE-UNDECLARED", "ASSESSED") == "OURS-ROLE-UNDECLARED"
    assert E.run_label(_Pins([]), "x", "OURS-ROLE-UNDECLARED", "FAULT_INJECTION").startswith("declared fault: kind not recorded")


def test_declared_fault_narrows_to_suppress_record_when_c7_lacks_an_event(tmp_path):
    pin = tmp_path / "p.json"
    pin.write_text(json.dumps({"c7": {"declared_faults": ["suppress-record:a:b:1", "inject-tool-output:a:t:f"]}}))

    class P(_Pins):
        def assessments_for(self, c, kinds):
            return [{"scope_id": "x", "exceptions": [{"kind": "missing-event", "key": "k"}]}]
    assert E.run_label(P([str(pin)]), "x", "OURS-ROLE-UNDECLARED", "FAULT_INJECTION") == "declared fault: suppress-record"
    assert E.run_label(_Pins([str(pin)]), "x", "OURS-ROLE-UNDECLARED", "FAULT_INJECTION") == \
        "declared fault: suppress-record, inject-tool-output"


@pytest.fixture()
def c7_pack(tmp_path):
    dst = str(tmp_path / "pack")
    shutil.copytree(SRC, dst)
    path = os.path.join(dst, "assessments", "C7", "C7_C7-v1_run_%s_r1.json" % C7_BREACH)
    doc = json.load(open(path))
    doc["completeness"] = {"expected": 9, "captured": 8, "missing": ["call:act-N4-t01"]}
    json.dump(doc, open(path, "w"))
    return dst


def test_c7_answer_shows_c7_evidence_not_c16_decisions(c7_pack):
    res = A.ask(E.Pack(c7_pack), "control 7 for run " + C7_BREACH)
    d = res["doc"]
    assert d["population"]["missing"] == 1 and d["population"]["missing_events"] == ["call:act-N4-t01"]
    assert d["population"]["matched"] == 8 and d["population"]["expected"]["count"] == 9
    assert all("C16" not in x["reason"] for x in d["enforcement"]["inline_decisions"])
    assert d["enforcement"]["mode"] == "POST_RUN"
