"""The AI inventory freeze (`inv-N`) and the register / risks / inventory cross-checks (ARCH §3.9, §3.10). Stdlib, 3.9.

    freeze_inventory("inv-1", inventory_path, out_dir)   # register/versions/inv-1.yaml + inv-1.sha256, never rewritten
    cross_check(register_doc, risks_doc, inventory_doc)  # the CI test of §3.9 and the scope rule of §3.10 -> errors

The inventory is off the path (no agent reads it); it is read by EP-0's preflight and by INV.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from prooflab.contract import register as _reg
from prooflab.registry import parse as _parse

INV_VERSION_RE = re.compile(r"^inv-[0-9]+$")
COMPONENT_REQUIRED = ("component_id", "kind", "owner", "approved_version", "approval_source", "declaration")
NON_CONTROL_REFS = ("ESC", "INV")  # a risk may name ESC (R-JDG) or the optional INV control (R-OWN); EP ids and register control refs are checked separately
EP_RE = re.compile(r"^EP-[0-9]+$")


class InventoryError(ValueError):
    """The inventory is refused; nothing was written."""


def validate_inventory(doc: dict) -> list:
    errors = []
    if doc.get("list_key") != "components":
        errors.append("list key must be 'components'")
    for k in ("version", "version_date", "owner"):
        if not (doc.get("top") or {}).get(k):
            errors.append("top.%s: required" % k)
    for e in doc.get("entries") or []:
        for k in COMPONENT_REQUIRED:
            if not e.get(k):
                errors.append("component %s.%s: required (every component has an owner and an approved version)" % (e.get("component_id"), k))
    return errors


def cross_check(register_doc: dict, risks_doc: dict, inventory_doc: dict) -> list:
    """§3.9: every control has a risk_ref that exists; every risk's controls name a register control, an EP id or ESC;
    §3.10: every component a risk names is inventoried; no control applies to a component declared out of scope or `control_scope: none` (the Assurance agent)."""
    errors = []
    risks = dict((r["risk_id"], r) for r in risks_doc["entries"])
    comps = dict((c["component_id"], c) for c in inventory_doc["entries"])
    refs = set(e.get("control_ref") for e in register_doc["entries"])
    for e in register_doc["entries"]:
        rr = e.get("risk_ref")
        if not rr:
            errors.append("control %s: no risk_ref" % e.get("control_ref"))
        elif rr not in risks:
            errors.append("control %s: risk_ref %s is not in risks.yaml" % (e.get("control_ref"), rr))
    for rid, r in risks.items():
        for c in _reg.as_list(r.get("controls", "")):
            if c not in refs and c not in NON_CONTROL_REFS and not EP_RE.match(c):
                errors.append("risk %s: controls names %r (no register control, EP id or ESC)" % (rid, c))
        for comp in _reg.as_list(r.get("components", "")):
            if comp not in comps:
                errors.append("risk %s: component %s is not in inventory.yaml" % (rid, comp))
    outside = set(c for c, e in comps.items() if e.get("in_scope") == "false" or e.get("control_scope") == "none")
    for e in register_doc["entries"]:
        for target in _reg.as_list(e.get("applies_to", "")):
            name = target.split("@", 1)[0]
            if name in outside:
                errors.append("control %s applies_to %s, which the inventory declares out of scope" % (e.get("control_ref"), name))
    return errors


def freeze_inventory(version: str, inventory_path: str, out_dir: str) -> dict:
    if not INV_VERSION_RE.match(version):
        raise InventoryError("inventory version must look like inv-<n>, got %r" % version)
    with open(inventory_path, "rb") as fh:
        data = fh.read()
    try:
        doc = _parse.parse_inventory(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InventoryError("inventory.yaml does not parse: %s" % exc)
    errors = validate_inventory(doc)
    if errors:
        raise InventoryError("; ".join(errors))
    vdir = os.path.join(out_dir, "versions")
    body, sha = os.path.join(vdir, version + ".yaml"), os.path.join(vdir, version + ".sha256")
    if os.path.exists(body) or os.path.exists(sha):
        raise InventoryError("%s already frozen (never rewritten)" % version)
    os.makedirs(vdir, exist_ok=True)
    digest = _reg.register_sha256(data)
    with open(body, "xb") as fh:
        fh.write(data)
    with open(sha, "xb") as fh:
        fh.write(("%s  %s.yaml\n" % (digest, version)).encode("utf-8"))
    return {"version": version, "sha256": digest, "files": [body, sha]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab register inventory")
    ap.add_argument("--version", required=True, help="inv-<n>")
    ap.add_argument("--inventory", default="register/inventory.yaml")
    ap.add_argument("--out", default="register")
    ns = ap.parse_args(argv)
    try:
        r = freeze_inventory(ns.version, ns.inventory, ns.out)
    except (InventoryError, OSError) as exc:
        print("inventory freeze refused: %s" % exc, file=sys.stderr)
        return 2
    print("frozen %s sha256 %s" % (r["version"], r["sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
