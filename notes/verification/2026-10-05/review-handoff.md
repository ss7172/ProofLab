# Independent review: `PLANNING-HANDOFF.md`

Reviewer: an independent subagent that did not write the handoff. Review run 2026-10-05, 18:02–18:20 UTC, against the file as saved at 18:01:29Z (510 lines).

## Verdict

**Ready after fixes.** The handoff covers all four of the user's asks and the promised §0–§10. The corrections table matches the lead report. The adapter bugs are stated correctly and confirmed. §7's live state matches the cluster. No secrets are present.

| Severity | Count | Note |
|---|---|---|
| ERROR | 2 | E1 is a factual claim that feeds the C9 statistic decision. E2 is a nonexistent cited path, low impact. Neither needs a rework. |
| IMPRECISE | 19 | Attributions, wording, small factual drift |
| GAP | 10 | G1, the ledger token in the kit's evidence pull and in the submission zip, is the one that matters most |
| STYLE | 8 | |

## Method (all read-only)

- **Read:**
  - the whole handoff and all 13 memory files (the primary and mirror copies are identical)
  - `gap-list.md`, the headings of `notes/platform-observations.md` and the cited items, `notes/servicenow/servicenow-context.md`, every report in `notes/verification/2026-10-05/`, `notes/playbook/playbook-verification.md`
  - the playbook (§1–§3, parts of §4), the whole SN handoff, and `prooflab/` (`cli.py`, `notifier.py`, `finding.py`, `delivery_log.py`, tests)
  - the snapshot's `MANIFEST.txt`, with the gateway and ledger statistics recomputed from the snapshot files
  - the kit's `starter/` and `workshop-static/`
  - the primary sources: the slides text, the transcript, the brief, kickoff-deck PDF pages 2, 5–8 and 21–24 via `pdftotext`, and the judging-slide image
- **Live checks, 18:03–18:15Z, through `env.sh`, read verbs only:**
  - Model/Tool/AgentConfig: phase, paused, dependsOn, generation, approval subject and time, empty or non-empty signature, and env-var NAMES and value types only
  - pods, the PVC and PV, ConfigMaps, HTTPRoute count
  - AgentCore `list-agent-runtimes`, and `get-agent-runtime` with `--query roleArn` only
  - CFN `describe-stacks`, the S3 object count, EKS logging
  - CloudWatch AgentCore metrics, and one log group's retention
