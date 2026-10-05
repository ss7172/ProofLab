#!/usr/bin/env python3
"""Bundle an evidence directory into the dashboard's evidence pack.

    python3 tools/pack_evidence.py --evidence ~/evidence [--app-out ~/evidence/dashboard]

Reads the layout described in dashboard/README.md, writes dashboard/data/evidence-pack.js
(loaded by index.html, works from file://) and evidence-pack.json (for the "Load evidence pack"
button), and computes a SHA-256 MANIFEST of every input file. Sections that are missing are left
out on purpose: the dashboard reports them as gaps instead of showing an empty page.
With --app-out it also copies the whole dashboard next to the evidence, so the judges' S3 bucket
holds an app that opens by double-clicking index.html.
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "dashboard"
SECTIONS = ["meta", "runs", "expected_events", "metric_windows", "human_loop", "levels", "architecture",
            "adversarial", "gaps", "auditor", "artefacts"]
REGISTER_KEYS = ["metric", "observation_limit", "exception_tolerance", "measurement_basis", "owner"]


def fail(msg):
    sys.exit("pack_evidence: " + msg)


def load_register(ev):
    for name in ("register/register.json", "register/register.yaml", "register.yaml", "register.json"):
        p = ev / name
        if not p.exists():
            continue
        if p.suffix == ".json":
            return json.loads(p.read_text()), p
        try:
            import yaml
        except ImportError:
            fail(f"{p} is YAML but PyYAML is not installed (pip install --user pyyaml), or provide register.json")
        return yaml.safe_load(p.read_text()), p
    fail("no register found (register/register.yaml or register/register.json)")


def check_register(reg):
    problems = []
    for k in ("version", "version_date", "controls"):
        if k not in reg:
            problems.append(f"register missing '{k}'")
    controls = reg.get("controls") or {}
    for c in ("C16", "C7", "C9"):
        if c not in controls:
            problems.append(f"register has no {c}")
    for c, rule in controls.items():
        for k in REGISTER_KEYS + ["figure_of_record_ep"]:
            if k not in rule:
                problems.append(f"register {c} missing '{k}'")
        lim = rule.get("observation_limit")
        tol = rule.get("exception_tolerance")
        if not isinstance(lim, dict) or not isinstance(tol, dict):
            problems.append(f"register {c}: observation_limit and exception_tolerance must be objects (see dashboard/README.md)")
            continue
        need = {"C16": (["operator", "value"], ["max_breaching_runs"]),
                "C7": (["coverage_min_pct", "gap_operator", "gap_limit_ms"], ["max_violating_gap_pct"]),
                "C9": (["operator", "max_relative_increase_pct"], ["max_violating_windows_pct"])}.get(c)
        if need:
            problems += [f"register {c}.observation_limit missing '{k}'" for k in need[0] if k not in lim]
            problems += [f"register {c}.exception_tolerance missing '{k}'" for k in need[1] if k not in tol]
        if c == "C9":
            if not isinstance(rule.get("baseline"), dict) or not rule["baseline"]:
                problems.append("register C9 needs baseline: {<runtime>: {value, unit, id, frozen_at}}")
            if "coverage_min_pct" not in rule:
                problems.append("register C9 missing 'coverage_min_pct'")
    return problems


def read_jsonl(paths):
    out = []
    for p in paths:
        for i, line in enumerate(Path(p).read_text().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                fail(f"{p}:{i} is not valid JSON ({e})")
    return out


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, help="evidence directory (see dashboard/README.md)")
    ap.add_argument("--out", default=str(APP / "data"), help="where to write evidence-pack.js and .json")
    ap.add_argument("--app-out", help="also copy the dashboard here (for the S3 submission)")
    ap.add_argument("--provenance", default="LIVE", help="LIVE for real runs; never label sample data LIVE")
    a = ap.parse_args()
    ev = Path(os.path.expanduser(a.evidence)).resolve()
    if not ev.is_dir():
        fail(f"{ev} is not a directory")

    register, reg_path = load_register(ev)
    problems = check_register(register)
    pack = {"schema_version": "1.0", "register": register}
    for s in SECTIONS:
        p = ev / "pack" / f"{s}.json"
        if p.exists():
            pack[s] = json.loads(p.read_text())
    pack.setdefault("meta", {})
    pack["meta"].update({"provenance": a.provenance, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "generator": "tools/pack_evidence.py"})
    pack["records"] = read_jsonl(sorted(glob.glob(str(ev / "records" / "**" / "*.jsonl"), recursive=True)))
    pack["assessments"] = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(ev / "assessments" / "**" / "*.json"), recursive=True))]

    skip = {str((Path(a.out) / n).resolve()) for n in ("evidence-pack.js", "evidence-pack.json")}
    manifest = []
    for p in sorted(ev.rglob("*")):
        if p.is_file() and str(p.resolve()) not in skip and "dashboard" not in p.relative_to(ev).parts:
            manifest.append({"path": str(p.relative_to(ev)), "sha256": sha256(p), "bytes": p.stat().st_size})
    pack["manifest"] = manifest

    ids = [r.get("id") for r in pack["records"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate record ids")
    missing = [s for s in SECTIONS if s not in pack]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    body = json.dumps(pack, indent=1, default=str)
    (out / "evidence-pack.json").write_text(body)
    (out / "evidence-pack.js").write_text("/* Evidence pack generated by tools/pack_evidence.py from " + str(reg_path.parent.parent if reg_path.parent.name == "register" else reg_path.parent) +
                                          " */\nwindow.EVIDENCE_PACK = " + body + ";\n")
    if a.app_out:
        dest = Path(os.path.expanduser(a.app_out))
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(APP, dest, ignore=shutil.ignore_patterns("tests"))
        shutil.copy(out / "evidence-pack.js", dest / "data" / "evidence-pack.js")
        shutil.copy(out / "evidence-pack.json", dest / "data" / "evidence-pack.json")
    print(f"pack: {len(pack['records'])} records, {len(pack.get('runs', []))} runs, {len(pack['assessments'])} assessments, "
          f"{len(manifest)} files in MANIFEST -> {out}")
    if missing:
        print("sections not supplied (the dashboard will show them as gaps): " + ", ".join(missing))
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
