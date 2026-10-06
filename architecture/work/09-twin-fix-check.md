# 09 · Twin fix check: the organisers' objects in our evidence bucket

Written 2026-10-05, 23:20–23:55 UTC, by a read-only investigation subagent, for the captain's question: do the four "twin-fix" objects the organisers put in our team evidence bucket at 21:14–21:21 UTC change notes #57 or #58 or gap 10, and can the twin now produce a declared breach that reaches the agents?

**Scope.** The four objects, the `network-twin` Lambda and ToolConfig, the event asset bucket's twin pages and files, and the organisers' activity in our account on 2026-10-05.

**Method.** Strictly read-only. AWS and cluster calls went through `workshop-local/env.sh` as `WSParticipantRole`.
- **Read:**
  - notes #57 and #58
  - `gap-list.md` gaps 10 and 11
  - memory `workshop-progress` (Module 10)
  - `ARCHITECTURE.md` (the breach lever, §5.5, and the twin rows)
  - `work/03-decision-options.md` (D9, the C7 E3 option, F1)
  - the kit copies in `workshop-static/`: `scripts/twin-scenario.sh`, `data/twin-dataset.json`, `lambda/network-twin/*`, `scripts/bootstrap-platform.sh` and `cfn/02-code-editor.yaml`
  - the guide's MCP call pattern from `workshop-assets/kb/index.json`
- **Run:**
  - S3:
    - `s3api list-objects-v2`
    - `list-object-versions` (AccessDenied)
    - 4 × `head-object`
    - `s3 cp` of the 4 objects and the 4 `content/digital-twin/*.en.md` pages to the scratchpad
    - `s3 ls` of the event bucket
  - Lambda: `list-functions` and `get-function-configuration` (environment values withheld except `DATA_DIR`). `list-versions-by-function` and `list-aliases` returned AccessDenied.
  - CloudTrail `lookup-events`:
    - 20:50–21:40 UTC: 2,005 events
    - `Username=Ops` for all of 2026-10-05: 2,403 events
    - `Username=WSControlPlaneUser` since 2026-10-04
    - the IDE instance session, 10:20–13:10 UTC
  - CloudTrail `describe-trails`: AccessDenied.
  - Logs: `filter-log-events` on `/aws/bedrock/aict-invocations`, an S3 filter plus a positive control.
  - Cluster and EKS:
    - `kubectl get toolconfig network-twin`
    - `kubectl logs` on the audit store (empty)
    - `eks describe-cluster` (logging)
  - `ssm list-commands`: AccessDenied.
- **Not run:**
  - The organisers' scripts. Executing the downloaded `twin-scenario.sh` on a scratch copy was declined by this session's permission guard, so everything below about its behaviour comes **from reading the code**.
  - `fix-twin.sh`: never intended to be run, because it writes `/tmp` and `~/evidence`.
- **No** writes to AWS, the cluster or the bucket. No secret, key or bearer link was printed. CloudTrail source IPs are not reproduced here.

---

## Verdict in one screen

**The twin the agents call has not changed. #58, gap 10 and the breach-lever decision stand.** The four objects repair the *IDE-side recipe helper* for Module 10's "Scenario recipes" page. They don't touch the `network-twin` tool:

| Object | What it is |
|---|---|
| `facilitator/twin-scenario.sh` | A **rewritten helper**: it prints JSON, adds `trap`, never writes the dataset, and defaults to the IDE bootstrap's copy of the dataset |
| `facilitator/fix-twin.sh` | A **repair script** for the IDE. It installs that helper at `/tmp/twin-scenario.sh` and restores the dataset if it is missing (most likely the "missing twin file"). Then it writes `~/evidence/twin-vs-agent.json` |
| `facilitator/twin-vs-agent.json` | The `trap` result, **precomputed from our own ledger**: two of our run ids, `disagree: false` for all three sites |
| `facilitator/twin-dataset.json` | **Byte-identical** to the kit's dataset (same three sites, nothing for S2). A fallback copy, not a new dataset |

