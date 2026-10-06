#!/usr/bin/env bash
# tools/gate.sh: the merge gate (T0.4). Run from anywhere; checks the repo that holds this script.
#
#   tools/gate.sh [--no-scan] [--no-tests] [--integration] [--no-integration] [--root DIR]
#
# Checks: (a) pytest on tests/ and tools/tests/ with the 3.9 interpreter (PY39); (a2) Arth's suite prooflab/tests alone: exactly
# 152 passed, 0 failed (ARTH_PASS_COUNT overrides, for the gate's own tests); (a3) Arth byte-identity against
# handoffs/ifabric-handoff-3; (b) the secret scan (must print "RESULT: clean"); (c) the code searches; (d) the integration
# stage tools/integration_check.sh (rehearse.py + ops-lane dryrun.sh), run by default when tests run, forced by --integration,
# dropped by --no-integration. Exit codes:
#   0  everything green, scan clean
#   1  at least one check failed
#   3  all other checks green but the scan was skipped (--no-scan): NOT mergeable, the scan must still run
# Credentials are never read here; the scan script loads its own values.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DO_SCAN=1; DO_TESTS=1; DO_INTEG=auto
while [ $# -gt 0 ]; do
  case "$1" in
    --no-scan) DO_SCAN=0 ;;
    --no-tests) DO_TESTS=0 ;;
    --integration) DO_INTEG=1 ;;
    --no-integration) DO_INTEG=0 ;;
    --root) shift; ROOT="$(cd "$1" && pwd)" ;;
    *) echo "usage: gate.sh [--no-scan] [--no-tests] [--integration] [--no-integration] [--root DIR]"; exit 2 ;;
  esac
  shift
done
SCAN_SCRIPT="${SCAN_SCRIPT:-$HOME/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh}"
FAILS=0
pass() { echo "PASS  $1"; }
na()   { echo "N/A   $1"; }
fail() { echo "FAIL  $1"; FAILS=$((FAILS + 1)); }

# python files of the product, excluding tests, docs, handoffs and prototypes
pyfiles() { # dirs relative to ROOT
  local d
  for d in "$@"; do
    [ -d "$ROOT/$d" ] && find "$ROOT/$d" -type f -name '*.py' ! -name 'test_*.py' ! -name 'conftest.py' \
      ! -path '*/tests/*' ! -path '*/__pycache__/*' 2>/dev/null
  done
}

# ---- (a) tests -------------------------------------------------------------------------------------------
check_tests() {
  local py="${PY39:-$HOME/firstmate-homes/TrustworthyAI/workshop-local/.venv-py39/bin/python}"
  if [ ! -x "$py" ]; then
    echo "WARNING: PY39 interpreter not found ($py); falling back. Results are NOT 3.9 evidence." >&2
    if [ -x /opt/anaconda3/bin/python3.12 ]; then py=/opt/anaconda3/bin/python3.12; else py="$(command -v python3)"; fi
    echo "WARNING: using $py" >&2
  fi
  local dirs="" d
  # prooflab/tests (Arth's) is run alone by check_arth_suite
  for d in tests tools/tests; do [ -d "$ROOT/$d" ] && dirs="$dirs $d"; done
  if [ -z "$dirs" ]; then na "tests: no test directories"; return; fi
  # shellcheck disable=SC2086
  if (cd "$ROOT" && "$py" -m pytest -q -p no:cacheprovider $dirs); then pass "pytest ($py):$dirs"; else fail "pytest ($py):$dirs"; fi
}

