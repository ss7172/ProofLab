#!/usr/bin/env python3
"""Write ONE self-contained source file per ifabric- agent (ARCH 7.1; 05 AR-03; plan T3.3).

The kit's build (build-agent-image.sh) ships exactly one file, as gzip+base64 inside the CodeBuild
buildspec (cap 25,600 chars, fixed overhead 1,551 -> 24,049 chars for the source). This tool embeds
each vendored module (the c16 core, the contract, the runtime adapters, the shared trio app) as its
EXACT bytes in a string literal, served by an importlib finder that registers each module in
sys.modules before exec (work/13 R4), then appends the role's own source as the __main__ part.

  python3 tools/bundle_agent.py --role customer            # one role, default manifest
  python3 tools/bundle_agent.py --all                      # the trio
  python3 tools/bundle_agent.py --manifest m.json --src-root DIR --out-dir DIR

Gate: len(base64(gzip -9n(bundle))) <= 24,000 (the CI gate; 24,049 is the hard cap) or exit 3.
It prints and embeds the c16 core sha256 (evaluator.sha256), checked again by the bundle at load.
Standard library only; Python 3.9+.
"""
import argparse
import base64
import glob
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys

GATE_CHARS = 24000          # the CI gate (ARCH 7.1)
HARD_CAP_CHARS = 24049      # 25,600 - 1,551 buildspec overhead (05 AR-03)
CORE_PATH = "prooflab/evaluators/c16_core.py"
CORE_MODULE = "prooflab.evaluators.c16_core"
ROLES = ("customer", "it", "network")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FORBIDDEN_NAME = "agent" + ".py"   # never the kit's reference file name (ARCH 7.1)

# The runtime subset: what an agent imports at run time. Never the tester c16.py, never schema JSON.
# Each entry is repo-relative; a glob is allowed. "required" ones must exist; "optional" ones are
# embedded when present (PR-05 rails/egress, PR-07 j2 may land after Stage A).
DEFAULT_REQUIRED = [
    CORE_PATH,
    "prooflab/contract/__init__.py",
    "prooflab/contract/record.py",
    "prooflab/contract/transports.py",
    "prooflab/contract/verdicts.py",
    "prooflab/adapters/runtime/model_call.py",
    "prooflab/adapters/runtime/action_id.py",
    "prooflab/adapters/runtime/tally.py",
    "prooflab/adapters/runtime/hooks.py",
    "prooflab/adapters/runtime/emit_client.py",
    "prooflab/adapters/runtime/tool_call.py",
    "prooflab/adapters/runtime/judgment.py",
    "prooflab/adapters/runtime/startup.py",
]
DEFAULT_OPTIONAL = [
    "prooflab/contract/clocks.py",
    "prooflab/evaluators/__init__.py",
    "prooflab/adapters/__init__.py",
    "prooflab/adapters/runtime/__init__.py",
    "prooflab/adapters/runtime/rails.py",
    "prooflab/adapters/runtime/egress.py",
    "prooflab/adapters/runtime/j2.py",
]
# The shared trio app: one canonical copy (agents/ifabric-customer/ifabric_app.py), embedded as the
# module "ifabric_app" in every role's bundle. Paths below are relative to the AGENT root (--agents-root).
APP_PATH = "agents/ifabric-customer/ifabric_app.py"


def default_manifest(role):
    return {
        "role": role,
        "name": "ifabric-" + role,
        "required": list(DEFAULT_REQUIRED),
        "optional": list(DEFAULT_OPTIONAL),
        "extra_modules": {"ifabric_app": APP_PATH},
        "entry": "agents/ifabric-%s/role.py" % role,
    }


LOADER = '''# ---- generated loader (tools/bundle_agent.py): serves the embedded modules, byte-identical to the repo
import hashlib as _hl
import importlib.abc as _iabc
import importlib.util as _iu
import sys as _sys


class _BundleFinder(_iabc.MetaPathFinder, _iabc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name not in _SOURCES:
            return None
        pkg = name in _PACKAGES
        # A location so __file__ exists; importlib registers the module in sys.modules before exec,
        # which dataclasses need under `from __future__ import annotations` (work/13 R4).
        return _iu.spec_from_file_location(
            name, _ORIGIN + "/" + name.replace(".", "/") + ("/__init__.py" if pkg else ".py"),
            loader=self, submodule_search_locations=[] if pkg else None)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(_SOURCES[module.__name__], module.__file__, "exec"), module.__dict__)


_ORIGIN = "/app/_bundle"
for _n, _h in _SHA256.items():  # fail closed: an edited literal never runs
    if _hl.sha256(_SOURCES[_n].encode("utf-8")).hexdigest() != _h:
        raise SystemExit("ifabric bundle: embedded module %s does not match its recorded sha256" % _n)
EVALUATOR_SHA256 = _SHA256.get("''' + CORE_MODULE + '''")
_sys.meta_path.insert(0, _BundleFinder())
# ---- end of generated loader; the role source follows
'''