- **#57 (the recipes are broken): partly fixed, and only out of band.** The new helper fixes JSON output, `trap`, the in-place overwrite and the dataset path. It lives only in our bucket's `facilitator/` prefix; the page and the event bucket are unchanged. Still broken:
  - `recovery >> drift-pair.json` gives invalid JSON;
  - no drift value is computed;
  - recipe 1's diff;
  - the file-count checkpoint.
- **#58 (breach on demand can't reach the agents): unchanged.** The Lambda is the same: same `CodeSha256` and `LastModified`, `DATA_DIR=/var/task`, ToolConfig generation 1. The new helper's `breach` doesn't even edit a file any more: it **prints** a declaration.
- **Gap 10 (element ids get "no twin data"): unchanged.** The handler is the same. The organisers' trap works around the element/site mismatch **by substring matching on the scoring side**, not in the tool.
- **Can a declared twin breach now reach the agents? No.** The only path from the twin to an agent is gateway → AgentCore Gateway → the Lambda → its own packaged `/var/task/twin-dataset.json` (2026-10-04 10:37 UTC). Nothing in the four objects touches that path.
- **Breach-lever decision (D9, §5.5): no change.**
  - The new `breach` output is a JSON fixture (every site at −110 dBm, "breached"). It could only feed a control that reads twin values, and our C9 reads AgentCore `Latency` (M1).
  - For C7, the trap's `twin_answer` is decided by the script, not by the twin, so it is not independent ground truth (E3 stays out).

**Also found: not twin changes, but they matter to us** (§7):
1. **The organisers ran seven shell commands on our IDE this morning** (SSM `AWS-RunShellScript`, 10:29–12:49 UTC). The content is hidden from us. This is the most likely "morning fix" (inferred).
2. **At 18:10 UTC the organisers granted versioned reads on our evidence bucket** (`s3:ListBucketVersions`, `GetObjectVersion`, `GetObjectVersionAttributes`) to the IDE role and `participant-app-role`, but **not** to `WSParticipantRole`, the role our laptop uses. This changes R-C-16.
3. **The organisers audited the account at 21:29–21:34 UTC:**
   - `GetFunction` on all seven tool Lambdas;
   - our gateway and evidence log groups;
   - 8 h of CloudTrail;
   - ECR and CodeBuild.

   Similar-sized sweeps ran at 13:xx and 16:xx UTC.
4. **The organisers read our ledger:** `twin-vs-agent.json` embeds two of our run ids.

---

## 1. What landed in the bucket

Bucket `team-evidence-613052889143`: the CFN output `TeamEvidenceBucketName` and `$TEAM_EVIDENCE_BUCKET` agree. **These four are the only objects in the bucket**, with no other prefixes.

| Key | LastModified (UTC) | Bytes | VersionId | Content-Type | ETag (= MD5) | sha256 (first 12) |
|---|---|---|---|---|---|---|
| `facilitator/twin-scenario.sh` | 2026-10-05 21:14:54 | 5,017 | `hFDOw4uvmTIM8El9k7DasLwzhzcT1t4j` | `application/x-sh` | `9edc585a…b01b` | `8ec1f6e848e6` |
| `facilitator/twin-vs-agent.json` | 2026-10-05 21:15:19 | 470 | `MyB8O7t.bZEhyozoqTLHcpxd.BeuLeNN` | `application/json` | `5a73d735…de74` | `104fd2e51b3e` |
| `facilitator/fix-twin.sh` | 2026-10-05 21:21:47 | 2,571 | `VzN4FHIGZUsArywna3sCxK8nI1HLUcz_` | `application/x-sh` | `cc7ffa31…a4b8` | `433336bd56f5` |
| `facilitator/twin-dataset.json` | 2026-10-05 21:21:56 | 2,162 | `E4ecQgd4nbV7cK07iU09hJVhqk2.CVpd` | `application/json` | `8086ffff…2a3b` | `0fb69cf4e082` |

