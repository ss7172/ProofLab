# Independent review of the third commit's changes (2026-10-05, read-only)

- **What was reviewed:** everything changed since `ecadb62`:
  - `PLANNING-HANDOFF.md`: the new §5.9, the claim labels replaced by descriptions, the §0 controls line, and the gateway-policy permission corrections
  - `notes/workshop-reference/platform-contract.md` and `notes/verification/2026-10-05/platform-contract-verify.md`
  - the notes added at the top of `verify-live.md` and `verify-review-claims.md`
  - the memory changes, diffed against the `notes/claude-memory/` snapshot taken at `ecadb62`
- **Who and when:** a fresh Claude subagent that did not write the changes, 2026-10-05, 19:31–19:50 UTC.
- **Identity:** `arn:aws:sts::613052889143:assumed-role/WSParticipantRole/Participant`; cluster `a-01-eks-cluster-modaas`; kubectl v1.36.5.
- **How commands ran:** every live command used `bash -c 'source /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <cmd>'`.
- **Read verbs only:**
  - kubectl `get` (CRs through jsonpath or key names only), `logs`, `get --raw`
  - aws `sts get-caller-identity`, `logs get-log-events` / `filter-log-events`, `bedrock list-guardrails`, `bedrock-agentcore-control list-agent-runtimes` / `list-gateways`, `cloudformation describe-stacks` (OutputKey only)
  - the kit's `show-run-spans.py` (read first: it prints span summaries only)
- **Not used:** `kubectl auth can-i` (it POSTs a SelfSubjectAccessReview), so RBAC was read from the roles and bindings. No write. No secret was printed. Pod logs were saved under the scratchpad with umask 077 and only counted.

## Findings and fixes

