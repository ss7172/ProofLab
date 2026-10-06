"""D9 (inventory under register/versions/inv-*.yaml) and D11 (a register dated after the run is not a clean answer)."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prooflab.query import engine as E  # noqa: E402


def test_inventory_glob_includes_versions(tmp_path):
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    (tmp_path / "register" / "versions").mkdir(parents=True)
    shutil.copy(os.path.join(repo, "register", "inventory.yaml"), str(tmp_path / "register" / "versions" / "inv-1.yaml"))
    name, doc = E._inventory(E.Pack(str(tmp_path)))
    assert name == "inv-1" and doc is not None