check_arth_suite() {  # Arth's own suite, alone: exactly ARTH_PASS_COUNT (152) passed, 0 failed
  local want="${ARTH_PASS_COUNT:-152}"
  if [ ! -d "$ROOT/prooflab/tests" ]; then na "Arth suite (no prooflab/tests)"; return; fi
  local py="${PY39:-$HOME/firstmate-homes/TrustworthyAI/workshop-local/.venv-py39/bin/python}"
  [ -x "$py" ] || py="$(command -v python3)"
  local out; out="$(cd "$ROOT" && "$py" -m pytest -q -p no:cacheprovider prooflab/tests 2>&1)"
  local summary; summary="$(echo "$out" | grep -E '^=*[[:space:]]*[0-9]+ (passed|failed|error)|no tests ran' | tail -1)"
  echo "      $summary"
  local passed failed
  passed="$(echo "$summary" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || true)"
  failed=""; echo "$summary" | grep -qE '[0-9]+ (failed|error)' && failed=1
  if [ "${passed:-x}" = "$want" ] && [ -z "$failed" ]; then pass "Arth suite prooflab/tests: exactly $want passed, 0 failed ($py)"
  else echo "$out" | tail -5 | sed 's/^/      /'; fail "Arth suite prooflab/tests: want exactly $want passed and 0 failed"; fi
}

check_arth_identity() {  # Arth's code is never edited here: byte-identical to the handoff copy
  local py="${PY39:-$HOME/firstmate-homes/TrustworthyAI/workshop-local/.venv-py39/bin/python}"
  [ -x "$py" ] || py="$(command -v python3)"
  local out code
  IFS= read -r -d '' code <<'PY'
import ast, os, sys
root = os.environ["ROOT"]
H = os.path.join(root, "handoffs", "ifabric-handoff-3")
HC = os.path.join(H, "code", "prooflab")
def rd(p):
    with open(p, "rb") as fh:
        return fh.read()
def tree(base):
    out = {}
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for fn in fns:
            if not fn.endswith(".pyc"):
                full = os.path.join(dp, fn)
                out[os.path.relpath(full, base)] = full
    return out
def say(ok, name, why=""):
    print("ARTH %s %s%s" % ("OK" if ok else "FAIL", name, (": " + why) if why else ""))
def na(name, why):
    print("ARTH NA %s: %s" % (name, why))
if not os.path.isdir(HC):
    na("all", "no handoffs/ifabric-handoff-3/code/prooflab under the root")
    sys.exit(0)
for sub in ("servicenow", "tests"):
    mine, theirs = os.path.join(root, "prooflab", sub), os.path.join(HC, sub)
    name = "prooflab/%s == handoff" % sub
    if not os.path.isdir(theirs):
        na(name, "no handoff copy"); continue
    if not os.path.isdir(mine):
        say(False, name, "directory missing"); continue
    a, b = tree(mine), tree(theirs)
    bad = ["only in repo: " + k for k in sorted(set(a) - set(b))] + ["only in handoff: " + k for k in sorted(set(b) - set(a))]
    bad += ["differs: " + k for k in sorted(set(a) & set(b)) if rd(a[k]) != rd(b[k])]
    say(not bad, name, "; ".join(bad[:4]))
cons = os.path.join(root, "prooflab", "console")
for fn in ("ifabric-case-panel.js", "ifabric-case-panel.css"):
    ref = os.path.join(HC, "servicenow", "panel", fn)
    found = []
    for dp, dn, fns in os.walk(cons):
        if fn in fns:
            found.append(os.path.join(dp, fn))
    if not os.path.exists(ref):
        na("console vendor " + fn, "no handoff copy")
    elif not found:
        na("console vendor " + fn, "no copy under prooflab/console")
    else:
        bad = [os.path.relpath(f, root) for f in found if rd(f) != rd(ref)]
        say(not bad, "console vendor %s (%d cop%s)" % (fn, len(found), "y" if len(found) == 1 else "ies"), "differs: " + ", ".join(bad) if bad else "")
bundle = os.path.join(root, "agents", "ifabric-assurance", "ifabric-assurance.py")
ref = os.path.join(HC, "servicenow", "nemotron.py")
if not (os.path.exists(bundle) and os.path.exists(ref)):
    na("embedded nemotron.py", "no assurance bundle or no handoff nemotron.py")
else:
    emb = None
    try:
        for node in ast.walk(ast.parse(rd(bundle).decode("utf-8"))):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "_SOURCES":
                emb = ast.literal_eval(node.value).get("prooflab.servicenow.nemotron")
    except (SyntaxError, ValueError) as exc:
        say(False, "embedded nemotron.py", "bundle does not parse: %s" % exc)
        emb = False
    if emb is None:
        say(False, "embedded nemotron.py", "no _SOURCES['prooflab.servicenow.nemotron'] in the bundle")
    elif emb is not False:
        say(emb.encode("utf-8") == rd(ref), "embedded nemotron.py == handoff", "bytes differ" if emb.encode("utf-8") != rd(ref) else "")
mine = os.path.join(root, "tools", "manifest.py")
ref = os.path.join(H, "deliverables", "evidence-pack", "tools", "manifest.py")
if not os.path.exists(ref):
    na("tools/manifest.py", "no handoff deliverable copy")
elif not os.path.exists(mine):
    say(False, "tools/manifest.py == handoff", "file missing")
else:
    say(rd(mine) == rd(ref), "tools/manifest.py == handoff", "bytes differ" if rd(mine) != rd(ref) else "")
PY
  out="$(ROOT="$ROOT" "$py" -c "$code" 2>&1)"
  echo "$out" | sed 's/^/      /'
  if echo "$out" | grep -qE '^ARTH FAIL|Traceback'; then fail "Arth byte-identity (servicenow, tests, panel vendor, nemotron embed, manifest.py)"
  else pass "Arth byte-identity (servicenow, tests, panel vendor, nemotron embed, manifest.py; N/A rows allowed)"; fi
}

