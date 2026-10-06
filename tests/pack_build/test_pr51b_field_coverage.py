"""PR-51b: field-coverage.md is staged in the pack, linked from the README limitations, every gap classed."""
import os
import re

from prooflab.pack import build

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_field_coverage_staged_and_classed():
    assert "field-coverage.md" in build.PACK_TOP
    path = os.path.join(ROOT, "evidence-templates", "field-coverage.md")
    text = open(path, encoding="utf-8").read()
    rows = [l for l in text.splitlines() if re.match(r"^\| [AH]-G\d+ ", l)]
    assert len(rows) == 48
    assert all(any(("**%s**" % c) in r for c in ("NEEDS-AGENT-REBUILD", "NEEDS-RE-RECORD", "PLATFORM", "VIEW")) for r in rows)
    assert "frozen and approved" in text and "never edited" in text
    # fix round: no FIX proposal presented as done, no false generation claim, view/collector rows not blamed on images
    assert "Generated at pack-build time" not in text and "Staged at pack build" in text
    for tag in ("self-asserted (shared ledger token)", "derived-from:aws-spans", "joined-from:b3d status capture",
                "witnessed-by:gateway-span(call.id)"):
        assert tag not in text.split("| proposed by the audit")[0] and all(tag not in r.split(" | ")[5] for r in rows)
    for gid in ("A-G13", "A-G14", "A-G17", "A-G19", "H-G02", "H-G19", "H-G20"):
        row = [r for r in rows if r.startswith("| %s " % gid)][0]
        assert "frozen, approved agent images" not in row.split(" | ")[7]


