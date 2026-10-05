# A. "Creating and Verifying Amazon Connection Setup" (ServiceNow PDF): notes

Prepared 2026-10-05 (~16:30 UTC) by a read-only research subagent. Nothing was written anywhere except this file and the scratch crops in `pdfA/` and `A-live/`. No secret values were printed.

**Sources**
- PDF: `~/Downloads/creating-and-verifying-amazon-connection-setup.pdf`. It is byte-identical (md5 d1c21c83…) to the kit copy in `workshop-static/servicenow/`. It has 12 A4 pages, was produced by `react-pdf` on 2026-09-30 12:15 CDT, and is a video transcript with one 2400×1203 screenshot per step. Screenshots were read at full resolution (`pdfA/img-*.png`).
- Template: `workshop-static/servicenow/03-servicenow-aict.yaml` (441 lines). Line numbers are cited as `TPL Lnn`.
- Module 11 page: `workshop/content/servicenow-integration/index.en.md`, rebuilt from `workshop-static/kb/index.json` (10 chunks, identical in `workshop-assets/`). Chunks are cited as `M11 #nn`. The full text is in `module11-reconstructed.txt`.
- Other kit file: `workshop-static/cfn/01-eks-cluster.yaml` (`EKS Lnnnn`).

**Labels**
- **[PDF pN]**: stated in the narration on page N. **[PDF pN shot]**: visible in that page's screenshot.
- **[TPL]**: verified in the template text.
- **[M11]**: stated on the Module 11 page.
- **[LIVE-now]**: read-only AWS check run in this session as WSParticipantRole, about 16:20–16:30 UTC on 2026-10-05.
- **[KNOWN]**: verified earlier, from the caller's brief or memory (`workshop-progress.md`, `workshop-aws-access.md`).
- **[INF]**: my inference.

The demo in the PDF used ServiceNow's own AWS account `273808626098`, not ours (`613052889143`), and the connection name "TeamSN DTW Hackathon 2026". The access key ID visible on p6–p8 belongs to that vendor demo account. It is redacted here as `AKIA…XBOO`.

---

## 1. Page-by-page summary

