"""The console projection's fixed points against Arth's handoff-3 schema and fixtures."""
import glob
import json
import os

import pytest

from prooflab.contract import app_format as A
from prooflab.contract import record as R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAN = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "evidence-console-plan")
SCHEMA = os.path.join(PLAN, "schemas", "contracts.schema.json")
needs_plan = pytest.mark.skipif(not os.path.exists(SCHEMA), reason="handoff-3 console plan not in the tree")


@needs_plan
def test_constants_match_arths_schema():
    with open(SCHEMA) as handle:
        defs = json.load(handle)["$defs"]
    assert tuple(defs["packIndex"]["required"]) == A.PACK_INDEX_REQUIRED
    assert tuple(defs["answer"]["required"]) == A.ANSWER_REQUIRED
    assert defs["packIndex"]["properties"]["schema"]["const"] == A.PACK_INDEX_SCHEMA
    assert defs["answer"]["properties"]["schema"]["const"] == A.ANSWER_SCHEMA
    assert tuple(defs["provenance"]["enum"]) == A.CONSOLE_PROVENANCE
    assert tuple(defs["verdict"]["enum"]) == A.CONSOLE_VERDICTS
    assert tuple(defs["claimVerdict"]["enum"]) == A.CONSOLE_CLAIM_VERDICTS
    assert tuple(defs["controlRef"]["enum"]) == A.CONSOLE_CONTROL_REFS
    assert tuple(defs["controlId"]["enum"]) == A.CONSOLE_CONTROL_IDS
    assert tuple(defs["controlMode"]["enum"]) == A.CONSOLE_CONTROL_MODES
    assert tuple(defs["scope"]["properties"]["kind"]["enum"]) == A.CONSOLE_SCOPE_KINDS


@needs_plan
@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(PLAN, "examples", "answer.*.json"))))
def test_answer_id_reproduces_arths_fixtures(path):
    with open(path) as handle:
        answer = json.load(handle)
    assert not A.missing_keys(answer, A.ANSWER_REQUIRED)
    assert A.answer_id_of(answer) == answer["answer_id"]


@needs_plan
def test_pack_index_fixture_has_the_required_keys():
    with open(os.path.join(PLAN, "examples", "pack-index.json")) as handle:
        assert A.missing_keys(json.load(handle), A.PACK_INDEX_REQUIRED) == []


def test_mapping_tables_cover_our_vocabularies():
    assert set(A.PROVENANCE_TO_CONSOLE) == set(R.PROVENANCE)
    assert set(A.PROVENANCE_TO_CONSOLE.values()) <= set(A.CONSOLE_PROVENANCE)
    assert A.console_provenance("PILOT") == "EXPLORATORY"
    assert A.console_provenance("FAULT_INJECTION", named=True) == "ASSESSED"
    assert A.console_inline_decision("DENY", "observe") == "ALERT"
    assert A.console_inline_decision("DENY", "enforce") == "DENY"
    assert A.console_inline_decision("ALLOW", "observe") == "ALLOW"
    assert A.console_record_kind("action", tool_name="x") == "tool-call"
    assert A.console_record_kind("action") == "model-call"
    assert A.console_record_kind("rail_decision") is None
    assert A.console_control_ref("INV") is None and A.console_control_ref("C16") == "C16"
    for ref, lib in R.CONTROL_LIBRARY_IDS.items():
        if ref in A.CONSOLE_CONTROL_REFS:
            assert lib in A.CONSOLE_CONTROL_IDS