check_integration() {
  if [ -x "$HERE/integration_check.sh" ] || [ -f "$HERE/integration_check.sh" ]; then
    local out rc; out="$(bash "$HERE/integration_check.sh" --root "$ROOT" 2>&1)"; rc=$?
    echo "$out" | sed 's/^/      /'
    if [ "$rc" = 0 ]; then pass "integration stage (tools/integration_check.sh)"; else fail "integration stage (tools/integration_check.sh)"; fi
  else
    fail "tools/integration_check.sh missing"
  fi
}

# ---- (c) searches ----------------------------------------------------------------------------------------
check_threshold_literals() {
  local files hits
  files="$(pyfiles evaluators adapters agents prooflab/evaluators prooflab/adapters prooflab/agents)"
  if [ -z "$files" ]; then na "no threshold literals (no evaluators/adapters/agents python files)"; return; fi
  # a cap/limit/threshold/ceiling-like name assigned a number (an annotation is allowed; == is not an assignment)
  # shellcheck disable=SC2086
  hits="$(echo "$files" | xargs grep -nEi '(cap|limit|threshold|ceiling)[a-z0-9_]*[[:space:]]*(:[^=#]*)?=[[:space:]]*-?[0-9]' 2>/dev/null | grep -Ev '[=!<>]=[[:space:]]*-?[0-9]' )"
  if [ -n "$hits" ]; then echo "$hits" | sed 's/^/      /'; fail "no threshold literal in evaluators/adapters/agents"; else pass "no threshold literal in evaluators/adapters/agents"; fi
}

check_evaluate_import() {
  local files hits
  files="$(pyfiles prooflab adapters agents | grep -Ev '/(evaluators)/' | grep -Ev '/adapters/runtime/model_call\.py$' || true)"
  if [ -z "$files" ]; then na "evaluate imported only by model_call.py"; return; fi
  hits="$(echo "$files" | xargs grep -nE '^[[:space:]]*(from[[:space:]]+[A-Za-z0-9_.]+[[:space:]]+import[^#]*\bevaluate\b|import[[:space:]]+[^#]*\bevaluate\b)' 2>/dev/null)"
  if [ -n "$hits" ]; then echo "$hits" | sed 's/^/      /'; fail "evaluate imported only by adapters/runtime/model_call.py"; else pass "evaluate imported only by adapters/runtime/model_call.py"; fi
}

