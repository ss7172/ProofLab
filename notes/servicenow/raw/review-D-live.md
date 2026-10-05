# Independent review: claims from D-docs-and-rails.md and A-connection-setup.md

- **When and as whom:** read-only review on 2026-10-05, about 16:30–16:40 UTC, as `WSParticipantRole/Participant` in account 613052889143, region us-east-1.
- **What was done:** AWS calls were describe, get, list, lookup and filter only, plus the `s3 ls` and `validate-logs` probes the brief asked for. Both probes were denied.
- **What was not done:** no secret values or access keys were printed, and nothing was written except this file.

## Verdicts

| # | Claim | Verdict |
|---|---|---|
| 1 | escalate-to-incident.py: no escalate gating, not idempotent, 8 fields, no assignee, token-less audit read, SNOW_* Basic auth, `--dry-run` | **CONFIRMED** (three precision notes) |
| 2 | servicenow-two-rails.svg shows three rails; no guide page references it | **CONFIRMED** |
| 3 | Docs page is KB chunks 1138–1157; Build 75 / Secure 29 / Govern 19; 121 unique URLs; "Writing effectively" flagged; Module 11 cites a nonexistent "Module 7 section 6" | **CONFIRMED** (D missed a second dangling reference) |
| 4 | AICT Logs Insights query ends `filter eventName = "InvokeAgent"` | **CONFIRMED live** |
| 5 | Deployed a-03 has 7 outputs and an extra `ConnectorSecretArn` parameter | **CONFIRMED live** |
| 6 | Trail has log-file validation and an S3 bucket | **CONFIRMED in substance, but the given verification route is AccessDenied.** Bucket listing and `validate-logs` are both **denied** to our role. |

---

## 1. escalate-to-incident.py: CONFIRMED

Source: `workshop-static/servicenow/escalate-to-incident.py` (169 lines).

**No escalate gating.**
- `incident_payload()` (L101–118) hard-codes `short_description = "[MoDaaS] Agents escalated {cid} — human decision required"`.
- `dispositions_of()` (L83–98) is used only to list dispositions in `description`.
- `main()` (L137–164) has no branch on `escalate`.
- *Precision:* "any CID" means any CID that has at least one parseable record. A CID with no records exits at L52–53, before any POST.

**Not idempotent.**
- There is a single `POST https://{instance}/api/now/table/incident` (L121–134).
- No lookup by `correlation_id` happens first, so a rerun files a second incident.
- INF: stock ServiceNow does not enforce uniqueness on `correlation_id`.

**Exactly 8 fields (L104–118).**
- The fields are `short_description`, `description`, `work_notes`, `urgency "2"`, `impact "2"`, `category "network"`, `correlation_id = cid` and `correlation_display "modaas-evidence-chain"`.
- It does not set `assigned_to`, `assignment_group`, `caller_id`, `state` or `cmdb_ci`.

**Audit read (L40–41).**
- The call is `urlopen(f"{audit_store}/records?cid={cid}")` with no headers and no token.
- *Precision:* the cid is not URL-encoded.
- The default store is `http://audit-store.components:8080`. It can be overridden with `--audit-store` or the `AUDIT_STORE` env var (L140–142).

**SNOW_* variables (L153–157, L123, L128–129).**
- The script builds the URL as `https://{instance}/...`, so `SNOW_INSTANCE` must be a bare host. With a scheme it becomes `https://https://…`.
- Authentication is Basic auth from `SNOW_USER` and `SNOW_PASS`.

**`--dry-run` (L143–151).**
- It returns before SNOW_* is read, so it needs no ServiceNow credentials.
- It still needs the audit store to be reachable.

## 2. servicenow-two-rails.svg: CONFIRMED

**Title (L8):** "ServiceNow: three rails, different jobs".

**Rail 1 (L24–30):** "RAIL 1 · ITSM — HUMANS".
- The arrow `M 272 190 L 600 104` starts at the evidence-ledger box (L16–17, y 170–210).
- It is labelled "disposition = escalate".

**Rail 2 (L32–39):** "RAIL 2 · AI CONTROL TOWER — RECORD".
- It carries the text '"does not by itself constrain runtime" — their docs'.
- A dashed arrow runs from the registry box, labelled "register governed assets".

