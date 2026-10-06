"""PR-22b docs checks (stdlib, Python 3.9): run of show, security matrix, review templates."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf8") as f:
        return f.read()


class RunOfShow(unittest.TestCase):
    def test_timed_within_fifteen_minutes(self):
        t = _read("docs/run-of-show.md")
        rows = re.findall(r"(?m)^\| (\d+):(\d\d)-(\d+):(\d\d) \|", t)
        self.assertGreaterEqual(len(rows), 8)
        prev = 0
        for a, b, c, d in rows:
            s, e = int(a) * 60 + int(b), int(c) * 60 + int(d)
            self.assertEqual(s, prev)
            self.assertGreater(e, s)
            prev = e
        self.assertLessEqual(prev, 15 * 60)
        for needle in ("C-1", "C-3", "C-4", "C-5", "C-6", "ADV-R-06"):
            self.assertIn(needle, t)

    def test_one_sentence_per_screen(self):
        t = _read("docs/run-of-show.md")
        for line in t.splitlines():
            m = re.match(r"\| \d+:\d\d-\d+:\d\d \|(.*)\|$", line)
            if m:
                cells = [c.strip() for c in m.group(1).split("|")]
                self.assertEqual(len(cells), 4, line[:60])
                self.assertTrue(cells[-1], line[:60])


class SecurityMatrix(unittest.TestCase):
    def test_ep0_to_ep16(self):
        t = _read("evidence-templates/security-matrix.md")
        for n in range(0, 17):
            self.assertRegex(t, r"(?m)^\| EP-%d \|" % n)
        for line in t.splitlines():
            if line.startswith("| EP-"):
                self.assertEqual(len(line.strip().strip("|").split("|")), 7, line[:40])


class Templates(unittest.TestCase):
    def test_exist(self):
        for f in ("rehearsal.md", "gate-record.md", "independent-review.md"):
            self.assertGreater(len(_read("reviews/templates/" + f)), 200, f)

    def test_readme_pillars(self):
        t = _read("evidence-templates/README.md")
        self.assertIn("| Pillar |", t)
        for p in ("Close the gap", "Build a control", "Handover proof"):
            self.assertIn(p, t)

    def test_no_secret_shaped_literals(self):
        pats = ["AK" + "IA[0-9A-Z]{16}", "AS" + "IA[0-9A-Z]{16}", "gh" + "p_[A-Za-z0-9]{20,}",
                "s" + "k-[A-Za-z0-9]{20,}", "Bear" + "er [A-Za-z0-9._-]{20,}", "tk" + "n=",
                "aws_secret" + "_access_key", "aws_session" + "_token"]
        for f in ("docs/run-of-show.md", "evidence-templates/security-matrix.md",
                  "reviews/templates/rehearsal.md", "reviews/templates/gate-record.md",
                  "reviews/templates/independent-review.md"):
            for p in pats:
                self.assertIsNone(re.search(p, _read(f)), (f, p))


if __name__ == "__main__":
    unittest.main()
