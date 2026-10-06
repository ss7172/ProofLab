"""Read the ServiceNow agent's analysis note back out of an incident's work notes.

The iFabric Assurance Agent (AI Agent Studio) writes one work note per run:

  [iFabric Assurance Agent analysis]
  Finding ID: ...
  Control: ...
  ... (one "Key: value" line per field in ANALYSIS_FIELDS)

The work-notes display text (readable by itil through the Table API, unlike
sys_journal_field rows) lists entries newest first, each headed
"YYYY-MM-DD HH:MM:SS - Author (Work notes)". Times are in the reading user's
display time zone. Model output is untrusted: missing fields and a wrong
finding id are flagged, never filled in.
"""
from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from prooflab.servicenow.finding import Finding

ANALYSIS_MARKER = "[iFabric Assurance Agent analysis]"
# Next step is policy, not model judgement: one exact sentence per verdict.
NEXT_STEPS = {"BREACHED": "Close only after a linked passing re-test.",
              "ESCALATED": "The named approver must record a decision.",
              "INDETERMINATE": "Restore monitoring and re-run the assessment.",
              "SATISFIED": "No action; keep monitoring."}
# Fields the model writes (facts it must echo + its judgement), then fields our code computes.
MODEL_FIELDS = ("Finding ID", "Control", "Threshold version", "Scope", "Verdict",
                "Measured vs limit", "Evidence refs", "Owner", "State", "Owner response",
                "Missing evidence", "Next step")
COMPUTED_FIELDS = ("Agent path", "Policy alignment", "Validation", "Model")
ANALYSIS_FIELDS = MODEL_FIELDS + COMPUTED_FIELDS
_HEADER = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (.+?) \(([^()]+)\)[ \t]*$",
                     re.MULTILINE)
_DECORATION = " \t-*•>#`"
_FIELD_BY_KEY = {name.lower(): name for name in ANALYSIS_FIELDS}


@dataclass(frozen=True)
class JournalEntry:
    at: str
    author: str
    kind: str
    body: str


@dataclass(frozen=True)
class AgentAnalysis:
    at: str
    author: str
    fields: Dict[str, str] = field(default_factory=dict)
    missing_fields: Tuple[str, ...] = ()
    finding_matches: bool = False
    digest: str = ""
    verified: Optional[bool] = None  # True: digest is in our run log; False: not ours; None: not checked

    @property
    def complete(self) -> bool:
        return not self.missing_fields

    def to_dict(self) -> dict:
        return {"status": "present", "at": self.at, "author": self.author,
                "fields": dict(self.fields), "missing_fields": list(self.missing_fields),
                "complete": self.complete, "finding_matches": self.finding_matches,
                "verified": self.verified, "note_sha256": self.digest}


def note_digest(body: str) -> str:
    """SHA-256 of a note, insensitive to blank lines and surrounding whitespace."""
    lines = [line.strip() for line in (body or "").strip().splitlines() if line.strip()]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def trusted_digests(history: Iterable[dict]) -> Set[str]:
    """Digests of notes our orchestrator wrote, from the delivery-log history of one finding."""
    return {entry["note_digest"] for entry in history
            if entry.get("state", "").startswith("ANALYSIS_") and entry.get("note_digest")}


def static_facts(finding: Finding) -> Dict[str, str]:
    """Fields fixed by the finding and policy; they never change after the incident is raised."""
    return {"Finding ID": finding.finding_id,
            "Control": f"{finding.control_ref} {finding.control_id}",
            "Threshold version": finding.threshold_version,
            "Scope": f"{finding.scope_kind} {finding.scope_id}", "Verdict": finding.verdict,
            "Next step": NEXT_STEPS.get(finding.verdict, "missing")}


def facts_match(fields: Dict[str, str], finding: Finding) -> bool:
    norm = lambda value: " ".join(str(value or "").split())  # noqa: E731
    return all(norm(fields.get(name)) == norm(value) for name, value in static_facts(finding).items())


def split_journal(text: Optional[str]) -> List[JournalEntry]:
    """Split work-notes display text into entries, in the order given (newest first)."""
    if not text:
        return []
    headers = list(_HEADER.finditer(text))
    entries = []
    for index, match in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        # Entities are decoded per entry, after splitting, so an encoded newline inside a note
        # cannot create a new header. Some instances return display text HTML-escaped.
        body = html.unescape(text[match.end():end]).strip("\n").rstrip()
        entries.append(JournalEntry(at=match.group(1), author=html.unescape(match.group(2)).strip(),
                                    kind=match.group(3).strip(), body=body))
    return entries


def is_analysis_note(body: Optional[str]) -> bool:
    return bool(body) and body.strip().startswith(ANALYSIS_MARKER)


def parse_note_fields(body: str) -> Dict[str, str]:
    """`Key: value` lines after the marker line, keyed by canonical field name."""
    fields: Dict[str, str] = {}
    for line in body.strip().splitlines()[1:]:
        key, sep, value = line.partition(":")
        name = _FIELD_BY_KEY.get(key.strip(_DECORATION).replace("*", "").strip().lower())
        if sep and name and name not in fields:
            fields[name] = value.strip().strip("*").strip()
    return fields


def latest_agent_analysis(notes_text: Optional[str], finding_id: str,
                          trusted: Optional[Set[str]] = None) -> Optional[AgentAnalysis]:
    """The newest analysis note, or None if none exists.

    Order is ServiceNow's display order (newest first), never the header timestamp: anyone
    who can write a note can also type a fake header with a future time. With `trusted`
    digests, the newest note that our orchestrator wrote wins and verified=True; if no
    trusted note exists, the newest note is returned with verified=False."""
    notes = [entry for entry in split_journal(notes_text) if is_analysis_note(entry.body)]
    if not notes:
        return None
    chosen, verified = notes[0], None
    if trusted is not None:
        ours = [entry for entry in notes if note_digest(entry.body) in trusted]
        chosen, verified = (ours[0], True) if ours else (notes[0], False)
    fields = parse_note_fields(chosen.body)
    missing = tuple(name for name in ANALYSIS_FIELDS if not fields.get(name))
    return AgentAnalysis(at=chosen.at, author=chosen.author, fields=fields,
                         missing_fields=missing,
                         finding_matches=fields.get("Finding ID") == finding_id,
                         digest=note_digest(chosen.body), verified=verified)
