#!/usr/bin/env python3
"""Write the ifabric- agents' source files, size-gated (ARCH 7.1; 05 AR-03; plan T3.3; decision D-B).

Default --layout two-stage (D-B): agents/ifabric-base/ifabric-base.py (the finder, the c16 core byte-identical
and the shared runtime modules that fit) built once as image ifabric-base-<sha>, and per role
agents/ifabric-<role>/ifabric-<role>.py (the remaining modules, the shared app, the role source and the
entrypoint) built FROM <repo>@<base digest>. Each file is gated on its own. Non-core modules are stripped of
docstrings, comments and annotations through ast.unparse (bundle with Python 3.12, the image's version).
--layout single: the original one-file-per-agent layout, described below.

The kit's build (build-agent-image.sh) ships exactly one file, as gzip+base64 inside the CodeBuild
buildspec (cap 25,600 chars, fixed overhead 1,551 -> 24,049 chars for the source). This tool embeds
each vendored module (the c16 core, the runtime adapters, the shared trio app; never prooflab/contract/) as its
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

# The runtime subset: what an agent imports at run time (ARCH 7.1: "no JSON-schema validator inside the
# agent; the laptop validates"). So NO prooflab/contract/* module: no runtime adapter needs one
# (model_call's optional `prooflab.contract.record` import falls back to its own builder when absent).
# Never the tester c16.py, never schema JSON. Each entry is repo-relative; a glob is allowed.
# "required" ones must exist (the app imports every one: a missing one is an ImportError at start-up);
# "optional" ones are embedded when present (the package markers are served empty otherwise).
DEFAULT_REQUIRED = [
    CORE_PATH,
    "adapters/runtime/model_call.py",
    "adapters/runtime/action_id.py",
    "adapters/runtime/tally.py",
    "adapters/runtime/hooks.py",
    "adapters/runtime/emit_client.py",
    "adapters/runtime/tool_call.py",
    "adapters/runtime/judgment.py",
    "adapters/runtime/startup.py",
    "adapters/runtime/rails.py",
    "adapters/runtime/egress.py",
    "adapters/runtime/j2.py",
]
DEFAULT_OPTIONAL = [
    "prooflab/evaluators/__init__.py",
    "adapters/__init__.py",
    "adapters/runtime/__init__.py",
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
        if mod.startswith("prooflab.contract"):
            raise BundleError("refusing to embed %s: prooflab/contract/ is laptop-side (ARCH 7.1)" % mod)
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


def _imports(text):
    import ast
    names = set()
    for n in ast.walk(ast.parse(text)):
        if isinstance(n, ast.Import):
            names.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            names.add(n.module)
            names.update(n.module + "." + a.name for a in n.names)
    return names


def surface_modules(app_text):
    """The module names in ifabric_app's SURFACE table (read by ast, never imported): the app loads each one
    through importlib.import_module, which a static import walk cannot see."""
    import ast
    found = []
    for n in ast.walk(ast.parse(app_text or "")):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SURFACE" for t in n.targets) \
                and isinstance(n.value, ast.Dict):
            found += [k.value for k in n.value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    return found


def prune(sources, entry_text, roots=()):
    """Keep the modules reachable from the roots: the c16 core, the entry's imports, and `roots` (bundle() passes
    every SURFACE module of ifabric_app and every required manifest entry, so a module the app loads by name is
    never dropped). Returns (kept sources, pruned names)."""
    keep = set()
    stack = [CORE_MODULE] + sorted(m for m in _imports(entry_text) if m in sources) + sorted(roots)
    while stack:
        m = stack.pop()
        if m in keep or m not in sources:
            continue
        keep.add(m)
        parts = m.split(".")
        stack += [".".join(parts[:i]) for i in range(1, len(parts))]
        stack += sorted(d for d in _imports(sources[m]) if d in sources)
    return dict((m, t) for m, t in sources.items() if m in keep), sorted(set(sources) - keep)


class _Strip(object):
    """Docstrings, comments (ast.unparse drops them) and annotations of functions and of module/function-level
    assignments. Class-body annotations stay: dataclass and NamedTuple fields are annotations."""

    @staticmethod
    def run(text):
        import ast

        def body(stmts, in_class):
            out = []
            for i, st in enumerate(stmts):
                if i == 0 and isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) \
                        and isinstance(st.value.value, str):
                    continue                                   # docstring
                if isinstance(st, ast.AnnAssign) and not in_class:
                    if st.value is None:
                        continue
                    st = ast.copy_location(ast.Assign(targets=[st.target], value=st.value), st)
                if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    a = st.args
                    for arg in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg]:
                        if arg is not None:
                            arg.annotation = None
                    st.returns = None
                    st.body = body(st.body, False)
                elif isinstance(st, ast.ClassDef):
                    st.body = body(st.body, True)
                else:
                    for field in ("body", "orelse", "finalbody"):
                        if isinstance(getattr(st, field, None), list) and getattr(st, field) \
                                and isinstance(getattr(st, field)[0], ast.stmt):
                            setattr(st, field, body(getattr(st, field), in_class))
                    for h in getattr(st, "handlers", None) or []:
                        h.body = body(h.body, in_class)
                out.append(st)
            return out or [ast.Pass()]

        tree = ast.parse(text)
        tree.body = body(tree.body, False)
        return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def strip_docstrings(text):
    """NOT byte-identical (opt-in, --strip-docstrings; default in --layout two-stage): docstrings, comments and
    function/assignment annotations removed via ast.unparse (bundle with Python 3.12, the image's version).
    Never applied to the c16 core, whose literal must equal the repo file (ARCH 7.1, 11.1)."""
    return _Strip.run(text)


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


def prune_roots(manifest, sources):
    """Every SURFACE module of the embedded ifabric_app (ast) and every required manifest entry."""
    roots = set(surface_modules(sources.get("ifabric_app", "")))
    for rel in manifest.get("required", []):
        if not any(ch in rel for ch in "*?["):
            roots.add(module_name(rel))
    return sorted(roots)


def _strip_all(sources):
    stripped = []
    for mod in sorted(sources):
        if mod != CORE_MODULE and sources[mod].strip():
            sources[mod] = strip_docstrings(sources[mod])
            stripped.append(mod)
    return stripped


# ---------------------------------------------------------------------------------------------------------
# Two-stage layout (D-B; ARCH 7.1 fallback; work/05 AR-03): ONE shared base file + one file per role, each
# gated on its own. The base (agents/ifabric-base/ifabric-base.py, installed in the base image as
# /app/ifabric_base.py) carries the finder, the c16 core byte-identical and as many shared runtime modules as
# fit; each role file (agents/ifabric-<role>/ifabric-<role>.py, the image's entrypoint) carries the rest, the
# shared app and the role source, and at start loads the base, failing closed unless the base file is the exact
# one it was built against and serves the pinned c16 core. ifabric_app stays in the role files, so an app or
# role edit rebuilds only the role images.
BASE_NAME = "ifabric-base"
BASE_IN_IMAGE = "/app/ifabric_base.py"      # where the base buildspec decodes the base file
BASE_MODULE = "ifabric_base"
# Measured fill order: the hot path first (model call, tally, hooks, action ids, emit), then the rest.
BASE_PRIORITY = ["adapters.runtime.model_call", "adapters.runtime.tally", "adapters.runtime.hooks",
                 "adapters.runtime.action_id", "adapters.runtime.emit_client", "adapters.runtime.startup",
                 "adapters.runtime.tool_call", "adapters.runtime.judgment", "adapters.runtime.rails",
                 "adapters.runtime.egress", "adapters.runtime.j2"]

BASE_LOADER = '''# ---- generated base loader (tools/bundle_agent.py, two-stage): serves the embedded modules
import hashlib as _hl
import importlib.abc as _iabc
import importlib.util as _iu
import sys as _sys


class _BundleFinder(_iabc.MetaPathFinder, _iabc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name not in _SOURCES:
            return None
        pkg = name in _PACKAGES
        return _iu.spec_from_file_location(
            name, _ORIGIN + "/" + name.replace(".", "/") + ("/__init__.py" if pkg else ".py"),
            loader=self, submodule_search_locations=[] if pkg else None)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(_SOURCES[module.__name__], module.__file__, "exec"), module.__dict__)


def _verify(sources, sha256):
    if set(sources) != set(sha256):
        raise SystemExit("ifabric bundle: module list and sha256 list differ")
    for n, h in sha256.items():  # fail closed: an edited literal never runs
        if _hl.sha256(sources[n].encode("utf-8")).hexdigest() != h:
            raise SystemExit("ifabric bundle: embedded module %s does not match its recorded sha256" % n)


def extend(sources, sha256, packages):
    """The role file's modules: verified, and never a module the base already serves."""
    _verify(sources, sha256)
    dup = sorted(set(sources) & set(_SOURCES))
    if dup:
        raise SystemExit("ifabric bundle: the role file redefines base modules: %s" % ", ".join(dup))
    _SOURCES.update(sources)
    _SHA256.update(sha256)
    _PACKAGES.extend(packages)


_ORIGIN = "/app/_bundle"
_verify(_SOURCES, _SHA256)
EVALUATOR_SHA256 = _SHA256.get("@CORE@")
if not [f for f in _sys.meta_path if type(f).__name__ == "_BundleFinder"]:
    _sys.meta_path.insert(0, _BundleFinder())
# ---- end of generated base loader
'''.replace("@CORE@", CORE_MODULE)

ROLE_LOADER = '''# ---- generated role loader (tools/bundle_agent.py, two-stage): loads the base, then the role source runs
import hashlib as _hl
import importlib.util as _iu
import os as _os
import sys as _sys

_BASE_PATH = _os.environ.get("IFABRIC_BASE_PATH") or "@BASE_PATH@"


def _load_base():
    try:
        with open(_BASE_PATH, "rb") as f:
            data = f.read()
    except OSError as exc:
        raise SystemExit("ifabric role bundle: the base bundle is missing at %s (%s); this image must be built "
                         "FROM the ifabric-base image" % (_BASE_PATH, exc))
    got = _hl.sha256(data).hexdigest()
    if got != _BASE_FILE_SHA256:
        raise SystemExit("ifabric role bundle: %s is not the base bundle this role was built against "
                         "(sha256 %s, want %s)" % (_BASE_PATH, got, _BASE_FILE_SHA256))
    spec = _iu.spec_from_file_location("@BASE_MODULE@", _BASE_PATH)
    base = _iu.module_from_spec(spec)
    _sys.modules["@BASE_MODULE@"] = base
    spec.loader.exec_module(base)
    core = base._SOURCES.get("@CORE@")
    if core is None or _hl.sha256(core.encode("utf-8")).hexdigest() != EVALUATOR_SHA256 \\
            or base.EVALUATOR_SHA256 != EVALUATOR_SHA256:
        raise SystemExit("ifabric role bundle: the base does not serve the pinned c16 core %s" % EVALUATOR_SHA256)
    base.extend(_SOURCES, _SHA256, _PACKAGES)
    return base


_BASE = _load_base()
# ---- end of generated role loader; the role source follows
'''.replace("@CORE@", CORE_MODULE).replace("@BASE_PATH@", BASE_IN_IMAGE).replace("@BASE_MODULE@", BASE_MODULE)


def _tables(sources, packages):
    sha = dict((m, hashlib.sha256(t.encode("utf-8")).hexdigest()) for m, t in sorted(sources.items()))
    body = ["_SOURCES = {\n"]
    for mod in sorted(sources):
        body.append("    %r: %r,\n" % (mod, sources[mod]))
    body.append("}\n_SHA256 = {\n")
    for mod in sorted(sha):
        body.append("    %r: %r,\n" % (mod, sha[mod]))
    body.append("}\n_PACKAGES = %r\n" % sorted(packages))
    return "".join(body)


def render_base(sources, packages, core_sha):
    header = ("# %s.py: GENERATED by tools/bundle_agent.py (two-stage base); do not edit. Installed as %s.\n"
              "# c16 core: prooflab/evaluators/c16_core.py (embedded byte-identical)\n"
              "# evaluator.sha256=%s\n" % (BASE_NAME, BASE_IN_IMAGE, core_sha))
    return header + _tables(sources, packages) + BASE_LOADER


def render_role(name, sources, packages, entry_text, core_sha, base_file_sha):
    header = ("# %s.py: GENERATED by tools/bundle_agent.py (two-stage role); do not edit. Built FROM the %s "
              "image.\n# c16 core: NOT embedded here; served by %s, pinned below (fails closed otherwise)\n"
              "# evaluator.sha256=%s\n" % (name, BASE_NAME, BASE_IN_IMAGE, core_sha))
    pins = "_BASE_FILE_SHA256 = %r\nEVALUATOR_SHA256 = %r\n" % (base_file_sha, core_sha)
    return header + _tables(sources, packages) + pins + ROLE_LOADER + "\n" + entry_text


def _parents(mod):
    parts = mod.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts))]


def buildspec_budgets(gate=GATE_CHARS):
    """(base budget, role budget): the gate, lowered when a buildspec's fixed text would push the
    --buildspec-override past CodeBuild's 25,600 chars (tools/make_ifabric_agents.py writes them)."""
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    try:
        import make_ifabric_agents as mk
        over_b, over_r = mk.buildspec_overheads()
        return min(gate, mk.BUILDSPEC_CAP - over_b), min(gate, mk.BUILDSPEC_CAP - over_r)
    except ImportError:
        return gate, gate
    finally:
        if sys.path and sys.path[0] == here:
            sys.path.pop(0)


def bundle_two_stage(roles=ROLES, src_root=REPO, agents_root=REPO, out_root=None, gate=GATE_CHARS, write=True,
                     do_prune=False, do_strip=True, manifest_for=default_manifest):
    """Returns (reports, texts {file name: text}). Writes nothing unless every file passes its budget."""
    roles = list(roles)
    base_budget, role_budget = buildspec_budgets(gate)
    fulls = {}
    for role in roles:
        m = manifest_for(role)
        entry_path = os.path.join(agents_root, m["entry"])
        if os.path.basename(entry_path) == _FORBIDDEN_NAME:
            raise BundleError("refusing an entry file named %s" % _FORBIDDEN_NAME)
        entry_text = _read_utf8(entry_path)[0]
        sources, packages, _missing, _synth = collect(m, src_root, agents_root)
        pruned = []
        if do_prune:
            sources, pruned = prune(sources, entry_text, prune_roots(m, sources))
            packages = set(p for p in packages if p in sources)
        stripped = _strip_all(sources) if do_strip else []
        fulls[role] = (m, entry_text, sources, packages, pruned, stripped)
    core_sha = hashlib.sha256(open(os.path.join(src_root, CORE_PATH), "rb").read()).hexdigest()
    m0, _e, src0, pk0, _p, strip0 = fulls[roles[0]]
    if hashlib.sha256(src0[CORE_MODULE].encode("utf-8")).hexdigest() != core_sha:
        raise BundleError("embedded c16 core differs from %s" % CORE_PATH)
    extras = set(m0.get("extra_modules", {}))
    shared = [x for x in src0 if x not in extras and x not in pk0 and x != CORE_MODULE]
    order = [x for x in BASE_PRIORITY if x in shared] + sorted(x for x in shared if x not in BASE_PRIORITY)
    base = set([CORE_MODULE] + _parents(CORE_MODULE))

    def render(mods):
        return render_base(dict((x, src0[x]) for x in mods), set(x for x in mods if x in pk0), core_sha)

    base_text = render(base)
    for cand in order:  # measured, not summed: gzip compresses across modules
        trial = base | set([cand] + _parents(cand))
        t = render(trial)
        if gz_b64_len(t)[0] <= base_budget:
            base, base_text = trial, t
    base_sha = hashlib.sha256(base_text.encode("utf-8")).hexdigest()
    b64, gz, how = gz_b64_len(base_text)
    reports = [{"name": BASE_NAME, "file": BASE_NAME + ".py", "raw_bytes": len(base_text.encode("utf-8")),
                "gzip_bytes": gz, "gzip_base64_chars": b64, "measured_with": how, "gate": base_budget,
                "hard_cap": HARD_CAP_CHARS, "c16_core_sha256": core_sha, "file_sha256": base_sha,
                "modules": sorted(base), "ok": b64 <= base_budget,
                "stripped_not_byte_identical": [x for x in strip0 if x in base]}]
    texts = {BASE_NAME + ".py": base_text}
    for role in roles:
        m, entry_text, sources, packages, pruned, stripped = fulls[role]
        missing = sorted(base - set(sources))
        if missing:
            raise BundleError("role %s lacks base modules %s" % (role, ", ".join(missing)))
        if [x for x in base if sources[x] != src0[x]]:
            raise BundleError("role %s embeds different base modules than the base" % role)
        name = m.get("name") or "ifabric-" + role
        if not re.match(r"^ifabric-[a-z][a-z0-9-]*$", name) or name == BASE_NAME:
            raise BundleError("bundle name %r must be ifabric-<role>" % name)
        mine = dict((x, t) for x, t in sources.items() if x not in base)
        if CORE_MODULE in mine:
            raise BundleError("a role file never embeds the c16 core")
        text = render_role(name, mine, set(p for p in packages if p in mine), entry_text, core_sha, base_sha)
        b64, gz, how = gz_b64_len(text)
        reports.append({"name": name, "file": name + ".py", "raw_bytes": len(text.encode("utf-8")),
                        "gzip_bytes": gz, "gzip_base64_chars": b64, "measured_with": how, "gate": role_budget,
                        "hard_cap": HARD_CAP_CHARS, "c16_core_sha256": core_sha, "base_file_sha256": base_sha,
                        "modules": sorted(mine), "pruned": pruned, "ok": b64 <= role_budget,
                        "stripped_not_byte_identical": [x for x in stripped if x in mine]})
        texts[name + ".py"] = text
    ok = all(r["ok"] for r in reports)
    for r in reports:
        r["out"] = None
        if write and ok:
            d = os.path.join(out_root, r["name"]) if out_root else os.path.join(agents_root, "agents", r["name"])
            os.makedirs(d, exist_ok=True)
            r["out"] = os.path.join(d, r["file"])
            with open(r["out"], "wb") as f:
                f.write(texts[r["file"]].encode("utf-8"))
    return reports, texts


def bundle(manifest, src_root=REPO, agents_root=REPO, out_dir=None, gate=GATE_CHARS, write=True,
           do_prune=False, do_strip=False):
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
    pruned, stripped = [], []
    if do_prune:
        sources, pruned = prune(sources, entry_text, prune_roots(manifest, sources))
        packages = set(p for p in packages if p in sources)
    if do_strip:
        stripped = _strip_all(sources)
    core_sha = hashlib.sha256(open(os.path.join(src_root, CORE_PATH), "rb").read()).hexdigest()
    if hashlib.sha256(sources[CORE_MODULE].encode("utf-8")).hexdigest() != core_sha:
        raise BundleError("embedded c16 core differs from %s" % CORE_PATH)
    # The marker line is exactly what tools/gate.sh (PR-00) greps: evaluator[_.]sha256\W{0,8}<64 hex>.
    header = ("# %s: GENERATED by tools/bundle_agent.py; do not edit. One file per agent (ARCH 7.1).\n"
              "# c16 core: prooflab/evaluators/c16_core.py (embedded byte-identical)\n"
              "# evaluator.sha256=%s\n" % (out_name, core_sha))
    text = render(sources, packages, entry_text, header)
    b64, gz, how = gz_b64_len(text)
    report = {
        "name": name, "file": out_name, "raw_bytes": len(text.encode("utf-8")), "gzip_bytes": gz,
        "gzip_base64_chars": b64, "measured_with": how, "gate": gate, "hard_cap": HARD_CAP_CHARS,
        "c16_core_sha256": core_sha, "modules": sorted(sources), "missing_optional": missing_opt,
        "synthesized_empty_packages": synthesized, "pruned": pruned, "stripped_not_byte_identical": stripped,
        "ok": b64 <= gate,
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


def _print_report(r):
    print("%s %s: raw=%d B gzip=%d B gzip+base64=%d chars (budget %d, gate %d, hard cap %d; %s) "
          "c16_core sha256=%s%s" % (
              "OK  " if r["ok"] else "FAIL", r["name"], r["raw_bytes"], r["gzip_bytes"], r["gzip_base64_chars"],
              r["gate"], GATE_CHARS, r["hard_cap"], r["measured_with"], r["c16_core_sha256"],
              "" if r["ok"] else "  OVER THE BUDGET: nothing written"))
    print("     modules: %s" % ", ".join(r["modules"]))
    for key, label in (("missing_optional", "missing optional (not embedded)"),
                       ("synthesized_empty_packages", "empty package markers served"),
                       ("pruned", "pruned (unreachable)")):
        if r.get(key):
            print("     %s: %s" % (label, ", ".join(r[key])))
    if r.get("stripped_not_byte_identical"):
        print("     docstrings/annotations stripped (NOT byte-identical): %d modules"
              % len(r["stripped_not_byte_identical"]))
    if r.get("out"):
        print("     wrote %s" % r["out"])


def main(argv=None):
    p = argparse.ArgumentParser(description="Bundle the ifabric- agents (size-gated).")
    p.add_argument("--layout", choices=("two-stage", "single"), default="two-stage",
                   help="two-stage (default, D-B): agents/ifabric-base/ifabric-base.py + one file per role; "
                        "single: one self-contained file per role")
    p.add_argument("--role", choices=ROLES, help="two-stage: limit the role files (the base is always built)")
    p.add_argument("--all", action="store_true", help="the trio (two-stage default)")
    p.add_argument("--manifest", help="single layout: JSON manifest (default: built in)")
    p.add_argument("--src-root", default=REPO, help="where prooflab/ and adapters/ are (default: this repo)")
    p.add_argument("--agents-root", default=REPO, help="where agents/ is (default: this repo)")
    p.add_argument("--out-dir", help="single: default <agents-root>/agents/ifabric-<role>/; two-stage: a root "
                                     "holding ifabric-base/ and ifabric-<role>/")
    p.add_argument("--gate", type=int, default=GATE_CHARS)
    p.add_argument("--no-write", action="store_true", help="measure only")
    p.add_argument("--json", action="store_true", help="print the reports as JSON")
    p.add_argument("--prune", action="store_true",
                   help="drop modules unreachable from the entry, the SURFACE table and the required entries")
    p.add_argument("--strip-docstrings", action="store_true",
                   help="single: strip docstrings/comments/annotations of every module EXCEPT the c16 core")
    p.add_argument("--no-strip", action="store_true", help="two-stage: keep every module byte-identical")
    a = p.parse_args(argv)
    if a.gate > HARD_CAP_CHARS:
        p.error("--gate above the hard cap %d" % HARD_CAP_CHARS)
    if a.layout == "two-stage":
        if a.manifest:
            p.error("--manifest is for --layout single")
        try:
            reports, _ = bundle_two_stage([a.role] if a.role else ROLES, a.src_root, a.agents_root, a.out_dir,
                                          a.gate, write=not a.no_write, do_prune=a.prune, do_strip=not a.no_strip)
        except BundleError as e:
            print("bundle_agent: %s" % e, file=sys.stderr)
            return 2
        if a.json:
            print(json.dumps(reports, indent=2))
        else:
            for r in reports:
                _print_report(r)
        return 0 if all(r["ok"] for r in reports) else 3
    roles = ROLES if a.all else ([a.role] if a.role else [])
    if not roles and not a.manifest:
        p.error("give --role, --all or --manifest")
    reports, rc = [], 0
    for role in roles or [None]:
        try:
            m = _load_manifest(a.manifest, role)
            r, _ = bundle(m, a.src_root, a.agents_root, a.out_dir, a.gate, write=not a.no_write,
                          do_prune=a.prune, do_strip=a.strip_docstrings)
        except BundleError as e:
            print("bundle_agent: %s" % e, file=sys.stderr)
            return 2
        reports.append(r)
        if not r["ok"]:
            rc = 3
        if not a.json:
            _print_report(r)
    if a.json:
        print(json.dumps(reports, indent=2))
    return rc


if __name__ == "__main__":
    sys.exit(main())
