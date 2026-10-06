# 08 · Feasibility: ServiceNow, the human loop and the delivery toolchain

Written 2026-10-05, 22:55–23:30 UTC, by an infrastructure-feasibility subagent, for the captain's question: "we are OK with the architecture, but does our infrastructure support development?"

**Scope.** The ServiceNow adapter used from the laptop, AICT for L2/L3, the owner's sign-offs, the delivery toolchain on this machine (Firstmate fleet), Python, overnight operations and the live-lane budget.

**Method.** Strictly read-only:
- **Read:** `ARCHITECTURE.md` (§1–§3.8, §5, §7, §8, §12, §14–§15), `work/03-decision-options.md` (D11, open checks), `work/02-requirements.md` (R-J-38, R-C-07, R-D-02–05), `SERVICENOW_INTEGRATION_HANDOFF.md`, `prooflab/servicenow/*` (README, client, notifier, cli, finding, delivery_log, tests), the ServiceNow, AWS-access and platform memory files, and the Firstmate README, AGENTS.md, bootstrap and project-management skill.
- **Run (status, version and help commands only):** one credential-less `curl -sI` and one stdlib HEAD request to the ServiceNow root. AWS and cluster reads went through `env.sh`: `sts get-caller-identity`, CloudTrail `lookup-events`, one Logs Insights query, `list-agent-runtimes` (names only) and `kubectl get` of rate-limit blocks only.
- **No:** ServiceNow API calls with credentials, writes, git writes or tests run. No secret or token was printed. The evidence log is at the end.

Status values: **SUPPORTED** · **SUPPORTED-WITH-CAVEAT** · **NEEDS-ARTH** · **NEEDS-CAPTAIN** · **SPIKE** (needs a small build or a first run to know) · **BLOCKED**.

---

## Verdict in one screen

**The infrastructure supports development.** The tools are installed at their required versions, GitHub auth works, the machine has capacity, the instance is reachable and the AWS reads work. Nothing is BLOCKED tonight.

What can stop us are four people-and-clock items, not tooling:
1. **One person gates everything overnight.** The user is the control owner, the captain and the builder. Every live write, every threshold approval and every merge needs the same person awake, from now until about 05:00 CDT.
2. **The AWS credentials expire at 2026-10-06T06:29:19Z**, in the middle of the baseline and C9 block. This is AWS-recorded: the current key was issued 18:29:19Z with a 12 h duration.
3. **ServiceNow is on the critical path twice before about 04:30 UTC:**
   - the T2 register approval at 03:30–04:00 UTC: the hard line, no assessed run before it;
   - the N2 incident at about 04:30 UTC.

   The OAuth credentials are not on the laptop yet, and the package has no code for the approval record.
4. **The fleet would start against nothing.** `architecture/` is untracked and unpushed; Firstmate clones from GitHub. The no-mistakes pipeline has never run on this machine.

**Counts (47 rows):** SUPPORTED 11 · SUPPORTED-WITH-CAVEAT 18 · NEEDS-ARTH 4 · NEEDS-CAPTAIN 11 · SPIKE 3 · BLOCKED 0.

**Live-lane budget: feasible on tokens.** About 37–45 runs come to about 2.5–4.3M tokens over about 10 h, with a peak hour of about 1.2M, against 2.5M/h. This holds if the observe-mode safety ceiling is ≤ about 300K and the inline halt is proven before the first S2-class run. The binding constraints are the human OK latency on a serial lane, the 06:29 credential expiry and overnight availability (§G).

### Clock-triggered items (each becomes BLOCKED at its time if unmet)