check_agents_py() {  # two-stage layout (D-B): c16 sha marker on every bundle that embeds the core; size per file; buildspec size
  local bundles specs
  bundles="$(find "$ROOT/agents" -type f -name 'ifabric-*.py' 2>/dev/null | sort)"
  specs="$( { find "$ROOT/tools" -maxdepth 1 -type f -name '*buildspec*' 2>/dev/null; find "$ROOT/agents" -type f -name 'buildspec*.yml' 2>/dev/null; } | sort)"
  if [ -z "$bundles" ]; then na "embedded c16 core sha256 (no agents/*/ifabric-*.py)"; na "bundle size <= 24000 (no bundles)"; fi
  if [ -z "$specs" ]; then na "buildspec size <= 25600 (no buildspec files)"; fi
  if [ -z "$bundles" ] && [ -z "$specs" ]; then return; fi
  local py="${PY39:-$HOME/firstmate-homes/TrustworthyAI/workshop-local/.venv-py39/bin/python}"
  [ -x "$py" ] || py="$(command -v python3)"
  local out code
  IFS= read -r -d '' code <<'PY'
import base64, gzip, hashlib, os, re, sys
root = os.environ["ROOT"]
core = os.path.join(root, "prooflab", "evaluators", "c16_core.py")
bundles, specs = [], []
for dp, _, fns in os.walk(os.path.join(root, "agents")):
    for fn in fns:
        full = os.path.join(dp, fn)
        if fn.startswith("ifabric-") and fn.endswith(".py"):
            bundles.append(full)
        elif fn.startswith("buildspec") and fn.endswith(".yml"):
            specs.append(full)
tools = os.path.join(root, "tools")
if os.path.isdir(tools):
    for fn in os.listdir(tools):
        if "buildspec" in fn and os.path.isfile(os.path.join(tools, fn)):
            specs.append(os.path.join(tools, fn))
bundles.sort(); specs.sort()
want = hashlib.sha256(open(core, "rb").read()).hexdigest() if os.path.exists(core) else None
pat = re.compile(r"(?:evaluator[_.]sha256|c16_core[_a-z]*sha256|C16_CORE_SHA256)\W{0,8}([0-9a-f]{64})", re.I)
# the embedded module key: a quoted dotted name used as a dict key (an import line is not an embed)
key = re.compile(r"""["']prooflab\.evaluators\.c16_core["']\s*:""")
for b in bundles:
    rel = os.path.relpath(b, root)
    data = open(b, "rb").read()
    text = data.decode("utf-8", "replace")
    found = pat.findall(text)
    is_base = os.path.basename(os.path.dirname(b)) == "ifabric-base"
    embeds = bool(found) or bool(key.search(text))
    if is_base or embeds:
        if want is None:
            print("SHA FAIL %s: prooflab/evaluators/c16_core.py is missing" % rel)
        elif not found:
            print("SHA FAIL %s: embeds the c16 core but has no sha256 marker" % rel)
        elif any(f.lower() != want for f in found):
            print("SHA FAIL %s: embedded %s != repo %s" % (rel, sorted(set(found))[0][:12], want[:12]))
        else:
            print("SHA OK %s" % rel)
    else:
        print("SHA NA %s: no c16 core embedded (role/assurance bundle)" % rel)
    size = len(base64.b64encode(gzip.compress(data, 9, mtime=0)))
    print("SIZE %s %s %d" % ("OK" if size <= 24000 else "FAIL", rel, size))
for sp in specs:
    rel = os.path.relpath(sp, root)
    n = len(open(sp, "rb").read().decode("utf-8", "replace"))
    print("SPEC %s %s %d" % ("OK" if n <= 25600 else "FAIL", rel, n))
PY
  out="$(ROOT="$ROOT" "$py" -c "$code")"
  echo "$out" | sed 's/^/      /'
  if [ -n "$bundles" ]; then
    if echo "$out" | grep -q '^SHA FAIL'; then fail "embedded c16 core sha256 equals prooflab/evaluators/c16_core.py"; else pass "embedded c16 core sha256 equals prooflab/evaluators/c16_core.py (N/A for bundles without the core)"; fi
    if echo "$out" | grep -q '^SIZE FAIL'; then fail "every agents/ifabric-*/ bundle gzip+base64 <= 24000 chars"; else pass "every agents/ifabric-*/ bundle gzip+base64 <= 24000 chars"; fi
  fi
  if [ -n "$specs" ]; then
    if echo "$out" | grep -q '^SPEC FAIL'; then fail "every buildspec <= 25600 chars"; else pass "every buildspec <= 25600 chars"; fi
  fi
}

