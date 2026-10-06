"""PR-48: the console renders the rule's date proof in three states (green / red / amber), executed in node."""
import json
import os
import re
import subprocess

import pytest

from prooflab.console import server as srv


def _render(rule):
    node = subprocess.run(["which", "node"], stdout=subprocess.PIPE).stdout.decode().strip()
    if not node:
        pytest.skip("node not installed")
    js = open(os.path.join(srv.STATIC_DIR, "app.js"), encoding="utf-8").read()
    hms = re.search(r"^const hms = .*$", js, re.M).group(0)
    fn = re.search(r"^function dateProof\(r\) \{.*?^\}", js, re.M | re.S).group(0)
    prog = "%s\n%s\nprocess.stdout.write(JSON.stringify(dateProof(%s)));" % (hms, fn, json.dumps(rule))
    out = subprocess.run([node, "-e", prog], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_proven_before_is_green_with_t1():
    text, tone = _render({"frozen_at": "2026-10-06T13:38:05Z", "date_before_scope": True,
                          "date_proof": {"state": "PROVEN_BEFORE", "t1_at": "2026-10-06T13:38:05Z"}})
    assert tone == "good" and text == "✓ dated before the scope (S3 T1 13:38:05Z)"


def test_proven_after_is_the_only_red_after():
    text, tone = _render({"frozen_at": "2026-10-06T14:00:00Z", "date_before_scope": False,
                          "date_proof": {"state": "PROVEN_AFTER", "t1_at": "2026-10-06T14:00:00Z"}})
    assert tone == "bad" and text.startswith("RULE DATED AFTER TEST")


@pytest.mark.parametrize("rule", [
    {"frozen_at": "2026-10-06T13:36:43Z", "date_before_scope": False,
     "date_proof": {"state": "NOT_PROVEN", "register_frozen_at": "2026-10-06T13:36:43Z"}},
    {"frozen_at": "2026-10-06T13:36:43Z", "date_before_scope": False},       # an answer from before PR-48
])
def test_not_proven_is_amber_never_after(rule):
    text, tone = _render(rule)
    assert tone == "warn" and "date proof not in this pack" in text and "13:36:43Z (unproven)" in text
    assert "AFTER" not in text


def test_app_js_has_no_unconditional_after():
    js = open(os.path.join(srv.STATIC_DIR, "app.js"), encoding="utf-8").read()
    assert 'r.date_before_scope ? spill("✓ dated before the scope", "good") : spill("RULE DATED AFTER TEST"' not in js
    assert js.count("RULE DATED AFTER TEST") == 1
