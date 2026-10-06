# Evidence Pack: team iFabric

> **Template.** This is the stranger's README for the pack. Every `<...>` is filled at submit; the
> text claims nothing that a record in this pack does not show. Delete this note when filled.

**For:** a sceptical stranger (a judge or an auditor), now or years later. It explains how to check
each verdict **without us**: one command per question, standard-library Python 3.9 or later, no
network.

## 1. What this pack covers

- **Claim:** "During fault resolution, the three collaborating agents meet our declared
  event-recording, drift and token-spend requirements." (the slides' wording, verbatim)
- **Declared event window (UTC):** `<WINDOW_START>` to `<WINDOW_END>`. Written before judging and
  filled at submit. Only runs inside this window are in scope; `--runs` (section 4) lists every
  run in it, including pilots, baselines and adversarial runs, each labelled as what it is.
- **Controls:** C16 (per-run token cap), C7 (event recording), C9 (drift and performance). Each
  control's threshold, owner and version is in `register/`; its date proof is the write-once object
  recorded in section 7.
- **Named runs** (written down before judging): `run-ids.txt` (one correlation id per line) and
  `named-runs.md` (control, role, every attempt, window, register and control version, mode,
  condition, incident).
- **Who owns what:** the accountable owner approves the thresholds; the builder does not approve
  their own work (section 10).

**The pillars, and where each is in this pack.** One row per pillar; no row is empty. A cell that
names a file is a claim only if that file is in the pack; `<...>` is filled at submit from what
the pack holds, and a pillar with nothing yet says so in the status column.

| Pillar | What we claim | Files that show it | Status at this submit |
|---|---|---|---|
| Close the gap (judgment) | The agents' dispositions carry deciding evidence and a reason, validated by code | `store/` judgment records, `answers/`, `gap-list.md` gap 1 | `<FULL / PARTIAL; if J2 did not ship, gap 1 is open and this row says so>` |
| Build a control | C16, C7 and C9 each run against a dated, versioned register with two named runs | `register/`, `named-runs.md`, `assessments/`, `security-matrix.md` | `<per control: assessed / not assessed yet>` |
| Handover proof | A stranger answers the six auditor questions from the pack alone | `prooflab query --incident`, `store/`, `gap-list.md` | `<per question: FULL / PARTIAL, and what arrives later>` |