check_forbidden() {
  local hits
  hits="$(find "$ROOT" \( -name .git -o -name node_modules \) -prune -o -type f -name 'agent.py' -print 2>/dev/null | grep -v '/tools/prototypes/' || true)"
  if [ -n "$hits" ]; then echo "$hits" | sed 's/^/      /'; fail "no file named agent.py"; else pass "no file named agent.py"; fi
  # the forbidden string is assembled from parts so this file never holds it
  local needle="approve""=True"
  hits="$(grep -rIn --include='*.py' --include='*.yaml' --include='*.yml' --include='*.json' --include='*.sh' \
      --exclude-dir=.git --exclude-dir=handoffs --exclude-dir=architecture --exclude-dir=notes --exclude-dir=hackathon-context \
      --exclude-dir=prototypes --exclude-dir=tests --exclude='gate.sh' --exclude='test_*.py' -- "$needle" "$ROOT" 2>/dev/null || true)"
  if [ -n "$hits" ]; then echo "$hits" | sed 's/^/      /'; fail "no $needle"; else pass "no $needle"; fi
}

check_console_secrets() {  # AT-06: no secret-shaped string under prooflab/console/
  if [ ! -d "$ROOT/prooflab/console" ]; then na "console AT-06 secret grep (no prooflab/console/)"; return; fi
  local a="AK""IA" b="AS""IA" k1="aws_secret""_access_key" k2="aws_session""_token" t="tk""n=" pem="-----BEGIN [A-Z ]*PRIV""ATE KEY-----"
  local gh="gh""p_[A-Za-z0-9]{20,}" ghp="github""_pat_" sk="s""k-[A-Za-z0-9]{20,}" xox="xo""x[bap]-[A-Za-z0-9-]{10,}" bearer="Bea""rer [A-Za-z0-9._~+/=-]{20,}"
  local pat="($a|$b)[A-Z0-9]{16}|$k1|$k2|$t|$pem|$gh|$ghp|$sk|$xox|$bearer"
  local hits
  hits="$(grep -rIlE -- "$pat" "$ROOT/prooflab/console" 2>/dev/null || true)"
  if [ -n "$hits" ]; then echo "$hits" | sed 's/^/      HIT: /'; fail "console AT-06 secret grep"; else pass "console AT-06 secret grep"; fi
}

# ---- run -------------------------------------------------------------------------------------------------
echo "== gate: $ROOT =="
if [ "$DO_TESTS" = 1 ]; then check_tests; else echo "SKIP  tests (--no-tests)"; fi
if [ "$DO_TESTS" = 1 ]; then check_arth_suite; else echo "SKIP  Arth suite (--no-tests)"; fi
check_arth_identity
check_threshold_literals
check_evaluate_import
check_agents_py
check_forbidden
check_console_secrets

if [ "$DO_INTEG" = 1 ] || { [ "$DO_INTEG" = auto ] && [ "$DO_TESTS" = 1 ]; }; then check_integration
else echo "SKIP  integration stage (--no-integration or --no-tests; --integration forces it)"; fi

SCAN_SKIPPED=0
if [ "$DO_SCAN" = 1 ]; then
  if [ ! -f "$SCAN_SCRIPT" ]; then fail "secret scan script missing: $SCAN_SCRIPT"
  else
    scan_out="$(bash "$SCAN_SCRIPT" "$ROOT" 2>&1)"
    echo "$scan_out" | tail -12 | sed 's/^/      /'
    if echo "$scan_out" | grep -q '^RESULT: clean'; then pass "secret scan: RESULT: clean"; else fail "secret scan did not print RESULT: clean"; fi
  fi
else
  echo "SCAN SKIPPED (--no-scan): this gate result is NOT mergeable until the scan prints RESULT: clean"
  SCAN_SKIPPED=1
fi

if [ "$FAILS" -gt 0 ]; then echo "GATE: FAILED ($FAILS check(s))"; exit 1; fi
if [ "$SCAN_SKIPPED" = 1 ]; then echo "GATE: all other checks green; scan skipped (exit 3)"; exit 3; fi
echo "GATE: green"; exit 0
