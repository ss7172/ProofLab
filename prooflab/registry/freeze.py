"""`prooflab register freeze`: register + risks frozen as ONE version (ARCH §3.3 freeze steps 1 and 5, §3.9). Stdlib, 3.9.

    freeze(version, register_path, risks_path, out_dir) ->
        register/versions/<v>.yaml, <v>.sha256, <v>.risks.yaml, <v>.risks.sha256   (byte-for-byte copies)
        register/pins/<v>-<mode>.json + .sha256                                      (one per declared mode)

A version that already exists is refused (one key per version, never rewritten): the check covers every target before
anything is written. The sha256 is taken over the file BYTES. The S3 PUT (T1) and the ServiceNow approval (T2) are the
live lane's; this module writes only local files.
"""
from __future__ import annotations

import argparse
import os
import sys

from prooflab.contract import pin as _pin
from prooflab.contract import register as _reg
from prooflab.registry import parse as _parse
from prooflab.registry import pinned as _pinned


class FreezeError(ValueError):
    """The freeze is refused; nothing was written."""


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def sha_line(digest: str, name: str) -> str:
    return "%s  %s\n" % (digest, name)


def targets(version: str, out_dir: str) -> dict:
    v = os.path.join(out_dir, "versions")
    return {
        "register": os.path.join(v, "%s.yaml" % version),
        "register_sha": os.path.join(v, "%s.sha256" % version),
        "risks": os.path.join(v, "%s.risks.yaml" % version),
        "risks_sha": os.path.join(v, "%s.risks.sha256" % version),
        "pins": os.path.join(out_dir, "pins"),
    }


def validate_pair(version: str, reg_bytes: bytes, risks_bytes: bytes, superseded_bytes=None) -> list:
    """Every refusal reason for freezing this pair as `version` (empty list = freezable)."""
    errors = []
    try:
        reg = _parse.parse_register(reg_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return ["register.yaml does not parse: %s" % exc]
    try:
        risks = _parse.parse_risks(risks_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return ["risks.yaml does not parse: %s" % exc]
    errors += ["register: " + e for e in _reg.validate_register(reg)]
    if reg["top"].get("version") != version:
        errors.append("register top.version %r is not %r" % (reg["top"].get("version"), version))
    if risks["top"].get("version") != version:
        errors.append("risks top.version %r is not %r (risks freeze with the register)" % (risks["top"].get("version"), version))
    if risks["top"].get("version_date") != reg["top"].get("version_date"):
        errors.append("risks version_date differs from the register's (one version, one date)")
    if superseded_bytes is not None:
        old = _parse.parse_register(superseded_bytes.decode("utf-8"))
        errors += ["supersedes: " + e for e in _reg.check_version_bumps(old, reg)]
    if not errors:
        try:
            for mode in _pinned.declared_modes(reg):
                _pinned.pin_from_register(reg_bytes, mode)
        except _pin.PinError as exc:
            errors.append("pin: %s" % exc)
    return errors


def freeze(version: str, register_path: str, risks_path: str, out_dir: str, superseded_path=None) -> dict:
    reg_bytes, risks_bytes = _read(register_path), _read(risks_path)
    old = _read(superseded_path) if superseded_path else None
    errors = validate_pair(version, reg_bytes, risks_bytes, old)
    if errors:
        raise FreezeError("; ".join(errors))
    t = targets(version, out_dir)
    existing = [p for k, p in t.items() if k != "pins" and os.path.exists(p)]
    if existing or glob_pins(t["pins"], version):
        raise FreezeError("version %s already frozen (never rewritten): %s" % (version, ", ".join(existing) or "pins"))
    os.makedirs(os.path.dirname(t["register"]), exist_ok=True)
    reg_sha, risks_sha = _reg.register_sha256(reg_bytes), _reg.register_sha256(risks_bytes)
    for key, data in (("register", reg_bytes), ("risks", risks_bytes)):
        with open(t[key], "xb") as fh:
            fh.write(data)
    with open(t["register_sha"], "xb") as fh:
        fh.write(sha_line(reg_sha, "%s.yaml" % version).encode("utf-8"))
    with open(t["risks_sha"], "xb") as fh:
        fh.write(sha_line(risks_sha, "%s.risks.yaml" % version).encode("utf-8"))
    pin_files = _pinned.write_pins(version, reg_bytes, t["pins"])
    return {"version": version, "register_sha256": reg_sha, "risks_sha256": risks_sha,
            "files": [t["register"], t["register_sha"], t["risks"], t["risks_sha"]] + pin_files}


def glob_pins(pins_dir: str, version: str) -> list:
    if not os.path.isdir(pins_dir):
        return []
    return [n for n in os.listdir(pins_dir) if n.startswith(version + "-")]


def verify(version: str, out_dir: str) -> list:
    """Re-check a frozen version on disk: each .sha256 matches its file's bytes. Errors list, empty = OK."""
    t, errors = targets(version, out_dir), []
    for key, shakey in (("register", "register_sha"), ("risks", "risks_sha")):
        try:
            expect = _read(t[shakey]).decode("utf-8").split()[0]
            if _reg.register_sha256(_read(t[key])) != expect:
                errors.append("%s: sha256 does not match the file bytes" % t[key])
        except (OSError, IndexError) as exc:
            errors.append("%s: %s" % (t[key], exc))
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab register freeze")
    ap.add_argument("--version", required=True)
    ap.add_argument("--register", default="register/register.yaml")
    ap.add_argument("--risks", default="register/risks.yaml")
    ap.add_argument("--out", default="register", help="the register directory (versions/ and pins/ go under it)")
    ap.add_argument("--supersedes", help="the superseded frozen register file (checks the per-control version bumps)")
    ns = ap.parse_args(argv)
    try:
        result = freeze(ns.version, ns.register, ns.risks, ns.out, ns.supersedes)
    except (FreezeError, OSError) as exc:
        print("freeze refused: %s" % exc, file=sys.stderr)
        return 2
    print("frozen %s\n  register sha256 %s\n  risks    sha256 %s" % (result["version"], result["register_sha256"], result["risks_sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
