---
name: workshop-aws-access
description: "How to reach the hackathon's AWS Workshop Studio account and EKS cluster from the laptop, what the participant role can and cannot do, the account's CloudFormation stacks (incl. facilitator-provisioned AICT), and how the gateway key is handled"
metadata:
  node_type: memory
  type: reference
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T17:48:37.594Z
---

- **Repo:** github.com/satyabrat-invences/TrustworthyAI-iFabric (private), cloned at ~/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric. Sibling folders: `agentic-template-hackathon/` (earlier brainstorm work) and `tmforum-rand/` (two TM Forum specification PDFs).
- **AWS:** Workshop Studio account 613052889143, us-east-1, role `WSParticipantRole` (session `Participant`). Temporary ASIA keys and a session token live in ~/.aws/credentials as profile `hackathon`. When they expire (ExpiredToken), the user pastes a fresh `export AWS_...` block and Claude rewrites the profile.
- **Participant role limits (verified):**
  - `bedrock:InvokeModel` is explicitly denied (console-iam-policy-0).
  - Denied: Bedrock Agents and Knowledge Bases APIs, `ssm:DescribeInstanceInformation`, `eks:ListAccessEntries`.
  - Allowed: `cloudtrail:LookupEvents`, X-Ray and CloudWatch Logs reads, reading the event asset bucket, EKS describe and kubeconfig.
  - Lambda PassRole only for `participant-app-role`.
  - Models are reachable only through the governed gateway `modaas-agw`; Module 2 Step 4 proved the other three routes closed.
- **Cluster:** EKS `a-01-eks-cluster-modaas` (1.36), kubeconfig ~/.kube/hackathon-config. The role maps to the k8s group `modaas:participants`, the same group the IDE lands in after bootstrap step 18. Not cluster-admin (it cannot create clusterrolebindings or delete namespaces), but it can create pods, port-forward and read secrets in every namespace tested, including kube-system (independent review, 2026-10-05). All EKS control-plane logging is off.
- **Local stand-in for the browser IDE:** ~/firstmate-homes/TrustworthyAI/workshop-local. See [[workshop-local-shell]]. Run every workshop command through it.
- **Workshop kit:** synced from the event S3 asset bucket to ~/firstmate-homes/TrustworthyAI/workshop-assets, deliberately outside the repo. It includes `modaas-aigateway-src.zip` (platform source). The Module 4 page's main diagram is NOT in that bucket; the user downloaded it, and it is in the repo at `notes/workshop-reference/modaas-platform-architecture.svg`.
- **Gateway key:**
  - `/tmp/modaas-token` (mode 600), extracted from secret `agw-apikeys` in `agentgateway-system`. macOS clears /tmp on reboot, so re-extract it then. Never print or commit it.
  - `modaas-agw` is an internet-facing ELB on plain HTTP: tools on :8080 `/mcp/<alias>`, models on :8081 `/v1/chat/completions`, TLS on :8443.
  - Keep the key in-cluster with `incluster` probes, as the guide does; never send it over the public plain-HTTP ELB.
  - `audit-store` is internal only: use `incluster`, port-forward or the kubectl service proxy.
- **CloudFormation stacks (4):**
  - `a-01-eks-cluster` (created 2026-10-04 10:03 UTC) and `a-02-code-editor` (10:18 UTC). The IdeUrl and CockpitUrl outputs are bearer links: never echo them.
  - **`a-03-servicenow-aict`** (22:02:58 UTC, updated 22:45 UTC) and **`aict-servicenow-user`** (22:43:21 UTC). CloudTrail shows both were executed by `assumed-role/WSOpsRole/Ops`, which the kit's `cfn/01-eks-cluster.yaml` describes as the facilitators' role.
  - They created `SgcAictReadOnlyAccessRole`, `sgc-aict-cloudtrail-cw-role-us-east-1`, the CloudTrail trail `sgc-aict-bedrock-trail` (Bedrock data events to CloudWatch Logs) and IAM user `ServiceNowAictUser`.
  - `WSOpsRole` then ran `CreateAccessKey` for that user directly (22:44:59 UTC), although a-03's description says no IAM user or access key is created anywhere in the workshop.
  - At 22:45:47 UTC `WSOpsRole` also ran `PutRolePolicy` on the IDE instance role (policy `AictGetRole`).
  - a-03 also created 2 S3 buckets and the log group `/aws/bedrock/aict-invocations`.
- **Cockpit:** the CloudFront CockpitUrl in the a-02 outputs. Without the token in its `tkn` query parameter it returns 403; with the token it sets a session cookie. Claude reads the URL from the stack output inside a command, never prints it, uses GET routes only, and never calls `POST /api/agents/{name}/ask` (that invokes an agent) unless the user approves it for a specific step. Approved once: Module 9 Step 1 section 3, 08:30 UTC 2026-10-05. Details in [[platform-verified-facts]].
- **Other pre-provisioned resources:**
  - 7 `team-a61f5-*` tool Lambdas.
  - AgentCore runtime `hackathon_helper` (pre-provisioned; the 3 reference-agent runtimes were added in Module 7).
  - Evidence bucket `team-evidence-613052889143`.

Related: [[aws-cli-install]], [[workshop-local-shell]], [[workshop-progress]], [[prooflab-project]]
