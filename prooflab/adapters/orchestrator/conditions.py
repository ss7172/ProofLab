"""Frozen condition texts and fault declarations (B-G7). The register lists each text's sha256."""
from __future__ import annotations

import os

from prooflab.adapters.orchestrator import common

CONDITIONS = ("prompt-attack", "encoded-attack", "tool-directive", "conflicting-context")
# Text-free run conditions: nothing is appended to the prompt. `warm-up` (ARCH 5.3, B13): the one unassessed
# invocation per updated runtime before N7/N8/N9 (provenance EXPLORATORY; C9 never assesses it).
PLAIN_CONDITIONS = ("warm-up",)
FAULT_KINDS = {"inject-tool-output": 3, "suppress-record": 3}   # number of ':' parts after the kind


def conditions_dir(root=None) -> str:
    return os.path.join(root or common.REPO_ROOT, "register", "conditions")


def load_condition(name: str, root=None) -> dict:
    """{name, path, sha256, text}; the sha256 comes from the file bytes AND must equal SHA256SUMS."""
    if name in (None, "", "none"):
        return {"name": "none", "path": None, "sha256": None, "text": ""}
    if name in PLAIN_CONDITIONS:
        return {"name": name, "path": None, "sha256": None, "text": ""}
    if name not in CONDITIONS:
        raise ValueError("unknown condition %r (known: %s)" % (name, ", ".join(CONDITIONS)))
    directory = conditions_dir(root)
    path = os.path.join(directory, name + ".txt")
    digest = common.sha256_file(path)
    sums = os.path.join(directory, "SHA256SUMS")
    if os.path.exists(sums):
        listed = {}
        with open(sums, "r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) == 2:
                    listed[parts[1].lstrip("*")] = parts[0]
        if listed.get(name + ".txt") != digest:
            raise ValueError("condition %s: file sha256 differs from SHA256SUMS (frozen text changed)" % name)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    return {"name": name, "path": os.path.relpath(path, root or common.REPO_ROOT), "sha256": digest, "text": text}


def parse_fault(spec: str, root=None) -> dict:
    """`inject-tool-output:<agent>:<tool>:<fixture>` or `suppress-record:<agent>:<event>:<n>` -> envelope block."""
    if not spec:
        return None
    parts = spec.split(":")
    kind = parts[0]
    if kind not in FAULT_KINDS or len(parts) != FAULT_KINDS[kind] + 1:
        raise ValueError("fault must look like inject-tool-output:<agent>:<tool>:<fixture> "
                         "or suppress-record:<agent>:<event>:<n>, got %r" % (spec,))
    out = {"kind": kind, "agent": parts[1], "spec": spec}
    if kind == "inject-tool-output":
        out["tool"], out["fixture"] = parts[2], parts[3]
        path = os.path.join(conditions_dir(root), parts[3] + ".txt")   # register/conditions/<fixture>.txt
        out["fixture_sha256"] = common.sha256_file(path) if os.path.exists(path) else None
        out["fixture_path"] = os.path.relpath(path, root or common.REPO_ROOT)
        if out["fixture_sha256"]:   # the agent appends these bytes (it has no repo); it re-checks the sha256
            with open(path, "rb") as fh:
                out["fixture_text"] = fh.read().decode("utf-8")
    else:
        out["event"], out["count"] = parts[2], parts[3]
    return out