- **Docker:** `docker ps -a` and `docker inspect`. I also read Docker Desktop's settings file (keys only) and grepped its backend log.
- **Tests:** the 46 `prooflab` tests ran on a scratchpad copy with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`, so the repo was untouched. Result: 46 passed.
- **No other writes:** the only files written are this one and the scratchpad test copy. No secret values were printed.

## Coverage

| Requirement | Where in the handoff | Result |
|---|---|---|
| The user's four asks: goal / what must be achieved / what must be done / winning handbook | §1 / §2 / §3 / §4 | Covered |
| §0–§10 as promised | All present | Covered |
| Critical questions from memory `challenge-requirements` (9) | §3b Q1–Q9, with extras Q10–Q17 | All 9 covered |
| First time-sensitive decision (IT on nano-9b vs the C9 baseline) | §3a item 1, the first row | Covered. Add G10 (no baseline hour exists yet) and G6 (how a revert is done) |
| Separation of duties (the user, Sree, is both control owner and AWS builder; Arth does ServiceNow) | §1 Team, §3a item 7, §3b Q14, §9 | Covered. G8 adds the slides as the primary source |
| Steps needing the user's OK, or eating the shared budget | §3d | Covered, with corrections I3–I5 and G1 |
| Open inputs (Evidence Pack format, more slides, the "What the platform gives you" page) | §9 | Covered |
| What a fresh planner still lacks | — | G1 (token in evidence/zip), G2 (deliverable status), G3 (Cedar judge hint), G4 (facts for Q16), G5 (account lifetime), G9 (judging format) |

**Requirement 3, the corrections table.** Rows 1–17 are character-identical to `playbook-verify-lead.md` (and to `notes/playbook/playbook-verification.md`), except in rows 2, 7 and 13. There, the lead's source labels ("resources verifier, today", "glossary verifier") were expanded to file paths. **PASS.** The extra note under the table on row 13 is correct: live, the specs hold the ledger token as a literal string, and no gateway-key env names appear. Row 8 needs a similar note (E1).

**Requirement 3, the adapter bugs.** Stated as confirmed by code reading and offline reproduction, with file:line. I verified every line reference:
- `notifier.py` 89–92, 115–131, 132–136, 189–203, 230, 233–234
- `cli.py` 60 and 73
- `fake_servicenow.py` 173–174

The reproduction outputs exist (scratchpad `prooflab-review/a-log.jsonl` and `b-log.jsonl`):
- (a) gives `DELIVERED (reused=true)` on a dry run, and its INTENT entry has no dry-run marker.
- (b) gives RESPONDED, then NO_RESPONSE_OBSERVED after a later non-owner update.

The only test of the dry run runs it before any incident exists, so no test covers (a). **PASS**, with two attribution fixes (I7, I8).

**Requirement 3, the ledger after 09:13.** §3b Q16 is labelled "OBSERVATION to explain (not a conclusion)" and stays neutral. **PASS.** G4 adds neutral facts that bear on it.

**Requirement 4, no planning decisions.** All four recommendations (Q2, Q3, Q10, Q12) are labelled "Recommendation (not decided)". One exception: §3(c) row 5 pre-decides Q12 (I2).

**Requirement 5, hygiene.**
- The pre-push secret scan prints `RESULT: clean`.
- The handoff contains no cockpit token query parameter, no URLs, no AWS key IDs and no presigned links, and gives no method for forging or altering records.
- One literal email address is present: the commit-trailer address on line 462 (S3).
- Two approval-subject strings are shaped like addresses (S4).

---

## Findings

### ERROR

**E1. Line 184 (§3b Q10).**
- **Quote:** "In S2 Errors stayed 0; only the hourly Maximum (278 s) showed the runaway."
- **Evidence:**
  - Live CloudWatch, `AWS/Bedrock-AgentCore` `Latency`, dimensions Resource = IT runtime ARN, Operation = `InvokeAgentRuntime`, Name = `it_resolution_agent::DEFAULT`, period 3600, hour 2026-10-05T05:00Z:
    - Average **71,581 ms**, Maximum 278,394 ms, SampleCount 6
    - Errors, SystemErrors, UserErrors and Throttles all 0
  - Same hour, other runtimes: customer averaged 8,210.8 ms (max 16,604); network averaged 8,491.6 ms (max 12,827).
  - Memory `workshop-progress` records the same numbers ("IT avg 71.6 s, max 278.4 s").
  - So the Average also showed the runaway, at about 9× the other runtimes. The claim comes from correction row 8 of the lead report, which overstates it. Memory's own numbers are right.
- **Replacement for Q10 (whole item):**
  > 10. **The C9 statistic: Maximum + Errors Sum, or Average?** In the S2 hour (05:00Z) the IT runtime had Errors 0, an hourly Average of 71.6 s and a Maximum of 278.4 s over 6 invocations. The customer and network runtimes averaged 8.2 s and 8.5 s in the same hour [live CloudWatch, 18:10Z; mem: workshop-progress]. Errors missed the runaway. The Average showed it (about 9× the other runtimes), and the Maximum showed it most strongly; an hourly Average dilutes one long invocation across the hour's other invocations. Latency is per invocation and moves with call count. A refused run is fast (1.05 s), so fast ≠ healthy. Recommendation (not decided): Maximum + Errors Sum, and/or the gateway's per-call duration [mem: prooflab-project; notes/verification/2026-10-05/playbook-verify-lead.md row 8, and the note under §4.2].
- **Insert after line 259** (keep row 8 itself verbatim):
  > Note on row 8: the row keeps the lead report's wording, but our own numbers don't support "only hourly **Maximum** latency (278 s) revealed it" or "Average hides the runaway". In the S2 hour the IT runtime's hourly Average was 71.6 s, against 8.2–8.5 s for the other two runtimes [mem: workshop-progress; live CloudWatch, 18:10Z]. Maximum (278.4 s) is the stronger signal. The statistic is still open (§3b Q10).

**E2. Line 436 (§7.6). Low impact.**
- **Quote:** "`pods.txt`; `.captime-*` and `.err-*` per capture."
- **Evidence:**
  - `ls -A` of `evidence-snapshots/20261005T173727Z/` lists exactly 9 files: `MANIFEST.txt`, `pods.txt`, `ledger-records.jsonl`, the gateway log, 2 PDP logs, 2 authz logs and the audit-store log.
  - `find -name '.*'` returns nothing.
  - Capture times are inside `MANIFEST.txt`. Separate capture-time files exist only in the session scratchpad (`captimes.txt`, `ledger-captime.txt`), which won't survive the session.
- **Replacement:**
  > - `pods.txt` (pod inventory at 17:38:34Z). Per-file capture times and sha256 values are in `MANIFEST.txt`; the folder holds no other files. All six captured pods had 0 restarts.

### IMPRECISE

**I1. Line 176 (Q2).**
- **Quote:** "would each breach every real run and leave no PASS run"
- **Evidence:** §5.6's own `my-agent` run is 7,313 tokens, and memory puts the helper's Q1 at about 6.2K; both are under 10,000. Every measured S1/S3 run (24,796–50,246) is above all three caps. The reader's wording was "every real S1/S3 run".
- **Replacement:**
  > would each breach every measured S1/S3 fault-resolution run (24.8K–50.2K) and leave no PASS fault-resolution run (single-agent runs such as `my-agent`'s 7,313 tokens fall under 10,000)

**I2. Line 200 (§3(c) row 5). Pre-decides Q12.**
- **Quote:** "Also fix evidence emission (the self-check can't pass otherwise)."
- **Evidence:** Q12 leaves "fix the reference agents, or build our own" open. Correction row 4 says "fixed (or our own agents)".
- **Replacement:**
  > Evidence emission also needs fixing, in the reference agents or in our own agents (§3b Q12; the self-check can't pass otherwise).

**I3. Line 210 (§3d).**
- **Quote:** "Cockpit `POST /api/agents/{name}/ask` | Invokes an agent | Helper Q3 used 123K tokens"
- **Evidence:** memory `workshop-progress` and `hackathon-working-agreement`: Module 9 Step 1 made ONE cockpit POST (section 3, CID `hackathon-helper-1791189048-a9c9fc`) and 3× `ask-agent.sh` (Q1–Q3). Q3's 123,476 tokens came through `ask-agent.sh`.
- **Replacement (cells 2–3):**
  > Invokes an agent (same cost as asking it via `ask-agent.sh`) | A helper question via `ask-agent.sh` (Q3) used 123K tokens; the only cockpit POST so far was the section-3 question

**I4. Line 213 (§3d).**
- **Quote:** "Hits every agent; nano-9b served for 33–41 s"
- **Evidence:** live `dependsOn`: super-120b serves customer, network and `my-agent`; nano-9b serves only IT; the helper has its own alias. Any agent can call any approved tool (gap 3).
- **Replacement:**
  > Hits every agent that uses the paused asset (super-120b: customer, network, `my-agent`; nano-9b: IT; a tool: any agent that calls it, declared or not); nano-9b served for 33–41 s; stale pause conditions remain

**I5. Line 215 (§3d).**
- **Quote:** "`new-agent.sh --dry-run` / server dry runs | None stored"
- **Evidence:** memory `workshop-progress`, Step 1b A: the dry run wrote `~/agents/my-agent/` and `/tmp/my-agent-agentcore.dry-run.yaml` (mode 600). The generator writes the ledger token into that YAML.
- **Replacement (cell 2):**
  > Nothing stored in the cluster; writes `~/agents/<name>/` and a `/tmp/<name>-agentcore.dry-run.yaml` that holds the ledger token (use umask 077)

**I6. Line 264 (§4.3).**
- **Quote:** "response states RESPONDED/NO_RESPONSE_OBSERVED/RESPONSE_UNKNOWN"
- **Evidence:** `notifier.py:207–237` also returns AWAITING_RESPONSE and NOT_DELIVERED. `cli.py:81` exits 1 on NOT_DELIVERED and RESPONSE_UNKNOWN.
- **Replacement:**
  > response states RESPONDED/AWAITING_RESPONSE/NO_RESPONSE_OBSERVED/RESPONSE_UNKNOWN/NOT_DELIVERED (`check` exits 1 on NOT_DELIVERED and RESPONSE_UNKNOWN)

**I7. Line 277 (bug a).**
- **Quote:** "The SN handoff's own §5.4 dry run on `examples/test_finding.json` hits it, because INC0010231 exists."
- **Evidence:** the offline reproduction used a different finding on the fake server. That INC0010231 belongs to this finding is the SN handoff's claim (§2, §5.4), not ours; we have no instance access.
- **Replacement:**
  > The SN handoff's own §5.4 dry run on `examples/test_finding.json` would hit it, because, per the SN handoff, INC0010231 already exists for that finding (UNVERIFIED by us).

**I8. Line 278 (bug b).**
- **Quote:** "A `sys_journal_field` read that returns 0 rows with HTTP 200 (the ACL)"
- **Evidence:** SN handoff §11 item 8 says "ACL returns 0 rows, no error … verified live on INC0010231"; that is Arth's observation. The code path (`readable` stays True, lines 189–198) and the offline reproduction are ours.
- **Replacement:**
  > A `sys_journal_field` read that returns 0 rows with HTTP 200 (the live ACL behaviour per SN handoff §11 item 8; UNVERIFIED by us)

**I9. Line 292 (§4.4).**
- **Quote:** "as a code default, the owner's email address (`cli.py`)."
- **Evidence:** a masked grep finds the owner's work address in:
  - `SERVICENOW_INTEGRATION_HANDOFF.md` (7×)
  - `HACKATHON_WINNING_PLAYBOOK.md` (1×, §3.1)
  - `prooflab/servicenow/README.md` (1×)
  - `prooflab/servicenow/cli.py` (2×, :28)
  - our own committed `notes/verification/2026-10-05/playbook-verify-lead.md` (1×; its twin `notes/playbook/playbook-verification.md` redacts it)
- **Replacement:**
  > the integration username and the owner's work email address: the `cli.py:28` default, plus the SN handoff (7×), PB §3.1, `prooflab/servicenow/README.md` and our own committed `notes/verification/2026-10-05/playbook-verify-lead.md` (its redacted twin is `notes/playbook/playbook-verification.md`).

**I10. Line 300 (§5.1).** Two different gateways share one word.
- **Quote:** "explicitly denies direct model and gateway access; the gateway is the only model path"
- **Evidence:** live `get-agent-runtime --query roleArn`: all 5 runtimes use `a-01-eks-cluster-agentcore-runtime`. The Deny covers `bedrock:InvokeModel*` and `bedrock-agentcore:InvokeGateway`, which is the AWS AgentCore Gateway [mem: platform-verified-facts].
- **Replacement:**
  > All 5 AgentCore runtimes share one IAM role (`a-01-eks-cluster-agentcore-runtime`, re-checked live), which explicitly denies direct Bedrock model calls and `bedrock-agentcore:InvokeGateway` (the AWS AgentCore Gateway); the MoDaaS gateway `modaas-agw` is the only model path [notes #48].

**I11. Lines 369 and 379 (§6).**
- **Quotes:** "uncommitted working-tree change at 17:56Z" and, in gap 7's row, "events kept ~1 h" (the row is not marked "not yet in the file").
- **Evidence:**
  - The file's mtime is 17:54:48Z.
  - `git diff gap-list.md` adds to gap 7 only: the run_id export, PDP/authz logs pod-only, retention 30 d / 7 d, and the X-Ray action_id fix. Memory `prooflab-project` lists the same four.
  - Gap 6's diff also adds "bucket versioning unreadable", which the row omits.
- **Replacements:**
  - Line 369:
    > (uncommitted working-tree change, file saved 17:54:48Z; no new numbered gaps)
  - Gap-7 cell:
    > The export policy already declares run_id/action_id, yet none reach CloudWatch; X-Ray gateway spans carry `action_id` (a durable join); `components` events are kept ~1 h (not yet in the file) [notes/verification/2026-10-05/glossary-verify.md; notes/verification/2026-10-05/resources-verify.md]
  - Gap-6 cell, append:
    > ; the evidence bucket's versioning is unreadable to us

**I12. Lines 26 and 42 (§0.2, §0.3). The memory snapshot is stale.**
- **Evidence:**
  - `diff -rq` of live memory against `notes/claude-memory/`: 8 files differ (MEMORY, challenge-requirements, hackathon-working-agreement, platform-observations-notes, platform-verified-facts, prooflab-project, servicenow-context, workshop-progress).
  - `reference-links.md` is missing from the snapshot.
  - The snapshot was committed in `bfb1ce6` at 17:50Z; memory was edited until 17:56Z.
- **Replacement, line 26 (second cell):**
  > Memory file `X.md`. Auto-loaded from `~/.claude/projects/-/memory/` (the mirror is identical). An older snapshot (commit `bfb1ce6`, taken before the last memory edits, with no `reference-links.md`) is in repo `notes/claude-memory/`; trust the live memory
- **Replacement, line 42:**
  > **Memory** (auto-loaded; an older snapshot is in `notes/claude-memory/`, see §0.2):

**I13. Line 351 (§5.6).** The CID is abbreviated.
- **Evidence:** the ledger snapshot holds correlation id `hackathon-helper-1791189106-6525ac` (08:31:46Z).
- **Replacement:**
  > `hackathon-helper-1791189106-6525ac`

**I14. Line 385 vs line 460.** Internal inconsistency.
- **Quotes:** "(gap-list updates are allowed; check with the user first)" vs "Gap-list updates are allowed (standing instruction: add new gaps)."
- **Evidence:** memory `hackathon-working-agreement`: "Standing instruction: add new gaps found to gap-list.md"; memory `prooflab-project`: "Keep adding gaps as found (user instruction)".
- **Replacement, line 385:**
  > (adding gaps is a standing instruction [mem: hackathon-working-agreement]; commit and push per §8)

**I15. Line 442 (§7.8). The discrepancy can now be explained.**
- **Quote:** "(`docker ps` printed "6 minutes ago", which disagrees; unexplained.)"
- **Evidence:**
  - Docker Desktop's backend log (`~/Library/Containers/com.docker.docker/Data/log/host/com.docker.backend.log*`) has `[2026-10-05T15:57:55.594Z][com.docker.backend.idle] VM stopped`. That is Docker Desktop's idle (Resource Saver) mode; `settings-store.json` sets no override.
  - At 18:04Z `docker ps -a` still printed "Exited (137) 6 minutes ago" for the five containers that finished at 15:51:53.85Z, and "Exited (143) 5 minutes ago" for kafka (15:51:54.78Z) and zookeeper (15:51:55.32Z).
  - The status uses whole minutes, so those strings are consistent only with a reference time between 15:57:53.85Z and 15:57:54.78Z, about a second before the logged VM stop. The status strings are frozen at that moment.
- **Replacement:**
  > (`docker ps` still prints "Exited … 6 minutes ago" (5 for kafka and zookeeper). Docker Desktop's idle mode stopped its Linux VM at 15:57:55Z (backend log: `com.docker.backend.idle VM stopped`), and the relative times are frozen as of that moment. `docker inspect`'s FinishedAt is authoritative.)

**I16. Line 443 (§7.8).**
- **Quote:** "Don't use `down` (it removes the containers and the trained state)."
- **Evidence:** `docker inspect` mounts: api_manager, training and rf_prediction mount the named volume `radp_prod_radp` at `/srv/radp`; kafka uses two anonymous volumes. `compose down` removes containers and the network; named volumes survive unless `-v` is given.
- **Replacement:**
  > Use `start`, not `down`: `down` removes the containers and the network. RADP's data volume `radp_prod_radp` (`/srv/radp`) survives `down` but not `down -v`, and Kafka's anonymous volumes would be orphaned. Whether the trained `tokyo-rf-twin` lives in that volume was not checked.

**I17. Line 452 (§8).** The rule is unsourced, and committed files already break it.
- **Quote:** "Keep the owner's email address out of files."
- **Evidence:** §8 is headed "[mem: hackathon-working-agreement unless noted]", but no memory file contains a rule about email addresses (grepping memory for "email" finds nothing). The address is already in 5 committed repo files (see I9), one written by Claude.
- **Replacement:**
  > Keep the owner's email address out of new files (from the user's requirements for this handoff; not yet in memory). It is already in 5 committed files (§4.4); whether to redact them is the user's call.

**I18. Line 419 (§7.3).**
- **Quote:** "| `modaas-system` aws-agent/model/tool operators | 2026-10-04 10:35–10:36Z | 1 each |"
- **Evidence:** live container `startedAt`: agent operator 2026-10-05T10:37:44Z, model operator 10:37:16Z, tool operator 10:38:01Z. The single restart happened on 10-05, not at bootstrap.
- **Replacement (cell 3):**
  > 1 each (containers restarted 2026-10-05 10:37–10:38Z; cause not checked)

**I19. Lines 31 and 107 (§0.2, §2.1). The judging slide is also in the kickoff PDF.**
- **Quotes:** "probably the three pillars below. The full 30-slide deck is not in hand." and the [judging slide] key, which points only to the WhatsApp image.
- **Evidence:** `pdftotext` of `~/Downloads/Agentic_Assurance_VaraF.pdf` (24 pages):
  - PDF p22 = "HOW YOU WILL BE JUDGED" (printed 23 of 30)
  - PDF p23 = the three-pillars slide (printed 24)
  - PDF p24 = "Thank you" (printed 25)
  - Memory notes that printed 22 is missing.
- **Replacement, line 107:**
  > "Within each level, the quality of your evidence is judged on the criteria on the next slide." In the kickoff deck PDF that next slide is the three-pillars slide (PDF p23, printed 24) [kickoff deck p22–p23]. The full 30-slide deck is not in hand: the PDF has 24 pages and lacks printed slides 22 and 26–30.
- **Line 31, append to the cell:**
  > ; the same slide is kickoff deck PDF p22

### GAP

**G1. Lines 452, 499, 219 and 501. The ledger write token enters the kit's evidence pull and the submission zip. The most important gap.**
- **Evidence, step by step:**
  1. `pull-evidence.sh:78` runs `kubectl get modelconfig,toolconfig,agentconfig -n components -o json > "$OUT/cr-status.json"`.
  2. Live, all 5 AgentConfigs carry `AUDIT_WRITE_TOKEN` as a literal string in `spec.awsAgentCore.environmentVariables` (checked by name and type only). So `cr-status.json` holds the token.
  3. `submit.sh:55–56` copies `~/evidence` into the zip. `:89–90` writes `./submission-<team>-<UTC>.zip` into the **current directory** (the repo root if run there). `:114` uploads it to the judges' bucket.
  4. The repo `.gitignore` excludes neither `*.zip` nor `evidence/`. SN handoff §8.3 places `evidence/raw/cr-status/` inside the repo.
  5. The pre-push scan matches the exact token value, so it backstops the repo. Nothing scans the S3 upload.
- **Related:** `pull-evidence.sh:174–212` writes the ledger chain as `otel-traces.json`, with a note that the collector "exports to debug only". Correction row 3 shows that note is false.
- **Not recorded anywhere:** neither memory, the notes, nor the handoff mentions this.
- **Replacements:**
  - §8, line 452, after "…without a query that excludes env values.", insert:
    > The kit's `pull-evidence.sh` is such a dump: its `cr-status.json` is the full Model/Tool/AgentConfig JSON (`pull-evidence.sh:78`), so it holds the literal ledger write token of all 5 AgentConfigs. Redact env values before that file goes into `~/evidence/`, the repo or a submission.
  - §10, line 499:
    > | Pull the 6 evidence surfaces | `bash pull-evidence.sh <run-id> [out-dir]` (gateway lines from pod stdout, `--tail=50000`). `cr-status.json` contains the ledger write token (§8). `otel-traces.json` is the ledger chain, under a false "collector exports to debug only" note (correction row 3) [kit] |
  - §3d, line 219:
    > | `submit.sh` | S3 bucket (judges read it); a local zip | Prints a presigned URL. Zips `~/evidence/` as it is, including any unredacted `cr-status.json`, and writes `submission-<team>-<UTC>.zip` to the current directory (`submit.sh:89–90`). `.gitignore` covers neither `*.zip` nor `evidence/`; the pre-push scan protects the repo, not the upload | [kit: submit.sh] |

**G2. After line 140 (§2.4). The status of the six deliverables is missing.**
- **Evidence:**
  - The repo root has no `register.yaml`, `run-ids.txt`, `sketch.png`/`.jpg`, `architecture.md` or `evidence/`.
  - `~/evidence` exists on the laptop and is empty (memory: created by the Module 10 setup script).
  - The kit's `register.yaml` is a template: C16 limit 2000, owner and version_date are `REPLACE_…`.
  - `evaluate.py` covers C16 only.
- **Insert:**
  > - **Status today (18:10Z):** (1) evidence file: none (the snapshot is outside the repo; `~/evidence` on the laptop is empty); (2) threshold document: none (only the kit template); (3) control test tool: only the kit's C16 `evaluate.py`; (4) named runs: none (all runs exploratory; no `run-ids.txt`); (5) sketch: none; (6) gap list: draft, 11 entries (§6).

**G3. Line 185 (§3b Q11), or §2.5. A second judge hint is missing.**
- **Evidence:** memory `platform-verified-facts`: the Cedar-lever analysis was "asked after a judge hinted 'you can change the Cedar policies of the agents'". The handoff quotes only the risk-matrix hint.
- **Append to Q11:**
  > A judge also hinted (to the user, 2026-10-05): "you can change the Cedar policies of the agents" [mem: platform-verified-facts]. The live lever is ToolConfig `spec.access.cedarPolicy`; the AgentConfig overlay is not wired, and one shared identity means a deny hits every agent (§5.1).

**G4. Line 190 (§3b Q16). Neutral facts that bear on the observation.**
- **Evidence** (recomputed from the snapshot's gateway log and ledger dump):
  - Of the 290 gateway run ids, 16 are CIDs and 274 are 32-hex, trace-id-shaped values (no baggage CID).
  - After 09:14Z there are 351 run-id lines. All are listener `http` on `agentgateway-system/modaas-docs-mcp-route`: `initialize`, `notifications/initialized` and `tools/list`, 117 each, spread over 09:xx–17:xxZ.
  - No `tools/call` line and no model (`llm`) line carries a run id after 09:14Z.
  - This matches resources-verify's 39 `modaas-docs` ALLOW decisions in an hour, 3 per handshake.
  - The one ledger CID with no gateway run id is `my-agent-1791191585-4d9744`, the pause-refused run. Its 404 pod line has no run id (gap 4).
- **Append to Q16:**
  > Facts that bear on it (not an explanation): 16 of the 290 gateway run ids are CIDs; 274 are trace-id-shaped (no baggage CID). Every run-id line after 09:14Z (351) is MCP session setup on `modaas-docs-mcp-route` (`initialize`, `notifications/initialized`, `tools/list`, 117 each, about 13 per hour), with no CID. No `tools/call` or model line carries a run id after 09:14Z. The caller is unknown. The one ledger CID without a gateway run id is `my-agent-1791191585-4d9744`, the pause-refused run (its 404 pod line has no run id; gap 4) [snapshot, recomputed].

**G5. After line 156 (§2.5). The account lifetime is missing.**
- **Evidence:** memory `prooflab-project`, Timing: the Workshop Studio dashboard shows 10/04/2026 09:00 AM and a 72-hour lifetime with no time zone. That is the account's lifetime, not a confirmed deadline.
- **Append to the End-time bullet:**
  > The Workshop Studio dashboard shows a start of 10/04/2026 09:00 AM and a 72-hour account lifetime, with no time zone; that is the account's lifetime, not a confirmed deadline [mem: prooflab-project].

**G6. Line 165 (§3a item 1). How a revert is done.**
- **Evidence:**
  - Memory `reference-agents-facts`: "the alias comes only from `dependsOn.models[0]` … the operator ignores [modelRef] and generated CRs have none".
  - Live, `it-resolution-agent` carries `modelRef: nemotron-nano-9b` (set by the Module 7 swap); the other 4 AgentConfigs have none.
  - The lead report's confirmed-facts list says "Model swap = patch both `dependsOn.models[0]` and `modelRef`"; the handoff is silent.
- **Append to the evidence cell:**
  > A swap or revert is a patch of `dependsOn.models[0]`, the only field the operator reads [mem: reference-agents-facts]. The IT CR also carries `modelRef: nemotron-nano-9b` from the Module 7 swap; the other AgentConfigs have none [live]. (The lead report lists "patch both" as confirmed.)

**G7. Line 325 (§5.3). A retention value is missing.**
- **Evidence:** `aws logs describe-log-groups --log-group-name-prefix /aws/bedrock/aict-invocations` returns `retentionInDays` 7.
- **Replacement (cell 2):**
  > 7 d (CloudTrail data events, AWS-written)

**G8. Line 188 (§3b Q14). The primary source for separation of duties is missing.**
- **Evidence:** masterclass slides:
  - "The GRC chain": "AND FOUR ROLES, BECAUSE NOBODY MAY CHECK THEIR OWN WORK" (accountable management, GRC, operations, assurance)
  - "What governance actually is": "Management owns the claim not the team that builds it, and not the tool … Assurance checks the evidence and the person who ran the test is not the person judged by it"
  - Axis 2: "Verifiable by somebody who is not you"
- **Replace** "PB §1.5: "Four roles; nobody checks their own work" (owner ≠ builder)." **with:**
  > The masterclass: "AND FOUR ROLES, BECAUSE NOBODY MAY CHECK THEIR OWN WORK" (accountable management, GRC, operations, assurance), and "the person who ran the test is not the person judged by it" [slides, "The GRC chain", "What governance actually is"]; PB §1.5 repeats it (owner ≠ builder).

**G9. After line 156 (§2.5). The judging format is missing.**
- **Evidence:** transcript: "We have a preliminary round of judging where every single team will present to a series of judges. Virtual teams will have a virtual set of judges…". Winners are announced at Wednesday's Innovate Americas keynote.
- **Append to the End-time bullet:**
  > Then: "We have a preliminary round of judging where every single team will present to a series of judges"; winners are announced at Wednesday's Innovate Americas keynote [transcript].

**G10. Line 165 (§3a item 1). No baseline hour exists yet.**
- **Evidence:**
  - CloudWatch AgentCore `Invocations` (hourly Sum), 06:00–18:10Z: no datapoints for IT, customer or network (`my_agent` had 4 at 09:00Z, the helper 5 at 08:00Z).
  - The only hour with IT on nano-9b, 05:00Z, holds 6 IT invocations. Five are on super-120b: S2's two, Claude's S3 at 05:20Z, and the user's S1 at 05:24Z and S3 at 05:25Z. One is on nano-9b: the swap S1 at 05:48Z.
- **Append to the evidence cell:**
  > No IT, customer or network invocation has happened since the 05:00Z hour [live CloudWatch, 18:10Z]. That hour mixes IT on super-120b (S2 and the S1/S3 runs) with IT on nano-9b (the 05:48Z swap run), so no clean baseline hour exists yet on either model.

### STYLE

**S1. Line 3.** "Written 2026-10-05, 17:40–18:15 UTC" is forward-dated: the file was last saved at 18:01:29Z, and the review started at 18:02Z. Replace with the actual finish time, e.g. "17:40–18:01 UTC" (or later, if edited).

**S2. Line 36.** The `[live]` window "17:41–17:50 UTC" doesn't cover §7.9's "(18:00Z) [live]". Replace with "(17:41–18:00 UTC)".

**S3. Line 462.** This is the handoff's only literal email address: the commit-trailer address in "End commit messages with `Co-Authored-By: …`". It is public and not personal, but the user's rule was "no email addresses". Replace with:
> End commit messages with the `Co-Authored-By: Claude Opus 5.5 (1M context)` trailer exactly as the session's attribution reminder gives it.

**S4. Lines 338 and 408.** The approver subjects (the user's name and the CloudShell user, each with the `team` suffix) are shaped like email addresses. They are verbatim approval subjects, not addresses, so keep them, but add "(approval-subject strings, not email addresses)" once, at line 338.

**S5. Line 276.** "**Two confirmed adapter bugs**" → "**Two adapter bugs, CONFIRMED**", to match memory `servicenow-context` and the requirement's wording.

**S6. Line 238.** Add:
> Rows are verbatim from the lead report; only the source labels in rows 2, 7 and 13 were expanded to file paths.

**S7. Line 185 (Q11).** Cite the primary source for the EP test, not only PB §1.6. Replace "by the playbook's own test an EP must "ask, wait, act" [PB §1.6; …]" with:
> by the masterclass's own test every enforcement point does "Ask if this is allowed · Wait for the answer · Act on it · Record what happened · Seal the record", and it lists the "Human approval queue (where a person decides; the verdict arrives hours later)" as an EP type [slides, "Enforcement points", "Five problems"; PB §1.6; playbook-verify-lead.md row 12]

**S8. Line 459.** "Independent reviewers for memory updates and big steps": memory scopes this to substantial memory rewrites, and "big steps" isn't in memory. Replace with:
> **Independent reviewers** for substantial memory rewrites (and, as done today, for big deliverables such as this handoff):

---

## §7 live-state spot check (18:03–18:15Z)

| Item | Handoff | Live | Verdict |
|---|---|---|---|
| ModelConfigs: phase, paused, model id, generation | 4 Approved, paused false; ids nano-3-30b / nano-9b-v2 / super-3-120b ×2; gen 1/7/3/1 | identical | ✓ |
| AgentConfigs | customer super-120b [customer-records] g1; IT **nano-9b** [runbook-lookup] g2; network super-120b [network-twin] g2; helper super-120b-helper (5 tools) g1; `my-agent` super-120b, no tools, g1; all Approved, not paused | identical (`my-agent` has no `dependsOn.tools` key) | ✓ |
| IT approval | one, 04:37:25Z, predates the swap | one, 04:37:25.62Z, by the user's subject | ✓ |
| `my-agent` approval | one, 08:59:52Z | one, 08:59:52.57Z | ✓ (memory says 08:59:51) |
| ToolConfigs | 10, none paused; 8 agentCoreGateway ~10:38Z; `modaas-docs` custom 21:29Z; `demo-crm-lookup` Reviewing 00:36:35Z; backend 00:36:19Z | 10; 8 created 10:37:46–10:38:01Z; `modaas-docs` 21:29:01Z (gen 3); `demo-crm-lookup` Reviewing, 00:36:35Z, no approvals; Deployment and pod `demo-tool-backend` 00:36:19Z | ✓ |
| Stale pause conditions | nano-9b 04:05:53Z, super-120b 09:13:05Z, `modaas-docs` 05:56:44Z | `ReconcilePaused`/`RegistryPauseProjected` True at exactly those times | ✓ |
| Runtimes | 5 READY; IT v2 05:47:50Z; network v2; `my_agent` v1 09:00:05Z | identical; all share role `a-01-eks-cluster-agentcore-runtime` | ✓ |
| Pods: gateway, agentgateway, PDP ×2, authz ×2, collector, audit-store | start times and 0 restarts as stated | identical | ✓ |
| Operators | 10:35–10:36Z, 1 restart each | started 10:35:42 / 10:35:42 / 10:36:06Z; restarted 2026-10-05 10:37–10:38Z | ✓, see I18 |
| PVC `audit-store-data` | Bound, 1Gi; reclaim Delete | Bound, 1Gi, PV reclaim Delete | ✓ |
| `my-team-policy` | created 03:41:51Z | 03:41:51Z; 15 PDP-labelled ConfigMaps incl. `modaas-toolconfig-demo-crm-lookup` | ✓ |
| CFN stacks | 4, statuses and times as stated | `a-01` CREATE_COMPLETE 10:03:03Z; `a-02` CREATE_COMPLETE 10:18:59Z; `a-03` UPDATE_COMPLETE, created 22:02:58Z, updated 22:45:14Z; `aict-servicenow-user` CREATE_COMPLETE 22:43:21Z | ✓ |
| Evidence bucket | set, 0 objects | `TEAM_EVIDENCE_BUCKET` set and named `team-evidence-613052889143`; 0 objects | ✓ |
| Approval records | 18, empty signatures; 11 / 5 / 2 | 18; system-admin 11, the user's subject 5, CloudShell 2; all signatures empty | ✓ |
| EKS logging | off, all 5 types | all 5 `enabled: false` | ✓ |
| MAVERIC | 7 stopped containers; FinishedAt 15:51:53–55Z; exit 137/143; restart none | identical (restart policy `no`); `dc-prod.yml` sets `name: radp_prod`, so the restart command targets the right project | ✓; "6 min" explained in I15 |
| Repo git state | `main` = `origin/main` = `bfb1ce6` (17:50Z); 5 uncommitted entries | identical (`bfb1ce6` at 17:50:39Z) | ✓ |

## Path check

- **Coverage:** 118 path-like strings in the handoff were tested against the repo, `~`, `workshop-local`, `workshop-assets/starter`, `workshop-static`, the snapshot, memory and `~/Downloads`. Every concrete file or folder exists except `.captime-*` and `.err-*` (E2).
- **Strings that don't resolve to a file, and why that's fine:**
  - Kubernetes object references, all verified live.
  - Metric namespaces, git refs and the GitHub repo name.
  - Placeholders: `X.md`, `starter/F`, `<id>-DEFAULT`.
  - Future deliverables: `register.yaml`, `run-ids.txt`, `MANIFEST.json`, `architecture.md`, sketch, `delivery-log.jsonl`, `~/.prooflab-snow.env`.
  - Names relative to a folder stated nearby, each confirmed: `START-HERE.txt`, `outputs/claude-hackathon-context.txt`, `query-tokyo-twin.py`, `ask-feed-check.sh`, `escalate-to-incident.py`, the scripts.
  - Things that must not be run or fetched: `cleanup-module1.sh`, `cedarpolicy.com/en`.
- **Also confirmed:** `notes/workshop-reference/modaas-platform-architecture.svg`, `workshop-static/reference-impl/reference-agent/agent.py`, `~/Downloads/IC-5x5-Risk-Matrix-Template.webp`, the WhatsApp judging slide, the kickoff PDF, `~/Downloads/servicenow-integration-package/` (byte-identical to the repo copies) and the memory mirror folder.

## Memory vs handoff: where they disagree, and which is right

| Topic | Memory | Handoff | Evidence | Right |
|---|---|---|---|---|
| C9: what showed the S2 runaway | `workshop-progress`: IT avg 71.6 s, max 278.4 s; `prooflab-project` recommends Max + Errors without saying Average hid it | Q10 and row 8: "only the hourly Maximum … showed the runaway" | live CloudWatch: Avg 71,581 ms vs 8.2–8.5 s for the others | **Memory** (E1) |
| `my-agent` approval time | 08:59:51 | 08:59:52Z | live 08:59:52.57Z | **Handoff** |
| Snapshot ledger dump | "being added" | done: 101 records at 17:44:26Z | MANIFEST and file | **Handoff** (memory stale) |
| Handoff and snapshot progress lines | "being written", "being taken" | written / done | files exist | **Handoff** (memory stale) |
| `modelRef` in a swap | operator ignores it (`reference-agents-facts`); the swap set both (`workshop-progress`) | silent | live: only the IT CR has `modelRef`; the lead says "patch both" | **Memory**'s operator fact stands (source-based); add G6 |
| Gap-list edits | standing instruction to add gaps | §6 "check with the user first"; §8 "allowed" | — | **Memory** (I14) |
| Gap-7 additions | 4 items | adds "events kept ~1 h" as already in the file | `git diff gap-list.md` | **Memory** (I11) |
| Rule on the owner's email | none | §8 rule, attributed to the working-agreement memory | memory grep | Handoff unsourced (I17) |
| `notes/claude-memory/` | — | "a snapshot" | 8 files differ; `reference-links.md` missing | Live memory (I12) |
| Index loaded into this reviewer session | The system-reminder copy says "9 gaps" and "Modules 2–9 … next Module 10" | 11 gaps; Modules 2–11 | the live `MEMORY.md` says 11 gaps, Modules 2–11 | The live file. A fresh planner should confirm the auto-loaded index shows "11 gaps". |

## Sampled facts (72 checked)

| # | Line | Fact | Checked against | Verdict |
|---|---|---|---|---|
| 1 | 81 | "look good but guess confidently under ambiguity. Closing that gap is the game." | kickoff PDF p2 | ✓ |
| 2 | 86 | C-FM-01 wording | slides "Your governance structure"; brief §2 | ✓ |
| 3 | 86 | PB §1.0 says "customer fault resolution", "drift and performance" | PB L33 | ✓ |
| 4 | 88 | Finish line, verbatim | slides "Your task" | ✓ |
| 5 | 90 | Headline, verbatim | kickoff PDF p23 | ✓ |
| 6 | 103 | L1, verbatim | judging slide (also kickoff PDF p22) | ✓ |
| 7 | 104–105 | L2/L3 excerpts ("Service[Now]" is an editorial insertion; the slide says "Service Control Tower") | judging slide | ✓ |
| 8 | 110–112 | Three pillars, wording | kickoff PDF p23; p5 "A passing grade / On the fault…" | ✓ |
| 9 | 115 | Axis 1 wording; transcript "Don't do things partially…" | slides; transcript | ✓ |
| 10 | 117–120 | Axis 2: live test, architecture, evidence, honesty | slides "How you will be judged" | ✓ |
| 11 | 121 | Axis 3 wording | slides | ✓ |
| 12 | 122 | WHAT LOSES MARKS, verbatim | slides | ✓ |
| 13 | 123 | Five habits, verbatim | slides p15; transcript | ✓ |
| 14 | 128–133 | Six MUST deliverables, quotes | slides "Judgement Day", "Your task" | ✓ |
| 15 | 135 | Bonus artefacts; "Rehearse it twice before you present." | slides | ✓ |
| 16 | 138 | `submit.sh` usage; a bare call exits 2 | `submit.sh:29–30` | ✓ |
| 17 | 139 | Contents zipped; S3 key `submissions/<team>/`; presigned URL | `submit.sh:55–119` | ✓ (the zip also lands in the current directory, G1) |
| 18 | 140 | Bucket empty; fallback lookup empty, so the env var is needed | live 0 objects; lead row 15 | ✓ |
| 19 | 143–149 | Six auditor questions, verbatim | kickoff PDF p7 | ✓ |
| 20 | 151 | "1.5 Days": 1h / 3h / 3h / 4h / 3h / 4h; "15 minutes live" | kickoff PDF p8 | ✓ |
| 21 | 152 | Two rules quote | kickoff PDF p8 | ✓ |
| 22 | 155 | "absolutely needed"; connector and agents named with the team name | transcript | ✓ |
| 23 | 155 | Brief quotes: no bonus for agents or workflows; clone; risk frameworks | brief L99, L313, L325 | ✓ |
| 24 | 156 | End-time quote; 10:00 CDT = 15:00 UTC | transcript; arithmetic | ✓ |
| 25 | 165 | IT on nano-9b since 05:47, generation 2 | live (gen 2; runtime v2 05:47:50Z) | ✓ |
| 26 | 165 | ~$0.064 vs ~$0.161 per M tokens | memory `challenge-requirements` | ✓ |
| 27 | 170 | AICT import ~15–20 min | SN §9 ("~20 min (15-min import + ~4-min run)") | ✓ |
| 28 | 175 | `_METRICS = {"16": …}` | `evaluate.py:117–119` | ✓ |
| 29 | 176 | S1 24.8K–50.2K; S3 ~37.8K; swap-S1 37.7K; S2 2.0M; ~4.2K per call | memory | ✓ (I1 on "every real run") |
| 30 | 176 | SN handoff hard-codes 10,000 | SN §6, §7.1, §8.2, §8.7 | ✓ |
| 31 | 184 | "only the hourly Maximum (278 s) showed the runaway" | live CloudWatch Avg 71,581 ms | ✗ E1 |
| 32 | 184 | Refused run 1.05 s | live CloudWatch (04:00Z hour, 1,052 ms) | ✓ |
| 33 | 190 | 290 run ids; to 17:33Z; 17 CIDs; 16 match; ledger ends 09:13:40Z | snapshot, recomputed | ✓ |
| 34 | 205 | Headroom check at 2.14M input tokens | memory (2,139,857) | ✓ |
| 35 | 210 | Helper Q3, 123K tokens, as a cockpit-POST cost | memory: Q3 was via `ask-agent.sh` | ✗ I3 |
| 36 | 230 | Playbook 595 lines, dated 2026-10-05, no author | `wc -l`; PB header | ✓ |
| 37 | 238–257 | Corrections table = lead report | programmatic diff | ✓ |
| 38 | 259 | Specs hold the ledger token, not the gateway key | live env names: no `OPENAI_API_KEY` in specs | ✓ |
| 39 | 263 | `finding_id` format; hashed above 100 chars | `finding.py:44–51` | ✓ |
| 40 | 264 | CLI subcommands; exit 0/1/2; fsync'd log | `cli.py`; `delivery_log.py:31` | ✓ (I6 on the state list) |
| 41 | 266 | 46 tests pass | re-run on a scratchpad copy: 46 passed | ✓ |
| 42 | 269 | Credentials via `read -rs`; `~/.prooflab-snow.env` mode 600 | SN §5.3 | ✓ |
| 43 | 277 | Bug (a) line refs | `notifier.py:89–92, 132–136`; `cli.py:73`; reproduction log | ✓ |
| 44 | 278 | Bug (b) line refs | `notifier.py:189–203, 230, 233–234`; `fake_servicenow.py:173–174`; reproduction log | ✓ |
| 45 | 279 | Dry run not offline | `cli.py:60`; `notifier.py:115–131` | ✓ |
| 46 | 290 | OAuth property name; property rule in SN §10; courtesy note in §14 | SN §2, §10, §14 | ✓ |
| 47 | 300 | 5 runtimes share one role | live `roleArn` | ✓ (I10 on wording) |
| 48 | 301 | 0 of 478 decisions | glossary-verify (48 h, one replica) | ✓ |
| 49 | 316 | Gateway pod `modaas-agw-88dc46ff4-jfcdx` | live | ✓ |
| 50 | 317–318 | Retention: `/aws/modaas/gateway` 7 d, `/modaas/evidence` 30 d | resources-verify | ✓ |
| 51 | 320 | authz: 4 startup lines per pod | snapshot MANIFEST | ✓ |
| 52 | 323 | Runtime log groups never expire | glossary-verify | ✓ |
| 53 | 325 | `aict-invocations` durability | live retention 7 d | GAP (G7) |
| 54 | 326 | EKS logging off, all 5 types; `describe-trails` denied | live; resources-verify | ✓ |
| 55 | 333 | Token is a literal string in all 5 AgentConfigs | live (type `str`); glossary (32 characters) | ✓ |
| 56 | 334 | 12 records per run; 3 per agent on refusal; helper 2; `my-agent` 3 | memory | ✓ |
| 57 | 338 | 18 approval records; empty signatures; 11 / 5 / 2 | live | ✓ |
| 58 | 340 | Ceilings 100 req/min, 2.5M tok/h; MCP 100 req/min | memory | ✓ |
| 59 | 345–350 | CIDs, tokens, grades for S1 ×2, S2, S3 ×2, swap-S1, `my-agent` | memory; CID epochs (04:47–09:01Z) | ✓ |
| 60 | 351 | Helper Q3 CID | ledger snapshot: full CID found | ✓ (I13 on the abbreviation) |
| 61 | 356–358 | Pause and resume timings; 24 s swap | memory; notes #36 | ✓ |
| 62 | 363 | AICT `InvokeAgent` filter; only ConverseStream, Converse and InvokeAgentRuntime | SN notes §1 (492 / 11 / 28) | ✓ |
| 63 | 394–402 | CR table | live | ✓ |
| 64 | 404 | ToolConfig times; `demo-crm-lookup` details; stale pause timestamps | live | ✓ |
| 65 | 407 | Runtime versions and update times | live | ✓ |
| 66 | 414–420 | Pod start times and restarts | live | ✓ (I18) |
| 67 | 425 | CFN statuses and times | live | ✓ |
| 68 | 432–435 | Snapshot line counts, coverage, ledger stats | MANIFEST; recomputed | ✓ |
| 69 | 436 | `.captime-*` / `.err-*` files | `ls -A` | ✗ E2 |
| 70 | 439 | kubectl 1.36.5; Helm 3.22.0 | live binaries | ✓ |
| 71 | 442 | FinishedAt 15:51:53–55Z; exit 137/143 | `docker inspect` | ✓ (I15 explains "6 min") |
| 72 | 446 | `bfb1ce6` = `origin/main` at 17:50Z; uncommitted list | `git` | ✓ |

**Additional kit checks, all ✓:**
- `pull-evidence.sh:120` uses `--tail=50000`
- `run-reference.sh:36` defaults to `S1-fronthaul-degradation`; the scenario ids match `data/network-inventory.json`
- the `new-agent.sh:50` usage line
- the `ask-agent.sh` usage line
- `register.yaml:31` has a C16 limit of 2000, a C7 phase-coverage metric and a C9 placeholder
- the kit's gap-list format is What's missing / Why / Impact / If you had one more day
- the package is byte-identical to `~/Downloads/servicenow-integration-package/`
