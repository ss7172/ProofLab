"""Evidence Pack builder (PR-21): stage the ARCH 9.1 tree, redact, scan, write MANIFEST.json.

  python3 -m prooflab pack build --out <dir> [--src <tree>] [--workdir <dir>] ...
  python3 -m prooflab pack scan <dir>          # exact-value scan only (exit 1 on any hit)
  python3 -m prooflab pack verify <dir>        # manifest.py verify

Exact-value scan values are injected by the caller: PROOFLAB_SCAN_VALUES (one value per
line) or --scan-values-stdin. This module never reads a secret file. A scan hit reports the
file and a count, never the value. Standard library only; Python 3.9.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys

PACK_TOP = ("store", "raw", "derived", "assessments", "register", "kit-crosscheck",
            "reviews", "servicenow", "adversarial", "answers", "architecture",
            "window.json", "live-lane-log.jsonl", "security-matrix.md", "pack-index.json")
WORKDIR_FILES = ("register.yaml", "gap-list.md", "run-ids.txt", "sketch.png")
STAGED_FROM_WORKDIR = ("gap-list.md", "run-ids.txt", "sketch.png")
# The three CR token paths (ARCH 9.3): never in the pack.
DROP_ANNOTATIONS = ("kubectl.kubernetes.io/last-applied-configuration",
                    "kopf.zalando.org/last-handled-configuration")
MIN_VALUE_LEN = 6
_IGNORE = ("__pycache__", "tests", ".pytest_cache")


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _copy(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copyfile(src, dst)


def _load_manifest_tool():
    """Arth's tools/manifest.py, by path (one import site)."""
    cands = [os.environ.get("PROOFLAB_MANIFEST_PY", ""),
             os.path.join(_repo_root(), "tools", "manifest.py")]
    for c in cands:
        if c and os.path.isfile(c):
            spec = importlib.util.spec_from_file_location("_pl_manifest", c)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit("pack: tools/manifest.py not found (set PROOFLAB_MANIFEST_PY)")


def _load_redactor():
    """PR-12a's prooflab.store.redact when merged; None otherwise (one import site)."""
    try:
        from prooflab.store import redact  # type: ignore
        fn = getattr(redact, "redact_tree", None)
        return fn
    except Exception:
        return None


def _strip(obj):
    """Drop the three CR token paths wherever they occur; return True when changed."""
    changed = False
    if isinstance(obj, dict):
        for k in list(obj):
            if k in DROP_ANNOTATIONS:
                del obj[k]
                changed = True
            elif k == "environmentVariables" and isinstance(obj[k], dict):
                del obj[k]
                changed = True
            else:
                changed = _strip(obj[k]) or changed
    elif isinstance(obj, list):
        for v in obj:
            changed = _strip(v) or changed
    return changed


def builtin_redact(root):
    """Fallback redaction of the three CR token paths in every .json file; returns dropped files."""
    touched = []
    for d, _, names in os.walk(root):
        for n in names:
            if not n.endswith(".json"):
                continue
            p = os.path.join(d, n)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (ValueError, OSError):
                continue
            if _strip(data):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, sort_keys=True)
                    f.write("\n")
                touched.append(os.path.relpath(p, root))
    return sorted(touched)


def read_scan_values(stdin=False):
    raw = os.environ.get("PROOFLAB_SCAN_VALUES", "")
    if stdin:
        raw += "\n" + sys.stdin.read()
    return sorted({v.strip() for v in raw.splitlines() if len(v.strip()) >= MIN_VALUE_LEN})


def scan_tree(root, values):
    """Exact-value scan; returns [(relative path, hit count)]. Never returns a value."""
    needles = [v.encode("utf-8") for v in values if v]
    hits = []
    for d, _, names in os.walk(root):
        for n in names:
            p = os.path.join(d, n)
            if os.path.islink(p):
                continue
            with open(p, "rb") as f:
                blob = f.read()
            c = sum(blob.count(x) for x in needles)
            if c:
                hits.append((os.path.relpath(p, root), c))
    return sorted(hits)


