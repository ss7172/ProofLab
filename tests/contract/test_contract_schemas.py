"""Committed JSON Schema files equal their generators; Arth's console contracts are a byte copy (PR-01)."""
import json
import os

import pytest

from prooflab.contract import app_format as A
from prooflab.contract import schemas as S

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAN = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "evidence-console-plan")
FM_B = os.path.join(PLAN, "examples", "answer.C16.run.FM-B.json")
COPY = os.path.join(S.SCHEMA_DIR, S.APP_CONTRACTS_FILE)


@pytest.mark.parametrize("name", sorted(S.GENERATED))
def test_schema_file_equals_generator(name):
    with open(os.path.join(S.SCHEMA_DIR, name)) as handle:
        on_disk = json.load(handle)
    assert on_disk == json.loads(json.dumps(S.GENERATED[name]()))


def test_expected_schema_files_exist():
    names = set(os.listdir(S.SCHEMA_DIR))
    assert {"evidence-record-1.json", "assessment-1.json", "register-1.json", "pin-1.json",
            S.APP_CONTRACTS_FILE} <= names


def test_app_contracts_is_a_byte_copy_of_handoff3():
    source = os.path.join(ROOT, S.APP_CONTRACTS_SOURCE)
    if not os.path.isfile(source):
        pytest.skip("handoff-3 not in this checkout")
    with open(source, "rb") as a, open(COPY, "rb") as b:
        assert a.read() == b.read()


def _defs():
    with open(COPY) as handle:
        return json.load(handle)["$defs"]


def test_answer_and_pack_index_required_match_our_constants():
    defs = _defs()
    assert tuple(defs["answer"]["required"]) == A.ANSWER_REQUIRED
    assert tuple(defs["packIndex"]["required"]) == A.PACK_INDEX_REQUIRED


def _enum(defs, name):
    node = defs[name]
    return set(node.get("enum") or [])


def test_fm_b_answer_validates_against_the_copy():
    if not os.path.isfile(FM_B):
        pytest.skip("handoff-3 examples not in this checkout")
    with open(FM_B) as handle:
        answer = json.load(handle)
    defs = _defs()
    assert A.missing_keys(answer, defs["answer"]["required"]) == []
    props = defs["answer"].get("properties", {})
    unknown = set(answer) - set(props) if defs["answer"].get("additionalProperties") is False else set()
    assert unknown == set()
    assert answer["schema"] == A.ANSWER_SCHEMA
    if _enum(defs, "provenance"):
        assert answer["provenance"] in _enum(defs, "provenance")
    verdict = answer["verdict"]["value"] if isinstance(answer["verdict"], dict) else answer["verdict"]
    if _enum(defs, "verdict"):
        assert verdict in _enum(defs, "verdict")
    assert verdict in A.CONSOLE_VERDICTS
    assert A.answer_id_of(answer) == answer["answer_id"]