| # | Severity | Finding | Evidence | Fix applied |
|---|---|---|---|---|
| 1 | Medium | §3b Q11 said the four refusing EPs (gateway+PDP, guardrails, admission, ledger) "take none of our code". The page, §3b Q3 and §5.9 all say the ledger is "Yes, with token" | Page table (`platform-contract.md`); KB chunk `#02` has "Yes, with token" | Q11 now says three of the four take none of our code, and the ledger takes our writes with the token |
| 2 | Medium | §5.9 said what the VAP refuses but not what it leaves open. `components`, where our ToolConfigs and AgentConfigs live, is not protected, and the CRD clause covers definitions, not resources. "Every change to the MoDaaS CRDs" could be read as "ToolConfig edits are refused", which would wrongly close the Cedar lever | Live VAP: `protectedNs` has 9 namespaces, without `components`; rule 2 applies only when `ns == ''`. Claude created `my-agent` (08:59:08Z) and paused/resumed `modaas-docs` (05:56Z) through our shell, after the VAP was created (10-04 10:49:31Z) | New §5.9 bullet on `components` and Cedar changes on our own `ifabric-*` ToolConfigs; §8 now lists the VAP's extra namespaces and says `components` is not protected |
| 3 | Medium | "Admission no" was stated without its limits. The VAP doesn't cover CONNECT, and by text it doesn't cover a route plus a policy in a team namespace, because the Gateway admits routes from all namespaces | Live: `operations: [CREATE, UPDATE, DELETE]`; Gateway listeners `http`, `llm` and `llm-tls` have `allowedRoutes.namespaces.from: All`; HTTPRoute and AgentgatewayModel `parentRefs` have `namespace`; AgentgatewayPolicy `targetRefs` don't | One sentence each in §5.9 (CONNECT; routes, "by text, untested"); §3b Q3 cross-references it. Memory `challenge-requirements` no longer says "neither is open to us" without qualification |
| 4 | Medium | `platform-contract-verify.md`'s "New findings" ("participants can edit the admission rules / the gateway's policies") and its EP 1/EP 3 RBAC caveats predate the VAP check, and the report never recorded it | VAP text (see "Admission policy facts" below) | Correction note at the top and an addendum at the end of the report (RBAC facts kept; VAP limits added) |
| 5 | Medium (process) | `res/verify-review-claims.md` lacked the committed vh.py note, so the commit's `rsync res/ → notes/verification/2026-10-05/` would have deleted that note from the repo | `diff` res vs repo: the repo had 2 more lines at the top | Note restored in `res/`; the two copies were identical before the rsync |
| 6 | Low | §0.2 said the committed snapshot (`bfb1ce6`) "lacks `reference-links.md`". `ecadb62` committed a refreshed snapshot that includes it | `git ls-tree ecadb62 notes/claude-memory/` | Reworded: refreshed with each commit; trust live memory if they differ. §0.3 "an older snapshot" → "a snapshot" |
| 7 | Low | §6 said `gap-list.md` was an "uncommitted working-tree change"; it is committed in `ecadb62` and unchanged since | `git status`; `git log -1 -- gap-list.md` = `ecadb62` | Reworded |
| 8 | Low | §7.9 (git state at 18:00Z) listed files as not yet committed; `ecadb62` committed them | `git log` | One sentence added (dated state kept) |
| 9 | Low | Memory `planning-handoff.md` body used "C1–C8". Only the §0 line and the memory description are allowed exceptions | grep | Reworded to "numbered claim labels" |
| 10 | Info | Notes #26 ("Impact: … They can also run pods in the gateway's own namespace") rests on `can-i` (RBAC only). By the VAP's text, a pod CREATE in a protected namespace is refused; `get secrets` and port-forward (CONNECT) are not | VAP rule 1; #26's own table | Not edited (notes items change only on the user's "add"). Flagged in the memory's parked #26 candidate |
| 11 | Info | The report's 573 id-less refused lines are the listener-attributed ones (24× 403, 127× 404, 422× 405). The pod log also has 27 listener-less 503 lines ("processing failed: no authority or host", malformed requests), which carry no ids either | Gateway stdout, bounded to ≤18:58:11Z: 1,692 request lines = 1,092 served + 573 + 27 | Not changed: "573 refused or unrouted lines carry no ids" is true |
| 12 | Info | A later agent used `kubectl auth can-i` (~19:15–19:25 UTC); the platform-contract verifier had avoided it as a POST. It is not persisted, but it is not a pure read verb | Handoff §5.9 and memory cite it | None; noted for the working agreement |
| 13 | Info | The one email address in the verification folder is in the already-committed `playbook-verify-lead.md` (unchanged here). Handoff §4.4 leaves redaction to the user | grep | None |

## Facts checked (sample: 44)
Verdicts: OK = matches the claim. Live = this review's read-only check, 19:31–19:47 UTC.

