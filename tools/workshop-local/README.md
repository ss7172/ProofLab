# workshop-local — the workshop IDE, on this laptop

A local stand-in for the MoDaaS workshop's browser IDE terminal. It gives a bash shell with the same tools, versions and variables as the IDE, using the Workshop Studio participant credentials (AWS profile `hackathon`). It lives **outside the repo** on purpose: nothing here belongs in the hackathon submission.

Created 2026-10-04 by Claude for the Trustworthy AI hackathon (ProofLab).

## Use it

| How | When |
|---|---|
| `~/firstmate-homes/TrustworthyAI/workshop-local/shell` | A person wants an interactive terminal. Opens bash with a `(hackathon)` prompt. `exit` to leave. |
| `bash -c 'source ~/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <command>'` | One-off commands, e.g. from Claude's Bash tool. Must be **bash**: the login shell is zsh, and `rehydrate.sh` is bash-only. |

Run workshop-guide commands **here, not in the normal terminal**. The normal terminal has kubectl 1.34 and Helm 4, no workshop variables and no AWS profile, and `aws eks update-kubeconfig` there would write into `~/.kube/config`.

## What `env.sh` sets up

1. `AWS_PROFILE=hackathon` and `KUBECONFIG=~/.kube/hackathon-config`. Both are set **before** `rehydrate.sh`, whose `aws eks update-kubeconfig` would otherwise write into `~/.kube/config`.
2. PATH, in order:
   - `bin/`: kubectl **1.36.5** and Helm **3.22.0+g144ca65**, the IDE's versions, checksum-verified downloads
   - `.venv/bin`: Python **3.12** with the starter kit's pins: strands-agents[openai] 1.57.2, bedrock-agentcore 1.24.0, mcp 1.30.0, aws-opentelemetry-distro 0.21.0, plus httpx, pyyaml, boto3, jsonschema. Full freeze in `requirements.lock.txt`
   - `../workshop-assets/starter`: the starter kit, including `incluster`
3. `REFERENCE_IMPL=../workshop-assets/reference-impl`, so `new-agent.sh` finds the reference scripts.
4. Sources `../workshop-assets/scripts/rehydrate.sh`, which exports REGION, ACCOUNT_ID, CLUSTER, STACK_NAME, CLUSTER_NAME, NODE_ROLE_ARN, ECR_HOST, MODAAS_SHA and PDP_DIGEST, and refreshes the kubeconfig.
5. Reads the IDE-only variables from ConfigMaps in `modaas-system`: `TEAM` (from `workshop-identity`, currently `a61f5`) and `MODAAS_GATEWAY_ID` (from `modaas-gateway`). Also sets `TEAM_EVIDENCE_BUCKET=team-evidence-$ACCOUNT_ID`.

Nothing outside this folder, `~/.kube/hackathon-config` and the `hackathon` AWS profile is affected.

## scripts/

| Script | What it does | Changes the cluster? |
|---|---|---|
| `findings-recheck.sh` | Live re-check of notes items #1, #3 (config), #4–#6, #8, #10, #12, #14, #15. Not #2, #7, #9, #11, #13 (see the script header). Prints no secrets. | **No.** Read-only |
| `side-entrance-probe.sh` | The live test behind finding #3: an unauthenticated MCP `initialize` through the gateway (403) vs. directly to the tool pod (200 + session) | **Yes.** Creates two throwaway curl pods, then deletes them. Ask first |

## research/

| File | What it is |
|---|---|
| `reference-agents-2026-10-05.md` | Source-cited profile of the three reference agents (roles, models, tools, deploy steps, ledger records, IDs, tokens, scenarios, guide discrepancies). Read-only research; key claims spot-checked. |

## Things that live elsewhere

- **Workshop kit** (scripts, starter, reference-impl, CRs, the platform source zip): `../workshop-assets/`, synced from the event's S3 asset bucket.
- **Gateway key:** `/tmp/modaas-token` (mode 600, from secret `agw-apikeys` in `agentgateway-system`). macOS clears `/tmp` on reboot; re-extract it with Module 2 Step 4 section 1. Never print or commit it.
- **AWS credentials:** temporary; `~/.aws/credentials`, profile `hackathon`. When calls fail with ExpiredToken, paste a fresh export block from Workshop Studio.
- **Guide-vs-cluster findings:** `../TrustworthyAI-iFabric/notes/platform-observations.md`.

## Differences from the real IDE

- **IDE role changed after bootstrap:** at 2026-10-04 22:45:47 UTC the facilitators' role (`WSOpsRole`) put a new policy on the IDE's instance role (CloudTrail `PutRolePolicy`), so the real IDE's AWS permissions are not frozen at their install-time state.
- **AWS role:** this runs as `WSParticipantRole`, not the IDE's `IdeInstanceRole`. In Kubernetes both land in the `modaas:participants` group. AWS permissions can differ: building agent images through CodeBuild (Module 9) is untested from here.
- **Missing IDE files:** there is no `~/.modaas-bootstrap/status`, because the installer ran on the IDE. Check the cluster instead; Module 2 Step 2 shows how.
- **Module 10 digital twin:** expects the IDE's Linux Docker host. Docker Desktop is here, but an Apple-Silicon build of the twin is untested.