def _stage(out, a):
    warnings = []
    src = a.src
    if src:
        for name in PACK_TOP:
            s = os.path.join(src, name)
            if os.path.exists(s):
                _copy(s, os.path.join(out, name))
    wd = a.workdir
    if wd:
        for name in STAGED_FROM_WORKDIR:
            s = os.path.join(wd, name)
            if os.path.isfile(s):
                _copy(s, os.path.join(out, name))
            elif name != "sketch.png":
                warnings.append("workdir has no " + name)
        reg = os.path.join(wd, "register.yaml")
        vdir = os.path.join(out, "register", "versions")
        if os.path.isfile(reg):
            same = False
            if os.path.isdir(vdir):
                with open(reg, "rb") as f:
                    b = f.read()
                for n in os.listdir(vdir):
                    if n.endswith(".yaml"):
                        with open(os.path.join(vdir, n), "rb") as g:
                            same = same or g.read() == b
            if not same:
                if os.path.isdir(vdir):
                    warnings.append("register.yaml is not byte-identical to any register/versions/*.yaml")
                else:
                    _copy(reg, os.path.join(vdir, "register.yaml"))
        else:
            warnings.append("workdir has no register.yaml")
    readme = a.readme or os.path.join(_repo_root(), "evidence-templates", "README.md")
    if os.path.isfile(readme):
        _copy(readme, os.path.join(out, "README.md"))
    else:
        with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Evidence Pack\n\nREADME template missing at build time; see the gap list.\n")
        warnings.append("README template missing: stub written")
    tool = a.tool_src or os.path.join(_repo_root(), "prooflab")
    if os.path.isdir(tool):
        shutil.copytree(tool, os.path.join(out, "prooflab"),
                        ignore=shutil.ignore_patterns(*_IGNORE, "*.pyc"))
    else:
        warnings.append("tool source not found: " + tool)
    for sub in ("store", "raw", "derived", "assessments", "register"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    return warnings


def cmd_build(argv):
    p = argparse.ArgumentParser(prog="prooflab pack build")
    p.add_argument("--out", required=True)
    p.add_argument("--src", help="tree holding store/ raw/ derived/ assessments/ register/ ...")
    p.add_argument("--workdir", help="dir with register.yaml gap-list.md run-ids.txt sketch.png")
    p.add_argument("--readme")
    p.add_argument("--tool-src")
    p.add_argument("--scan-values-stdin", action="store_true")
    a = p.parse_args(argv)
    out = os.path.abspath(a.out)
    if os.path.exists(out) and os.listdir(out):
        print("pack: refusing a non-empty --out " + out, file=sys.stderr)
        return 2
    os.makedirs(out, exist_ok=True)
    warnings = _stage(out, a)
    redactor = _load_redactor()
    if redactor:
        redactor(out)
    dropped = builtin_redact(out)
    hits = scan_tree(out, read_scan_values(a.scan_values_stdin))
    for w in warnings:
        print("warning: " + w)
    if dropped:
        print("redacted token paths in: " + ", ".join(dropped))
    if hits:
        for rel, c in hits:
            print("SCAN HIT: %s (%d)" % (rel, c), file=sys.stderr)
        print("pack: exact-value scan not clean; MANIFEST.json not written", file=sys.stderr)
        return 1
    m = _load_manifest_tool()
    manifest = m.build_manifest(out)
    print("OK: staged %d files in %s; exact-value scan: 0 hits" % (len(manifest["files"]), out))
    return 0


def cmd_scan(argv):
    if len(argv) != 1:
        print("usage: pack scan <dir> (values in PROOFLAB_SCAN_VALUES)", file=sys.stderr)
        return 2
    hits = scan_tree(argv[0], read_scan_values())
    for rel, c in hits:
        print("SCAN HIT: %s (%d)" % (rel, c), file=sys.stderr)
    print("exact-value scan: %d hit(s)" % sum(c for _, c in hits))
    return 1 if hits else 0


def cmd_verify(argv):
    if len(argv) != 1:
        print("usage: pack verify <dir>", file=sys.stderr)
        return 2
    return _load_manifest_tool().main(["verify", argv[0]])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("build", "scan", "verify"):
        verb, rest = argv[0], argv[1:]
    else:
        verb, rest = "build", argv
    return {"build": cmd_build, "scan": cmd_scan, "verify": cmd_verify}[verb](rest)


if __name__ == "__main__":
    sys.exit(main())