**Rail 3 (L41–47):** "RAIL 3 · SERVICENOW AGENTS — CALLERS".
- The text reads "AI Agent Studio adds the governed MCP server" and "OAuth 2.0 / API key · admitted, authorized, audited".
- The arrow points into the governed-gateway box, labelled "tool call through the gateway".

**No references anywhere.**
- `grep -rIl two-rails` over all of `/Users/satyabratsrikumar/firstmate-homes` (md, html, json, yaml, yml, txt) returns 0 hits.
- `kb/index.json` contains 0 occurrences.
- The absence is meaningful: the KB keeps image references (for example `/static/images/step-mcp-tool.svg`, `modaas-platform-architecture.svg` and `ui-*.png`), and `index.py` and `build-corpus.sh` contain no image stripping.
- `images/README.md` covers only the provenance of the `ui-*.png` files.
- *Caveat:* there is no local `workshop/content` tree, so only the indexed guide was checked. The hosted copy was not.

## 3. KB docs page: CONFIRMED

The range is exact, not approximate.

**Chunk range.**
- Positional indices 1138–1157 are `workshop/content/resources/servicenow-docs.en.md#00…#19`.
- Index 1158 starts Module 11 (`servicenow-integration/index.en.md#00`).

**Link counts** (the regex counts `[text](http…)` links):

| Set | Chunks | Links per chunk | Total |
|---|---|---|---|
| Build | 1140–1146 | 10 / 13 / 8 / 3 / 12 / 12 / 17 | 75 |
| Secure | 1148–1152 | 4 / 6 / 2 / 7 / 10 | 29 |
| Govern | 1153–1157 | 1 / 9 / 4 / 4 / 1 | 19 |

- The final Govern link is the bare `www.servicenow.com` homepage.
- That gives 123 links in total and 121 unique URLs.
- The two duplicates are `define-sec-controls-aia.html` and `define-sec-controls-aw.html`.

**The flag.** Chunk 1140 reads: "[Writing effectively for agentic AI](…/gg-creating-aia.html) The single most useful page for a hackathon team."

**Dangling reference.**
- Chunk 1166 (Module 11 §5) says "[Module 7](/reference-agents) section 6 shows the `escalate` disposition".
- None of Module 7's six indexed pages has a section 6:
  - setup: §1–5
  - run-and-read: §1–4 plus 3a
  - swap-model: §1–4
  - kill-switch: Pause and Unpause
  - self-check: no numbered sections

**ADDITION (D missed it).** The same dangling reference appears a second time.
- Chunk 905, `workshop/content/challenge-brief/index.en.md#02`, cites "`score-run.py` ([Module 7](/reference-agents) section 6)".
- INF: Module 7 was probably once a single page whose §6 was the self-check and scoring section.

## 4. AICT usage query: CONFIRMED live

**What `lookup-events EventName=StartQuery --max-results 20` returned.**
- All 20 events, from 11:37:55 to 16:22:56Z, came from `assumed-role/SgcAictReadOnlyAccessRole/613052889143-session` with user agent `ServiceNow/1.0`.
- There were no errors. Every event targeted `logGroupNames: ['/aws/bedrock/aict-invocations']`, on a ~15-minute cadence with windows of about 15.1 minutes.
- No other principal appears among the 20.

**The query.** There is exactly one distinct `queryString`, 234 characters long. The full text is:

```
stats max(@timestamp) as timestamp, count(*) as eventCount by eventName, requestParameters.sessionId as sessionId, requestParameters.agentId as agentId, requestParameters.agentAliasId as agentAliasId | filter eventName = "InvokeAgent"
```

- The filter is an exact equality, so `InvokeAgentRuntime`, `Converse` and `ConverseStream` all fall outside it.

**Supporting check: the whole log group.** `filter-log-events` read 531 events, covering 2026-10-05 00:01:41Z to 09:13:40Z, with no NextToken (so it was complete; retention is 7 days).

| Event | Caller | Count |
|---|---|---|
| ConverseStream | gateway role | 492 |
| Converse | gateway role | 8 |
| Converse | WSParticipantRole | 3 |
| InvokeAgentRuntime | WSParticipantRole | 26 |
| InvokeAgentRuntime | IDE role | 2 |
| **InvokeAgent** | — | **0** |

