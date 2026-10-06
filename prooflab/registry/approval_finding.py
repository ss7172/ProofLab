"""G-13: the T2 approval Finding, written from the frozen bytes (ARCH §3.3 T2; work/12 G-13). Stdlib, Python 3.9.

    finding = approval_finding(version, register_bytes, risks_bytes, detected_at)
    path    = write_approval_finding(version, register_path, risks_path, out_dir, detected_at)

Shape (Arth's `thresholds/approval-finding.template.json` with the risk register added): control_ref REG,
control_id THRESHOLD-REGISTER, kind approval, scope_kind escalation, scope_id register-<v>, verdict ESCALATED, evidence
= both full sha256s. It is NOT a control verdict: never analyzed, never an assessment. `notify` (PR-20a) sends it to its
own absolute delivery log. The register and risks files are never modified; the hashes are of the file bytes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from prooflab.contract import clocks as _clocks
from prooflab.contract import finding as _finding
from prooflab.contract import register as _reg

CONTROL_REF = "REG"
CONTROL_ID = "THRESHOLD-REGISTER"
KIND = "approval"
APPROVAL_FILE = "approval-finding.json"


def approval_note_text(version: str, register_sha256: str, risks_sha256: str) -> str:
    """The exact note the owner adds (hex12 of each digest), for the instructions printed to the humans."""
    return "APPROVED threshold register %s, sha256 %s; risks sha256 %s" % (version, register_sha256[:12], risks_sha256[:12])


def approval_finding(version: str, register_bytes: bytes, risks_bytes: bytes, detected_at: str,
                     register_path: str = "evidence/register/register.yaml",
                     risks_path: str = "evidence/register/risks.yaml") -> dict:
    reg_sha, risks_sha = _reg.register_sha256(register_bytes), _reg.register_sha256(risks_bytes)
    return _finding.make_finding(
        CONTROL_REF, CONTROL_ID, version, "escalation", "register-%s" % version, "ESCALATED",
        "Approve register %s (sha256 %s) and risks (sha256 %s)" % (version, reg_sha[:12], risks_sha[:12]),
        detected_at,
        evidence=["register:sha256=%s" % reg_sha, "risks:sha256=%s" % risks_sha,
                  "register:path=%s" % register_path, "risks:path=%s" % risks_path],
        kind=KIND)


def write_approval_finding(version: str, register_path: str, risks_path: str, out_dir: str, detected_at=None) -> str:
    detected_at = detected_at or _clocks.now_utc()
    if not _clocks.is_utc(detected_at):
        raise ValueError("detected_at must be a full UTC time, got %r" % (detected_at,))
    with open(register_path, "rb") as fh:
        reg_bytes = fh.read()
    with open(risks_path, "rb") as fh:
        risks_bytes = fh.read()
    data = approval_finding(version, reg_bytes, risks_bytes, detected_at)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, APPROVAL_FILE)
    with open(path, "xb") as fh:  # never rewritten: a new version is a new file elsewhere
        fh.write((json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab register approval-finding")
    ap.add_argument("--version", required=True)
    ap.add_argument("--register", required=True, help="the FROZEN register file")
    ap.add_argument("--risks", required=True, help="the FROZEN risks file")
    ap.add_argument("--out", default="evidence/register/approval")
    ap.add_argument("--detected-at", help="UTC time; default now")
    ns = ap.parse_args(argv)
    try:
        path = write_approval_finding(ns.version, ns.register, ns.risks, ns.out, ns.detected_at)
    except (ValueError, OSError) as exc:
        print("approval finding refused: %s" % exc, file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