| Page | Step | Content |
|---|---|---|
| 1 | Title | "Creating and Verifying Amazon Connection Setup". The video "demonstrates how to establish a connection to the Amazon environment… from setup instructions to activating scheduled jobs for agent discovery." [PDF p1] |
| 2 | 01 Introduction | The "Connect to Amazon" guided setup. Left nav: Prerequisites › *Review setup instructions*; Setup (Pending). Panel text: "Before configuring the connection, review the AWS setup guide below to prepare your IAM user, roles, and credentials." It shows a link **"AI Service Graph connector for Amazon - Setup Instructions"**, a checkbox "I have read the setup instructions." and Continue. [PDF p2 shot] |
| 3 | 02 Review instructions | The link "will redirect you to a knowledge article in ServiceNow. The same knowledge article will be part of your workshop studio instructions and guides." The narration is cut off ("you..."). **The knowledge article itself is not in the PDF.** [PDF p3] |
| 4 | 03 Name the connection | "select all three check marks and name your connection like Team ServiceNow or… your team name… Start with your team name so it will be easier to figure it out in the connection database." [PDF p4]<br>Screenshot, "Configure Amazon Connection": "Select the AWS services from the source system to discover, then provide a connection name and the credentials of an Identity Access Management (IAM) user. If that IAM user was created in a Designated Member account rather than your AWS organization's management account, also supply the management account ID so discovery can operate at the organization level." The fields are used to "Scope discovery by region and account", "Route the connection through a MID server (optional)" and "Rotate the IAM user's keys (optional)". Button: "Create and test connection". Setup sub-steps: *Configure Amazon Connection* › *Configure Amazon connection [import schedule]* › *Confirm connection setup*. [PDF p4 shot] |
| 5 | 04 Access key and secret | "You will need your access key ID that you can get from the AWS environment. You will need your secret access key. **You don't need to use a mid-server.**" [PDF p5]<br>The full form is visible (section 2). Only one of the three service checkboxes is legible: **"Amazon SageMaker"** (checked). The two above it are cut off. [PDF p5 shot] |
| 6 | 05 Region and account ID | "The server is going to be **US East 1**. The account ID you will have from your environment as well." The screenshot shows the access key ID entered, the secret masked, and "us" being typed into AWS regions. [PDF p6] |
| 7 | 06 Assume role and CloudWatch group | "**The assume role should be pre-created. It should be the same for everyone, and the CloudWatch group should be the same for everyone.**" [PDF p7]<br>Screenshot: regions `us-east-1`; Target account IDs `273808626098`; **Management account ID `273808626098` (the same account)**; User created in = "Designated account"; STS assume role empty, with the validation error "Field is required". [PDF p7 shot] |
| 8 | 07 Test and verify | "You click the button to test the connection… connection verified… **You will have four parent tasks.**" [PDF p8]<br>Greyed screenshot taken while the test runs: STS assume role = **`SgcAictReadOnlyAccessRole`** (bare name, not an ARN); Amazon CloudWatch log group name = **`/aws/bedrock/aict-invocations`**. [PDF p8 shot] |
| 9 | 08 Activate scheduled jobs | "Jobs schedules are scheduled to run. **You need to activate all of them because so far they are not active.** You can set how often they will run, **maybe every one hour or so**." [PDF p9]<br>Screenshot, "Configure Amazon connection import schedule": banner **"Connection Successful"**, **"Import schedules 14"**. Columns: Scheduled Data Import / Parent / Run / Data source / Active / Updated. The four top-level rows are `…-SG-AWSAgentCore-System`, `… SG-AWSBedrock-Usage`, `… SG-AWSBedrock-Asset` and `… SG-AWSSageMaker-AI Model`. All four show **Run = Daily, Active = false** and Updated 2026-09-30 10:08:51–53. Child groups: Parent `SG-AWSBedrock-Asset` (5), Parent `SG-AWSBedrock-Model` (1), Parent `SG-AWSAgentCore-System` (4). 4+5+1+4 = 14. [PDF p9 shot] |
| 10 | 09 Confirm activation | "All right." The screenshot shows a "Please wait… / Loading" overlay. Behind it, the AgentCore-System row now reads **Run = "Periodically", Active = "true"** (faint, but legible when zoomed). [PDF p10 shot] |
| 11 | 10 Creation and discovery | "After you set all of them active, **all the child jobs will be active as well**… If you come back to the connectors tab, you will see your newest connection… and it will start discovering the agents from your environment. **…please name your agents in the AWS environment starting with your team name.**" [PDF p11]<br>Screenshot: toast "Import schedule set.", the groups collapsed, "Continue" enabled, Setup "1 of 3". **The third step, "Confirm connection setup", is never shown.** [PDF p11 shot] |
| 12 | Closing | "The video guides through creating an Amazon connection, verifying it, and activating scheduled jobs to enable agent discovery within the environment." Then a "Get started" link. [PDF p12] |

---

## 2. Connection inputs and prerequisites

### 2.1 The form ("Configure Amazon Connection", p5–p8)

An asterisk in the "Req." column means the form marks the field as required.

| Field | Req. | PDF demo value | Value in our account | Source |
|---|---|---|---|---|
| AWS service checkboxes (3) | – | all 3 checked; only "Amazon SageMaker" is legible | – | [PDF p4, p5 shot]. The other two are probably Bedrock and AgentCore, matching the four parent jobs [INF]. |
| Connection name | * | `TeamSN DTW Hackathon 2026` | (ServiceNow side, unknown) | [PDF p4 / p5 shot]. Should start with the team name. |
| Access key ID | * | `AKIA…XBOO` (vendor demo) | key of IAM user `ServiceNowAictUser`, stored in Secrets Manager | [PDF p6 shot]; [KNOWN] |
| Secret access key | * | masked | same secret | [PDF p6 shot]; [KNOWN] |
| Rotate keys | optional | unchecked | – | [PDF p4–p5 shot] |
| Use MID server | optional | unchecked; "You don't need to use a mid-server" | – | [PDF p5] |
| AWS regions | * | `us-east-1` | `us-east-1` | [PDF p6–p7] |
| Target account IDs | no asterisk | `273808626098` | `613052889143` | [PDF p7 shot]; TPL L434–436 |
| STS assume role | * | `SgcAictReadOnlyAccessRole` (name only) | same | [PDF p8 shot]; TPL L68–74 |
| User created in | dropdown | "Designated account" | Live user stack: `UserAccountType = DesignatedMemberAccount` | [PDF p5 shot]; [LIVE-now] |
| Management account ID | * | `273808626098` (= target) | unknown (ServiceNow side) | [PDF p7 shot] |
| Amazon CloudWatch log group name | * | `/aws/bedrock/aict-invocations` | same (stack parameter) | [PDF p8 shot]; TPL L82–88; [LIVE-now] |

