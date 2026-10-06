"""Parsing the ServiceNow agent's analysis note out of the incident's work notes."""
from __future__ import annotations

from prooflab.servicenow.analysis import (ANALYSIS_FIELDS, ANALYSIS_MARKER, is_analysis_note,
                                          latest_agent_analysis, split_journal)

FID = "ifabric:C16:TEST:run:AGENT-ANALYSIS-TEST-2:wiring-test"

NOTE = "\n".join([
    ANALYSIS_MARKER,
    f"Finding ID: {FID}",
    "Control: C16 ACN-COST-001",
    "Threshold version: TEST",
    "Scope: run AGENT-ANALYSIS-TEST-2",
    "Verdict: INDETERMINATE",
    "Measured vs limit: missing",
    "Evidence refs: test:gateway-action-none; test:ledger-cid-none",
    "Owner: Sree Annapurna Rallabandi",
    "State: In Progress",
    "Owner response: No",
    "Missing evidence: measured value",
    "Next step: Restore monitoring and re-run the assessment.",
    "Agent path: not provided by the evaluator",
    "Policy alignment: 4/8 pass; unknown: P1, P2, P3, P8",
    "Validation: facts echoed exactly",
    "Model: NVIDIA Nemotron via modaas-agw:nemotron-super-120b (alias nemotron-super-120b; model m; action a)",
])


def journal(*entries):
    """Build ServiceNow's journal display text, newest entry first."""
    return "\n\n".join(f"{at} - {author} (Work notes)\n{body}" for at, author, body in entries)


def test_split_journal_reads_time_author_and_body():
    text = journal(("2026-10-05 09:01:00", "iFabric Assurance Agent", "second"),
                   ("2026-10-05 08:51:09", "iFabric Integration", "ProofLab finding x\nline 2"))
    entries = split_journal(text)
    assert [(e.at, e.author) for e in entries] == [("2026-10-05 09:01:00", "iFabric Assurance Agent"),
                                                   ("2026-10-05 08:51:09", "iFabric Integration")]
    assert entries[1].body == "ProofLab finding x\nline 2"


def test_split_journal_of_empty_text_is_empty():
    assert split_journal("") == [] and split_journal(None) == []


def test_latest_analysis_is_parsed_into_named_fields():
    text = journal(("2026-10-05 09:01:00", "iFabric Assurance Agent", NOTE),
                   ("2026-10-05 08:51:09", "iFabric Integration", "ProofLab finding " + FID))
    analysis = latest_agent_analysis(text, FID)
    assert analysis is not None
    assert analysis.fields["Verdict"] == "INDETERMINATE"
    assert analysis.fields["Evidence refs"] == "test:gateway-action-none; test:ledger-cid-none"
    assert analysis.author == "iFabric Assurance Agent" and analysis.at == "2026-10-05 09:01:00"
    assert analysis.complete and analysis.finding_matches
    assert analysis.to_dict()["missing_fields"] == []


def test_newest_of_several_analyses_wins():
    older = NOTE.replace("Owner response: No", "Owner response: Yes")
    text = journal(("2026-10-05 09:10:00", "iFabric Assurance Agent", NOTE),
                   ("2026-10-05 09:01:00", "iFabric Assurance Agent", older))
    assert latest_agent_analysis(text, FID).fields["Owner response"] == "No"


def test_markdown_decoration_from_the_model_is_tolerated():
    decorated = NOTE.replace("Verdict: ", "- **Verdict**: ").replace("Scope: ", "* Scope: ")
    analysis = latest_agent_analysis(journal(("2026-10-05 09:01:00", "a", decorated)), FID)
    assert analysis.fields["Verdict"] == "INDETERMINATE"
    assert analysis.fields["Scope"] == "run AGENT-ANALYSIS-TEST-2"


def test_missing_fields_and_wrong_finding_are_flagged_not_hidden():
    partial = "\n".join(line for line in NOTE.splitlines() if not line.startswith("Measured"))
    partial = partial.replace(FID, "ifabric:other")
    analysis = latest_agent_analysis(journal(("2026-10-05 09:01:00", "a", partial)), FID)
    assert not analysis.complete and analysis.missing_fields == ("Measured vs limit",)
    assert not analysis.finding_matches


def test_no_analysis_note_returns_none():
    text = journal(("2026-10-05 08:51:09", "iFabric Integration", "ProofLab finding " + FID))
    assert latest_agent_analysis(text, FID) is None


def test_is_analysis_note_ignores_leading_whitespace():
    assert is_analysis_note("  \n" + NOTE) and not is_analysis_note("Acknowledged")


def test_field_list_matches_the_agent_instructions():
    assert ANALYSIS_FIELDS[0] == "Finding ID" and ANALYSIS_FIELDS[-1] == "Model"
    assert ANALYSIS_FIELDS[12:] == ("Agent path", "Policy alignment", "Validation", "Model")
    assert len(ANALYSIS_FIELDS) == 16
