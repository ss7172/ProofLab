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
    assert all(("**NEEDS-AGENT-REBUILD**" in r) or ("**PLATFORM**" in r) for r in rows)
    assert "frozen and approved" in text and "never edited" in text


def test_readme_links_field_coverage():
    text = open(os.path.join(ROOT, "evidence-templates", "README.md"), encoding="utf-8").read()
    assert "field-coverage.md    which fields" in text
    assert "`field-coverage.md` lists every missing or wrong field" in text
