import hashlib
import os
import re
import subprocess
import unittest

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "policies", "cedar")


def rd(n):
    with open(os.path.join(D, n), "rb") as f:
        return f.read()


def forbid_text():
    t = rd("customer-records.forbid-site-adv.cedar").decode()
    t = "\n".join(l for l in t.splitlines() if not l.strip().startswith("//"))
    i = t.index("forbid")
    return t[i:]


class T(unittest.TestCase):
    def test_restore_is_original(self):
        self.assertEqual(rd("customer-records.restore.cedar"), rd("customer-records.original.cedar"))

    def test_forbid_is_additive(self):
        o = rd("customer-records.original.cedar")
        self.assertTrue(rd("customer-records.forbid-site-adv.cedar").startswith(o))

    def test_attribute_refs_have_guards(self):
        f = forbid_text()
        for attr in re.findall(r"context\.(\w+)", f):
            first = f.index("context." + attr)
            guard = f.find("context has " + attr)
            self.assertTrue(0 <= guard < first, attr)
        # nested: arguments.site guarded before use
        self.assertLess(f.index("arguments has site"), f.index("arguments.site like"))

    def test_forbid_only_site_adv(self):
        f = forbid_text()
        self.assertEqual(f.count("forbid"), 1)
        self.assertEqual(re.findall(r'like\s+"([^"]*)"', f), ["SITE-ADV-*"])
        self.assertNotIn("permit", f)
        self.assertNotIn("unless", f)

    def test_sha256sums(self):
        for line in rd("SHA256SUMS").decode().splitlines():
            h, n = line.split(None, 1)
            self.assertEqual(hashlib.sha256(rd(n.strip().lstrip("*"))).hexdigest(), h)
        r = subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=D, capture_output=True)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