| UTC (CDT) | What must be true by then | Row |
|---|---|---|
| 01:00 (20:00) | The T2 approval mechanism is decided: Option A (owner in the UI) or Option B (glue code) | SN-09 |
| 03:30–06:29 (22:30–01:29) | **One AWS credential refresh** in this window covers 15:00 UTC with a margin (a refresh at exactly 03:00 expires at exactly 15:00); recommended at the 03:30 freeze step | OP-01, OP-02 |
| 03:30 (22:30) | SN credentials on the laptop and `selftest` OK; the owner can sign T2 for `v1` (the hard line) | SN-02, HL-02 |
| ~04:30 (23:30) | `notify` works from the laptop for N2's finding (the C16 milestone gate) | SN-04, SN-12 |
| **06:29:19 (01:29)** | **The current AWS credentials expire.** Runs, pulls, kubectl, S3 and the secret scan (so every push) stop | OP-01 |
| ~06:30 (01:30) | T2 for `v1.1` (the C9 baseline and N8's declared swap) | HL-02 |
| 09:30 (04:30) | Arth's AICT exports are in `evidence/servicenow/aict/` before the pack is sealed | AI-04 |
| 12:00 (07:00) | `check --cutoff` for every finding | SN-05 |
| 15:00 (10:00) | Deadline (UNCONFIRMED). The account is destroyed when the event ends, at a time not known | OP-04 |

---

## The table

### A. The ServiceNow adapter, used from the laptop

| ID | Component / assumption | What must be true | Evidence | Status | Action |
|---|---|---|---|---|---|
| SN-01 | Network path from the laptop to `platformdemoh8.service-now.com` | HTTPS reachable; TLS verifies with the stdlib client's Python | `curl -sI` at 23:00:52Z: `HTTP/1.1 200 OK`, `Server: snow_adc`, HSTS. `/usr/bin/python3` 3.9.6 (LibreSSL 2.8.3, CA file `/private/etc/ssl/cert.pem`), HEAD with no redirect followed: 200 | SUPPORTED | None. No `SSL_CERT_FILE` is needed with `/usr/bin/python3`; the handoff's §12 fix is for python.org builds only |
| SN-02 | OAuth client id + secret (app "iFabric Agent Assurance") on the laptop | Present in the lane's shell before T2 (03:30 UTC) and the first `notify` (~04:30 UTC) | `~/.prooflab-snow.env` is absent; 0 `SNOW_*` variables in the shell. The handoff §5.3 says the values are "in Arth **or Sree's** password manager", and Sree is the user | NEEDS-CAPTAIN (check your own vault first; else Arth) | Put `SNOW_INSTANCE`, `SNOW_CLIENT_ID`, `SNOW_CLIENT_SECRET` and an absolute `PROOFLAB_DELIVERY_LOG` in `~/.prooflab-snow.env` (`chmod 600`, outside the repo). Source it in the lane's shell and run `python3 -m prooflab.servicenow selftest` (read-only). Add the id and secret to the exact-value secret scan (§9.3). Fleet workers run as the same OS user and could read the file: forbid it in the briefs |
| SN-03 | Integration identity and the instance setting | `ifabric.integration` (itil only) is active; the OAuth app is active; the Global property `glide.oauth.inbound.client.credential.grant_type.enabled` is still true on the **shared** instance | The handoff §2 only (Arth, live, 2026-10-05); we can't verify without credentials. The courtesy note to the facilitators was still pending; a Global property on a shared instance can be reverted at any time | NEEDS-ARTH | Arth confirms all three tonight and sends the courtesy note. The lane runs `selftest` before each `notify` batch, so a reverted property shows as a delivery gap, never as silence |
| SN-04 | Create and read back an incident | One incident per finding, assigned to the owner. DELIVERED only after a readback that matches the correlation id and the assignee | Code: `notifier.py:110-147` (lookup → create → `_confirm`). Lookups filter `sys_created_by = ifabric.integration`, so other teams' records are never read as ours. Live proof: INC0010231, by Arth only | SUPPORTED-WITH-CAVEAT | The first real `notify` from the laptop is N2's finding. Never notify the example file, because INC0010231 already exists for it |
| SN-05 | The response check (`check --cutoff`) | The owner's reply is recorded as RESPONDED; silence only after the cutoff; an unknown is never shown as silence | **Bug (b)**, confirmed: the itil user can't read `sys_journal_field` (the ACL returns HTTP 200 and 0 rows), yet `readable` stays True (`notifier.py:189-204`). The owner is detected only through `sys_updated_by`, so only when she is the **last** updater. Any later update masks her response and gives a false NO_RESPONSE_OBSERVED after the cutoff. Later updates include: Arth closing the incident, the integration user adding a re-test link, a system job, another team's admin | SUPPORTED-WITH-CAVEAT | Minimal fix below (3 lines + 1 test). Process rule: run `check` and `export` right after each owner note, and no one but the owner updates our incidents after she responds |
| SN-06 | `notify --dry-run` | A dry run leaves nothing that reads as delivery evidence | **Bug (a)**, confirmed: on the existing-incident path `notify()` returns `_confirm(...)` before the `dry_run` branch (`notifier.py:132-136`). It logs INTENT + DELIVERED (`reused`) with the dry run's time. It is not offline either: an OAuth token, two `sys_user` reads and an `incident` lookup + readback. The tests cover only the no-incident path (`test_dry_run_never_writes_to_servicenow`) | SUPPORTED-WITH-CAVEAT | Never dry-run against the evidence log: set `PROOFLAB_DELIVERY_LOG` to a scratch path for any dry run. Minimal fix below (6 lines + 1 test) |
| SN-07 | The delivery log and `export` as pack evidence | One append-only log for every human-loop step; each incident exported as stored | The default log path is **relative** (`cli.py:30`, `evidence/servicenow/delivery-log.jsonl`), so a call from another working directory starts a second log. `export_incident` (`notifier.py:150-180`) writes the raw incident (UTC `sys_*_on`), `journal: []` for itil with no error, and `notes_display`, whose timestamps are in the integration user's display time zone | SUPPORTED-WITH-CAVEAT | Make `PROOFLAB_DELIVERY_LOG` absolute in the env file. The pack README says that `journal: []` means hidden by ACL, not "no notes", and that the raw `sys_*_on` (UTC) are the times of record |
| SN-08 | Incident volume on the shared instance | Bounded, ours only, no spam | Per-run C9 scope (§3.8) gives about **8–15 incidents overnight**: N2 C16 BREACH; N3's halt → ESC (`c16-budget-halt`); N4 C7 BREACH; N6 S3 ESC; N8 C9 BREACH (+ESC if the swapped model's structured output fails); ADV-R-06's floor BREACH; 0–2 approvals; 0–1 wiring test; 1–3 BREACH re-runs (each new CID is a new finding id, so a new incident, and the superseded one stays open); 0–2 genuine monitoring gaps. Each `notify` makes about 5 API calls, and re-confirming an existing incident about 4. The handoff's original per-hour × per-runtime C9 windows would have given up to about 30 findings, mostly idle-hour gaps | SUPPORTED-WITH-CAVEAT | `publish()` and `prooflab watch` notify only **new** finding ids (check the delivery log first). Never notify a monitoring gap for an idle hour: no expected invocation means no gap. Before judging, Arth closes INC0010231 and adds a note to superseded re-run incidents |
| SN-09 | The register approval record (date proof T2) | A server-timestamped owner approval naming the version and sha256, exported, **before the first assessed run** (`v1` at 03:30–04:00 UTC) | The package has **no code for it**: it handles findings only (four verdicts; §3.3 says an approval is not a Finding), has no update/PATCH method, and its export is keyed by a Finding. The mechanism is "pending Arth" (§3.3) | SPIKE | Decide by 01:00 UTC. **Option A (no Arth needed):** Sree creates the record in the UI (she has admin + itil, per the handoff §2) with the version, sha256 and "Approved", and exports it at once (list Export → JSON); record the self-approval in the gap list. **Option B:** W9 adds `request_register_approval()` + `export_by_correlation_id()` (about 1–2 fleet h); the owner's note is the approval |
| SN-10 | The re-test closure link in the incident's work notes (§3.8) | "Closed only by a later SATISFIED assessment, linked in the work notes" | `client.py` has no update method, and a link note from the integration user would trigger SN-05's masking | SUPPORTED-WITH-CAVEAT | The owner adds the re-test link note herself (it then also counts as her response). Otherwise add a PATCH and re-export after `check` |
| SN-11 | Off the agent's path | ServiceNow is never in a request path | `notify()` runs only from the laptop's evaluator runner (§3.8, §8); agents never hold SN credentials (§8 table) | SUPPORTED | Keep SN credentials out of every AgentConfig env (all participants can read it) |
| SN-12 | Where the human-loop adapter runs (D11) | One host with the SN credentials, the delivery log and Logs Insights | The IDE role has no Logs Insights [03 F2], and Claude can't drive the IDE (SSM denied); the laptop has both | NEEDS-CAPTAIN | Decide D11 = laptop (P3). If Arth keeps the credentials on his machine or in the IDE, every `notify`/`check` waits for Arth, and his delivery log must be merged into the pack |