### 2.2 Prerequisites: what the PDF says and does not say

- **IAM user with an access key.** The PDF requires "the credentials of an Identity Access Management (IAM) user" [PDF p4 shot]. It does not say how to create the user, what it may do, or where it lives. It defers to the knowledge article [PDF p2–p3].
- **Pre-created assume role** with the same name for everyone [PDF p7]. It shows **no trust policy and no permission list** [PDF, by absence].
  - Template trust: exactly one principal, `arn:${Partition}:iam::${ServiceNowUserAccountId}:user/${ServiceNowUserName}`, for `sts:AssumeRole` [TPL L126–134].
  - Template permissions [TPL L162–207]:
    - sts:GetCallerIdentity and ec2:DescribeRegions
    - bedrock:List/GetInferenceProfile(s)
    - logs:StartQuery and logs:GetQueryResults on `Resource: '*'`
    - cloudtrail:LookupEvents
    - bedrock-agentcore List/Get for Gateways, GatewayTargets and AgentRuntimes
    - an explicit **Deny** on GetWorkloadAccessToken*, GetResourceApiKey and GetResourceOauth2Token
    - **no** bedrock:ListAgents, sagemaker:*, organizations:* or bedrock:ListGuardrails
  - The deployed role matches this list [KNOWN].
- **The user side, from the vendor kit stack `aict-servicenow-user`** [LIVE-now: describe-stacks parameters and outputs]:
  - Parameters: `SNUserName=ServiceNowAictUser`, `GroupName=SgcAictReadOnlyAccessGroup`, `PolicyName=SgcAictAssumeRolePolicy`, `MbrActRoleName=SgcAictReadOnlyAccessRole`, `UserAccountType=DesignatedMemberAccount`.
  - Output `NextSteps` = `arn:aws:iam::*:role/SgcAictReadOnlyAccessRole`. The user can assume that role name in any account.
  - Output `DeploymentScenario`: "Scenario B: User in Designated Member Account. Org permissions via role hop. Deploy SgcAictReadOnlyOrgAccessRole.yml in the Management Account, AND deploy SgcAictReadOnlyAccessRole.yml in every member account…"
  - **This explains the form's "User created in" and "Management account ID" fields** [INF].
  - The access key was created outside CloudFormation, by `WSOpsRole` calling CreateAccessKey at 22:44:59 UTC [KNOWN].
- **CloudWatch log group** with the same name for everyone [PDF p7, p8 shot]. **The PDF never says what the log group is for.** The words "invocation" and "counting" do not appear in it.
  - The template supplies the purpose: "Create the kit's CloudTrail trail + log group so AICT can count per-agent invocations with logs:StartQuery. Discovery works without it." [TPL L79–81]
  - It is fed by trail `sgc-aict-bedrock-trail` [TPL L354–422]:
    - data events only, single region
    - log-file validation on (L373)
    - selectors for Bedrock AgentAlias, AsyncInvoke, InlineAgent, KnowledgeBase, Model and FlowAlias, plus the workshop's added `AWS::BedrockAgentCore::Runtime` (L414–422)
  - Retention is 7 days for both the log group and the S3 copy [TPL L89–93, L221, L233–239].
- **Region:** us-east-1 only [PDF p6]. The trail is single-region [TPL L371].
- **ServiceNow-side plugins, roles and entitlements: not mentioned anywhere in the PDF.** It does not say how to reach the "Connect to Amazon" guided setup. It only refers to the "connectors tab" and the "connection database" [PDF p4, p11].

---

## 3. What gets discovered, and how often

