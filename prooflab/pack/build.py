"""Evidence Pack builder (PR-21): stage the ARCH 9.1 tree, redact, scan, write MANIFEST.json.

  python3 -m prooflab pack build --out <dir> [--src <tree>] [--workdir <dir>] ...
  python3 -m prooflab pack scan <dir>          # exact-value scan only (exit 1 on any hit); with no injected values
                                               #   it runs the pre-push scan script (RESULT: clean required)
  python3 -m prooflab pack index <dir>         # (re)project pack-index.json into an UNSEALED pack dir
  python3 -m prooflab pack verify <dir>        # manifest.py verify
  python3 -m prooflab pack root ...            # root published (unsigned): MANIFEST sha256 to ServiceNow (PR-32)

Exact-value scan values are injected by the caller: PROOFLAB_SCAN_VALUES (one value per
line) or --scan-values-stdin. This module never reads a secret file. With none injected, `pack scan` delegates to
`bash $PROOFLAB_PREPUSH_SCAN <dir>` (default ~/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh,
which loads the exact values itself) and needs its `RESULT: clean` line. A scan hit reports the
file and a count, never the value. Standard library only; Python 3.9.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys

PACK_TOP = ("store", "raw", "derived", "assessments", "findings", "register", "kit-crosscheck",
            "reviews", "servicenow", "adversarial", "answers", "architecture", "records", "runs", "auditor", "gaps",
            "window.json", "live-lane-log.jsonl", "security-matrix.md", "pack-index.json", "t1",
            "named-runs.md", "decisions-log.md", "closures", "field-coverage.md")
WORKDIR_FILES = ("register.yaml", "gap-list.md", "run-ids.txt", "sketch.png")
STAGED_FROM_WORKDIR = ("gap-list.md", "run-ids.txt", "sketch.png")
# Files the README names: from --src or --workdir when there, else the checked-in copy (said so in a warning).
README_DOCS = ("named-runs.md", "decisions-log.md", "security-matrix.md")
# The three CR token paths (ARCH 9.3): never in the pack.
DROP_ANNOTATIONS = ("kubectl.kubernetes.io/last-applied-configuration",
                    "kopf.zalando.org/last-handled-configuration")
MIN_VALUE_LEN = 6
TEAM_NAME = "ifabric"                      # the submission record's team name (PR-34); tools/submit_wrapper.sh mirrors it
KEY_PREFIX = "submissions/" + TEAM_NAME + "/"
_IGNORE = ("__pycache__", "tests", ".pytest_cache")


class DraftRegister(Exception):
    """register.yaml matches no frozen version: never present it as frozen (PR-34)."""


class SketchMissing(Exception):
    """sketch.png is a deliverable (R-J-44): the build fails loudly rather than ship a pack without it."""


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _copy(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copyfile(src, dst)


def _manifest_path():
    for c in (os.environ.get("PROOFLAB_MANIFEST_PY", ""), os.path.join(_repo_root(), "tools", "manifest.py")):
        if c and os.path.isfile(c):
            return c
    return None


def _load_manifest_tool():
    """Arth's tools/manifest.py, by path (one import site)."""
    c = _manifest_path()
    if c:
        spec = importlib.util.spec_from_file_location("_pl_manifest", c)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    raise SystemExit("pack: tools/manifest.py not found (set PROOFLAB_MANIFEST_PY)")


def _is_bytecode(rel):
    parts = rel.replace("\\", "/").split("/")
    return "__pycache__" in parts or rel.endswith(".pyc")


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


def _redact_json_file(p):
    """Returns (changed, parsed_ok)."""
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return False, False
    if _strip(data):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        return True, True
    return False, True


