"""PR-22a docs checks (stdlib, Python 3.9). Run from the worktree root:

    $PY39 -m pytest -q -p no:cacheprovider tests/docs

The verb check reads prooflab.cli.VERBS when PR-01's dispatcher is importable (set
PYTHONPATH=<PR-01 worktree>:<this worktree> before PR-01 merges); otherwise it uses FALLBACK_VERBS.
"""
import hashlib
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# the one coupling to the dispatcher (PR-01): the verb names, mirrored here as a fallback
FALLBACK_VERBS = {"run", "query", "pack", "watch", "tail", "recheck", "register", "humanloop",
                  "assess", "collect", "console", "servicenow"}


def _verbs():
    try:
        from prooflab.cli import VERBS  # PR-01
        return set(VERBS)
    except Exception:
        return set(FALLBACK_VERBS)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf8") as f:
        return f.read()


def _section_a(text):
    a0 = text.index("## A. ServiceNow")
    a1 = text.index("\n---\n\n## B.")
    return text[a0:a1]


def _sha(s):
    return hashlib.sha256(s.encode("utf8")).hexdigest()


class FilesExist(unittest.TestCase):
    def test_files_exist_and_nonempty(self):
        for rel in ("evidence-templates/README.md", "evidence-templates/decisions-log.md",
                    "evidence-templates/named-runs.md", "evidence/adversarial/cases/ADV-H-01.md",
                    "evidence/adversarial/README.md", "gap-list.md"):
            p = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(p), rel)
            self.assertGreater(os.path.getsize(p), 200, rel)


class GapList(unittest.TestCase):
    def setUp(self):
        self.text = _read("gap-list.md")
        self.b = self.text[self.text.index("\n## B."):]

    def test_section_a_byte_identical_to_arths_source(self):
        src = _read("handoffs", "ifabric-handoff-3", "deliverables", "evidence-pack", "gap-list.md")
        a_src = src[src.index("## A. ServiceNow"):src.index("\n---\n\n## B.")]
        self.assertEqual(_sha(_section_a(self.text)), _sha(a_src))
        for n in range(1, 19):
            self.assertIn("**A%d. " % n, _section_a(self.text))

    def test_section_a_hash_matches_main_when_main_has_it(self):
        # main's gap-list.md carries no section A yet (PR-22a adds the merged file); when a later
        # main does, the sha256 of the section must be the same.
        main = os.environ.get("PROOFLAB_MAIN_GAPLIST")
        if not main or not os.path.isfile(main):
            self.skipTest("set PROOFLAB_MAIN_GAPLIST to main's gap-list.md to compare")
        with open(main, encoding="utf8") as f:
            m = f.read()
        if "## A. ServiceNow" not in m:
            self.skipTest("main has no section A yet")
        self.assertEqual(_sha(_section_a(self.text)), _sha(_section_a(m)))

    def test_gaps_1_to_11(self):
        for n in range(1, 12):
            self.assertRegex(self.b, r"(?m)^### %d\. " % n)
        for part in ("What's missing", "Impact", "If you had one more day"):
            self.assertGreaterEqual(self.b.count(part), 11)

    def test_rails_gaps_g1_to_g14(self):
        for n in range(1, 15):
            self.assertRegex(self.b, r"(?m)^\| G-%d \|" % n)

    def test_extra_section_b_entries(self):
        for needle in ("Adapter bug (a)", "Adapter bug (b)", "no subject CID", "at most 200 steps",
                       "Readiness records", "Design gaps"):
            self.assertIn(needle, self.b)

    def test_no_false_entry(self):
        self.assertNotIn("no durable exporter?", self.b)
        self.assertRegex(self.b, r"(?s)Dropped, on purpose.*no durable exporter")
        # no "ledger verification output" claim as a feature
        self.assertNotIn("verify-<date>.txt", self.text)