### B. AICT for L2/L3

| ID | Component / assumption | What must be true | Evidence | Status | Action |
|---|---|---|---|---|---|
| AI-01 | AICT discovery is running | AICT still polls our account | CloudTrail 20:00–23:10Z: `ListAgentRuntimes` by `SgcAictReadOnlyAccessRole` 12 times at 14–16 min intervals, last at **22:54:26Z** | SUPPORTED | None |
| AI-02 | Our new `ifabric_` runtimes appear in AICT | AWS side: AICT reads them. ServiceNow side: they are imported as AI Function records | **AWS side proven:** `GetAgentRuntime` on `my_agent-9AyPFbHh5Z` (created about 09:00Z) 12 times in 3 h, so a new runtime is read every cycle (≤ 15 min). **ServiceNow side** (+ ~4 min import) is per the handoff only; whether `my_agent` shows in AICT is unverified (the handoff's files predate it) | NEEDS-ARTH | Arth checks that `my_agent` is in AICT **now**, which proves the ServiceNow half. After the L2 builds (~00:30–02:00 UTC), expect `ifabric_*` by about 02:20 UTC |
| AI-03 | AICT Monitor and usage | Our traffic is counted | AICT's `StartQuery` at **22:52:58Z** still ends `filter eventName = "InvokeAgent"`. Our traffic is `InvokeAgentRuntime` + `Converse*`, so the usage count is 0. Monitor covers Managed agents only (vendor PDF) | SUPPORTED-WITH-CAVEAT (as a recorded gap) | Keep it in the gap list; never claim AICT usage. Use the AWS-written `aict-invocations` records instead (EP-11). Don't touch the connector (shared, facilitator-owned) |
| AI-04 | AICT exports for the pack: who, when, what format | Exported, in a plain format, in `evidence/servicenow/aict/` before the pack is sealed | Who: Arth (handoff §9, §8.3). When: after the named runs exist (plan: from about 07:20 UTC). Planned files: `discovered-assets.json`, `cloudtrail-assumerole.json`, PNG screenshots. R-J-38 lists JSON, JSONL, CSV, Markdown and static HTML | NEEDS-ARTH | Primary: a list export (JSON or CSV) of the AI asset records filtered to the connection "iFabric Hackathon 2026", with its export time. Screenshots (Inventory → Details; Monitor, likely "Unable to show Monitor dashboard", itself evidence of the gap) are supplementary. Deadline 09:30 UTC |
| AI-05 | L3: the ServiceNow-native `iFabric-assurance-agent` | It reads our incidents; labelled with ServiceNow's model | Handoff §9: Arth, after findings exist. The vendor PDF shows Agent Studio run logs with no timestamps, ids, identity or version, and a demo agent with an `admin` approved role | NEEDS-ARTH | It needs: Agent Studio rights on the shared instance; the instance LLM (labelled as such); a read-only tool scoped to `correlation_display = ifabric-prooflab` and `sys_created_by = ifabric.integration`; a restricted ACL (not "any authenticated user", not the `admin` role); and an export of one run's decision log. Earliest useful: after the N2 incident (~04:30 UTC) |
| AI-06 | The AWS half of the AICT proof, without Arth | AWS-written proof that AICT read our runtimes | Tonight's reads prove it works: CloudTrail `AssumeRole` by `ServiceNowAictUser`, plus the role's `Get`/`ListAgentRuntimes` on our runtime ids (event history is kept 90 days) | SUPPORTED | Add an `aict_discovery` pull to W4 → `raw/aict-discovery/` (read-only, laptop). It replaces the pending `cloudtrail-assumerole.json` from Arth |

### C. The owner's sign-offs and separation of duties

| ID | Component / assumption | What must be true | Evidence | Status | Action |
|---|---|---|---|---|---|
| HL-01 | Agent approvals (CR annotations, EP-10) | The three `ifabric-` AgentConfigs are approved by the owner (a human act), plus any re-approval after an env-pin patch (OC-12) | Module 9: the build took 72 s, approval at 08:59:52Z, READY at 09:00:31Z, so it takes seconds. That approval was **executed by Claude** under the string `satyabratsrikumar@team`, on the user's OK | SUPPORTED-WITH-CAVEAT | The user runs the approve command themself, or gives exact words that the live-lane log quotes. Record it as self-asserted (gap 5) |
| HL-02 | Register sign-offs: T2 for `v1` (03:30–04:00 UTC), `v1.1` (~06:30 UTC) and N8's declared treatment | The owner signs before each assessed block | Sree has ServiceNow UI access (admin + itil; she posted the note on INC0010231, per the handoff), so it takes minutes if she is awake | NEEDS-CAPTAIN | Pre-write the four answers and the approval text before the pilots end. Declare N8's swap inside `v1.1`, so one T2 covers it |
| HL-03 | Every live write has the user's OK (R-D-03) | Someone with authority is awake 21:00–10:00 UTC (16:00–05:00 CDT) | One person is the owner, the captain and the builder. About 60–90 OKs: runs, applies, pins, mode switches, freezes, uploads and merges, over about 17 h, after a long day | NEEDS-CAPTAIN | Batch the OKs per declared run card (for example, "pilots P1–P8 as listed, in order"). Finish P0 (C16 end to end) by about 05:00 UTC, then use the cut lines (§12.4) if a sleep window is needed |
| HL-04 | Separation of duties (R-D-02) | Nobody checks their own work; the four roles are named | The owner also builds and approves; Arth is the only other person; AI reviewers are not the GRC or assurance role (§15.2) | NEEDS-CAPTAIN (+ Arth) | A roles table: Sree = accountable management + operations; Arth = assurance (adds a "reviewed" note to each T2 record **before** Sree approves, and signs each control result's assurance check); GRC stated as vacant in the gap list |

### D. The delivery toolchain on this machine (Firstmate fleet)

| ID | Component / assumption | What must be true | Evidence | Status | Action |
|---|---|---|---|---|---|
| TC-01 | The Firstmate distro is installed | `bin/fm-*.sh`, the skills and the Claude hooks are present | `~/workspaces/projects/firstmate` at `1b0fbb9` (2026-09-03), clean. `bin/` holds the fm scripts (spawn, bootstrap, send, teardown…). `.claude/settings.json` wires the SessionStart, PreToolUse and Stop hooks | SUPPORTED | None (an `/updatefirstmate` is optional; the copy is a month old) |
| TC-02 | The required tools and their version floors | node, git, gh, no-mistakes ≥ 1.46.0, gh-axi ≥ 0.1.29, lavish-axi ≥ 0.1.46, tasks-axi ≥ 0.2.4, quota-axi ≥ 0.1.29, chrome-devtools-axi, treehouse with `--lease`, tmux | node v24.5.0 · git 2.39.5 · gh 2.101.0 · no-mistakes 1.64.0 · gh-axi 0.1.29 · lavish-axi 0.1.64 · tasks-axi 0.2.4 · quota-axi 0.1.36 · chrome-devtools-axi 0.1.33 · treehouse v2.1.1 (lease: yes) · tmux 3.7c | SUPPORTED | None. tasks-axi and gh-axi sit exactly at their floors: don't downgrade |
| TC-03 | GitHub authentication | `gh` can push and open PRs on the repo | `gh auth status`: active account `satyabrat-invences` (keyring), and an inactive second account `ss7172`. `gh repo view`: private, default branch `main`, viewerPermission **ADMIN** | SUPPORTED | Keep `satyabrat-invences` active; a switch to `ss7172` would break pushes |
| TC-04 | A Firstmate home and project registry for this repo | A home with `data/projects.md`, and a clone under `projects/` | The repo-root home has `data/backlog.md` and `done-archive.md` but **no `projects.md` and no `projects/`**. `firstmate-homes/TrustworthyAI/` has none of `data/`, `state/`, `config/`, `projects/`, so it is not a home. The only full home is `firstmate-homes/invences-website`. `state/.lock` names pid 90663, which is not running (stale) | NEEDS-CAPTAIN | Setup, about 30–45 min (estimate): launch `claude` in the firstmate directory (session start reclaims the stale lock); add the project (clone `satyabrat-invences/TrustworthyAI-iFabric` into `projects/`; registry entry with a delivery posture); run `no-mistakes init && no-mistakes doctor` in the clone; set `config/backend` = `tmux`. The captain chooses the posture and yolo (TC-07) |
| TC-05 | The fleet can see the contracts it codes against | Workers clone from GitHub, so the architecture must be pushed | `git status`: **`architecture/` untracked**; `PLANNING-HANDOFF.md`, `gap-list.md` and `notes/playbook/playbook-verification.md` modified; local `main` = `origin/main` = `6905e47` (committed 19:45Z) | NEEDS-CAPTAIN | Step 1 of the night: commit, run the secret scan, push (git is the lead's call). Without it, W0–W10 build against nothing. The live lane later pulls `main` before each live block, so it runs merged code |
| TC-06 | The no-mistakes pipeline (R-D-04) | PRs validate through no-mistakes in reasonable time | `no-mistakes stats`: **no runs yet** on this machine ("Total changes 0 across all repos"; the `repos/` directory also looks empty by its size). The daemon has run since 2026-09-03; its PATH resolves `~/.local/bin/claude` (stable). Config: `agent: auto`, `ci_timeout: "168h"`. The repo has no `.github/` | SPIKE | Put one tiny PR (W0's first commit) through it before the fleet depends on it. Define the test command. If the CI step parks with no checks, use `no-mistakes --skip ci`, or add a Python 3.9 GitHub Actions workflow (which also gives an independent 3.9 check, see PY-02) |
| TC-07 | Merge authority overnight | Green PRs land without waiting for the captain | Firstmate AGENTS.md §1 and §7: every merge needs the captain's explicit word unless the project is `+yolo` | NEEDS-CAPTAIN | Decide `+yolo` for this repo: Firstmate then merges green, in-scope PRs; red or security-sensitive ones still escalate. Without it, expect about 15–25 merge requests overnight, competing with live-lane OKs |
| TC-08 | The secret scan before every push | `pre-push-secret-scan.sh` prints `RESULT: clean` | It is **not a git hook** (`.git/hooks` holds samples only), so nothing enforces it. It loads values through `env.sh` (kubectl + AWS) and stops when credentials lapse (06:29:19Z). It doesn't load the ServiceNow values | SUPPORTED-WITH-CAVEAT | Every brief runs `bash -c 'source …/workshop-local/env.sh >/dev/null 2>&1; …/pre-push-secret-scan.sh <worktree>'` before pushing. Refresh credentials before they expire, or pushes stop. Add the ServiceNow values once SN-02 is done |
| TC-09 | Workers make no live writes (R-D-03) | The fleet does offline work only | There is no default AWS profile (only `[hackathon]`), no AWS key variables in the environment and no default kube context. A worker has no live access unless it sources `env.sh` | SUPPORTED-WITH-CAVEAT | Briefs: source `env.sh` only for the secret scan; any other AWS or kubectl call breaks the brief. Keep the live lane in one separate session (not the first mate) |
| TC-10 | Claude Code as the fleet harness | A verified primary harness on a stable binary | `claude` 2.1.289 at `~/.local/bin/claude` (this session sees a per-session cmux shim first). Firstmate lists Claude Code as a co-primary harness; tmux 3.7c is present | SUPPORTED-WITH-CAVEAT | Set `config/backend` = `tmux`: this terminal is cmux, which auto-detection would pick, and cmux is an experimental backend. Briefs give absolute paths to the kit, `workshop-static/` and the 17:37Z snapshot, which are outside the repo |
| TC-11 | Fleet capacity (Claude subscription quota) | 6–8 parallel workers plus no-mistakes reviews, which also use Claude, for about 6–8 h | `quota-axi --provider claude --no-credential-refresh` → `auth_required … keychain_access_required`, so headroom is **unknown**. Fallback harnesses are installed (codex, grok, pi per `no-mistakes doctor`); their auth is unknown | NEEDS-CAPTAIN | Run `quota-axi --allow-keychain-prompt` once and approve. Start with W0 alone, then 4–6 workers, then scale on what quota shows |
| TC-12 | Machine capacity | CPU, RAM and disk for the fleet | Apple M4 Max, 16 cores, 48 GB RAM (84% free), 446 GB disk free; no Docker containers running; 23 Claude processes already running | SUPPORTED | None |
| TC-13 | R-D-04's memory snapshot refreshed with each commit | Parallel PRs don't conflict | Every fleet PR that refreshes `notes/claude-memory/` would conflict with the others (inference) | SUPPORTED-WITH-CAVEAT | Exempt fleet PRs; the lead refreshes the snapshot in its own commits |
| TC-14 | `submit.sh` from the laptop | Its tools exist on macOS | It uses `zip`, `find`, `date -u`, `aws s3 cp` and `aws s3 presign`; `/usr/bin/zip`, `/sbin/sha256sum` and `aws` are present | SUPPORTED | Keep `TEAM_EVIDENCE_BUCKET` set (`env.sh` sets it) |

### E. Python and tooling

| ID | Component / assumption | What must be true | Evidence | Status | Action |
|---|---|---|---|---|---|
| PY-01 | The judge-side runtime | The pack's tool runs on Python 3.9+, stdlib only | `/usr/bin/python3` = 3.9.6. All 12 `prooflab/**/*.py` compile under 3.9.6 (in memory, nothing written). No third-party imports | SUPPORTED | None |
| PY-02 | A 3.9 test lane for the fleet | Tests run on 3.9 before merge, because the judge may use 3.9 | The default `python3` is **Anaconda 3.12.7**, then Homebrew 3.14.8, then `/usr/bin` 3.9.6. The earlier pytest venv (`venv-prooflab`) is **3.12.7** with pytest 9.1.1, and it lives in this session's scratchpad, where workers can't see it. So the earlier "46 passed" was a 3.12 run. 44 `def test_` functions are counted. `/usr/bin/python3` has no pytest | SUPPORTED-WITH-CAVEAT | Create `/usr/bin/python3 -m venv` outside the repo (for example `workshop-local/.venv-py39`) and `pip install pytest` (pip picks a 3.9-compatible pytest). Make `<venv>/bin/python -m pytest` the test command in briefs and in no-mistakes. Optionally add 3.9 CI (TC-06) |
| PY-03 | The IDE vs laptop split | Pulls run on the laptop; the IDE is for human reads only | [03 F2]: the IDE role has no Logs Insights, and Claude can't drive the IDE (SSM denied). [03 F1]: the IDE role is the only team role that can list bucket versions | SUPPORTED-WITH-CAVEAT | For the T1 export, a person runs `aws s3api list-object-versions` in the IDE and `aws s3 cp`s the JSON into the team bucket (the IDE role has PutObject); the laptop reads it back. CloudShell is the fallback for pulls |

### F. Operations overnight

| ID | Component / assumption | What must be true | Evidence | Status | Action |
|---|---|---|---|---|---|
| OP-01 | AWS credential lifetime | Valid through every live step | CloudTrail `AssumeRole` into WSParticipantRole (session `Participant`): **`durationSeconds=43200` (12 h) on all 11 issuances** since 2026-10-04. The current key (matched in-shell, never printed) was issued **18:29:19Z** and **expires 2026-10-06T06:29:19Z**. This matches the earlier lapse: issued 06:20:01Z, expired at about 18:20Z. `~/.aws/credentials` was last written 18:30:06Z and has no expiry field. `get-caller-identity` worked at about 23:01Z | SUPPORTED-WITH-CAVEAT (clock-triggered at 06:29:19Z) | One refresh **between 03:30 and 06:29 UTC** (22:30–01:29 CDT) gives an expiry of 15:30–18:29 UTC and covers the deadline with a margin (03:00 would give exactly 15:00). Do it at the 03:30–04:00 freeze, already a human step. A refresh now would expire at about 11:00 UTC and force a second refresh during rehearsals. New credentials don't revoke the old ones, so refreshing early is safe |
| OP-02 | The refresh duty | A named person refreshes; collectors detect expiry | The user, from the Workshop Studio dashboard ("Get AWS CLI credentials"), after which Claude rewrites the `hackathon` profile [mem: workshop-aws-access]. D11's supervisor records ExpiredToken as a `monitoring-gap` | NEEDS-CAPTAIN | Put the refresh at 03:30 UTC in the critical-path table, with a backstop alarm at 05:45 UTC. If judging needs live AWS after the expiry, plan one more refresh |
| OP-03 | Laptop power and sleep | The laptop stays awake and online all night; background agents and `prooflab watch` survive | On AC, battery 30% and charging. **`pmset sleep 1`** (idle sleep after 1 min) is held off only by transient assertions: WhatsApp's camera, a 300-s `caffeinate` and powerd while the display is on. `displaysleep 10`. Lid-close sleep is currently off. A reboot clears `/tmp/modaas-token` | SUPPORTED-WITH-CAVEAT | Run `caffeinate -dimsu` in a dedicated terminal for the night. Stay on AC; keep the lid open (or `sudo pmset -a disablesleep 1`, reverted afterwards). Pause macOS auto-updates and restarts. After any reboot, re-extract the gateway token |
| OP-04 | The deadline and the account's end | Tue 2026-10-06 15:00 UTC (10:00 CDT); the account is up until judging ends | UNCONFIRMED [handoff §2.5]. "The account is destroyed when the event ends" (kickoff deck p8), at a time not known | NEEDS-CAPTAIN | Confirm both with the organisers. The final export must precede the account's end |

### G. The live-lane budget

| ID | Component / assumption | What must be true | Evidence | Status | Action |
|---|---|---|---|---|---|
| LB-01 | Token ceiling | ≤ 2.5M tokens in any 60 min, account-wide | `modaas-ceiling` and `modaas-llm-auth`: local `{requests: 100/Minutes, tokens: 2,500,000/Hours}` on listener `llm` (one replica). The last 8 h of `aws/spans`: **1–2 model calls an hour**, so headroom is full and nobody else is drawing on it now | SUPPORTED-WITH-CAVEAT | Safety ceiling ≤ about 300K; at most 3 S2-class runs per clock hour; a headroom check before every run (§7.2) |
| LB-02 | Request ceiling | ≤ 100 model requests/min (MCP: 100/min, separately) | The S2 peak was 49/min; runs are serialized and spaced ≥ 2 min apart | SUPPORTED | None |
| LB-03 | Lane wall-clock | About 37–45 runs + builds, approvals, pins and freezes fit in 22:00–08:30 UTC | About 40 runs × about 5 min (a 1–5 min run + ≥ 2 min spacing + ≥ 60 s before the span pull) ≈ 3.3 h. Builds ran in 64–72 s and READY took about 2.5 min (Module 7/9). The rest is human OK latency | SUPPORTED-WITH-CAVEAT | Batch the OKs (HL-03); protect P0 by 05:00 UTC |
| LB-04 | The inline halt bounds S2-class runs | The C16 hook really cancels (OC-1), retries don't bypass it (OC-2), and the pinned safety ceiling halts in observe mode | Unverified (§14 OC-1, OC-2). One unbounded S2 costs about 2.0M tokens in about 5 min and up to about 1 h of lane (the reference S2) | SPIKE | In the smoke phase, prove a halt on a deliberately low test cap with an S1 run, **before** any S2-class pilot. Only then run P5–P7 |

---

## The two confirmed adapter bugs: impact and minimal fixes (notes only; Arth's code, the captain decides who fixes)

**Bug (a): `notify --dry-run` reports DELIVERED** (`prooflab/servicenow/notifier.py:128-136`).
- **What happens:** when an incident already exists for the finding, `notify()` returns `_confirm(...)` before it looks at `dry_run`. It makes a live readback and appends `INTENT` and `DELIVERED (reused=true)` to the delivery log, stamped with the dry run's time. The CLI prints DELIVERED and exits 0.
- **Impact on human-loop evidence:**
  - the log entry carries no dry-run marker, so a judge can't tell it from a real delivery;
  - the offline "Human loop" line (the latest DELIVERED) shows the dry run's time;
  - the log is append-only, so a wrong line can only be explained, never removed.

  The README's "writes nothing" is also wrong about being offline: a dry run takes an OAuth token and makes 3–4 reads.
- **Minimal fix** (about 6 lines + 1 test: an existing incident + `dry_run=True` → DRY_RUN, no DELIVERED line, no readback):
  ```python
  if existing:
      if dry_run:
          log.append(fid, "DRY_RUN", would_reuse=existing.get("number"), payload=payload)
          return DeliveryResult(fid, "DRY_RUN", existing.get("number"), existing.get("sys_id"), reused=True)
      return _confirm(finding, client, log, existing["sys_id"], assignee, reused=True)
  ```
- **Guard with no code change:** set `PROOFLAB_DELIVERY_LOG` to a scratch path for every dry run.

**Bug (b): the journal ACL can give a false NO_RESPONSE_OBSERVED** (`notifier.py:183-235`).
- **What happens:** the itil integration user gets HTTP 200 with **0 rows** from `sys_journal_field`, so `readable` stays True and the owner's notes are invisible. She is then detected only as the incident's last updater (`sys_updated_by`). If anyone updates the incident after her, her response disappears: before the cutoff it reads AWAITING_RESPONSE, after it NO_RESPONSE_OBSERVED. That "anyone" includes Arth closing it, our integration user adding a re-test link, a system job, or another team's admin.
- **Impact:** a **false "silence" record** on exactly the claim the judges probe ("who was told, and what happened"). The same masking can hide the owner's T2 approval if that record is updated afterwards.
- **Minimal fix** (about 3 lines + 1 test). Every incident we create carries our own work note from creation, so a readable journal always has at least one row. Zero rows therefore means "hidden", never "none":
  ```python
  notes = client.list_work_notes(incident["sys_id"])
  if not notes:
      readable = False  # our creation note guarantees >= 1 row; 0 rows = hidden by the ACL
  for note in notes: ...
  ```
  A masked response then becomes RESPONSE_UNKNOWN (honest) instead of silence. `export` should likewise write `journal_error: "hidden by ACL (0 rows)"` instead of `journal: []`.
- **Better, optional:**
  - parse `notes_display` (itil can read it) for the owner's display name as a second basis (`at_basis: notes_display`); its timestamps are in the integration user's display time zone, so convert them or record the zone;
  - or Arth grants read on `sys_journal_field` for our incidents (an ACL change on a shared instance, his call).
- **Process guard:** `check` + `export` right after each owner note; nobody but the owner updates our incidents afterwards.

**If the fleet fixes them:** W9 scope, about 30–45 min with tests, merged before the first real `notify` (about 04:30 UTC).

---

## The live-lane budget, worked

**Variables:**
- `s` = an S1/S3-class run of the `ifabric-` trio, about **50K**. The measured reference runs were S1 24.8K–50.2K and S3 37.8K; add about 20% for J2's structured output and re-asks.
- `CAP` = the S2 tier's cap (D2, pending).
- `SC` = the observe-mode safety ceiling (D2, pending).

The example uses CAP = 150K and SC = 300K. Plug in the captain's D2 values.

| Block (plan §5.4, §5.5, §6.4, §12.1) | Runs | Tokens | Example |
|---|---|---|---|
| Smoke runs (EXPLORATORY), including the LB-04 halt proof | 3–4 | 3–4·s | 0.15–0.2M |
| Pilots P1–P8: 4 × S1/S3, P8 swap, P5–P7 S2 bounded by SC | 8 | 5·s + 3·min(natural S2, SC) | 1.15M (about 0.55M if the `ifabric` S2 doesn't loop) |
| Baseline (C9): 2 each of S1, S2 (enforce, halted at CAP), S3 | 6 | 4·s + 2·CAP | 0.5M |
| Named N1–N9 (N2 observe → SC; N3 enforce → CAP) | 9 | 7·s + SC + CAP | 0.8M |
| Adversarial live cases (H-01, H-04 → CAP, R-06 → 1–2·CAP, R-01 if D10) | 3–5 | about 2·s + 2–3·CAP | 0.4–0.55M |
| Inline-stop demo, its rehearsal, and a judge-day live run | 2–3 | 1–2·CAP + s | 0.2–0.35M |
| Re-runs (about 30% of pilots, named and adversarial) | 6–10 | about 0.3 × those | 0.6–0.75M |
| **Total** | **about 37–45** | | **about 3.5–4.3M upper; about 2.5M if S2 doesn't loop** |

**Verdict: feasible.**
- Spread over about 10 h, that is about 0.35–0.45M an hour on average.
- The heaviest hour is the pilot block: 3·SC + 5·s ≈ 1.15M in about 1.5 h, under 2.5M/h.
- If all three S2-class pilots fall into one 60-min window, a 20% margin needs 3·SC + 0.25M ≤ 2.0M, so SC ≤ about 580K. Keep SC ≤ about 300K anyway.
- Requests (49/min peak) are not binding.

**What breaks it:**
- **An unbounded S2-class run** (LB-04 unproven, or SC mis-pinned) costs about 2.0M in about 5 min and up to about 1 h of stalled lane. One fits in the 13:00–15:00 buffer; two don't.
- **The lane's clock.** About 3.3 h of pure run time plus builds, freezes and pack work fits in 22:00–08:30 UTC only if each OK takes minutes. The human, not the token ceiling, is the binding constraint, together with the 06:29:19Z credential expiry.

---

## Top delivery risks (ranked)

1. **One human gates the whole night (HL-03, HL-04, TC-07).**
   - **Why:** the owner, captain and builder is the same person. Sleep or fatigue stalls the live lane, the T2 sign-offs and every merge.
   - **Mitigation:** batched run-card OKs; `+yolo` merges; finish P0 (C16) by about 05:00 UTC, then apply the cut lines.
2. **AWS credentials expire at 06:29:19Z (OP-01).**
   - **Why:** the expiry lands in the baseline/C9 block. Runs, pulls, kubectl, S3, the secret scan and therefore every push stop together.
   - **Mitigation:** one refresh at 03:30–04:00 UTC covers the deadline.
3. **ServiceNow sits on the hard line (SN-02, SN-09, SN-12).**
   - **Why:** there is no assessed run before T1 and T2. The credentials are not on the laptop, and the package has no approval-record code. Arth's availability overnight is unknown.
   - **Mitigation:** credentials from Sree's own vault tonight; T2 by Option A (the owner in the UI); D11 = laptop.
4. **The fleet would start blind on an untried pipeline (TC-05, TC-06, TC-04).**
   - **Why:** the contracts are untracked and unpushed; no-mistakes has never run here; the repo has no CI; no Firstmate home or registry exists for the repo.
   - **Mitigation:** push first; register; put one pilot PR through no-mistakes before fanning out.
5. **Human-loop evidence can lie (SN-05, SN-06, SN-07).**
   - **Why:** a dry run writes DELIVERED; later updates turn a real response into false silence; a relative log path splits the log.
   - **Mitigation:** scratch log for dry runs, the two minimal fixes, export right after each response, an absolute log path.
6. **Laptop sleep (OP-03).**
   - **Why:** idle sleep is 1 minute and is held off only by transient assertions. Sleep kills the background fleet, `prooflab watch` and the live lane.
   - **Mitigation:** `caffeinate -dimsu`, AC power, lid open.
7. **An unbounded S2-class run (LB-04).**
   - **Why:** one costs about 2M tokens and about 1 h of lane.
   - **Mitigation:** prove the halt on a low cap first; SC ≤ about 300K; a headroom check per run.
8. **Fleet quota unknown (TC-11).**
   - **Why:** Claude headroom can't be read without a one-time Keychain approval, and no-mistakes reviews draw on the same quota.
   - **Mitigation:** approve the read; size the fleet to what it shows.
9. **Python drift (PY-02).**
   - **Why:** workers default to 3.12, while the judge may run 3.9.
   - **Mitigation:** a 3.9 venv as the test command; optional 3.9 CI.
10. **Shared-instance fragility (SN-03, AI-02, AI-04, AI-05).**
    - **Why:** a Global OAuth property that facilitators can revert, and L2/L3 proof that depends on Arth.
    - **Mitigation:** `selftest` before each batch; collect the AWS half of the AICT proof ourselves (AI-06); give Arth a 09:30 UTC deadline.

---

## What must happen in the first 2 hours (23:00–01:00 UTC on 2026-10-05/06)

In order. Each item has an owner, and none needs a live AWS write.

1. **Push the contracts (lead, with the captain's OK; about 10 min).** Commit `architecture/` and the three modified files, run the secret scan (valid until 06:29Z) and push to `main`. This is the fleet's prerequisite (TC-05).
2. **Keep the laptop awake (captain; 2 min).**
   - `caffeinate -dimsu` in its own terminal; stay on AC; lid open; pause OS updates (OP-03).
   - Set two alarms: **03:30 UTC (22:30 CDT), refresh AWS credentials** (OP-01, OP-02), and a backstop at 05:45 UTC.
3. **ServiceNow credentials onto the laptop (captain, else Arth; about 15 min).**
   - Write `~/.prooflab-snow.env` (600) with an absolute `PROOFLAB_DELIVERY_LOG`.
   - Run `selftest`, which is read-only (SN-02).
   - Decide D11 = laptop (SN-12).
4. **Message Arth with the asks (captain; 5 min):**
   - confirm the integration user, the OAuth app and the Global property, and send the courtesy note (SN-03);
   - is `my_agent` visible in AICT now (AI-02)?
   - the T2 mechanism, or agree on Option A (SN-09);
   - the export format and the 09:30 UTC deadline (AI-04); the L3 agent plan (AI-05);
   - his availability window and time zone; whether he will be the assurance reviewer on T2 (HL-04);
   - closing INC0010231 before judging.
5. **Decide what only the captain can (captain; 10 min):**
   - the T2 mechanism, by 01:00 UTC (SN-09);
   - the delivery posture and `+yolo` for the repo (TC-07);
   - the safety ceiling ≤ about 300K and the cap (D2) used in the budget (LB-01);
   - the roles table (HL-04);
   - confirm the deadline and the account's end time with the organisers (OP-04).
6. **Set up Firstmate (captain launches; the first mate executes; about 30–45 min).**
   - Launch the first mate in `~/workspaces/projects/firstmate`, in a session separate from the live lane.
   - Register the project from GitHub; `config/backend` = `tmux`; `no-mistakes init && no-mistakes doctor` in the clone.
   - Approve `quota-axi --allow-keychain-prompt` once (TC-04, TC-10, TC-11).
7. **Prove the pipeline (fleet).**
   - Create the 3.9 test venv outside the repo (PY-02).
   - W0 (contract v1) goes first, as the pilot PR through no-mistakes. It defines the test command and the CI step (TC-06).
   - Briefs carry the secret-scan command (TC-08) and the no-live-calls rule (TC-09). Then spawn W1–W10, plus the bug fixes (a) and (b) in W9.
8. **Read-only live-lane L1, in parallel (lead).**
   - OC-4, -7, -13, -14, -15 as planned, and the OC-8 ledger POST (it needs an OK).
   - Plan the smoke phase so LB-04's halt proof comes before any S2-class run.

---

## Evidence log (read-only; times UTC, 2026-10-05; no secret printed)

| Time | Command (what it did) | Result used above |
|---|---|---|
| 23:00:52 | `date -u`; `curl -sI https://platformdemoh8.service-now.com` (no credentials) | 200 OK, `snow_adc`, HSTS (SN-01) |
| ~23:01 | `/usr/bin/python3` urllib HEAD on `/` with no redirect, no credentials | 200; LibreSSL 2.8.3; CA `/private/etc/ssl/cert.pem` (SN-01) |
| ~23:01 | `which -a python3`, `--version` | Anaconda 3.12.7 first; Homebrew 3.14.8; `/usr/bin` 3.9.6 (PY-02) |
| ~23:01 | `--version` of claude, tasks-axi, treehouse, no-mistakes, gh, gh-axi, lavish-axi, quota-axi, chrome-devtools-axi, node, git; `tmux -V`; `treehouse get --help` | Versions in TC-02; lease supported |
| ~23:02 | `gh auth status` (token lines removed); `gh repo view … --json` | `satyabrat-invences` active; ADMIN, private (TC-03) |
| ~23:02 | Firstmate: `ls` of data/config/state; `.lock` pid check; `git log -1`; floors in `bin/fm-*-lib.sh` | TC-01, TC-02, TC-04 |
| ~23:03 | `git --no-optional-locks status/log/branch` in the repo | `architecture/` untracked; last push 6905e47 (TC-05) |
| ~23:03 | `no-mistakes doctor`, `daemon status`, `stats`; config keys only; daemon PATH entries only | No runs yet; daemon OK; `agent: auto`; `ci_timeout 168h` (TC-06) |
| ~23:04 | `aws sts get-caller-identity`; `~/.aws/credentials` mtime and key names only | WSParticipantRole/Participant; file written 18:30:06Z (OP-01) |
| ~23:04 | CloudTrail `lookup-events` (ResourceName = WSParticipantRole, 2026-10-04..06); filtered to time, duration and expiry; key compared in-shell | 11 × 43200 s; current key expires 2026-10-06T06:29:19Z (OP-01) |
| ~23:05 | CloudTrail `lookup-events` for ListAgentRuntimes, GetAgentRuntime and StartQuery by the AICT role, 20:00–23:10Z | 12 lists at 14–16 min; `my_agent` read 12×; filter `InvokeAgent` at 22:52:58Z (AI-01–AI-03) |
| ~23:05 | `bedrock-agentcore-control list-agent-runtimes` (names, update times, status only; no env) | 5 runtimes, no `ifabric_` yet (AI-02) |
| ~23:06 | `kubectl get agentgatewaypolicy` (the `rateLimit` block only) | 100 req/min + 2.5M tokens/h on `llm` (LB-01) |
| ~23:06 | `pmset -g batt`, `pmset -g`, `pmset -g assertions`, clamshell state | AC 30%; `sleep 1`; transient assertions (OP-03) |
| ~23:06 | `quota-axi --provider claude --no-credential-refresh` | `keychain_access_required` (TC-11) |
| ~23:07 | In-memory `compile()` of `prooflab/**/*.py` with 3.9.6; grep for third-party imports | 12 ok, 0 bad; none (PY-01) |
| ~23:08 | Locating the scratch venv; `pytest --version` | `venv-prooflab`: 3.12.7, pytest 9.1.1 (PY-02) |
| ~23:09 | Logs Insights on `aws/spans`, the last 8 h, model calls per hour | 1–2 calls/h (LB-01) |
| ~23:10 | `df -h`, `sysctl hw.memsize/ncpu`, `memory_pressure`, `docker ps`; existence of `~/.prooflab-snow.env`, `/tmp/modaas-token` | TC-12; SN-02 (absent); token file present, mode 600 |
