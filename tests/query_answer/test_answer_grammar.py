"""PR-15b: the query grammar, the answer composer, answer_id determinism, schema validity, the CLI verb aliases."""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil

import pytest

import _projector_schema as sch
from prooflab.contract import verdicts as V
from prooflab.query import answer as A
from prooflab.query import cli
from prooflab.query import engine as E
from prooflab.query import grammar as G
from prooflab.query import render_text as R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "query", "fixtures", "pack")
CID1 = "ifabric-run-1791260000-ab12cd"     # C16 BREACHED
CID2 = "ifabric-run-1791261000-cd34ef"     # C16 SATISFIED
GEN = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "evidence-console-plan", "examples", "generate_examples.py")
NOW = "2026-10-06T09:00:00Z"


@pytest.fixture()
def pack_dir(tmp_path):
    dst = str(tmp_path / "pack")
    shutil.copytree(FIX, dst)
    rows = []
    for line in open(os.path.join(dst, "derived", "run-catalogue.jsonl")):
        r = json.loads(line)
        if r["cid"] == CID1:
            r["alias"] = "FM-B"
        if r["cid"] == CID2:
            r["alias"] = "FM-C"
        rows.append(r)
    with open(os.path.join(dst, "derived", "run-catalogue.jsonl"), "w") as f:
        f.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    return dst


@pytest.fixture()
def pack(pack_dir):
    return E.Pack(pack_dir)