| # | Claim (where) | Check | Result |
|---|---|---|---|
| 1 | Our shell runs as WSParticipantRole (§5.9) | `aws sts get-caller-identity` | OK |
| 2 | 6 gateway policies, not 4 (§5.9; page checkpoint) | `kubectl get agentgatewaypolicy -n agentgateway-system` | OK: 6 |
| 3 | All six Accepted and Attached | status conditions (jsonpath) | OK |
| 4 | Names and creation times (report table) | jsonpath | OK: 4 at 10:33:53–54Z; telemetry-export 10:36:58Z; ceiling 10:37:03Z |
| 5 | A 7th, `modaas-system/modaas-authz-timeout` (memory) | `get -A` | OK |
| 6 | 0 of 1,097 Cedar decisions denied (§5.9) | PDP `--all-pods=true --tail=-1 --prefix`, bounded ≤18:58:59Z | OK: 501 + 596 = 1,097, all ALLOW. Live at 19:3xZ: 1,106, still 0 DENY |
| 7 | `my-team-policy` named in 0 of 1,097 | same | OK |
| 8 | 12 policy ids, all `model-*` / `modaas-toolconfig-*` | same | OK |
| 9 | Every `trace_id` line is a `decide` line | same | OK |
| 10 | `deploy/` alone reads one replica; `--all-pods` both (§10) | both commands, `grep -c ' decide '` | OK: 521 vs 1,127 (live) |
| 11 | `/modaas/evidence`: 1,130 records to 19:07Z, 1,106 ALLOW / 24 DENY | `filter-log-events`, counted locally | OK |
| 12 | 23 keyless refusals (`NoSigV4Credential`, principal `unknown`, asset `-unresolved-`) | same | OK: 23 |
| 13 | 1 `PolicyEngineUnavailable` (bootstrap-key, runbook-lookup) | same | OK |
| 14 | 1,107 records are `bootstrap-key` | same | OK |
| 15 | DENYs 00:32–04:47Z | same | OK: 00:32:50Z → 04:47:15Z |
| 16 | Page grep `modaas.run_id=$CID` matches nothing (S2, snapshot) | `grep -c` on the snapshot gateway log (1,895 lines) | OK: 0 |
| 17 | `grep -F "modaas.run_id=\"$CID\""` finds S2's 353 (snapshot) | same | OK: 353; `grep -F "$CID"` also 353 |
| 18 | S1 quoted grep: 24 | same | OK: 24 (unquoted 0) |
| 19 | Live pod stdout S2 quoted grep: 353 | `kubectl logs … \| grep -cF` | OK |
| 20 | All 1,092 `modaas.run_id=` values are quoted | live pod log ≤18:58:11Z | OK |
| 21 | 1,092 served lines carry all three ids | same | OK |
| 22 | 258 served `llm` lines carry tokens, cost and action id | same | OK |
| 23 | 573 refused or unrouted lines carry no ids (24× 403, 127× 404, 422× 405) | same | OK (plus 27 listener-less 503s; finding 11) |
| 24 | Pod log 2,033 lines to 18:58:11Z | same, incl. 138 continuation lines | OK |
| 25 | Stale pause conditions (nano-9b 04:05:53Z, super-120b 09:13:05Z, modaas-docs 05:56:44Z) | ModelConfig/ToolConfig conditions (jsonpath) | OK: `ReconcilePaused=True`, `spec.paused=false` |
| 26 | VAP fail-closed, binding Deny | VAP + binding YAML | OK: `failurePolicy: Fail`; `validationActions: [Deny]` |
| 27 | Matches participants | `matchConditions` | OK: group `modaas:participants` or username containing `:assumed-role/WSParticipantRole/` |
| 28 | Doesn't cover exec/port-forward/proxy | `operations` | OK: CREATE, UPDATE, DELETE only |
| 29 | `agentgateway-system`, `modaas-system` + 7 others; `components` not protected | `protectedNs` | OK: 9 namespaces (`modaas-system`, `agentgateway-system`, `canvas`, `canvas-system`, `canvas-vault`, `istio-system`, `istio-ingress`, `cert-manager`, `kube-system`); no `components` |
| 30 | CRD names guarded | `guardedClusterKinds` | OK: `*.oda.tmforum.org`, `*.agentgateway.dev`, `*.gateway.networking.k8s.io`, `*.istio.io`, `*.cert-manager.io`; cluster-scoped only |
| 31 | 94 CEL rules in 4 CRDs | CRD schemas, served versions | OK: AgentConfig 36, ModelConfig 33, ToolConfig 20, Registry 5; all `.oda.tmforum.org` |
| 32 | Builder role: CRDs update/patch, not delete; VAPs read-only | ClusterRole `modaas-participant-builder` | OK (also create on CRDs) |
| 33 | `admin` cluster-wide: all four `agentgateway.dev` kinds writable | ClusterRole `admin` + CRB `modaas-participant-admin` | OK: `oda.tmforum.org`, `agentgateway.dev`, `gateway.networking.k8s.io` `*` with delete; pods/exec, portforward, proxy create |
| 34 | Policy `targetRefs` have no namespace | AgentgatewayPolicy CRD | OK: group, kind, name, port, sectionName |
| 35 | `modaas-llm-auth` holds only rate limits; `modaas-authz` is the extAuth hook, FailClosed | policy key names | OK |
| 36 | Ceilings 100 req/min and 2.5M tokens/h | `rateLimit.local` numbers | OK (ceiling and llm-auth; mcp-ratelimit 100 req/min) |
| 37 | 10 ToolConfigs set `access.cedarPolicy`; `demo-crm-lookup` Reviewing | booleans | OK |
| 38 | 15 labelled PDP ConfigMaps (10 tool, 4 model, `my-team-policy`) | `-l app.kubernetes.io/part-of=modaas-pdp` | OK; operator ones are `managed-by=modaas` |
| 39 | 4 READY guardrails; `safety.required: true`, enforcer `bedrockGuardrail`; consumers `bootstrap-key` | `list-guardrails`; ModelConfig jsonpath | OK |
| 40 | 5 runtimes READY | `list-agent-runtimes` | OK |
| 41 | Collector pipelines | `otel-collector-config` pipelines section | OK: traces→awsxray; metrics→debug; logs/audit→`/modaas/evidence`; logs/gateway→`/aws/modaas/gateway` |
| 42 | Ledger PVC 1Gi gp3, reclaim Delete; `TeamEvidenceBucketName` is an `a-02-code-editor` output | PVC/PV/SC; OutputKey | OK |
| 43 | `show-run-spans.py` totals 2×: S1 75,328 vs 37,664 | ran it on trace `e13e7b73…`; gateway figure from the snapshot | OK: 48 spans, 12 "model calls"; gateway 9 calls = 36,862 + 802 |
| 44 | Ledger S1 "AUDIT TRAIL -- 12 records"; AWS AgentCore gateway `AWS_IAM` | `get --raw …/timeline`, `/records`; `list-gateways` | OK |

