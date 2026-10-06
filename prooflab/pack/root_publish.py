"""Root published (unsigned): post the pack's MANIFEST sha256 to ServiceNow as one work note (PR-32).

  python3 -m prooflab pack root --label submit-1|submit-2|final --s3-version-id <id> \
      --incident-sys-id <sys_id> (--pack-dir <dir> [--zip <zip>] | --zip <zip>) [--sidecar <path>] [--dry-run]
  python3 -m prooflab pack root --recompute <dir-or-zip>      # print the MANIFEST sha256 (the judge check)

What this is: a dated, outside-our-control copy of one hash. What it is not: a signature or a hash
chain; per-producer signing is out of scope (masterclass slide section 4). The note carries only the
label, the MANIFEST sha256, the zip sha256 if any, and the S3 version id: no URL, no bucket, no
account id. The sidecar pack-root.json lives OUTSIDE the MANIFEST (the MANIFEST cannot contain the
note that hashes it) and is uploaded AFTER the pack. The live call is made by the ops lane only, with
the ServiceNow environment sourced there; this module never reads a credential file. The client is
Arth's, used only through add_work_note and list_work_notes (never edited). Standard library; 3.9.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

from prooflab.contract.record import secret_shaped
from prooflab.servicenow.client import ServiceNowError

LABELS = ("submit-1", "submit-2", "final")
MANIFEST_NAME = "MANIFEST.json"
SIDECAR_NAME = "pack-root.json"
SCHEMA = "ifabric.pack-root/v1"
HONEST_LINE = ("root published (unsigned): MANIFEST sha256 posted to ServiceNow; not a signature or chain "
               "- per-producer signing is out of scope (masterclass slide §4)")
_HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
_TWELVE_DIGITS = re.compile(r"(?<!\d)\d{12}(?!\d)")
_URLISH = re.compile(r"(?i)(://|\bwww\.|\bs3:|\barn:|[a-z0-9-]+\.(com|net|org|io|aws|amazonaws|service-now)\b|\.amazonaws\b)")
_VERSION_ID = re.compile(r"^[A-Za-z0-9._~+=-]{1,128}$")


class RefusedNote(Exception):
    """The note text or one of its inputs failed a check; nothing was posted."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def manifest_sha256(src):
    """sha256 of MANIFEST.json bytes, from a pack directory or from the zip (top level or one folder down)."""
    if os.path.isdir(src):
        p = os.path.join(src, MANIFEST_NAME)
        if not os.path.isfile(p):
            raise RefusedNote("no %s in %s" % (MANIFEST_NAME, src))
        return sha256_file(p)
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            names = sorted((n for n in z.namelist() if n.split("/")[-1] == MANIFEST_NAME and n.count("/") <= 1),
                           key=lambda n: n.count("/"))
            if not names:
                raise RefusedNote("no %s in the zip" % MANIFEST_NAME)
            return sha256_bytes(z.read(names[0]))
    raise RefusedNote("not a directory or zip: %s" % src)


def check_version_id(version_id):
    if not isinstance(version_id, str) or not _VERSION_ID.match(version_id):
        raise RefusedNote("S3 version id missing or has unexpected characters")
    if _URLISH.search(version_id) or _TWELVE_DIGITS.search(version_id):
        raise RefusedNote("S3 version id looks like a URL, ARN or account id")
    return version_id


def build_note(label, manifest_sha, zip_sha, version_id):
    """The exact note text. Refuses a bad label, a URL-like or 12-digit value, or any secret-shaped text."""
    if label not in LABELS:
        raise RefusedNote("label must be one of " + ", ".join(LABELS))
    for name, v in (("manifest sha256", manifest_sha), ("zip sha256", zip_sha)):
        if v is not None and not re.match(r"^[0-9a-f]{64}$", v):
            raise RefusedNote(name + " is not a sha256 hex digest")
    check_version_id(version_id)
    lines = ["pack root: " + label, "MANIFEST sha256: " + manifest_sha]
    if zip_sha:
        lines.append("zip sha256: " + zip_sha)
    lines.append("S3 VersionId: " + version_id)
    lines.append(HONEST_LINE)
    text = "\n".join(lines)
    scrubbed = _HEX64.sub("", text)  # a hash may hold a 12-digit run by chance; everything else may not
    if _URLISH.search(scrubbed):
        raise RefusedNote("note text looks like it holds a URL, bucket or ARN")
    if _TWELVE_DIGITS.search(scrubbed):
        raise RefusedNote("note text holds a 12-digit run (account id shape)")
    if secret_shaped(text):
        raise RefusedNote("note text is secret-shaped")
    return text


def _display(v):
    return v.get("display_value") if isinstance(v, dict) else v


