"""PR-39: the committed pilot artifacts are byte-identical to what the ops lane froze and uploaded (T1)."""
import hashlib
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "register")
T1 = {"versions/v0-pilot.yaml": "0db68e6612be985eda75eeb21141623625fca1dfd725bd67d3c16675d54b2fdb",
      "versions/v0-pilot.risks.yaml": "3ebe051617fdb86e345bd70cae404fce02cb577c59a29ad772fb2313fa9b9957",
      "versions/inv-1.yaml": "807cccc3510412eddd9238d38a2688f3db5a5cd008f88546eed20a1eb3c9bc78",
      "experiments/plan.md": "497f9cec3fd8dfcc2f8b37cb089a03f5b633b2edf498434060e8d938041b49ab",
      "experiments/rules.json": "bfece3ad92b37c9a00a0182459402e3a1b96d4e223ac12cd0383d3fc9f7d8904",
      "pins/v0-pilot-observe.json": "a9b115f5c3dc72c45a3d8bcef2d6a10ec6bfc30d20940520525a32102d9604dd"}


def _sha(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def test_t1_checksums():
    for rel, want in T1.items():
        assert _sha(rel) == want, rel


def test_sidecar_sha256_files_match_their_artifacts():
    for rel in ("versions/v0-pilot", "versions/v0-pilot.risks", "versions/inv-1", "pins/v0-pilot-observe"):
        side = os.path.join(ROOT, rel + ".sha256")
        with open(side) as fh:
            want, name = fh.read().split()
        art = os.path.join(os.path.dirname(side), name)
        assert os.path.isfile(art), art
        with open(art, "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == want, rel


def test_scenarios_and_experiments_present_and_free_of_account_ids():
    import re
    for rel in ("scenarios/S1.json", "scenarios/S2.json", "scenarios/S3.json", "experiments/experiments.jsonl",
                "experiments/rules-adoption.md"):
        with open(os.path.join(ROOT, rel), "rb") as fh:
            data = fh.read()
        assert data and not re.search(rb"(?<![0-9])[0-9]{12}(?![0-9])", data), rel