The extract `platform-contract.md` was also compared with the KB: 11 chunks, 4,679 characters; chunks `#01`–`#10` are verbatim, and `#00` differs only by the frontmatter-to-H1 conversion its header describes.

## Admission policy facts (live, 19:3x UTC)
- **Objects:** VAP `modaas-governance-guardrail` (created 2026-10-04 10:49:31Z, generation 1, no type-checking warnings) and its binding (10:49:32Z, `validationActions: [Deny]`). It is the only VAP. The validating webhooks are platform ones: cert-manager, PDB operator, Istio ×2, VPC resource and an empty `sman.sidecar.kopf`.
- **Covered:** creates, updates and deletes by participants in the 9 protected namespaces (except team Cedar ConfigMaps in `modaas-system`: label `part-of: modaas-pdp`, no `managed-by`, annotation `policy-id`), and cluster-scoped RBAC, admission, node, protected-namespace and MoDaaS/gateway/Istio/cert-manager CRD changes. `failurePolicy: Fail`.
- **Not covered:**
  - reads, and CONNECT (`exec`, `port-forward`, `proxy`)
  - namespaced resources outside the 9, so `components` and team namespaces
- **Cedar changes on our own `ifabric-*` ToolConfigs:** a ToolConfig is a namespaced resource in `components`, so the VAP doesn't refuse creating or editing it, including `spec.access.cedarPolicy`. The RBAC role `admin` allows it, and our shell already created `my-agent` and paused `modaas-docs` there after the VAP existed.
  - The operator projects the policy into `modaas-system/modaas-toolconfig-<alias>` (label `managed-by=modaas`). Participants can't edit that ConfigMap: the VAP's exemption excludes `managed-by`.
  - Still in force: the ToolConfig CRD's 20 CEL rules; approval (whether an edit resets it is untested); an unapproved ToolConfig gets its ConfigMap but no route (`demo-crm-lookup`).
  - Every edit is a cluster write: ask first.

## Labels, secrets
- **Claim labels:** outside `notes/verification/`, "C1–C8" remains only in the handoff's §0 line and the memory description of `planning-handoff`. The `notes/servicenow/raw/` files use C1/C2 as names of the Agent Studio PDF parts (pre-existing, not claim labels). Every other "C7" in the handoff, gap list, notes and memory means the control.
- **Secrets:**
  - no `tkn` literal, AWS key id, presigned URL or bearer link in the changed files or memory
  - the five 32/40-hex strings are trace ids and a MAVERIC commit id
  - `satyabratsrikumar@team` and `cloudshell-user@team` are approval-subject strings (pre-existing)
  - the commit's secret scan (exact values) is the final check