class BundleError(Exception):
    pass


def module_name(rel):
    parts = rel[:-3].split("/")
    return ".".join(parts[:-1]) if parts[-1] == "__init__" else ".".join(parts)


def _expand(src_root, pattern):
    if any(ch in pattern for ch in "*?["):
        found = sorted(glob.glob(os.path.join(src_root, pattern)))
        return [os.path.relpath(p, src_root).replace(os.sep, "/") for p in found]
    return [pattern] if os.path.isfile(os.path.join(src_root, pattern)) else []


def _read_utf8(path):
    data = open(path, "rb").read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise BundleError("%s is not UTF-8; it cannot be embedded byte-identically" % path)
    if text.encode("utf-8") != data:  # paranoia: round-trip must be exact
        raise BundleError("%s does not round-trip through UTF-8" % path)
    return text, data


def collect(manifest, src_root, agents_root):
    """Return (sources {module: text}, packages set, missing_optional list, synthesized list)."""
    sources, files, missing_opt = {}, {}, []
    for pattern in manifest.get("required", []):
        rels = _expand(src_root, pattern)
        if not rels:
            raise BundleError("required module missing: %s (under %s)" % (pattern, src_root))
        for rel in rels:
            files[module_name(rel)] = os.path.join(src_root, rel)
    for pattern in manifest.get("optional", []):
        rels = _expand(src_root, pattern)
        if not rels:
            missing_opt.append(pattern)
        for rel in rels:
            files[module_name(rel)] = os.path.join(src_root, rel)
    for mod, rel in sorted(manifest.get("extra_modules", {}).items()):
        path = os.path.join(agents_root, rel)
        if not os.path.isfile(path):
            raise BundleError("extra module %s missing: %s" % (mod, path))
        files[mod] = path
    for mod, path in files.items():
        if os.path.basename(path) == _FORBIDDEN_NAME:
            raise BundleError("refusing to embed a file named %s: %s" % (_FORBIDDEN_NAME, path))
        sources[mod] = _read_utf8(path)[0]
    if CORE_MODULE not in sources:
        raise BundleError("the c16 core (%s) is not in the manifest" % CORE_PATH)
    # Every dotted prefix is a package. A package marker absent from the tree is served as an EMPTY
    # module (never a non-empty guess); a present one is embedded byte-identically above.
    packages, synthesized = set(), []
    for mod in list(sources):
        parts = mod.split(".")
        for i in range(1, len(parts)):
            packages.add(".".join(parts[:i]))
    for mod, path in files.items():
        if path.endswith("__init__.py"):
            packages.add(mod)
    for pkg in sorted(packages):
        if pkg not in sources:
            sources[pkg] = ""
            synthesized.append(pkg)
    return sources, packages, missing_opt, synthesized


def render(sources, packages, entry_text, header):
    sha = dict((m, hashlib.sha256(t.encode("utf-8")).hexdigest()) for m, t in sorted(sources.items()))
    body = ["_SOURCES = {\n"]
    for mod in sorted(sources):
        body.append("    %r: %r,\n" % (mod, sources[mod]))
    body.append("}\n_SHA256 = {\n")
    for mod in sorted(sha):
        body.append("    %r: %r,\n" % (mod, sha[mod]))
    body.append("}\n_PACKAGES = %r\n" % sorted(packages))
    loader = LOADER.replace("_ORIGIN = ", "".join(body) + "_ORIGIN = ", 1)
    return header + loader + "\n" + entry_text


def gz_b64_len(text):
    """Measured exactly as build-agent-image.sh does: gzip -9nc | base64 | tr -d newline."""
    data = text.encode("utf-8")
    try:
        gz = subprocess.run(["gzip", "-9nc"], input=data, stdout=subprocess.PIPE, check=True).stdout
        how = "gzip -9n (subprocess)"
    except (OSError, subprocess.CalledProcessError):
        gz = gzip.compress(data, 9, mtime=0)
        how = "python gzip (fallback: no gzip binary)"
    return len(base64.b64encode(gz)), len(gz), how