- **All four objects:**
  - SSE `AES256`, a full-object CRC64NVME checksum, `STANDARD` storage class;
  - **no user metadata**;
  - the same owner id (an account-level identity, which can't tell roles apart).

  The content types are what the AWS CLI guesses from the file extension, which suggests a plain `aws s3 cp`.
- **VersionIds are present,** so the bucket is versioned (consistent with 03 F1).
- **`ListBucketVersions` is AccessDenied for our role,** so we can't see whether these are first versions or whether earlier objects were written and deleted. (The IDE role can list versions since 18:10 UTC; see §7.)
- **Local copies** (ephemeral): `/private/tmp/claude-501/-/ca14fa49-a079-47de-a9fb-a38b37dcff99/scratchpad/twinfix/obj/`.

## 2. Who wrote them

**Authorship is self-declared:** the `facilitator/` prefix, *"Event-side helper … (build 9cdfd646)"*, *"using the facilitator copy"*, *"tell a facilitator"*. **The exact writing principal is not provable from anything we can read:**
- `PutObject` is an S3 *data* event, and `lookup-events` returns management events only.
- `cloudtrail:DescribeTrails` is AccessDenied to us.
- The one CloudTrail data-event sink we can read, `/aws/bedrock/aict-invocations` (trail `sgc-aict-bedrock-trail`), holds **no S3 events at all** since 2026-10-04. Our positive control on Bedrock events did return matches, so the filter works.
- The audit store writes no log at all (0 bytes, as in the 17:37Z snapshot).
- EKS control-plane logging is still off on all five types, and its log group doesn't exist.

**The circumstantial chain** (UTC, management events):

| Time | Event |
|---|---|
| 20:52:51 | `user/WSControlPlaneUser` → `AssumeRole` `WSOpsRole`, session `Ops`, 12 h. The kit's `cfn/01-eks-cluster.yaml` names `WSOpsRole` as the facilitators' role |
| 20:53:07–27 | `WSOpsRole`: `eks:DescribeCluster` and `ListAgentRuntimes` from an organiser laptop. Its CLI and OS fingerprint (aws-cli 2.33.18, macOS 25.6) differ from ours (aws-cli 2.37.9, macOS 25.2) |
| 20:53:18, 21:09:38, **21:14:34** | `WSOpsRole` `sts:GetCallerIdentity` with user agent `Go-http-client/1.1` from the same two source addresses our own kubectl logins show. That is the EKS authenticator verifying a **kubectl token**: the organisers were using kubectl on our cluster |
| 21:10:28 | The last `WSParticipantRole` (team) management event in the 20:50–21:40 window |
| **21:14:54** | `twin-scenario.sh` lands (20 s after the kubectl login) |
| **21:15:19** | `twin-vs-agent.json` lands. It holds our run ids, which can only come from our audit store's `/records` (what `trap` reads via kubectl) |
| 21:21:47 / 21:21:56 | `fix-twin.sh` / `twin-dataset.json` land |
| 21:29–21:34 | The `WSOpsRole` account sweep (§7) |

**Conclusion:** the objects were written by the organisers, almost certainly from the `WSOpsRole` session that began at 20:52:51. That session read our ledger through kubectl at about 21:14 to build `twin-vs-agent.json`. This is an inference, but nothing points elsewhere.

## 3. What each object is (from reading the code)

### 3.1 `twin-scenario.sh`: the rewritten helper

| | Kit `static/scripts/twin-scenario.sh` (1,958 B, 2026-10-04 09:36 UTC) | Organisers' version (5,017 B, 2026-10-05 21:14:54 UTC) |
|---|---|---|
| Scenarios | `baseline`, `breach`, `recovery` | the same, **plus `trap`** |
| Output | text | **JSON** |
| Writes the dataset? | `breach`/`recovery` **overwrite** `twin-dataset.json` in place | **No**: `json.load` only; every scenario prints to stdout |
| Dataset path | `$(dirname $0)/../data`, which is `/data` when run as `/tmp/twin-scenario.sh`, so it fails (#57) | `$TWIN`, else `~/.modaas-bootstrap/assets/data/twin-dataset.json`: the copy the IDE bootstrap fetches (it runs as `ec2-user`, `HOME=/home/ec2-user`) |
| `baseline` | echoes one line | a JSON list `{site_id, rsrp_dbm, assessment, confidence}` per site |
| `breach` | sets RSRP to ≤ −110, loss ≥ 5 % in the file | **prints** `{"scenario":"breach","sites":[…]}` with **every site at −110 dBm** and "breached: packet loss above SLO threshold". The original confidence is kept, and no drift value or threshold is computed |
| `recovery` | rewrites the file to −82 dBm, healthy | **prints** every site at −82 dBm, "healthy: protection path active" |
| `trap` | none (exit 2) | twin vs agent per site (below) |

**How `trap` decides:**
- **Source:** `kubectl get --raw /api/v1/namespaces/components/services/audit-store:8080/proxy/records`, falling back to `~/evidence/actual-events.json`.
- **`twin_answer` is written into the script, not asked of the twin:** `SITE-PHX-04` → `escalate` *by site id*; otherwise `resolve` if the assessment string contains "degraded", else `no-action`. Neither the `network-twin` Lambda nor MAVERIC is consulted.
- **`agent_answer`:**
  - it takes the newest run whose records contain the site tag (`SITE-DEN-12` → `DEN-12`) *anywhere* in the JSON;
  - it reads the disposition with the regex `disposition=` on `detail`, preferring an actor containing "network";
  - it maps `auto-resolve` to `resolve`.
- **Element ids:** this matches runs to sites through the element names (`DU-DEN-12-A` contains `DEN-12`). The organisers bridged gap 10's element/site mismatch **in the scorer**, not in the tool.

### 3.2 `fix-twin.sh`: the IDE repair ("Module 10 step 2 repair", step 2 being the "Scenario recipes" page)

1. **The helper.** If `/tmp/twin-scenario.sh` doesn't hash to `8ec1f6e848e6…` (the object above), it saves the old copy as `.old` and downloads `s3://team-evidence-$ACCT/facilitator/twin-scenario.sh`. If `/tmp` isn't writable, it installs the helper at `~/twin-scenario.sh` instead.
2. **The dataset.** If `~/.modaas-bootstrap/assets/data/twin-dataset.json` is missing or empty, it fetches it from the public assets URL for build `9cdfd646`, then falls back to the bucket copy. If that path isn't writable, it uses `~/evidence/.twin-dataset.json`.
3. **The trap.** It runs `trap` into `~/evidence/twin-vs-agent.json`. **If that prints nothing, it copies the organisers' precomputed `twin-vs-agent.json` in its place;** only a console line says so.
4. **The check.** It validates the JSON and prints one line per site.

- **Only one artifact.** It produces only recipe 3's artifact, not `expected-events.json` or `drift-pair.json`.
- **Defensive branches.** The "not writable" branches fit files left root-owned by the morning's root SSM commands (§7). This is an inference: we can't see the IDE.
- **Our laptop.** Our laptop's `~/evidence` is empty, so nothing from this script is in what `submit.sh` would package.

### 3.3 `twin-vs-agent.json`: the trap, run on our ledger

| site | twin_answer | agent_answer | run_id | disagree |
|---|---|---|---|---|
| SITE-DEN-12 | resolve | resolve | `fault-1791179282-8ef1a8` | false |
| SITE-DEN-09 | no-action | null | null | false |
| SITE-PHX-04 | escalate | escalate | `fault-1791177926-b0ce69` | false |

- **The run ids are ours:**
  - `fault-1791179282-8ef1a8` is the Module 7 swap S1 run (05:47 UTC);
  - `fault-1791177926-b0ce69` is the user's S3 re-run (about 05:24 UTC).

  Both are in memory `workshop-progress`.
- **The page expects `disagree: true`; on our data the trap finds no disagreement.** SITE-DEN-09 has no scenario, so it has no agent answer.

### 3.4 `twin-dataset.json`

The sha256 is `0fb69cf4…`, **identical** to the kit's `static/data/twin-dataset.json` and `assets/data/twin-dataset.json` (local copies). The event bucket's `assets/data/twin-dataset.json` has the same MD5 ETag, `8086ffff…2a3b`. It has the same three sites, no S2 site and no element-to-site map.

## 4. Did anything else change for the twin?

| Item | Before (our notes) | Now (2026-10-05 ~23:30 UTC) | Changed? |
|---|---|---|---|
| Lambda `team-a61f5-network-twin`: LastModified | 2026-10-04 10:37 UTC | `2026-10-04T10:37:34.898+0000` | No |
| CodeSha256 / CodeSize | `PaWw7RVO…` | `PaWw7RVOWUexhnPJJFJ98xQ12vZB+J1UIa2zX9IX/+E=` / 1,578 B | No |
| `DATA_DIR` | `/var/task` | `/var/task`. The env names are `AUDIT_URL`, `CLUSTER_NAME`, `DATA_DIR`, `GATEWAY_LOG_GROUP`, `INDEX_PATH` and `TEAM`. RevisionId `e9e678bf-…`; role `participant-app-role`; no layers | No |
| Versions / aliases | ToolConfig unqualified (`$LATEST`) | AccessDenied to us; the ToolConfig is still unqualified | n/a |
| Other functions | 7 tool Lambdas | the same 7 (LastModified 2026-10-04 10:37:06–10:45:14) plus `WSConcurrencyCurtailer` (2024); no new function | No |
| ToolConfig `network-twin` | Approved, `system-admin` | generation 1 = observed 1; created 2026-10-04T10:37:57Z; Approved; endpoint the unqualified function ARN | No |
| Event bucket `ws-event-70748eba-1eb-us-east-1/9cdfd646-…/` | "nothing dated 2026-10-05" | 290 objects (assets 90, static 136, content 62, manifest, metadata); **newest 2026-10-04T09:36:20Z** | No |
| Module 10 pages (`content/digital-twin/*.en.md`) | as in #57 | unchanged. They still say `/tmp/twin-scenario.sh`, `static/data/twin/`, `recovery >> drift-pair.json` and the timeline diff | No |
| CFN stacks | — | last update of any stack 2026-10-04T22:45:14Z | No |
| Bootstrap re-run | — | step 14 **skips any tool Lambda that already exists** (`get-function` → `continue`), so a re-run can't refresh the twin | — |

**Correction to #57:** the event bucket's objects are dated 2026-10-04 **09:36 UTC**, not 04:36 UTC. `aws s3 ls` printed CDT; `list-objects-v2` gives `09:36:19+00:00`.

## 5. Verdict

### 5.1 #57: partly fixed, out of band only
- **Fixed, if a participant runs `fix-twin.sh` or uses the new helper:**
  - `baseline` emits the JSON the page expects;
  - `trap` exists;
  - `breach`/`recovery` no longer destroy the baseline;
  - the dataset path resolves on the IDE.
- **Still broken:**
  - Nothing is shipped through the page or the event bucket: the fix exists only in each team bucket's `facilitator/` prefix.
  - The page's `recovery >> drift-pair.json` concatenates two JSON documents, so the file is still not valid JSON.
  - `breach` computes no drift value: it sets every site to −110 dBm.
  - Recipe 1's ledger diff still can't work: the timeline is text, and no record has a `site` field.
  - The checkpoint still only counts files.
  - The trap's "ground truth" is hard-coded.

### 5.2 #58: unchanged
- **The agents' twin is the same.** It is the same code and data package (identical `CodeSha256`), reading its own `/var/task` copy.
- **"Breach on demand" still can't reach the agents.** It is now *less* connected than before: the old helper at least edited a local file, and the new one only prints.
- S2 still has no site.

### 5.3 Gap 10: unchanged
- **The handler is unchanged,** so `DU-DEN-12-A`, `RTR-DEN-12-CORE` and `RTR-PHX-04-CORE` still return "no twin data for site".
- **The organisers' scorer matches element names to sites by substring.** That shows the mismatch is known, but the tool still takes site ids only.

### 5.4 Could the twin now produce a declared breach that reaches the agents? No.
- **Nothing in the four objects reaches the agents.** What reaches an agent is only what `predict_rsrp` returns from the packaged dataset.
- **Only two things would change what agents see:**
  - **(a) Replacing the shared tool's code or package** (`lambda:UpdateFunctionCode`; a config change alone can't help, because the only data is in `/var/task`). Participants appear able to do this (gap 11). But it changes an organiser-approved, shared tool under its old approval, which is exactly gap 11's hole. It would also change what the reference agents see, and `ARCHITECTURE.md` says "clone rather than modify" shared ToolConfigs without the user's explicit OK. **Not recommended.**
  - **(b) Our own declared twin tool:** a clone Lambda plus a ToolConfig through review, with a breach dataset version named in the register. That is a build, not a spike, and it is only worth it if a control reads twin values.

### 5.5 Impact on the breach-lever decision (D9, §5.5)
- **None.** The twin still can't produce PASS/BREACH runs on the agents, and the `ARCHITECTURE.md` row "The twin can't make breaches (gap 10) → declared levers (§5.5)" stands.
- **C9:** M1 is AgentCore invocation `Latency`. A twin RSRP fixture doesn't move it, so B9-1 (the S2 runaway), B9-2 (a declared injected delay) and B9-3 (a model swap, unproven) remain the options.
- **C7:** option E3 (the twin as the expected source) stays out. `twin_answer` is decided by the script, it covers three sites with nothing for S2, and the twin emits no events.
- **The new `breach` JSON is usable only as a declared fixture** for a control that reads twin predictions. If it is ever cited, label it "a declaration printed by the organisers' helper", not "a twin state".

## 6. Spike to confirm empirically (not run; needs the captain's OK)

The static evidence already settles it: the helper writes nothing, and the Lambda reads its own unchanged package. This spike turns that into **gateway evidence** we can cite.
- **Cost:** about 10 minutes, 0 model tokens.
- **What it changes:**
  - it creates one throwaway pod per call (the guide's `incluster` pattern);
  - it adds about 4 governed tool calls, with no run id, to the gateway and PDP logs;
  - step 3 runs the organisers' code.

0. In the `workshop-local` shell (`source env.sh`), check that `/tmp/modaas-token` exists with mode 600. Re-extract it if the laptop rebooted (memory `workshop-aws-access`), and never print it. Note the UTC start time, and pick a time with no assessed runs.
1. **Identity before:** `aws lambda get-function-configuration --function-name team-a61f5-network-twin --query '[LastModified,CodeSha256,RevisionId,Environment.Variables.DATA_DIR]' --output text`. Expect `2026-10-04T10:37:34.898+0000  PaWw7RVO…  e9e678bf-…  /var/task`.
2. **Call A, through the governed door the agents use.** Use the guide's own MCP recipe (the docs-tool page, "4. Ask it something", `platform-access/docs-tool.en.md`: `incluster kb-probe --env="TOKEN=$TOKEN" -- sh -c '…'`) with:
   - `U=http://modaas-agw.agentgateway-system:8080/mcp/network-twin`
   - `initialize`, then capture `Mcp-Session-Id`
   - `tools/call` with `{"name":"network-twin___predict_rsrp","arguments":{"site":"SITE-DEN-12"}}`
   - in the same pod, a second `tools/call` with `{"site":"DU-DEN-12-A"}`

   Save both bodies to the scratchpad. Expect `rsrp_dbm: -98`, "degraded: fronthaul packet loss reducing effective RSRP by 6 dB", and then `"no twin data for site DU-DEN-12-A"` (gap 10).
3. **Declare the breach as the recipe intends:** on the IDE after `fix-twin.sh`, `bash /tmp/twin-scenario.sh breach`; or on the laptop, `TWIN=<scratch copy> bash <scratch>/twin-scenario.sh breach`. Expect every site at −110 dBm, "breached: …".
4. **Call B:** repeat step 2 exactly.
5. **Identity after:** repeat step 1.
6. **Evidence:** in `/aws/modaas/gateway` and the PDP log, find the four `network-twin` `tools/call` lines in the window and record their action ids and times. Label them "spike, not a run" in our notes so they're never read as agent calls.

**Pass:** A and B are byte-identical, and steps 1 and 5 are identical. That confirms "a declared twin breach does not reach the agents" (n = 1). **Any difference:** stop, and check CloudTrail for `UpdateFunctionCode20150331v2` or `UpdateFunctionConfiguration20150331v2` on the function.

## 7. Other organiser activity in our account today (side findings, not twin changes)

All of the following come from CloudTrail management events made by `WSOpsRole` (session `Ops`, assumed by `WSControlPlaneUser`).
- **Sessions on 2026-10-05:** at 10:23, 11:55, 13:27, 15:49, 18:08, 20:52, 22:09 and 23:13 UTC.
- **Non-read events on 2026-10-05:** exactly 9. S3 object writes don't appear here.

1. **Seven SSM `SendCommand` (`AWS-RunShellScript`) calls to our IDE instance `i-0e9832c8d45eb0273`,** at 10:29:37, 11:02:28, 11:55:57, 11:57:25, 12:31:27, 12:42:21 and 12:49:58 UTC (05:29–07:49 CDT).
   - CloudTrail hides the parameters, and `ssm:ListCommands` is AccessDenied to us, so **what they did is unknown**.
   - The IDE role's only non-heartbeat API calls in that period were two kubectl logins, at 12:49 and 12:50, right after the last command.
   - These are the most plausible source of the captain's "fixed a missing twin file this morning". **The bucket objects are not:** they came at 16:14–16:21 CDT.
   - The IDE is therefore **not a team-exclusive environment.** Anything there, including `~/evidence`, can be changed by the organisers, which is one more reason to build the pack on the laptop.
2. **`iam:PutRolePolicy` `EvidenceVersionRead`** on `a-02-code-editor-IdeInstanceRole-…` (18:10:39) and `participant-app-role` (18:10:41).
   - It allows `s3:ListBucketVersions` on `team-evidence-613052889143`, plus `s3:GetObjectVersion` and `GetObjectVersionAttributes` on its objects.
   - `WSParticipantRole` did **not** get it: our call at about 23:25 UTC was still denied.
   - **This changes R-C-16** ("participants … can't list its versions"): the IDE role, and the tool Lambdas' execution role, now can.
   - It helps T1, the date proof: the IDE can now show a register object's version history.
3. **Account audit sweep, 21:29–21:34 UTC (566 events from that session):**
   - `lambda:GetFunction` on all seven tool Lambdas (it returns the code location and `CodeSha256`), with a KMS `Decrypt` of each one's environment;
   - `logs:FilterLogEvents` on `/aws/modaas/gateway` (26 calls) and `/modaas/evidence` (17), and once on `/aws/eks/a-01-eks-cluster-modaas/cluster`, filtering create/update/patch verbs on a log group that doesn't exist;
   - `cloudtrail:LookupEvents` (437 calls) over 13:27–21:27 in 2-hour slices;
   - ECR `DescribeImages` on the five MoDaaS repositories, CodeBuild, Bedrock logging and guardrails, IAM, GuardDuty and the AgentCore gateways and runtimes.

   Sessions at 13:27 (999 events) and 15:49 (791) were similar in size. This is an auditor reading our account, which is relevant to gap 11 and to how judges may check tool integrity and our evidence.
4. **They write into our evidence bucket.** The bucket we plan to use for T1 (`register/<version>.yaml`) and for `submit.sh` (`submissions/<team>/`) is not team-exclusive. Versioning still prevents backdating.
   - **Leave `facilitator/` alone:** don't delete it (`fix-twin.sh` depends on it), and don't treat it as our evidence.
   - **If `fix-twin.sh` is ever run where `submit.sh` packages `~/evidence`,** decide explicitly whether `twin-vs-agent.json` belongs in the pack. Its fallback can silently be the organisers' file.

## 8. Suggested follow-ups to other documents (not applied)

- **notes #57:**
  - add an update: "2026-10-05 21:14–21:21 UTC: the organisers put a rewritten helper and `fix-twin.sh` in each team bucket's `facilitator/` prefix (this doc)";
  - correct "04:36 UTC" to "09:36 UTC".
- **notes #58 and gap 10:** add "re-checked 2026-10-05 ~23:30 UTC: unchanged (same `CodeSha256`, `DATA_DIR=/var/task`, ToolConfig generation 1)".
- **`02-requirements.md` R-C-16:** the IDE role and `participant-app-role` can list and read versions since 2026-10-05 18:10 UTC; `WSParticipantRole` still can't.
- **Memory `workshop-progress` (Module 10) and `platform-observations-notes`:** record the `facilitator/` objects, the morning SSM commands and the 18:10 policy.
- **Candidate notes item:** the organisers' trap derives "ground truth" from the script, not from the twin, and finds no disagreement on our runs.

## Evidence log

| # | Call (read-only) | Result |
|---|---|---|
| 1 | `s3api list-object-versions --bucket team-evidence-613052889143` | AccessDenied (`s3:ListBucketVersions`) |
| 2 | `s3api list-objects-v2 --fetch-owner` | 4 objects, all `facilitator/` (§1) |
| 3 | 4 × `s3api head-object --checksum-mode ENABLED` | VersionIds, AES256, no metadata (§1) |
| 4 | `s3 cp s3://…/facilitator/ <scratchpad>/obj/ --recursive` | 4 text files; the MD5 of each equals its ETag |
| 5 | `cloudformation describe-stacks` | event bucket `ws-event-70748eba-1eb-us-east-1`, prefix `9cdfd646-…/assets/`; last stack update 2026-10-04 22:45:14Z |
| 6 | `s3 ls --recursive` on the event prefix; `list-objects-v2` max LastModified | 290 objects; newest 2026-10-04T09:36:20Z |
| 7 | `s3 cp` of `content/digital-twin/*.en.md` | 4 pages, unchanged since the build cut |
| 8 | `lambda list-functions`; `get-function-configuration team-a61f5-network-twin` | unchanged (§4); versions and aliases AccessDenied |
| 9 | `kubectl get toolconfig network-twin -n components` | generation 1, Approved, unqualified ARN |
| 10 | `cloudtrail lookup-events` 20:50–21:40Z (41 pages) | 2,005 events; `WSOpsRole` 566; team role last at 21:10:28Z (§2) |
| 11 | `cloudtrail lookup-events Username=WSControlPlaneUser` since 2026-10-04 | `WSOpsRole` sessions (§7) |
| 12 | `cloudtrail lookup-events Username=Ops` for 2026-10-05 (49 pages) | 2,403 events; 9 non-read: 7 × SSM `SendCommand`, 2 × `PutRolePolicy` (§7) |
| 13 | `cloudtrail lookup-events Username=i-0e9832c8d45eb0273` 10:20–13:10Z | 59 events; 2 kubectl logins (12:49, 12:50), the rest SSM agent heartbeats |
| 14 | `cloudtrail describe-trails`, `list-event-data-stores`; `ssm list-commands` | AccessDenied |
| 15 | `logs filter-log-events /aws/bedrock/aict-invocations`, S3 filter since 2026-10-04, plus a Bedrock positive control | 0 S3 events; the control matched |
| 16 | `kubectl logs` audit-store (since 20:45Z, tail 400, all) | 0 bytes: the store doesn't log |
| 17 | `eks describe-cluster` logging; `logs describe-log-streams /aws/eks/…/cluster` | all 5 types off; the log group doesn't exist |
| 18 | Local reads of `workshop-static/` (helper, dataset, handler, bootstrap step 14, `cfn/02-code-editor.yaml` UserData) and `kb/index.json` (the guide's `incluster` and MCP recipe) | §3, §4, §6 |
| — | Executing `twin-scenario.sh` on a scratch copy | **declined by the session's permission guard; not run** |