**Second enforcement point.** The same C16 core function runs at EP-1 (inline, in the agent) and at
EP-2 (after the run, over the gateway's log). `<adapter-diff PR sha, its git diff --stat, and the
core's sha256 at EP-1 and EP-2; filled at submit, and the two hashes must be equal>`. The
full list of enforcement points is `security-matrix.md`.

## 2. Retention

Kept for `<RETENTION_RULE>` from the submission date (`<YYYY-MM-DD>`). *(Hackathon note: the event
account is deleted after the event; this states the rule we would operate under in production.)*

## 3. Was anything changed after hand-in?

1. Every file is listed in `MANIFEST.json` with its SHA-256 and size. Check it:
   `python3 tools/manifest.py verify .` should print `OK` and exit 0; any changed byte makes it exit 1.
   Run it **before** you run anything else from this pack, or set `PYTHONDONTWRITEBYTECODE=1` first
   (`export PYTHONDONTWRITEBYTECODE=1`): Python otherwise writes `prooflab/__pycache__/`, and the
   check then lists those files as unlisted. If that happens, delete the `__pycache__` folders and
   run it again. (`python3 -m prooflab pack verify .` does the same check and ignores bytecode.)
2. Raw captures under `raw/` are never edited; a correction is a new file.
3. The upload's key, version id and time are recorded in section 7 (set by AWS, not by us).
4. **Root published (unsigned).** At each submit (`<submit-1 / submit-2 / final>`) we posted the
   SHA-256 of `MANIFEST.json` as a work note on ServiceNow incident `<INCnnnnnnn>`, a system we do
   not control that stamps its own time. Check it in three steps: (a) recompute the hash from this
   pack: `python3 -m prooflab pack root --recompute .` (same value as `shasum -a 256 MANIFEST.json`);
   (b) compare it with the note's `MANIFEST sha256` line, and confirm the note's journal time
   (`<NOTE_JOURNAL_TIME_UTC>`, also in `pack-root.json`) is before the deadline; (c) compare the note's
   `S3 VersionId` with the version id of the uploaded object in section 7. `pack-root.json` (label,
   both hashes, version id, incident, journal time, note hash) is a sidecar uploaded after the pack,
   so it is not listed in the MANIFEST (the MANIFEST cannot contain the note that hashes it).
   **Honest label:** root published (unsigned): this is a dated copy of one hash, not a signature or
   a chain; per-producer signing is out of scope (masterclass slide section 4).
5. **What this is not.** It is a checksum list. It is not a signature or hash chain, and the audit
   store has no verification route of its own, so there is no "ledger verification output" in this
   pack. We corroborate records against surfaces written outside the agents (the gateway's spans,
   the platform's decision records, the AWS invocation records) and report any mismatch in
   `derived/corroboration/`. That is corroboration, not proof.

## 4. Answer the questions yourself

Run these from the folder that holds `prooflab/` (the unzipped pack), with
`export PYTHONDONTWRITEBYTECODE=1` set first so nothing is written into the pack. Each prints the rule, its
version and date, owner, population, measured value against the limit, exceptions, verdict, gaps
and the record references.

| Question | Command |
|---|---|
| Was control C16 satisfied for run R? | `python3 -m prooflab query --control C16 --run <CID>` |
| Was control C7 satisfied for run R? | `python3 -m prooflab query --control C7 --run <CID>` |
| Was control C9 satisfied for run R? | `python3 -m prooflab query --control C9 --run <CID>` |
| Was C16 satisfied across a time window? | `python3 -m prooflab query --control C16 --window <T1>..<T2>` |
| What happened in an incident (any run id or time in the window)? | `python3 -m prooflab query --incident <CID-or-time>` |
| Which runs are in the declared window, and what is each? | `python3 -m prooflab query --runs` |

An incident answer covers the six auditor questions (who acted, what it touched, was it
authorized, who approved, can it be trusted, can it be reconstructed), each with its record ids
and the limit of what the platform can show. The limits are in `gap-list.md`; read them with the
answers.

**Recompute by hand, without our tool.**
- **C16:** keep the gateway's spans (`raw/`, `aws/spans`) whose run id is the CID; add the
  input and output tokens of every model call, retries included; compare with the register's limit
  for that run's version. Over the limit means not satisfied.
- **C7:** `<expected-event source, reconciliation and gap rule, from the register>`
- **C9:** `<baseline, closed UTC windows, relative change, crossings; a missing window is a monitoring gap>`

### Open the console (optional, read-only)

The same stored answers, the six auditor questions, the run catalogue and the records in a browser, on
your own machine, nothing leaves it. From the folder that holds `prooflab/`:

```
export PYTHONDONTWRITEBYTECODE=1
python3 -m prooflab console --data pack --pack .
```

It prints a one-time URL on `127.0.0.1`; open it, then type a question (for example `control 16 for run <CID>`).
It refuses to start on synthetic data, and its banner says whether `MANIFEST.json` still matches. The console
only shows what the pack stores: `answers/` holds the answers composed at build by the same engine as the
section 4 commands (C16 and C7 per run), `pack-index.json` is its table of contents, and `records/` its
evidence records. Anything not stored there (for example a window or an auditor view not yet composed) is
answered "nothing stored"; use the section 4 commands for it. The section 4 commands are the authority.

## 5. Layout

```
README.md            this file                 MANIFEST.json   SHA-256 of every file
run-ids.txt          named runs, written before judging
named-runs.md        the same runs with role, window, versions, mode, condition, incident
gap-list.md          what we could not close, why, impact, next step (section A: Arth; B: ours)
decisions-log.md     dated decisions
register/            the frozen registers, the date proofs, the approval
raw/                 captures as pulled (redacted by our collector)
store/               the stitched evidence records
assessments/         one JSON per control and scope
answers/             stored answers the console shows (composed at build by the query engine)
pack-index.json      the console's table of contents; records/ and projected-assessments/ are its projections
adversarial/         pre-registered defence, observed outcome, what broke, what changed
servicenow/          delivery log, incidents, Assurance Agent records
prooflab/            the tool (standard library only)
tools/manifest.py    the integrity check
```

## 6. The honest failure

`<Fill at rehearsal from what happened. Default, if ADV-R-06 ran as planned:>` One adversarial case
was built to be passed and did not: a forged token tally in the run envelope (ADV-R-06). The
in-path check trusts the tally it is handed, because the frame allows no store read in the path, so
the inline guard was fooled. The post-run floor, which counts the gateway's own figure, still
flagged the overspend. The change we made afterwards and its re-test (ADV-R-06b) are linked in
`adversarial/`. Also stated here, because they are recorded elsewhere as ALLOW: calls the
guardrail blocked (gap 4 in `gap-list.md`), and any control we could not make breach (named in the
gap list). If a result in this pack differs from the above, the pack wins and this paragraph is wrong.

## 7. Submission record

`<bucket, keys, version ids, upload time (UTC), the write-once register object and its time,
read-back result, MANIFEST verify result>` Filled after upload; the readback is recorded, not edited.

## 8. ServiceNow: the human loop and the Assurance Agent

`<Filled from servicenow/ at submit.>` Every breach became an incident assigned to the named owner,
read back after writing. The delivery log is append-only. A reply is not required; silence is
recorded only after the stated cutoff `<CUTOFF_UTC>`. `DELIVERED` means read back with the right
correlation id; it does not prove the owner read it. The Assurance Agent's analysis counts only if its
SHA-256 is in the delivery log; a look-alike note is flagged, never trusted. Section A of
`gap-list.md` lists the limits.

## 9. What was left out, and why

- **Signing, hash chains and sealing of the records:** out of scope for this challenge; the MANIFEST
  is a checksum list only.
- **The reference trio is not assessed:** it is the "before" system; our controls apply to our own
  `ifabric-` agents.
- **Per-agent platform identity, per-agent Cedar, a per-run platform spend limit:** the platform does
  not provide them (gaps 2, 3, 8); we show what we recorded and where it stops.
- **Guardrails we could not create or edit, and NVIDIA safety models:** not available to us (rails
  gaps G-1 to G-3); our own in-agent rails are self-enforced and their misses are published.
- **Items listed as open in `gap-list.md`:** anything marked `<update before each submit>` there
  had no result at the time of this submit.
- `<anything cut during the build, with the reason>`

## 10. Test-only material and people

Anything labelled wiring test or TEST ONLY proves an integration works but is **not** a control
result and is excluded from every verdict.

- **Owner** (accountable; approves thresholds): `<owner name and contact>`
- **Builder** (AWS agents, controls): `<builder>`
- **ServiceNow integration and the Assurance Agent:** Arth

Nobody approves their own work: Arth reviews before the owner approves. The governance-assurance
role is vacant (stated in `gap-list.md`).
