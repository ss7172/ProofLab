"""PR-49 fix round: the lint runs on the pack shape main's build produces (PR-47 / PR-48), not only the old prelim
shape. A regression test builds a pack with PR-47's own fixture (tests/pack_build/test_pack_complete.py build_src +
`prooflab pack build --label final`) and runs the REAL lint on it; then targeted cases for R2 / R4 / R5 on that shape:
  - the whole register chain (pilot registers included) ships under register/versions/ (date_proof reads there);
  - pack-index register.versions[N].approval is per version; an EXPLORATORY pilot register honestly has none;
  - pack-index runs[] lists EVERY run with its provenance (EXPLORATORY pilots / warm-ups, ASSESSED named runs).
"""
import importlib.util
import json
import os
import shutil

import pytest

from prooflab.pack import redflag

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SPEC = importlib.util.spec_from_file_location(
    "pr47_pack_fixture", os.path.join(REPO, "tests", "pack_build", "test_pack_complete.py"))
PR47 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(PR47)


def _flags(root):
    return [f for f in redflag.lint(str(root))]


def _edit(root, rel, fn):
    path = os.path.join(str(root), *rel.split("/"))
    with open(path) as fh:
        doc = json.load(fh)
    fn(doc)
    with open(path, "w") as fh:
        json.dump(doc, fh)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """(src, pack) built by main's own `prooflab pack build --label final` from PR-47's fixture."""
    base = tmp_path_factory.mktemp("main_shape")
    src = PR47.build_src(str(base / "src"))
    p, out = PR47._build(src, base, "--label", "final")
    assert p.returncode == 0, p.stdout
    return src, out


@pytest.fixture
def pack(built, tmp_path):
    dst = str(tmp_path / "pack")
    shutil.copytree(built[1], dst)
    return dst


def test_main_built_pack_has_only_the_flags_the_fixture_earns(built):
    # The one flag the fixture earns: README section 5 names derived/corroboration/, which PR-47's minimal fixture
    # does not ship (a real pack does). Pilot registers under register/versions/, the EXPLORATORY v0-pilot4 with no
    # approval, pilots and the warm-up in runs[]: none of those is a red flag.
    lines = sorted(f.line() for f in _flags(built[1]))
    assert [(f.rule, f.text) for f in _flags(built[1])] == [("R7", "derived/corroboration/")], "\n".join(lines)


def test_main_built_pack_with_corroboration_is_clean(built, tmp_path):
    src = str(tmp_path / "src")
    shutil.copytree(built[0], src)
    os.makedirs(os.path.join(src, "derived", "corroboration"))
    with open(os.path.join(src, "derived", "corroboration", "mismatches.jsonl"), "w") as fh:
        fh.write("")
    p, out = PR47._build(src, tmp_path, "--label", "final")
    assert p.returncode == 0, p.stdout
    assert _flags(out) == [], "\n".join(f.line() for f in _flags(out))
    assert redflag.main([out]) == 0


# ---------------------------------------------------------------- R2 on the per-version shape
def test_r2_names_the_hit_s_own_version(pack):
    # v1 (FROZEN, approved on INC0000321, its finding in register/approval/) shown MISSING: FALSE, about v1, not v1.1
    def mut(d):
        d["register"]["versions"][1]["approval"] = {"status": "MISSING"}
    _edit(pack, "pack-index.json", mut)
    r2 = [f for f in _flags(pack) if f.rule == "R2"]
    assert len(r2) == 1 and "register.versions[1]" in r2[0].file
    assert "FALSE: approval evidence for v1 is in the pack" in r2[0].hint and "v1.1" not in r2[0].hint


def test_r2_exploratory_pilot_register_without_approval_is_not_flagged(pack):
    idx = json.load(open(os.path.join(pack, "pack-index.json")))
    v0 = [v for v in idx["register"]["versions"] if v["version"] == "v0-pilot4"][0]
    assert v0["approval"]["status"] == "MISSING"          # PR-47 says so honestly
    assert [f for f in _flags(pack) if f.rule == "R2"] == []


def test_r2_frozen_version_missing_with_no_evidence_is_flagged_as_omitted(pack):
    shutil.rmtree(os.path.join(pack, "register", "approval"))
    for n in os.listdir(os.path.join(pack, "servicenow", "export")):
        os.remove(os.path.join(pack, "servicenow", "export", n))

    def mut(d):
        d["register"]["versions"][1]["approval"] = {"status": "MISSING"}
    _edit(pack, "pack-index.json", mut)
    r2 = [f for f in _flags(pack) if f.rule == "R2"]
    assert len(r2) == 1 and "approval evidence for v1 is omitted" in r2[0].hint


# ---------------------------------------------------------------- R4 on main's register layout
def test_r4_accepts_the_whole_chain_under_register_versions(pack):
    assert os.path.exists(os.path.join(pack, "register", "versions", "v1.yaml"))
    assert os.path.exists(os.path.join(pack, "register", "versions", "v0-pilot4.yaml"))   # status EXPLORATORY
    assert [f for f in _flags(pack) if f.rule == "R4"] == []


def test_r4_still_flags_a_shown_register_that_is_not_the_head(pack):
    _edit(pack, "pack-index.json", lambda d: d["register"].update(version="v1"))
    r4 = [f for f in _flags(pack) if f.rule == "R4"]
    assert any("head of the frozen chain is v1.1" in f.hint for f in r4)


# ---------------------------------------------------------------- R5 on runs[] with provenance
def test_r5_pilots_and_warm_up_in_runs_are_honest_entries(pack):
    runs = json.load(open(os.path.join(pack, "pack-index.json")))["runs"]
    assert {r["provenance"] for r in runs} == {"EXPLORATORY", "ASSESSED"}
    assert [f for f in _flags(pack) if f.rule == "R5"] == []


def test_r5_named_run_shown_as_exploratory_is_flagged(pack):
    def mut(d):
        for r in d["runs"]:
            if r["cid"] == PR47.NAMED:
                r["provenance"] = "EXPLORATORY"
    _edit(pack, "pack-index.json", mut)
    assert any(PR47.NAMED in f.text and "EXPLORATORY" in f.text for f in _flags(pack) if f.rule == "R5")


def test_r5_pilot_with_verdicts_and_unlabelled_failure_are_flagged(pack):
    def mut(d):
        for r in d["runs"]:
            if r["cid"] == PR47.PILOT_OK:
                r["verdicts"] = {"C16": "SATISFIED"}
            if r["cid"] == PR47.PILOT_FAIL:
                r.pop("failure_class", None)
                r["purpose"] = "pilot P1b"
    _edit(pack, "pack-index.json", mut)
    texts = [f.text for f in _flags(pack) if f.rule == "R5"]
    assert any(PR47.PILOT_OK in t for t in texts) and any("%s state FAILED" % PR47.PILOT_FAIL in t for t in texts)


def test_r5_run_with_no_declared_role_anywhere_is_flagged(pack):
    def mut(d):
        for r in d["runs"]:
            if r["cid"] == PR47.WARM:
                r["provenance"] = ""
    _edit(pack, "pack-index.json", mut)
    assert any(PR47.WARM in f.text for f in _flags(pack) if f.rule == "R5")