def _redact_jsonl_file(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
    except (ValueError, OSError):
        return False, False
    changed, ok = False, True
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        try:
            obj = json.loads(ln)
        except ValueError:
            ok = False
            continue
        if _strip(obj):
            lines[i] = json.dumps(obj, sort_keys=True)
            changed = True
    if changed:
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    return changed, ok


def builtin_redact(root):
    """Fallback redaction of the three CR token paths in .json and .jsonl files.

    Returns (touched files, errors). Fail closed: a file under raw/cr-status/ that cannot be
    parsed and redacted, or any other file under raw/ that is not json/jsonl yet names one of
    the token paths, is an error (the build must not continue).
    """
    touched, errors = [], []
    for d, _, names in os.walk(root):
        for n in names:
            p = os.path.join(d, n)
            rel = os.path.relpath(p, root)
            parts = rel.split(os.sep)
            in_cr = parts[:2] == ["raw", "cr-status"]
            in_raw = parts[0] == "raw"
            if n.endswith(".json"):
                changed, ok = _redact_json_file(p)
            elif n.endswith(".jsonl"):
                changed, ok = _redact_jsonl_file(p)
            else:
                changed, ok = False, True
                if in_raw:
                    try:
                        with open(p, "rb") as f:
                            blob = f.read()
                    except OSError:
                        blob = b""
                    marked = any(a.encode() in blob for a in DROP_ANNOTATIONS)
                    if in_cr or marked:
                        ok = False
            if changed:
                touched.append(rel)
            if not ok and (in_cr or in_raw):
                errors.append(rel)
    return sorted(touched), sorted(errors)


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


NO_FROZEN_NOTE = ("# No version frozen\n\nThe register in this pack is a DRAFT: it is not byte-identical to any "
                  "frozen version, so nothing under register/versions/ is a frozen register. Read "
                  "register/draft/ as a draft.\n")


def _frozen_match(reg, vdir):
    """True when reg is byte-identical to a register/versions/*.yaml file."""
    if not os.path.isdir(vdir):
        return False
    with open(reg, "rb") as f:
        b = f.read()
    for n in os.listdir(vdir):
        if n.endswith(".yaml"):
            with open(os.path.join(vdir, n), "rb") as g:
                if g.read() == b:
                    return True
    return False


def _precheck_register(a):
    """Refuse (before staging anything) an unfrozen register.yaml unless --allow-draft-register."""
    if a.allow_draft_register or not a.workdir:
        return
    reg = os.path.join(a.workdir, "register.yaml")
    if os.path.isfile(reg) and not _frozen_match(reg, os.path.join(a.src or "", "register", "versions")):
        raise DraftRegister("workdir register.yaml is not byte-identical to any register/versions/*.yaml "
                            "in --src; refusing to present it as frozen (use --allow-draft-register to stage "
                            "it under register/draft/)")


def _missing_t1(src):
    """PR-48: the register versions under <src>/register/versions with no T1 proof (<v>.head.json beside it or at
    register/<v>.head.json): without one the console can only say NOT_PROVEN. Run tools/stage_t1.py first."""
    if not src:
        return []
    vdir = os.path.join(src, "register", "versions")
    names = sorted(n[:-5] for n in (os.listdir(vdir) if os.path.isdir(vdir) else [])
                   if n.endswith(".yaml") and not n.endswith(".risks.yaml") and not n.startswith("inv-"))
    return [n for n in names if not os.path.isfile(os.path.join(vdir, n + ".head.json"))
            and not os.path.isfile(os.path.join(src, "register", n + ".head.json"))]


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
            if not _frozen_match(reg, vdir):
                # never present an unfrozen register as frozen (PR-34); the caller checked the flag
                ddir = os.path.join(out, "register", "draft")
                os.makedirs(ddir, exist_ok=True)
                _copy(reg, os.path.join(ddir, "register.yaml"))
                os.makedirs(vdir, exist_ok=True)
                with open(os.path.join(vdir, "NO-VERSION-FROZEN.md"), "w", encoding="utf-8") as f:
                    f.write(NO_FROZEN_NOTE)
                warnings.append("register.yaml matches no frozen version: staged as register/draft/register.yaml "
                                "(NO-VERSION-FROZEN.md written)")
        else:
            warnings.append("workdir has no register.yaml")
    for name in README_DOCS:
        dst = os.path.join(out, name)
        if not os.path.isfile(dst) and wd and os.path.isfile(os.path.join(wd, name)):
            _copy(os.path.join(wd, name), dst)
        if not os.path.isfile(dst):
            tmpl = os.path.join(_repo_root(), "evidence-templates", name)
            if os.path.isfile(tmpl):
                _copy(tmpl, dst)
                warnings.append("%s: not in --src or --workdir; staged the checked-in evidence-templates/%s "
                                "(fill it before submit if it still says template)" % (name, name))
    # PR-51b: the field-coverage statement (what the records carry, each gap classed by where the field is written) is
    # a static copy of the offline audit, not a template: staged from --src when there, else the checked-in copy, no "fill it" warning
    fc = os.path.join(out, "field-coverage.md")
    if not os.path.isfile(fc):
        tmpl = os.path.join(_repo_root(), "evidence-templates", "field-coverage.md")
        if os.path.isfile(tmpl):
            _copy(tmpl, fc)
    adv = os.path.join(out, "adversarial")
    if not os.path.isdir(adv):
        repo_adv = os.path.join(_repo_root(), "evidence", "adversarial")
        if os.path.isdir(repo_adv):
            _copy(repo_adv, adv)
            warnings.append("adversarial/: not in --src; staged the repo's evidence/adversarial/ (pre-registered cases%s)"
                            % ("" if os.path.isfile(os.path.join(adv, "log.jsonl")) else "; no log.jsonl, so no observed result is claimed"))
    for sub in ("findings", "servicenow"):
        if not os.path.isdir(os.path.join(out, sub)):
            warnings.append("%s/: not in --src (copy it into the snapshot before the final build; see the runbook)" % sub)
    sketch = os.path.join(out, "sketch.png")
    if not os.path.isfile(sketch):      # D2: the checked-in render of architecture/one-page.svg; never silently absent
        tmpl = os.path.join(_repo_root(), "evidence-templates", "sketch.png")
        if os.path.isfile(tmpl):
            _copy(tmpl, sketch)
        else:
            raise SketchMissing("sketch.png: not in --workdir and no checked-in render at " + tmpl
                                + " (render architecture/one-page.svg to it once)")
    readme = a.readme or os.path.join(_repo_root(), "evidence-templates", "README.md")
    if os.path.isfile(readme):
        _copy(readme, os.path.join(out, "README.md"))
    else:
        with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Evidence Pack\n\nREADME template missing at build time; see the gap list.\n")
        warnings.append("README template missing: stub written")
    mp = _manifest_path()      # the README tells a judge to run tools/manifest.py: it ships in the pack (PR-34)
    if mp:
        _copy(mp, os.path.join(out, "tools", "manifest.py"))
    else:
        warnings.append("tools/manifest.py not found: not staged")
    tool = a.tool_src or os.path.join(_repo_root(), "prooflab")
    if os.path.isdir(tool):
        shutil.copytree(tool, os.path.join(out, "prooflab"),
                        ignore=shutil.ignore_patterns(*_IGNORE, "*.pyc"))
    else:
        warnings.append("tool source not found: " + tool)
    for sub in ("store", "raw", "derived", "assessments", "register"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    return warnings


def readme_placeholders(path):
    """Unfilled template markers in the README: <UPPER_CASE>, <INCnnnnnnn>-style, <...> and the template note."""
    import re
    try:
        with open(path, "r", encoding="utf-8") as fh:
            t = fh.read()
    except (IOError, OSError):
        return ["(README.md missing)"]
    found = re.findall(r"<(?:[A-Z][A-Z0-9_]+|INC[a-z]+|\.\.\.|YYYY-MM-DD|[a-z][a-z0-9 ,/;.\-]{8,}[a-z.])>", t)
    found = [f for f in found if f not in ("<CID>", "<T1>", "<T2>", "<CID-or-time>", "<port>")]    # the reader's own command arguments
    if "Delete this note when filled" in t:
        found.append("Delete this note when filled")
    return found


def _project_console(out, warnings):
    """Console entry point (D1/D2): compose stored answers and project pack-index.json + records/ from the STAGED tree.

    One-way: the projection goes to a temp dir; only pack-index.json, records/ and the projected assessments (under
    projected-assessments/, apart from the native assessments/ the query engine reads) are copied into the pack."""
    import tempfile
    from prooflab.pack import answers as _answers
    entries, skipped = _answers.compose(out)
    aud, aud_skipped = _answers.compose_auditor(out)
    for sk in skipped + aud_skipped:
        warnings.append("answer not composed (%s): %s" % (sk["query"], sk["reason"]))
    tmp = tempfile.mkdtemp(prefix="prooflab-proj-")
    try:
        pj = os.path.join(tmp, "p")
        idx = os.path.join(tmp, "answers.json")
        with open(idx, "w", encoding="utf-8") as fh:
            json.dump(entries, fh)
        aidx = os.path.join(tmp, "auditor.json")
        with open(aidx, "w", encoding="utf-8") as fh:
            json.dump(aud, fh)
        # the projector runs as its own process: nothing imports it (the one-way grep in tests/projector)
        env = dict(os.environ, PYTHONPATH=_repo_root(), PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, "-m", "prooflab.pack." + "projector", "--src", out, "--out", pj,
                            "--answers", idx, "--auditor", aidx, "--assessments-dir", "projected-assessments"],
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if r.returncode != 0:
            raise RuntimeError("projector exit %d: %s" % (r.returncode, r.stderr.strip()[-300:]))
        for line in r.stderr.splitlines():     # every skipped assessment is said, never silent
            if line.strip():
                warnings.append(line.strip())
        for name in ("pack-index.json", "records", "projected-assessments", "projection-report.json"):
            s = os.path.join(pj, name)
            if os.path.exists(s):
                dst = os.path.join(out, name)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                _copy(s, dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return len(entries)


def cmd_build(argv):
    p = argparse.ArgumentParser(prog="prooflab pack build")
    p.add_argument("--out", required=True)
    p.add_argument("--src", help="tree holding store/ raw/ derived/ assessments/ register/ ...")
    p.add_argument("--workdir", help="dir with register.yaml gap-list.md run-ids.txt sketch.png")
    p.add_argument("--readme")
    p.add_argument("--tool-src")
    p.add_argument("--scan-values-stdin", action="store_true")
    p.add_argument("--strict-readme", action="store_true",
                   help="fail the build while the staged README still holds a <PLACEHOLDER> or the template note")
    p.add_argument("--label", default=None, help="the submit label for the README (submit-1, submit-2, final)")
    p.add_argument("--allow-draft-register", action="store_true",
                   help="stage an unfrozen register.yaml under register/draft/ instead of refusing")
    p.add_argument("--allow-missing-t1", action="store_true",
                   help="build although a register version has no <v>.head.json T1 proof (its rule date reads NOT_PROVEN)")
    a = p.parse_args(argv)
    out = os.path.abspath(a.out)
    if os.path.exists(out) and os.listdir(out):
        print("pack: refusing a non-empty --out " + out, file=sys.stderr)
        return 2
    try:
        _precheck_register(a)
    except DraftRegister as exc:
        print("pack: " + str(exc), file=sys.stderr)
        return 2
    no_t1 = _missing_t1(a.src)
    if no_t1 and not a.allow_missing_t1:
        print("pack: no T1 date proof for register version(s) %s (register/versions/<v>.head.json); run "
              "tools/stage_t1.py --from <ops-lane dirs> --to <src>/register/versions first, or pass --allow-missing-t1 "
              "(the rule date then reads NOT_PROVEN, never 'after')" % ", ".join(no_t1), file=sys.stderr)
        return 2
    os.makedirs(out, exist_ok=True)
    try:
        warnings = _stage(out, a)
        if no_t1:
            warnings.append("--allow-missing-t1: no T1 proof for %s; those rule dates read NOT_PROVEN" % ", ".join(no_t1))
    except SketchMissing as exc:
        print("pack: " + str(exc), file=sys.stderr)
        return 2
    redactor = _load_redactor()
    if redactor:
        redactor(out)
    dropped, redact_errors = builtin_redact(out)
    if not redact_errors:
        try:
            _project_console(out, warnings)
        except Exception as exc:       # the pack is still valid without the console entry point; say so loudly
            warnings.append("console projection FAILED (%s: %s): pack-index.json not written" % (type(exc).__name__, exc))
    if not redact_errors:
        try:
            from prooflab.pack import readme as _readme
            rf = _readme.fill(out, label=a.label)
            if rf["not_available"]:
                warnings.append("README: %d placeholder(s) not fillable from the pack, stated as 'not yet available': %s"
                                % (len(rf["not_available"]), "; ".join(rf["not_available"][:6])))
            if rf["absent_files"]:
                warnings.append("README names files not in the pack (marked so): " + ", ".join(rf["absent_files"]))
        except Exception as exc:       # the README stays as staged; strict mode below then refuses it
            warnings.append("README fill FAILED (%s: %s)" % (type(exc).__name__, exc))
    if a.strict_readme:
        left = readme_placeholders(os.path.join(out, "README.md"))
        if left:
            print("pack: README.md still holds %d placeholder(s), e.g. %s (--strict-readme)" % (len(left), ", ".join(left[:4])),
                  file=sys.stderr)
            return 2
    if redact_errors:
        for rel in redact_errors:
            print("REDACT FAIL: cannot parse and redact " + rel, file=sys.stderr)
        print("pack: redaction incomplete; MANIFEST.json not written", file=sys.stderr)
        return 1
    values = read_scan_values(a.scan_values_stdin)
    hits = scan_tree(out, values)
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
    scanmsg = "exact-value scan: 0 hits" if values else "scan skipped: no values"
    print("OK: staged %d files in %s; %s" % (len(manifest["files"]), out, scanmsg))
    return 0


PREPUSH_SCAN_DEFAULT = os.path.join("~", "firstmate-homes", "TrustworthyAI", "workshop-local", "scripts",
                                    "pre-push-secret-scan.sh")


def prepush_scan_script():
    return os.path.expanduser(os.environ.get("PROOFLAB_PREPUSH_SCAN") or PREPUSH_SCAN_DEFAULT)


def run_prepush_scan(directory):
    """The delegated scan: `bash <script> <dir>`; clean = exit 0 AND a `RESULT: clean` line. -> (clean?, tail text)."""
    script = prepush_scan_script()
    if not os.path.isfile(script):
        return False, "scan script not found: %s" % script
    p = subprocess.run(["bash", script, directory], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    lines = p.stdout.splitlines()
    clean = p.returncode == 0 and any(l.startswith("RESULT: clean") for l in lines)
    return clean, "\n".join(lines[-8:])


def cmd_scan(argv):
    allow = "--allow-empty-scan" in argv or os.environ.get("PROOFLAB_ALLOW_EMPTY_SCAN") == "1"
    argv = [x for x in argv if x != "--allow-empty-scan"]
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print("usage: pack scan [--allow-empty-scan] <dir>\n"
              "  values in PROOFLAB_SCAN_VALUES: the exact-value scan runs here.\n"
              "  none injected: delegates to bash $PROOFLAB_PREPUSH_SCAN <dir> (default %s), RESULT: clean required."
              % PREPUSH_SCAN_DEFAULT, file=sys.stderr if argv[:1] not in (["-h"], ["--help"]) else sys.stdout)
        return 0 if argv[:1] in (["-h"], ["--help"]) else 2
    values = read_scan_values()
    if not values and not allow:
        clean, tail = run_prepush_scan(argv[0])
        if clean:
            print("pre-push scan: RESULT: clean (%s)" % argv[0])
            return 0
        print("REFUSED: no scan values injected and the pre-push scan is not clean on %s" % argv[0], file=sys.stderr)
        print(tail, file=sys.stderr)
        return 1
    hits = scan_tree(argv[0], values)
    for rel, c in hits:
        print("SCAN HIT: %s (%d)" % (rel, c), file=sys.stderr)
    print("exact-value scan: %d hit(s)%s" % (sum(c for _, c in hits), "" if values else " (skipped: no values)"))
    return 1 if hits else 0


def cmd_index(argv):
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        text = ("usage: pack index <dir>\n  (re)compose answers/ and project pack-index.json + records/ into a staged pack "
                "dir that has no MANIFEST.json yet (`pack build` already does this; a sealed pack is rebuilt, not edited)")
        print(text, file=sys.stdout if argv[:1] in (["-h"], ["--help"]) else sys.stderr)
        return 0 if argv[:1] in (["-h"], ["--help"]) else 2
    if not os.path.isdir(argv[0]):
        print("pack: not a directory: %s" % argv[0], file=sys.stderr)
        return 2
    if os.path.exists(os.path.join(argv[0], "MANIFEST.json")):
        print("pack: %s is sealed (MANIFEST.json); an index change would break it. Rebuild with pack build." % argv[0],
              file=sys.stderr)
        return 2
    warnings = []
    try:
        _project_console(os.path.abspath(argv[0]), warnings)
    except Exception as exc:   # noqa: BLE001
        print("pack: index FAILED (%s: %s)" % (type(exc).__name__, exc), file=sys.stderr)
        return 1
    for w in warnings:
        print("warning: " + w)
    print("OK: pack-index.json projected in %s" % argv[0])
    return 0


def cmd_verify(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print("usage: pack verify <dir>\n  tools/manifest.py verify: every file matches MANIFEST.json, none unlisted")
        return 0
    if len(argv) != 1:
        print("usage: pack verify <dir>", file=sys.stderr)
        return 2
    # manifest.py verify, but bytecode a run may have written (prooflab/__pycache__) is not "unlisted"
    m = _load_manifest_tool()
    try:
        result = m.verify_manifest(argv[0])
    except (OSError, ValueError, KeyError) as exc:
        print("pack: cannot verify: %s" % exc, file=sys.stderr)
        return 1
    result["unlisted"] = [x for x in result["unlisted"] if not _is_bytecode(x)]
    problems = ["%s: %s" % (k, x) for k, v in result.items() for x in v]
    print("\n".join(problems) if problems else "OK: every file matches MANIFEST.json")
    return 1 if problems else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "root":
        from prooflab.pack import root_publish
        return root_publish.main(argv[1:])
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__.split("\n\n")[1] if "\n\n" in __doc__ else __doc__)
        print("python3 -m prooflab pack <verb> --help  for a verb's options")
        return 0
    if argv and argv[0] in ("build", "scan", "verify", "index"):
        verb, rest = argv[0], argv[1:]
    else:
        verb, rest = "build", argv
    return {"build": cmd_build, "scan": cmd_scan, "verify": cmd_verify, "index": cmd_index}[verb](rest)


if __name__ == "__main__":
    sys.exit(main())