- **AICT's usage query therefore returns zero rows for all of our traffic.**
- *Minor correction to A's [KNOWN] sample:* A attributed all 11 Converse calls to the gateway role, but 3 are WSParticipantRole. The counts are now 492 / 11 / 28, against A's 466 / 11 / 25.
- No events have arrived since 09:13Z. There are no StopLogging or DeleteTrail events in history, so the most likely reason is simply no traffic (INF).

## 5. Deployed a-03 vs the kit template: CONFIRMED live

**Deployed stack (`describe-stacks`).**
- 8 parameters: `ConnectorSecretArn`, RoleName, ServiceNowUserAccountId, ServiceNowUserName, LogGroupName, TrailName, EnableInvocationLogging, LogRetentionDays.
- 7 outputs: ServiceNowAictSecretArn, StsAssumeRoleArn, AictConfigured, ServiceNowAictRoleName, InvocationLogGroupName, TargetAccountId, ServiceNowAictAccountId.

**Kit file `workshop-static/servicenow/03-servicenow-aict.yaml`.**
- 7 parameters (L52–94): the same list minus `ConnectorSecretArn`.
- 4 outputs (L425–437): AictConfigured, StsAssumeRoleArn, TargetAccountId, InvocationLogGroupName.

**How they relate.**
- The three extra deployed outputs are exactly the ones Module 11 §1 expects.
- The deployed stack's Description matches the kit file's word for word. INF: the deployed template is an extended revision of the kit, not an unrelated one.

**Why it cannot be diffed.** `get-template-summary` is also AccessDenied, in addition to GetTemplate as A reported.

**Timing.**
- The stack was created at 2026-10-04T22:02:58Z and reached UPDATE_COMPLETE at 22:45:14Z.
- That is 15 s after the WSOpsRole CreateAccessKey that A reports at 22:44:59Z. INF: that update probably supplied `ConnectorSecretArn`.

## 6. Trail sgc-aict-bedrock-trail: CONFIRMED in substance; bucket and validate-logs denied

**The suggested route is denied.** `describe-trails`, `get-event-selectors` and `get-trail-status` all return AccessDeniedException ("no identity-based policy allows cloudtrail:DescribeTrails / GetEventSelectors / GetTrailStatus").

**Evidence from CloudTrail event history instead** (`lookup-events`).

*CreateTrail* (2026-10-04T22:03:40Z, by WSOpsRole/Ops), from both the request and response elements:

| Setting | Value |
|---|---|
| LogFileValidationEnabled | **true** |
| S3BucketName | **`sgc-aict-cloudtrail-613052889143-us-east-1`** (no prefix, KMS or SNS) |
| IsMultiRegionTrail | **false** |
| IncludeGlobalServiceEvents | false |
| IsOrganizationTrail | false |
| CW Logs destination | `/aws/bedrock/aict-invocations`, via role `sgc-aict-cloudtrail-cw-role-us-east-1` |

*PutEventSelectors* (same second): 7 advanced selectors, all `eventCategory=Data`.
- Bedrock: AgentAlias, Model, AsyncInvoke, InlineAgent, KnowledgeBase, FlowAlias.
- AgentCore: Runtime.

*Later events:* StartLogging ran in the same second. No UpdateTrail, StopLogging or DeleteTrail events have occurred since.

**Bucket listing is denied.**
- `aws s3 ls s3://sgc-aict-cloudtrail-613052889143-us-east-1/ --recursive` returns AccessDenied (`s3:ListBucket`).

**validate-logs is denied.**
- `aws cloudtrail validate-logs --trail-arn arn:aws:cloudtrail:us-east-1:613052889143:trail/sgc-aict-bedrock-trail --start-time 2026-10-05T15:37:22Z` returns AccessDenied on DescribeTrails.
- Retrying with `--s3-bucket <bucket>` to skip that lookup returns AccessDenied on `s3:GetBucketLocation`.

**Consequence for A.**
- A's INTEGRITY row (L292) is only true as "a facilitator could prove it". The team cannot validate digests or read the S3 copy, so validated CloudTrail logs are facilitator-only evidence.
- The CloudWatch log group's 7-day retention is live-confirmed (`describe-log-groups` returns `retentionInDays: 7`). The 7-day S3 expiry and S3 versioning remain template-only claims, not verified live.