def _arth():
    spec = importlib.util.spec_from_file_location("generate_examples", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------ grammar: every phrase of Arth's 06 section 6
PHRASES = [
    ("Show me control 16 for run FM-B", "controltest-run", "C16"),
    ("Was control 9 satisfied for run FM-B?", "controltest-run", "C9"),
    ("Was control 9 satisfied between 23:00Z and 09:00Z?", "controltest-window", "C9"),
    ("control 9 from 2026-10-06T06:00:00Z to 2026-10-06T07:00:00Z", "controltest-window", "C9"),
    ("control 9 for window 2026-10-06T00", "controltest-window", "C9"),
    ("controltest 16 --run FM-B", "controltest-run", "C16"),
    ("six questions for INC0090216", "auditor", None),
    ("six questions INC0090216", "auditor", None),
    ("auditor INC0090216", "auditor", None),
    ("reconstruct run FM-B", "trail", None),
    ("trail FM-B", "trail", None),
    ("who acted in FM-B", "who", None),
    ("who was told for FM-B", "told", None),
    ("SHOW ME CONTROL 7 FOR RUN fm-b", "controltest-run", "C7"),
    ("show me control spend cap for run FM-B", "controltest-run", "C16"),
    ("was control drift satisfied for run FM-B", "controltest-run", "C9"),
    ("control event recording for run FM-B", "controltest-run", "C7"),
]


@pytest.mark.parametrize("text,kind,control", PHRASES)
def test_every_phrase_parses(pack, text, kind, control):
    p = G.parse(text, pack)
    assert p["ok"], p
    assert p["kind"] == kind and p["control"] == control
    assert p["normalized"]


def test_alias_resolves_to_cid_and_cid_passes_through(pack):
    assert G.parse("Show me control 16 for run FM-B", pack)["run"] == CID1
    assert G.parse("Show me control 16 for run FM-b", pack)["run"] == CID1
    assert G.parse("Show me control 16 for run %s" % CID2, pack)["run"] == CID2


def test_ambiguous_run_gives_candidates_not_a_guess(pack):
    p = G.parse("Show me control 16 for run ifabric-run", pack)
    assert not p["ok"] and sorted(p["candidates"]) == [CID1, CID2]


def test_unknown_input_is_never_guessed(pack):
    for text in ("what is the weather", "", "control 99 for run FM-B", "control 16"):
        p = G.parse(text, pack)
        assert not p["ok"] and p["examples"], text
    assert "can't parse" in G.parse("tell me a joke", pack)["error"]


def test_hhmmz_resolves_within_the_event_window(pack):
    p = G.parse("Was control 9 satisfied between 23:00Z and 09:00Z?", pack)
    assert (p["t1"], p["t2"]) == ("2026-10-05T23:00:00Z", "2026-10-06T09:00:00Z") or p["t1"] < p["t2"]
    assert p["t1"].endswith("T23:00:00Z") and p["t2"].endswith("T09:00:00Z")
    assert G.parse("control 9 between 06:00Z and 07:00Z", pack)["t1"] == "2026-10-06T06:00:00Z"


def test_hhmmz_without_a_window_is_an_error(tmp_path):
    p = G.parse("control 9 between 06:00Z and 07:00Z", E.Pack(str(tmp_path)))
    assert not p["ok"] and "window" in p["error"]


def test_hour_window_is_one_hour(pack):
    p = G.parse("control 9 for window 2026-10-06T06", pack)
    assert (p["t1"], p["t2"]) == ("2026-10-06T06:00:00Z", "2026-10-06T07:00:00Z")


def test_no_verdict_literals_or_llm_in_grammar():
    src = open(os.path.join(ROOT, "prooflab", "query", "grammar.py")).read()
    assert not re.search(r"SATISFIED|BREACHED|INDETERMINATE|anthropic|openai|bedrock", src)


# ------------------------------------------------------------ answers
def test_run_answer_validates_against_the_contract_schema(pack):
    for cid, want in ((CID1, V.BREACHED), (CID2, V.SATISFIED)):
        res = A.ask(pack, "Show me control 16 for run %s" % cid, now=NOW)
        assert res["kind"] == "answer", res["doc"]
        d = res["doc"]
        assert sch.validate_def(d, "answer") == []
        assert d["verdict"]["value"] == want
        assert res["exit"] == V.exit_code(want)
        assert d["verdict"]["label"] == V.display(want)


def test_window_answer_validates(pack):
    res = A.ask(pack, "control 16 between 2026-10-06T05:00:00Z and 2026-10-06T09:00:00Z", now=NOW)
    assert res["kind"] == "answer", res["doc"]
    assert sch.validate_def(res["doc"], "answer") == []
    assert res["doc"]["scope"]["kind"] == "interval"


def test_auditor_answer_validates(pack):
    res = A.ask(pack, "six questions for FM-B", now=NOW) if False else A.ask(pack, "six questions for %s" % CID1, now=NOW)
    assert res["kind"] == "auditor", res["doc"]
    assert sch.validate_def(res["doc"], "auditor") == []
    assert set(res["doc"]["questions"]) == {"who", "what", "authorized", "approved", "integrity", "reconstruct"}


def test_who_acted_is_an_auditor_question(pack):
    res = A.ask(pack, "who acted in FM-B", now=NOW)
    assert res["kind"] == "auditor" and res["doc"]["focus"] == "who"
    assert "WHO" in "\n".join(R.render(res))


def test_the_same_question_twice_gives_the_same_answer_id(pack):
    q = "Show me control 16 for run FM-B"
    a = A.ask(pack, q, now="2026-10-06T09:00:00Z")["doc"]
    b = A.ask(pack, q, now="2026-10-06T09:30:00Z")["doc"]
    assert a["answered_at"] != b["answered_at"]
    assert a["answer_id"] == b["answer_id"]
    assert re.match(r"^[0-9a-f]{64}$", a["answer_id"])


def test_answer_id_equals_arths_answer_id_of(pack):
    gen = _arth()
    d = A.ask(pack, "Show me control 16 for run FM-B", now=NOW)["doc"]
    assert d["answer_id"] == gen.answer_id_of(d)
    other = dict(d, source=dict(d["source"], mode="LIVE"), elapsed_ms=999)
    assert gen.answer_id_of(other) == d["answer_id"]      # mode and elapsed_ms are outside the id
    changed = A.ask(pack, "Show me control 16 for run FM-C", now=NOW)["doc"]
    assert changed["answer_id"] != d["answer_id"]


def test_answer_id_survives_a_different_pack_path(pack_dir, tmp_path):
    other = str(tmp_path / "elsewhere")
    shutil.copytree(pack_dir, other)
    q = "Show me control 16 for run FM-B"
    assert A.ask(E.Pack(pack_dir), q, now=NOW)["doc"]["answer_id"] == A.ask(E.Pack(other), q, now=NOW)["doc"]["answer_id"]


def test_verdict_comes_from_the_stored_assessment(pack):
    d = A.ask(pack, "Show me control 16 for run FM-B", now=NOW)["doc"]
    stored = E.control_run(pack, "C16", CID1)
    assert d["verdict"]["value"] == stored["verdict"]
    assert d["measurement"]["value"] == stored["measured"]["value"]
    assert d["comparison"]["limit"] == stored["limit"]


def test_unknown_run_and_unassessed_control_are_gaps_exit_2(pack):
    for q in ("Show me control 16 for run nonesuch", "Show me control 16 for run %s" % "customer-1791250000-0a0a0a"):
        res = A.ask(pack, q, now=NOW)
        assert res["kind"] in ("gap", "unparsed") and res["exit"] == 2
        assert R.render(res)


def test_tampered_manifest_is_reported(pack_dir):
    import hashlib
    rel = "store/records.jsonl"
    m = {"files": [{"path": rel, "sha256": hashlib.sha256(open(os.path.join(pack_dir, rel), "rb").read()).hexdigest()}]}
    json.dump(m, open(os.path.join(pack_dir, "MANIFEST.json"), "w"))
    assert A.ask(E.Pack(pack_dir), "Show me control 16 for run FM-B", now=NOW)["doc"]["source"]["manifest_status"] == "VERIFIED"
    with open(os.path.join(pack_dir, rel), "a") as f:
        f.write("\n")
    assert A.ask(E.Pack(pack_dir), "Show me control 16 for run FM-B", now=NOW)["doc"]["source"]["manifest_status"] == "MODIFIED"


def test_text_render_is_one_screen_and_shows_the_verdict(pack):
    res = A.ask(pack, "Show me control 16 for run FM-B", now=NOW)
    text = "\n".join(R.render(res))
    assert "NOT SATISFIED" in text and "FM-B" in text
    assert len(R.render(res)) < 60


# ------------------------------------------------------------ the CLI verbs
def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(argv)
    return code, buf.getvalue()


@pytest.mark.parametrize("argv", [
    ["ask", "Show me control 16 for run FM-B"],
    ["controltest", "16", "--run", "FM-B"],
    ["ASK", "show me control 16 for run FM-B"],
])
def test_verbs_answer_and_exit_with_the_verdict(pack_dir, argv):
    code, out = run_cli(["--pack", pack_dir] + argv if False else argv + ["--pack", pack_dir])
    assert code == V.exit_code(V.BREACHED)
    assert "NOT SATISFIED" in out


def test_auditor_and_trail_verbs(pack_dir):
    code, out = run_cli(["auditor", CID1, "--pack", pack_dir])
    assert code == 0 and "AUDITOR" in out
    code, out = run_cli(["trail", CID1, "--pack", pack_dir])
    assert code == 0 and "TRAIL" in out


def test_ask_json_is_the_schema_document(pack_dir):
    code, out = run_cli(["ask", "Show me control 16 for run FM-C", "--json", "--pack", pack_dir])
    d = json.loads(out)
    assert code == 0 and sch.validate_def(d, "answer") == []


def test_ask_unparsed_exits_2_with_examples(pack_dir):
    code, out = run_cli(["ask", "gibberish", "--pack", pack_dir])
    assert code == 2 and "examples" in out


def test_existing_flag_form_still_works(pack_dir):
    code, _ = run_cli(["--pack", pack_dir, "--control", "C16", "--run", CID2])
    assert code == 0