def find_journal_time(client, sys_id, text):
    """(sys_created_on, match_count) of the journal entry whose value equals the note; newest match."""
    want = sha256_bytes(text.encode("utf-8"))
    rows = [r for r in client.list_work_notes(sys_id)
            if isinstance(r, dict) and sha256_bytes(str(_display(r.get("value")) or "").encode("utf-8")) == want]
    if not rows:
        return None, 0
    rows.sort(key=lambda r: str(_display(r.get("sys_created_on")) or ""))
    return _display(rows[-1].get("sys_created_on")), len(rows)


_HEADER = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - [^\n]*\(Work notes\)\n$")


def _time_from_display(client, sys_id, text):
    """Fallback when the journal table is hidden by an ACL: the incident's display work notes carry
    '<time> - <author> (Work notes)' above each entry (newest first)."""
    shown = _display(client.get_incident_notes_text(sys_id).get("work_notes")) or ""
    at = shown.find(text)
    exact = at >= 0 and shown[at + len(text):at + len(text) + 1] in ("", "\n")  # not edited after the text
    m = _HEADER.search(shown[:at]) if exact else None
    return (m.group(1), 1) if m else (None, 0)


def publish(label, pack_src, version_id, sys_id, client, zip_path=None, sidecar=None, dry_run=False, out=None):
    """Hash, build the note, post it once, read the journal back, write the sidecar. Returns (code, sidecar dict)."""
    out = out or sys.stdout
    msha = manifest_sha256(pack_src)
    zsha = sha256_file(zip_path) if zip_path else None
    text = build_note(label, msha, zsha, version_id)
    if dry_run:
        out.write(text + "\n")
        return 0, None
    if sidecar:
        side = os.path.realpath(sidecar)
        if os.path.isdir(pack_src) and side.startswith(os.path.realpath(pack_src) + os.sep):
            raise RefusedNote("the sidecar must live outside the pack directory (the MANIFEST must not list it)")
    posted = client.add_work_note(sys_id, text)  # exactly one PATCH, work_notes only
    number = _display(posted.get("number")) if isinstance(posted, dict) else None
    try:
        time_, matches = find_journal_time(client, sys_id, text)
    except ServiceNowError:
        try:
            time_, matches = _time_from_display(client, sys_id, text)
        except ServiceNowError:
            time_, matches = None, 0
    if not number:
        try:
            number = _display(client.get_incident(sys_id).get("number"))
        except ServiceNowError:
            number = None
    record = {"schema": SCHEMA, "label": label, "manifest_sha256": msha, "zip_sha256": zsha,
              "s3_version_id": version_id, "servicenow_incident_number": number,
              "note_journal_time": time_, "note_text_sha256": sha256_bytes(text.encode("utf-8")),
              "readback": "matched" if time_ else "NOT FOUND in the journal", "readback_matches": matches,
              "unsigned": True, "note": "Not in MANIFEST.json (it cannot hold the note that hashes it); uploaded after the pack."}
    if sidecar:
        os.makedirs(os.path.dirname(os.path.abspath(sidecar)), exist_ok=True)
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, sort_keys=True)
            f.write("\n")
    return (0 if time_ else 1), record


def main(argv=None, client=None, out=None):
    out = out or sys.stdout
    p = argparse.ArgumentParser(prog="prooflab pack root")
    p.add_argument("--recompute", help="print the MANIFEST sha256 of a pack dir or zip and exit")
    p.add_argument("--label", choices=LABELS)
    p.add_argument("--pack-dir")
    p.add_argument("--zip")
    p.add_argument("--s3-version-id")
    p.add_argument("--incident-sys-id")
    p.add_argument("--sidecar", default=os.path.join("evidence", SIDECAR_NAME),
                   help="default evidence/pack-root.json; must be outside the pack dir")
    p.add_argument("--dry-run", action="store_true", help="print the note text; post nothing")
    a = p.parse_args(argv)
    try:
        if a.recompute:
            out.write(manifest_sha256(a.recompute) + "\n")
            return 0
        src = a.pack_dir or a.zip
        if not (a.label and src and a.s3_version_id) or not (a.dry_run or a.incident_sys_id):
            print("pack root: need --label, --s3-version-id, --pack-dir or --zip, and --incident-sys-id", file=sys.stderr)
            return 2
        if client is None and not a.dry_run:
            from prooflab.servicenow.client import ServiceNowClient  # Arth's client, environment set by the ops lane
            client = ServiceNowClient.from_env()
        code, rec = publish(a.label, src, a.s3_version_id, a.incident_sys_id, client, zip_path=a.zip,
                            sidecar=a.sidecar, dry_run=a.dry_run, out=out)
    except RefusedNote as exc:
        print("pack root: REFUSED: " + str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print("pack root: " + str(exc), file=sys.stderr)
        return 2
    if rec:
        out.write("root published (unsigned): %s, incident %s, journal time %s; sidecar %s\n"
                  % (rec["label"], rec["servicenow_incident_number"], rec["note_journal_time"], a.sidecar))
        if code:
            print("pack root: the note was posted but not found on read-back; check the incident", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