class Readme(unittest.TestCase):
    def setUp(self):
        self.text = _read("evidence-templates", "README.md")

    def test_commands_are_prooflab_verbs(self):
        cmds = re.findall(r"python3 -m prooflab (\S+)([^`\n]*)", self.text)
        self.assertGreaterEqual(len(cmds), 5)
        verbs = _verbs()
        for verb, rest in cmds:
            self.assertIn(verb, verbs, verb)
        joined = " ".join(v + r for v, r in cmds)
        for needle in ("--control C16 --run", "--window", "--incident", "--runs"):
            self.assertIn(needle, joined)

    def test_required_parts(self):
        t = self.text
        self.assertIn("python3 -m prooflab query --control C16 --run <CID>", t)
        self.assertIn("<WINDOW_START>", t)
        self.assertIn("manifest.py verify", t)
        self.assertIn("ADV-R-06", t)
        self.assertIn("What was left out, and why", t)

    def test_r2_r3_r4_r21_applied(self):
        t = self.text
        self.assertNotIn("verify-<date>", t)                      # R-2
        self.assertIn("no verification route", t)
        self.assertNotIn("ledger-recorded", t)                    # R-4
        self.assertIn("During fault resolution, the three collaborating agents", t)  # R-21
        self.assertNotIn("customer fault resolution", t)
        self.assertNotIn("drift and performance, and token-spend", t)


class DecisionsLog(unittest.TestCase):
    def setUp(self):
        self.text = _read("evidence-templates", "decisions-log.md")

    def test_all_ids_present(self):
        ids = ["D%d" % n for n in range(1, 24)] + ["DG-%d" % n for n in range(1, 8)] + \
              ["DC-%d" % n for n in range(1, 12)]
        for i in ids:
            self.assertRegex(self.text, r"\*\*%s\*\*" % re.escape(i), i)

    def test_format_and_captain_change(self):
        self.assertIn("| Date | Decision | Why | Who | Reference |", self.text)
        self.assertIn("2026-10-06 01:40Z", self.text)
        self.assertRegex(self.text, r"T2.*INTO Phase 1")

    def test_table_rows_have_five_columns(self):
        for line in self.text.splitlines():
            if line.startswith("| 20") or line.startswith("| ≤"):
                self.assertEqual(len(re.split(r"(?<!\\)\|", line.strip())) - 2, 5, line[:80])


class NamedRunsAndAdv(unittest.TestCase):
    def test_named_runs_columns(self):
        t = _read("evidence-templates", "named-runs.md")
        for col in ("control", "role", "attempt", "start (UTC)", "end (UTC)", "register version",
                    "control version", "mode", "condition", "incident"):
            self.assertIn(col, t)

    def test_adv_h_01(self):
        t = _read("evidence", "adversarial", "cases", "ADV-H-01.md")
        self.assertRegex(t, r"Pre-registered:\*\* 2026-10-06")
        for needle in ("Leg A", "Leg B", "BLOCKED_GUARDRAIL", "HELD", "DETECTED-ONLY", "BROKE", "Observed"):
            self.assertIn(needle, t)


class Hygiene(unittest.TestCase):
    def test_no_secret_shaped_literals(self):
        pats = [r"AKIA[0-9A-Z]{16}", r"ASIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{20,}", r"github_pat_",
                r"-----BEGIN [A-Z ]*PRIVATE KEY", r"sk-[A-Za-z0-9]{20,}", r"xox[a-z]-[A-Za-z0-9-]{10,}",
                r"Bearer [A-Za-z0-9._-]{20,}", "tk" + "n=", "aws_secret" + "_access_key",
                "aws_session" + "_token"]
        files = ["gap-list.md", "evidence-templates/README.md", "evidence-templates/decisions-log.md",
                 "evidence-templates/named-runs.md", "evidence/adversarial/cases/ADV-H-01.md",
                 "evidence/adversarial/README.md"]
        for f in files:
            t = _read(*f.split("/"))
            for p in pats:
                self.assertIsNone(re.search(p, t), (f, p))


if __name__ == "__main__":
    unittest.main()