- **According to the PDF:**
  - Three AWS services are selectable (one legible: SageMaker) [PDF p4–p5].
  - The connection creates **4 parent and 14 total scheduled data imports**: AgentCore-System, Bedrock-Usage, Bedrock-Asset (5 children, one of them the Bedrock-Model group with 1 child) and SageMaker-AI Model [PDF p9 shot].
  - The jobs default to **Daily** and **inactive**. You must activate them all, and the narration suggests "every one hour or so". Activating a parent activates its children [PDF p9, p11].
  - The PDF never lists asset types, never shows a discovered-asset list, and never says what is out of reach [PDF, by absence].
- **According to the ServiceNow docs** (via the team's earlier research file `agentic-template-hackathon/…/servicenow-ai-control-tower.md` L91–93, not this PDF):
  - "Each connector runs two scheduled jobs: Discovery, and Execution", which "Collects usage data, such as run counts by agent, date, and session".
  - Usage lands in `sn_ai_disc_ai_usage`.
  - Trace connections (CloudWatch traces for AgentCore) run through a **MID Server** polling every 30 min (L101).
- **Live in our account** [LIVE-now]:
  - **CloudTrail:** 400 events from the connector session `613052889143-session`, 09:56–16:22 UTC, all with user agent `ServiceNow/1.0`. They repeat on a **~15-minute cycle** (25 cycles):

    | API call | Result | Count |
    |---|---|---|
    | ListAgentRuntimes | OK | ×25 |
    | GetAgentRuntime | OK | ×175 (≈7 per cycle, for 5 READY runtimes) |
    | ListGateways | OK | ×26 |
    | StartQuery | OK | ×26 |
    | GetQueryResults | OK | ×48 |
    | bedrock **ListAgents** | **AccessDenied** | ×25 |
    | sagemaker **ListModelCards** | **AccessDenied** | ×25 |
    | agentcore **ListBrowsers** | **AccessDenied** | ×25 |
    | agentcore **ListCodeInterpreters** | **AccessDenied** | ×25 |

    - No ListGatewayTargets, ListInferenceProfiles or organizations calls appear in the sample.
  - **The usage query.** It runs every 15 min on `/aws/bedrock/aict-invocations`, over consecutive windows of about 15.1 min (for example, 16:07:49 to 16:22:56). The exact query is:
    `stats max(@timestamp) as timestamp, count(*) as eventCount by eventName, requestParameters.sessionId as sessionId, requestParameters.agentId as agentId, requestParameters.agentAliasId as agentAliasId | filter eventName = "InvokeAgent"`
    - It counts **only classic Bedrock Agents `InvokeAgent` calls**. The template had already recorded this filter from the 2026-09-28 test [TPL L145–146].
  - **What the log group actually holds** [KNOWN, sample from earlier in the session]:
    - ConverseStream ×466 and Converse ×11 by role `a-01-eks-cluster-agentgateway-bedrock`
    - InvokeAgentRuntime ×23 by WSParticipantRole and ×2 by the IDE role
    - **Nothing matches `InvokeAgent`, so AICT's usage count for our agents should be zero** [INF, strongly supported].
  - **AssumeRole:** 60 calls by `ServiceNowAictUser` between 14:37 and 16:12 UTC, bursty (median gap 37 s, maximum 747 s). The role session name is always `613052889143-session`.
  - **AgentCore runtimes:** `customer_experience_agent`, `it_resolution_agent`, `network_resolution_agent`, `hackathon_helper` and `my_agent`, all READY. **None starts with the team name** that p11 recommends.
- **Mapping of jobs to API calls** [INF, not verified on the ServiceNow side]:
  - AgentCore-System (1 parent and 4 children) ↔ ListAgentRuntimes, GetAgentRuntime, ListGateways, ListBrowsers and ListCodeInterpreters: five call families for five jobs.
  - Bedrock-Asset ↔ ListAgents (denied).
  - SageMaker ↔ ListModelCards (denied).
  - Bedrock-Usage ↔ the Logs Insights query.
  - Our live cadence (15 min) is a facilitator setting. It is not the PDF's default (Daily) or its suggestion (hourly).

---

## 4. How to verify the connection

- **ServiceNow side** (the PDF's only verification):
  - "Create and test connection", then the banner **"Connection Successful"** and an import schedule list that loads (14 rows) [PDF p8–p9].
  - After activation: "Import schedule set." [PDF p11].
  - The "connectors tab" lists the new connection [PDF p11].
  - The PDF shows no discovered assets and no "Confirm connection setup" step.
- **AWS side** (Module 11, not in the PDF):
  - The CloudTrail `lookup-events` AssumeRole check filtered on `SgcAict` [M11 #06–#07]. It works [LIVE-now].
  - **Better participant checks**, all working as WSParticipantRole [LIVE-now]:
    1. `lookup-events Username=613052889143-session`, summarised by eventName and errorCode. This shows what AICT read and what it was denied.
    2. `lookup-events EventName=StartQuery` and print `requestParameters.queryString`. This shows exactly what AICT counts.
    3. `describe-stacks` on both AICT stacks. Parameters and outputs are readable; `GetTemplate` and `ListStackResources` are **AccessDenied** for participants.

---

## 5. What AICT can and cannot see

| Asset or signal | M11 claim | Template | Live | Verdict |
|---|---|---|---|---|
| AgentCore runtimes | discovered (#06) | List/GetAgentRuntime allowed (L189–198) | OK every 15 min | **Seen** |
| AgentCore gateway | (not stated) | ListGateways/GetGateway allowed | ListGateways OK; no ListGatewayTargets seen | Gateway enumerated. Whether it shows as an MCP server is unknown [INF] |
| Bedrock (classic) agents | discovered (#06) | **removed** (deviation 6, L37–39) | **ListAgents AccessDenied** | **Not seen** (and the participant role is denied the Bedrock Agents APIs anyway [KNOWN]) |
| SageMaker models | discovered (#06) | **removed** (L37–39) | **ListModelCards AccessDenied** | **Not seen** |
| Kubernetes-pod agents | not discovered (#06) | no EKS permissions | – | Not seen |
| MCP servers / ToolConfigs | not discovered (#06) | – | – | Not seen, except possibly the AgentCore gateway (above) |
| MoDaaS guardrails | not discovered; no bedrock:ListGuardrails (#06) | absent (L172–177) | absent [KNOWN] | Not seen. The trail does record `guardrailConfig` per model call [KNOWN] |
| Which ModelConfig served a call | no; single gateway principal (#06) | Bedrock::Model data events (L402–407) | caller = `a-01-eks-cluster-agentgateway-bedrock` [KNOWN] | Not attributable |
| Invocation counts | "for invocation counting" (#05) | count via logs:StartQuery (L79–81) | query filters `InvokeAgent` only | **Zero for our traffic** [INF] |
| Traces and spans | – | – | no MID server configured [PDF p5] | **Not provided by this connection** [INF: the docs require a MID-server trace connection] |
| Prompts and responses | – | – | not in the trail's requestParameters [KNOWN] | Not seen |

---

## 6. Comparison: PDF vs Module 11 vs template vs live/known facts

### Agreements

1. **Region us-east-1.**
   - PDF: "The server is going to be US East 1" [p6]
   - M11 #05: `us-east-1`
   - TPL L371: `IsMultiRegionTrail: false`; L365: "in the one region the event runs in"
   - LIVE: the queries run in us-east-1
2. **Role name `SgcAictReadOnlyAccessRole`, pre-created, the same name in every account.**
   - PDF: "The assume role should be pre-created. It should be the same for everyone" [p7], plus the p8 screenshot
   - M11 #05: "`SgcAictReadOnlyAccessRole` (role name only…)"
   - TPL L70 and L72–73: "Must match the kit user's assume-role policy (arn:aws:iam::*:role/SgcAictReadOnlyAccessRole)"
   - LIVE: user-stack output `NextSteps` = that wildcard ARN
3. **Log group `/aws/bedrock/aict-invocations`, the same for everyone.**
   - PDF: p7 narration and the p8 screenshot
   - TPL L84 and L86–88: "Give this exact name to ServiceNow for the connector's 'CloudWatch log group name' field"
   - LIVE: stack parameter and StartQuery target
4. **The connector uses an IAM user's access key and secret.**
   - PDF: p4 shot ("credentials of an… IAM user") and p5 ("your access key ID… from the AWS environment")
   - M11 #03: "The connector's access key is stored in Secrets Manager"
   - KNOWN: `ServiceNowAictUser` with an AKIA key in Secrets Manager
   - The template disagrees: see D1.
5. **Target account = the team's own account.**
   - PDF: p7 (the demo's own account ID)
   - M11 #05: "your event account id"
   - TPL L434–436: `TargetAccountId: !Ref AWS::AccountId`
   - LIVE: `613052889143`
6. **No guardrail discovery.**
   - M11 #06: "the connector role lacks `bedrock:ListGuardrails`"
   - TPL: the policy has no such action (L166–207)
   - KNOWN: confirmed on the deployed role
   - The PDF is silent.
7. **Read-only and no token issuance.**
   - M11 #04: "grants read-only access to AgentCore, Bedrock and CloudWatch Logs"
   - TPL L199–207: explicit Deny
   - LIVE: only List/Get/StartQuery calls were observed
   - The PDF is silent.
8. **No MID server.** The PDF says so [p5]. M11 and the template are silent.

### Discrepancies

- **D1. Whether an IAM user and access key exist.**
  - TPL L6–7: "**No IAM user and no access key is created here or anywhere in this workshop.**" TPL L48–49 adds that a sensor fails if a template declares `AWS::IAM::User` or `AWS::IAM::AccessKey`.
  - M11 #03 disagrees: "The connector's access key is stored in Secrets Manager… Stack deletion at the end of the event removes the IAM user and the key."
  - PDF p4–p6: an IAM user's key is mandatory.
  - KNOWN: the IAM user `ServiceNowAictUser` comes from the vendor stack `aict-servicenow-user`, and `CreateAccessKey` was run directly by WSOpsRole.
  - LIVE-now: the deployed a-03 stack **still carries the "No IAM user…" description**.
  - EKS L1190 says the 01 template "Creates the connector IAM user's access key and stores it in Secrets". But its secret, `modaas/servicenow-aict-connector` (L1205), holds only "the member-role ARN and the ServiceNow account/user" (L1208). The live secret is a different one, `team-servicenow-aict-connector-…`.
- **D2. Where the trusted user lives.**
  - TPL L3–6 says the role trusts "ServiceNow's own IAM user in ServiceNow's own AWS account". TPL L58–59 says "ServiceNow's own account". TPL L64 says "(a facilitator-owned account; never a participant account)".
  - LIVE-now: `ServiceNowUserAccountId = 613052889143`, which is **our participant account**, and the user-stack scenario is "User in Designated Member Account".
  - The PDF demo is consistent with live, not with the template: the user is in the target account, and Management = Target [p7].
- **D3. Stack outputs.**
  - M11 #02 expects `AictConfigured true`, `ServiceNowAictRoleName`, `ServiceNowAictSecretArn` and `ServiceNowAictAccountId`.
  - The kit file outputs only `AictConfigured`, `StsAssumeRoleArn`, `TargetAccountId` and `InvocationLogGroupName` [TPL L424–440].
  - LIVE-now: the deployed a-03 has all 7 outputs and an **extra parameter, `ConnectorSecretArn`**. **The deployed template is not the kit file.** It cannot be diffed, because GetTemplate is denied to participants.
- **D4. Required fields that Module 11 omits.**
  - The form marks **Connection name, Management account ID and Amazon CloudWatch log group name** as required [PDF p5–p8 shot].
  - The M11 #05 table lists only Access key ID, Secret, Regions, Target account IDs and STS assume role. It drops Management account ID, User created in and Connection name, and defers the log group to the PDF.
  - TPL L81 says "Discovery works without it", but the form will not submit with the log group field empty [PDF].
- **D5. ARN or name for the STS assume role.**
  - TPL L428–433: output `StsAssumeRoleArn` ("Give this to ServiceNow for the connector's 'STS assume role' field") is the **full ARN**.
  - PDF p8 shot: **bare name**.
  - M11 #05: "role name only; **the form prepends the ARN prefix**". That last claim is not in the PDF. It is plausible given the wildcard `arn:aws:iam::*:role/…` [INF].
- **D6. Discovery scope.**
  - M11 #06: "AICT discovers your AgentCore runtimes, **Bedrock agents and SageMaker models**."
  - TPL deviation 6 (L29–41) removed "classic Bedrock Agents List/Get, SageMaker List/Describe".
  - LIVE-now: ListAgents and ListModelCards are AccessDenied every cycle.
  - PDF p9/p11 still has you activate the SageMaker and Bedrock-Asset jobs. They run and fail [INF].
- **D7. "Invocation counting".**
  - M11 #05: the PDF "walks through each field, including the CloudWatch log group for invocation counting."
  - **The PDF never mentions invocation counting.** It says only "the CloudWatch group should be the same for everyone" [p7]. Most fields are not narrated: Management account ID is filled in silently.
  - The source of the phrase is TPL L79–81.
  - Deviation 5 (TPL L27–28, L414–422) adds AgentCore Runtime data events "so invocations… are recorded". They are recorded [KNOWN], but **AICT's live query filters `eventName = "InvokeAgent"`**, so it never counts them [LIVE-now].
- **D8. Who fills in the form.**
  - The PDF speaks to participants: "You will need your access key ID that you can get from the AWS environment"; "your team name" [p4–p5].
  - M11 #05: "A facilitator enters the redacted values… **Participants do not enter these values.**"
  - The connection here is live; AWS does not show who created it on the ServiceNow side [INF: a facilitator].
- **D9. Cadence.**
  - PDF: default **Daily**, inactive, "maybe every one hour or so" [p9].
  - LIVE-now: a **15-minute** cycle, with usage windows of 15.1 min.
  - M11 #07 mentions only CloudTrail delivery lag ("allow about 2 minutes").
- **D10. Session name.**
  - M11 #07: "The session name identifies the AICT discovery run."
  - LIVE-now: always `613052889143-session` (60 of 60). It identifies the **target account**, not a run.
- **D11. Management account and organisation scope.**
  - PDF p4 shot: supply the management account ID "so discovery can operate at the organization level".
  - TPL L19–21: team accounts sit in Workshop Studio's Organization, "not ours". Deviation 6 removed `organizations:*`.
  - LIVE-now: the user stack's scenario B asks for an Org role "in the Management Account" (not possible here), and no organizations calls were seen.
  - The facilitator probably entered our own account ID, as the demo did [INF].
- **D12. The template contradicts itself.**
  - L35 says StartQuery "on the invocation log group", but the grant at L183 is `Resource: '*'`.
  - L40–41 says the Deny "is unchanged", but L156–161 says it "is ADDED here: the vendor kit and the prior version… carried neither".
  - L13–14 says "copied unchanged, except deviation 6" and L120 says "unchanged permissions and trust", yet deviations 1–7 exist and deviation 6 replaced the permissions.
- **D13. Agent naming.**
  - PDF p11: "please name your agents in the AWS environment starting with your team name."
  - LIVE-now: the runtimes are `customer_experience_agent`, `it_resolution_agent`, `network_resolution_agent`, `hackathon_helper` and `my_agent`, with no team prefix.
  - M11 is silent. In a shared AICT instance, every team's identical reference agents may be told apart only by connection or account [INF].
- **D14. The setup knowledge article.**
  - PDF p3: the setup knowledge article "will be part of your workshop studio instructions and guides".
  - M11 #00–#01 links only the three PDFs and the ServiceNow docs set.
  - A search of `workshop-static/` and `workshop-assets/` for "Service Graph Connector" finds only the M11 form chunk. **The article (IAM user, permissions and trust steps) is not in the kit**, so the prerequisites are documented only by the templates.

---

## 7. What this means for the team

### (a) The judges' auditor questions

AICT, as connected here, answers almost none of the six questions per run. Its value is asset-level inventory under a provably read-only observer identity. The AWS-written trail it consumes, `/aws/bedrock/aict-invocations`, is the stronger evidence source, and we can read it ourselves.

| Question | What AICT adds | What the AICT trail and log group add (readable by participants) |
|---|---|---|
| WHO | Nothing per run | `userIdentity` per Bedrock call. All model calls show the single gateway role, which itself shows there is no per-agent identity (consistent with gap 2). InvokeAgentRuntime shows which human or IDE role started an agent [KNOWN]. The observer's own identity (ServiceNowAictUser → SgcAict role, `ServiceNow/1.0`) is provable [LIVE-now]. |
| WHAT | Inventory of 5 AgentCore runtimes and the gateway [LIVE-now]. No tools, MCP targets, models or guardrails | modelId per call [KNOWN]. The runtime ARN in each InvokeAgentRuntime data event's `resources` is likely but unverified [INF] |
| AUTHORIZED | Nothing: no Cedar/PDP, no guardrails | `guardrailConfig` attached per model call (attachment, not the verdict) [KNOWN] |
| APPROVED | Nothing from this connection. MoDaaS approval annotations are invisible to AICT [INF] | Nothing |
| INTEGRITY | Nothing | Trail `EnableLogFileValidation: true` and a versioned S3 bucket [TPL L373, L231–232]. `aws cloudtrail validate-logs` could prove the data-event files were not altered [INF]. Caveats: data events only (management events are not in this trail, TPL L377–422); 7-day expiry [TPL L237]; the participant role's S3 and validate-logs access is unverified. |
| RECONSTRUCT | No traces (no MID-server trace connection) [INF] | AWS-written timestamps for every model call and agent invocation. No run_id, so join by time or session [KNOWN]. An independent cross-check for the gateway line and the ledger. |

### (b) Level 2: "ServiceNow Control Tower adds additional observability"

- **As configured, AICT adds:**
  - an AgentCore runtime and gateway inventory, refreshed every ~15 min, under an identity with an explicit Deny on token issuance
  - a usage count that **cannot see our traffic**, because it filters on InvokeAgent [LIVE-now, INF]
  - Bedrock-agent and SageMaker discovery that is **denied** [LIVE-now]
- **Claiming "AICT adds observability" for MoDaaS calls would be wrong unless facilitators change the query or permissions** [INF, from the LIVE-now query text and the KNOWN log-group contents].
- **What we can honestly show** [INF]:
  - the AICT connection is live and read-only (CloudTrail)
  - exactly what it reads and counts (the query text)
  - why it sees no MoDaaS calls (a candidate gap-list entry)
  - the extra evidence its trail gives us
- **Anything shown from the ServiceNow side needs the instance.** We need screenshots or exports from the facilitator or judge.
- **Low-cost lever** [INF]: if we deploy a new agent runtime, name it with the team prefix (per p11), so that it is findable in a shared AICT.

### (c) Without a ServiceNow instance, a participant can

1. **Prove the connection and its scope** [LIVE-now]: CloudTrail by Username `613052889143-session`, AssumeRole by `ServiceNowAictUser`, and errors (AccessDenied for ListAgents, ListModelCards, ListBrowsers and ListCodeInterpreters).
2. **Read the exact AICT usage query** from the StartQuery events [LIVE-now].
3. **Run our own Logs Insights query on `/aws/bedrock/aict-invocations`**, for example counting ConverseStream, Converse and InvokeAgentRuntime by `userIdentity.arn` for a run's time window. That gives AWS-written evidence for WHO, WHAT and RECONSTRUCT [KNOWN that the logs are readable; the query is my suggestion]. **Copy it into ~/evidence before the 7-day retention runs out or the account is wiped.**
4. **Enumerate what AICT would inventory** with `list-agent-runtimes` [LIVE-now].
5. **Read stack parameters and outputs.** We cannot read templates or resources (AccessDenied) [LIVE-now].
6. **Cannot:** see the ServiceNow inventory or usage tables, change job schedules, or widen the role (that needs facilitator IAM). **Should not:** use the connector key. M11 #03 lets participants read it, but using it would put the observer's identity on our own calls and blur WHO [INF].

---

## 8. Open questions

1. Will judges or facilitators show AICT-side views (inventory, `sn_ai_disc_ai_usage`) for our connection, and how do we cite them in the Evidence Pack?
2. Could facilitators widen the usage query (InvokeAgentRuntime, Converse) or restore the ListAgents and SageMaker permissions? Does Level 2 require AICT to show usage at all?
3. What does the knowledge article "AI Service Graph connector for Amazon - Setup Instructions" contain? It is referenced on p2–p3 but is not in the kit.
4. What values were entered for Management account ID and "User created in" on our connection?
5. Does AICT represent the AgentCore gateway as an MCP server? Why are there 7 GetAgentRuntime calls per cycle for 5 runtimes (versions or endpoints)?
6. Can WSParticipantRole run `cloudtrail validate-logs` and read the `sgc-aict-cloudtrail-…` bucket? (Not tested.)
7. How exactly does the deployed a-03 template differ from the kit file? (GetTemplate is denied; ask the facilitators.)