def bundle(manifest, src_root=REPO, agents_root=REPO, out_dir=None, gate=GATE_CHARS, write=True):
    role = manifest["role"]
    name = manifest.get("name") or "ifabric-" + role
    if not re.match(r"^ifabric-[a-z][a-z0-9-]*$", name):
        raise BundleError("bundle name %r must be ifabric-<role>" % name)
    out_name = name + ".py"
    if out_name == _FORBIDDEN_NAME:
        raise BundleError("refusing output name %s" % out_name)
    entry_path = os.path.join(agents_root, manifest["entry"])
    if os.path.basename(entry_path) == _FORBIDDEN_NAME:
        raise BundleError("refusing an entry file named %s" % _FORBIDDEN_NAME)
    entry_text = _read_utf8(entry_path)[0]
    sources, packages, missing_opt, synthesized = collect(manifest, src_root, agents_root)
    core_sha = hashlib.sha256(open(os.path.join(src_root, CORE_PATH), "rb").read()).hexdigest()
    if hashlib.sha256(sources[CORE_MODULE].encode("utf-8")).hexdigest() != core_sha:
        raise BundleError("embedded c16 core differs from %s" % CORE_PATH)
    header = ("# %s: GENERATED by tools/bundle_agent.py; do not edit. One file per agent (ARCH 7.1).\n"
              "# evaluator.sha256 (prooflab/evaluators/c16_core.py) = %s\n" % (out_name, core_sha))
    text = render(sources, packages, entry_text, header)
    b64, gz, how = gz_b64_len(text)
    report = {
        "name": name, "file": out_name, "raw_bytes": len(text.encode("utf-8")), "gzip_bytes": gz,
        "gzip_base64_chars": b64, "measured_with": how, "gate": gate, "hard_cap": HARD_CAP_CHARS,
        "c16_core_sha256": core_sha, "modules": sorted(sources), "missing_optional": missing_opt,
        "synthesized_empty_packages": synthesized, "ok": b64 <= gate,
    }
    out_path = None
    if write and report["ok"]:
        out_dir = out_dir or os.path.join(agents_root, "agents", name)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, out_name)
        with open(out_path, "wb") as f:
            f.write(text.encode("utf-8"))
    report["out"] = out_path
    return report, text


def _load_manifest(path, role):
    if path:
        with open(path) as f:
            m = json.load(f)
        if role:
            m["role"] = role
        return m
    return default_manifest(role)


def main(argv=None):
    p = argparse.ArgumentParser(description="Bundle one ifabric- agent into one file (size-gated).")
    p.add_argument("--role", choices=ROLES)
    p.add_argument("--all", action="store_true", help="the trio")
    p.add_argument("--manifest", help="JSON manifest (default: built in)")
    p.add_argument("--src-root", default=REPO, help="where prooflab/ is (default: this repo)")
    p.add_argument("--agents-root", default=REPO, help="where agents/ is (default: this repo)")
    p.add_argument("--out-dir", help="default: <agents-root>/agents/ifabric-<role>/")
    p.add_argument("--gate", type=int, default=GATE_CHARS)
    p.add_argument("--no-write", action="store_true", help="measure only")
    p.add_argument("--json", action="store_true", help="print the reports as JSON")
    a = p.parse_args(argv)
    if a.gate > HARD_CAP_CHARS:
        p.error("--gate above the hard cap %d" % HARD_CAP_CHARS)
    roles = ROLES if a.all else ([a.role] if a.role else [])
    if not roles and not a.manifest:
        p.error("give --role, --all or --manifest")
    reports, rc = [], 0
    for role in roles or [None]:
        try:
            m = _load_manifest(a.manifest, role)
            r, _ = bundle(m, a.src_root, a.agents_root, a.out_dir, a.gate, write=not a.no_write)
        except BundleError as e:
            print("bundle_agent: %s" % e, file=sys.stderr)
            return 2
        reports.append(r)
        if not r["ok"]:
            rc = 3
        if not a.json:
            print("%s %s: raw=%d B gzip=%d B gzip+base64=%d chars (gate %d, hard cap %d; %s) "
                  "c16_core sha256=%s%s" % (
                      "OK  " if r["ok"] else "FAIL", r["name"], r["raw_bytes"], r["gzip_bytes"],
                      r["gzip_base64_chars"], r["gate"], r["hard_cap"], r["measured_with"],
                      r["c16_core_sha256"], "" if r["ok"] else "  OVER THE GATE: not written"))
            if r["missing_optional"]:
                print("     missing optional (not embedded): %s" % ", ".join(r["missing_optional"]))
            if r["synthesized_empty_packages"]:
                print("     empty package markers served: %s" % ", ".join(r["synthesized_empty_packages"]))
            if r["out"]:
                print("     wrote %s" % r["out"])
    if a.json:
        print(json.dumps(reports, indent=2))
    return rc


if __name__ == "__main__":
    sys.exit(main())
