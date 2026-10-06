"""AT-11 (09-BUILD-ORDER): no threshold literal in evaluators/adapters/agents. The authoritative check is tools/gate.sh
(check_threshold_literals, itself tested by tests/gate/test_gate.py). This thin wrapper carries the name the plan cites
and applies the same pattern directly (it must not call gate.sh: the gate runs this directory's pytest)."""
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAT = re.compile(r"(cap|limit|threshold|ceiling)[a-z0-9_]*\s*(:[^=#]*)?=\s*-?[0-9]", re.I)
NOT_ASSIGN = re.compile(r"[=!<>]=\s*-?[0-9]")


def test_repo_root_resolves_to_real_tree():
    # guards against a wrong REPO depth silently scanning nothing
    assert os.path.isdir(os.path.join(REPO, "prooflab", "evaluators"))
    assert os.path.isdir(os.path.join(REPO, "prooflab", "adapters"))


def test_pattern_catches_planted_literal():
    assert PAT.search("    cap_tokens = 5000") and not NOT_ASSIGN.search("    cap_tokens = 5000")


def test_no_threshold_literal_in_evaluators_adapters_agents():
    hits = []
    for top in ("evaluators", "adapters", "agents", "prooflab/evaluators", "prooflab/adapters", "prooflab/agents"):
        for dp, dn, fn in os.walk(os.path.join(REPO, top)):
            for f in fn:
                if f.endswith(".py"):
                    p = os.path.join(dp, f)
                    for n, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                        if PAT.search(line) and not NOT_ASSIGN.search(line):
                            hits.append("%s:%d" % (os.path.relpath(p, REPO), n))
    assert hits == []
