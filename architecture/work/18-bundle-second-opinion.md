# Second opinion: the AgentCore agent size limit (AR-03)

Read-only investigation, 2026-10-06 ~03:00Z. No repo edits, no AWS writes, no builds and no agent invocations. The AWS reads were IAM, CodeBuild, CloudTrail, ECR, AgentCore and kubectl GETs. Account ids are scrubbed throughout.

## 0. Bottom line

1. **The limit is CodeBuild's own cap of 25,600 characters on `buildspecOverride`.** It is enforced by the service at `StartBuild` and is not in AWS's published quotas or in the API reference. The kit's author hit the error "Max buildspec length is 25600" live (`build-agent-image.sh:168-170`), and the kit pre-checks it at `:197-201`.
   - The kit inlines `agent.py` (gzip -9n, then base64) and the Dockerfile (base64) into that one buildspec.
   - Fixed overhead is 1,383 to 1,551 chars, so **24,049 to 24,217 chars** remain. The figure 24,049 corresponds to tag `ifabric-customer` with new-agent.sh's `EXTRA_PIP`. The planned tag `ifabric-customer-<7hex>` with `EXTRA_PIP=openai==2.54.0` leaves **24,149**.
2. **The bundle measures 46,028 chars**, as the kit measures it, for the byte-identical customer bundle; IT and network are within ±100.
   - The brief's "~66K" is almost certainly the *raw* minified source: 66,873 bytes measured here.
   - Shrinking alone cannot fit. The best case, python-minifier plus a self-extracting lzma loader, is **32,592** chars: 35% over budget.
3. **The two-stage fallback (D-B, `FROM <repo>@<base digest>`) is almost certainly blocked by IAM.** The CodeBuild role has `ecr:BatchGetImage` but **not `ecr:GetDownloadUrlForLayer`**, and the repo has no repository policy. Docker therefore cannot fetch the base image's config or layers, and build 2 would fail at `FROM` with a 403.
   - Confidence is high, but this is unverified; a 1-minute probe confirms it (§4.3).
   - D-B is now committed: `501ea78` on `pr/PR-06-bundler-trio`. `tools/make_ifabric_agents.py:270` emits the role Dockerfile `FROM <repo>@<base digest>`.
   - **Its arm64 Docker smoke cannot catch this.** `tools/docker_smoke/run_smoke.py:16` swaps in a local base tag, so the build role's ECR pull is never exercised. **This needs to reach them now.**
4. **PRIMARY (gated by a 1-minute probe): carry the whole bundle in a StartBuild `environmentVariablesOverride`.**
   - The buildspec keeps only `printf %s "$AGENT_B64" | base64 -d | gunzip > agent.py`, which brings it to about 1.5K chars.
   - Modules stay byte-identical, no minification is needed, the whole code is inside the image, and one build runs per role.
   - It needs no new permission. The only unknown is an undocumented CodeBuild limit on env-value size.
5. **FALLBACK (all limits documented and verified): split across the image and AgentConfig env vars, hash-pinned.**
   - The kit build runs unchanged. The image holds the loader, the c16 core and the C16 path: 18,356 chars, about 5.8K under budget.
   - The rest rides in 6 env vars `IFABRIC_LIB_0..5` of 5,000 chars or less each. The image pins their sha256, so the image digest still determines every byte that runs.

## 1. The limit, traced

### 1.1 How agent.py reaches CodeBuild

`new-agent.sh:151-153` runs `TARGET=agentcore AGENT_SRC=… EXTRA_PIP=… bash build-agent-image.sh`. Then, in `build-agent-image.sh`:

| Line | What happens |
|---|---|
| `:171` | `AB64=$(gzip -9nc < "$AGENT_SRC" \| base64 \| tr -d '\n')` runs **on the laptop** (Apple gzip 475 here; GNU gzip in the IDE, which differs by tens of chars). |
| `:172` | `DB64`: the whole Dockerfile, base64-encoded. It contains `RUN pip install <SDK_PIP + EXTRA_PIP>`, `ENV OTEL…` and `COPY agent.py /app/agent.py`. |
| `:173-196` | One JSON buildspec. It contains `echo <AB64> \| base64 -d \| gunzip > agent.py` and `echo <DB64> \| base64 -d > Dockerfile`. The image ref `<ecr-host>/<stack>-aws-agent-operator:<tag>` appears 3 times (docker build, arch assert, docker push), and the ECR host appears 4 times. |
| `:197-201` | `FATAL` if `${#SPEC} > 25600`. |
| `:221-223` | `aws codebuild start-build --project-name a-01-eks-cluster-modaas-image-build <ARM overrides> --buildspec-override "$SPEC"`. |

None of this goes through SSM, a ConfigMap, an annotation or a CR field. The CodeBuild project, read live, is `source.type = NO_SOURCE` with service role `a-01-eks-cluster-ImageBuildRole-…`, so the inline buildspec is the **only** code carrier in the kit path.

### 1.2 What produces 24,049

- **The source is CodeBuild `StartBuild` server-side validation of `buildspecOverride`, capped at 25,600 chars.** The StartBuild API reference lists `buildspecOverride` as "Type: String" with no length constraint, and the quotas page doesn't list it either. The value is empirical, from the kit's live error (event b0525231, 2026-09-28).
- **Overhead formula.** Measured with a replica of `:135-196`. The replica is byte-identical to the kit's own `DRY_RUN=1` output, and `DRY_RUN` calls no AWS.

| Tag | `EXTRA_PIP` | Overhead | AB64 budget |
|---|---|---|---|
| `my-agent` | none | 1,383 | 24,217 |
| `my-agent` | new-agent.sh pins | 1,527 | 24,073 |
| `ifabric-customer` | new-agent.sh pins | 1,551 | **24,049** (the AR-03 figure) |
| `ifabric-customer-<7hex>` (the plan) | `openai==2.54.0` | 1,451 | **24,149** |
| `ifabric-customer-<40hex>` | `openai==2.54.0` | 1,550 | 24,050 |

- Each tag character costs 3 chars. Each `EXTRA_PIP` character costs about 1.33 chars plus 2 quote chars per word, because it sits inside the base64 Dockerfile.

### 1.3 Other carriers in the same path

None of them has its own budget:

- **`EXTRA_PIP`**: it lives inside `DB64`, so it **shares** the 25,600 cap. The regex at `:141` rejects every URL form. Tested locally:
  - `https://…whl`, `name@https://…`, `--index-url=…` and `git+https://…` are all REJECTED.
  - Only a plain `name==ver` passes, which means a package on **public PyPI**.
- **`IMAGE_TAG`**: inside the same buildspec, at 3 chars per tag character.
- **`--skills`**: becomes `spec.agentCard.skills` (`make-agentcore-agents.py:249`). This is CR metadata and never reaches the image or the environment.
- **`requirements.txt`**: copied by `new-agent.sh:79` but **never read** by the build. The Dockerfile at `:172` COPYs only `agent.py`, so this carrier is dead.
- **Role or prompt files**: the kit has none.
- **`TOOL_MCP_URL` / `TOOL_MCP_ALIAS`** (`new-agent.sh:111-127`): patched into the AgentConfig env. That is a **runtime** channel with its own documented budget:
  - AgentCore `CreateAgentRuntime.environmentVariables` allows at most 50 entries, each value at most 5,000 chars.
  - The live CRD `agentconfigs.oda.tmforum.org` has the same schema (`maxProperties: 50`, `maxLength: 5000`) and refuses "names the operator owns".
  - The live `my-agent` runtime uses 13 of the 50 slots: 7 declared plus 6 operator-owned.

### 1.4 Permissions (read live; the live policies equal the `workshop-static/iam` copies apart from string-vs-list normalization)

**Participant (`console-iam-policy-0`, `participant-permissions-policy-1`, `ws-default-policy`):**
- `codebuild:StartBuild` and `BatchGetBuilds` on `project/*eks-cluster*`, with **no condition keys**. Every override is therefore allowed, including source-type and location, env vars and buildspec. A service-role override would also need `iam:PassRole` on the target role.
- Logs read on `*`: every participant can read build logs.
- S3 `Get`/`Put`/`Delete`/`List` on `team-evidence-*`, but no `PutBucketPolicy`.
- ECR read plus `CreateRepository team-*`, but no `PutImage` and no `SetRepositoryPolicy`.
- Lambda `Create`/`Update`/`AddPermission`/`Invoke` on `function:team-*`, plus `PassRole participant-app-role` to Lambda. That role exists.
- `iam:Get*`/`List*`.

**CodeBuild role** (inline `modaas-image-build`, which matches `cfn/01-eks-cluster.yaml:1319-1363`; no permissions boundary):
- Its own log group.
- `s3:GetObject` **only** on the workshop event bucket.
- ECR `GetAuthorizationToken`, plus push actions and `BatchGetImage` on the 5 CFT repos.
- **No `GetDownloadUrlForLayer`.**
- **So it can neither read the team bucket nor pull private images.**

**ECR repos:**
- `cfn/01-eks-cluster.yaml:1243-1317` defines no `RepositoryPolicyText`.
- CloudTrail has **0** `SetRepositoryPolicy` events.
- The only principal ever seen calling `GetDownloadUrlForLayer` or `BatchGetImage` is the runtime role `a-01-eks-cluster-agentcore-runtime`.

**Runtime role:** ECR pull on `*`, and no S3.

**`WSParticipantRole` trust:** account root and `WSControlPlaneUser` only, so `serviceRoleOverride` to it is impossible.

## 2. The bundle

**Sources:**
- Committed branch tips, copied read-only with `git show`: PR-02 core, PR-03/04/05/07 adapters, and PR-06 app, roles and bundler.
- I left the uncommitted `rails.py` in PR-05 aside. It is 389 B larger, which is noise.

**Measured with the kit's exact gzip+base64:**

| Customer bundle | Raw | Kit chars | Over 24,149 |
|---|---|---|---|
| Byte-identical (committed `bundle_agent.py`) | 113,223 B | **46,028** | +21,879 |
| Committed `--strip-docstrings` | 100,864 B | 38,688 | +14,539 |

**Composition** (byte-identical; *marginal* = kit chars removed if the module were empty):

| Module | Raw B | Marginal | Share | Docstrings B | Comments B | Indent B |
|---|---|---|---|---|---|---|
| model_call | 21,780 | 7,788 | 16.9% | 1,963 | 1,080 | 3,592 |
| emit_client | 16,559 | 6,300 | 13.7% | 1,456 | 500 | 3,129 |
| ifabric_app | 14,853 | 5,964 | 13.0% | 1,697 | 576 | 2,256 |
| rails (already hand-minified: dense regexes, near its floor) | 9,532 | 5,920 | 12.9% | 218 | 0 | 183 |
| j2 | 8,455 | 3,552 | 7.7% | 1,209 | 169 | 1,064 |
| c16_core (must stay byte-identical) | 8,673 | 3,508 | 7.6% | 624 | 399 | 1,145 |
| startup | 6,391 | 2,576 | 5.6% | 932 | 146 | 811 |
| egress | 3,652 | 1,800 | 3.9% | 719 | 261 | 384 |
| tally | 4,750 | 1,672 | 3.6% | 822 | 367 | 1,016 |
| tool_call | 3,770 | 1,620 | 3.5% | 505 | 90 | 557 |
| hooks | 3,356 | 1,196 | 2.6% | 526 | 198 | 764 |
| judgment | 2,334 | 960 | 2.1% | 436 | 0 | 272 |
| action_id | 1,587 | 728 | 1.6% | 469 | 0 | 320 |
| Loader, role, sha table, header | — | ~2,030 | 4.4% | | | |

- Docstrings are 11% of raw, comments 4% and indentation 15%. There are no annotations.
- No schemas, contract or pack logic are in the bundle: `prooflab/contract` is already excluded.
- **All 12 adapters are on the hot path**: `ifabric_app.SURFACE` imports every one of them.

## 3. Workarounds evaluated

All sizes are kit chars for the customer role; IT and network are within ±110. Every generated variant was import-smoked: it was run from an empty cwd under the workshop venv (Python 3.12.7 with the exact pins), every SURFACE name resolved, and `EVALUATOR_SHA256` equalled sha256 of the repo's `c16_core.py`. **An import is not proof of semantics:** the team's unit tests were not run against the minified modules.

| # | Workaround | Measured | Fits? | Permissions / feasibility | Risks | Effort | Verdict |
|---|---|---|---|---|---|---|---|
| a | python-minifier 3.4.0: docstrings, annotations (not class fields), `pass`, rename locals; core untouched | 34,460 (SAFE profile without renames: 35,084; with hoist: 35,500, worse) | No (+10.3K) | none | Unaudited semantic transforms; tracebacks unreadable; the image is not human-readable | 20 min | lever only |
| b | Self-extracting loader: lzma raw (lc=4, pb=0), base85, sha256-verified, core byte-identical inside the payload | V0: 43,684 · V1 strip: 34,496 · with (a): **32,592** (bz2: 32,452; base64: 32,480) | No (+8.4K) | none | Opaque blob in the image (auditability, judges' optics) | 30 min | lever only; it gains only about 5% over the kit's gzip |
| e | Thin agent | Fitting from (a)+(b) means dropping 9.5K or more: rails 4.5K + j2 2.1K + startup 1.4K + egress 0.9K + tool_call 0.85K | Only by cutting governance | — | Removes the product | — | not viable |
| c | Another kit carrier (skills, requirements.txt, `EXTRA_PIP`) | — | No separate budget | §1.3 | — | — | dead |
| c′ | **Runtime env chunks** in the AgentConfig env (50 × 5,000), hash-pinned in the image | Image **18,356** + env 26,684 in **6** vars (byte-identical). With V1 strip: 21,340 + 4 vars. With V3: 22,572 + 3 vars | **Yes** | None new; limits documented and verified in the CRD | Plain text in the CR and runtime config (code only; the audit token is already there); operator reconcile refusal untested | 75-90 min | **FALLBACK** |
| d | `EXTRA_PIP` wheel | — | — | The regex rejects URLs, so only public PyPI is possible | Code exposed publicly, irreversibly | — | reject |
| d′ | Presigned team-bucket URL fetched in the build | Unlimited | Yes | The participant can presign; the build role cannot read the bucket itself | **Credential-bearing**: carries the ASIA key id and the session token, valid until the session expires (12 h or less). CodeBuild logs every command verbatim ("Running command …"), and every participant can read the logs. Passed via an env var it stays out of the logs but sits in BatchGetBuilds and CloudTrail | 30 min | avoid |
| f1 | **StartBuild `environmentVariablesOverride`** carrying AB64 | env value 45,952-46,040; buildspec about 1,450-1,470 (5.7% of the cap) | Yes, **if** CodeBuild accepts a value of about 46K (undocumented) | StartBuild has no condition keys: nothing new | Visible in BatchGetBuilds, the console and likely CloudTrail: **the same exposure class as today's inline buildspec**. Not in the logs (`$AGENT_B64` stays unexpanded) | Probe 10 min + about 40 min | **PRIMARY (gated)** |
| f2 | Two-stage `FROM <repo>@<digest>` (D-B) | each part 24K or less | **Blocked** | Needs `ecr:GetDownloadUrlForLayer` on the build role, which only facilitators can add | — | — | blocked |
| f3 | Lambda channel: `team-ifabric-src` returns the bundle; `AddPermission` lets the build role invoke it; the build runs `aws lambda invoke` | Unlimited (6 MB) | Yes | Uses existing `team-*` Lambda rights, but **adds a resource-policy grant** to the build role, and needs 2 AWS writes | No URL, IAM-signed, nothing in the logs | about 60 min | alternate fallback |
| f4 | The runtime role pulls a FROM-scratch "code image" by digest at startup | Unlimited | Likely: the runtime role has ECR pull on `*`; needs VPC egress to ECR and S3 | none new | Cold-start dependency, more moving parts | about 2 h | not now |
| f5 | `--source-type-override S3`, or a buildspec read from S3 | — | No: the build role reads only the event bucket | — | — | — | dead |
| f6 | `serviceRoleOverride` = WSParticipantRole | — | No: its trust policy excludes CodeBuild | — | — | — | dead |

## 4. Recommendation

### 4.1 PRIMARY: whole bundle in a StartBuild env-var override, gated by a probe

**Step 0, the probe.** It is one AWS write: a throwaway build with no docker and no push, and it needs captain approval. If CodeBuild rejects the value at `StartBuild`, nothing runs.

```bash
python3 - > /tmp/pa-probe.json <<'EOF'
import json, base64, os
v = base64.b64encode(os.urandom(48000)).decode()        # 64,000 chars: about 39% headroom over 46K
print(json.dumps({"projectName": "a-01-eks-cluster-modaas-image-build",
  "buildspecOverride": json.dumps({"version": "0.2", "phases": {"build": {"commands": [
      'echo "len=${#AGENT_B64}"', 'printf %s "$AGENT_B64" | sha256sum']}}}),
  "environmentVariablesOverride": [{"name": "AGENT_B64", "value": v, "type": "PLAINTEXT"}]}))
EOF
aws codebuild start-build --cli-input-json file:///tmp/pa-probe.json --query build.id --output text
```

- **Pass:** the build SUCCEEDS, the log shows `len=64000`, and the sha256 equals the local one.
- **InvalidInputException:** optionally retry once at 47K. If that also fails, go straight to §4.2.

**Steps 1-4 (the fork lives in the repo, owned by the PR-06 session):**

1. **Fork `build-agent-image.sh`** as `tools/build_ifabric_image.sh`. Keep `:53-166` unchanged: the ARM overrides, the reference-tag guard, the `EXTRA_PIP` regex and discovery. Then:
   - Replace the `:190` command with `printf '%s' "$AGENT_B64" | base64 -d | gunzip > agent.py`, followed by `echo "<sha256>  agent.py" | sha256sum -c -`.
   - Send `AB64` as `environmentVariablesOverride` through `--cli-input-json file://…`, not on argv.
   - Keep the 25,600 check on `SPEC` and add `${#AB64} <= <probed limit> - 2000`.
   - Keep the arch assertion, the push and the digest written to `URI_FILE`.
   - Never `env`, `printenv` or `set -x` in the buildspec.
2. **Bundler:** keep the committed byte-identical layout and drop strip/prune. **Gate:** replace "gz+b64 ≤ 24,000" with "≤ probed limit − margin AND `DRY_RUN` buildspec ≤ 25,600". D-B and PR-00b's two-stage gate rules are no longer needed.
3. **Checks:** run the fork with `DRY_RUN` offline, then the existing local arm64 Docker smoke. The Dockerfile is unchanged.
4. **Builds:** 3 builds of about 70 s each. Record the digests (EP-0).

**Size:** an env value of about 46.0K and a buildspec of about 1.5K. Headroom depends on the probe: with 64K accepted, the margin is about 18K, or 28%.

**Effort:** about 50 min, including the probe.

**Risks and containment:**
- Unknown limit: the probe answers it first.
- Exposure: unchanged in class. Today the kit already puts the code in the buildspec, which BatchGetBuilds, the console and CloudTrail show in the same way. Run `pre-push-secret-scan.sh` on the bundle before each build.
- Integrity: the sha256 check runs inside the build, and the digest is recorded.
- Linux allows 128 KiB per env string, which is ample.

### 4.2 FALLBACK: hash-pinned runtime env chunks, kit build unchanged

1. **Bundler `--layout env-split`.** The image file holds:
   - the header with the `evaluator.sha256` marker;
   - a loader;
   - `c16_core` byte-identical;
   - the C16 path (`model_call`, `tally`, `hooks`, `action_id`);
   - the role.

   The remaining modules become JSON, then lzma raw, then base64, chunked into `IFABRIC_LIB_0..5` of 5,000 chars or less each. The image pins sha256 of the env part and of every module. The prototype is at `out/PB-V0-customer.py` with `out/PB-V0-customer.env.json`; it passed the import smoke and refused on both a tampered chunk and absent chunks.
2. **Loader failure must fail closed, not crash.** On a missing or altered env part, the production loader must set a flag that `ifabric_app` reports as `startup-failed` (every invocation refused, the model never called). The prototype's `SystemExit` would crash-loop the runtime instead.
3. **Build:** run the kit's `build-agent-image.sh` unchanged (`TARGET=agentcore`, `AGENT_SRC=agents/ifabric-<role>/ifabric-<role>.py`, a unique `IMAGE_TAG`). Result: **18,356 chars against a budget of 24,149**.
4. **Deploy:** generate the AgentConfig (`tools/make_ifabric_agents.py`), add the `IFABRIC_LIB_n` entries as `new-agent.sh`'s `patch_tool_env` does, run `kubectl apply --dry-run=server`, apply, and approve. Deploy **one agent first**: the dry run validates only the schema, so a reconcile-time refusal of the `DeclaredEnvInvalid` class only shows on a real apply. `IFABRIC_LIB_*` is not operator-owned, so a refusal is unlikely.

**Slots and effort:** 13 runtime env slots are in use, plus 6 here, plus the pin vars, all within 50. Effort is about 75-90 min.

**Risks and containment:**
- The code sits partly outside the image, but the image pins its hash, so the digest still determines every byte. Record the env-part hash in the EP-0 freeze.
- Env values are plain text in the CR and runtime config. They hold code only; the audit token is already there.
- Any env change triggers an UpdateAgentRuntime, so the freeze record must be re-run.

**Alternate:** if the probe fails and the team needs **all** code inside the image, use the Lambda channel (f3). It adds a resource-policy grant and two AWS writes.

### 4.3 Confirm or rescue D-B before anyone spends more time on it

- **Probe** (one build, no push): log in to ECR, then `docker pull <ecr-host>/a-01-eks-cluster-aws-agent-operator@<digest of reference-agent-v5-agentcore>`.
  - Expected: a denial naming `ecr:GetDownloadUrlForLayer` for `assumed-role/a-01-eks-cluster-ImageBuildRole-…`.
- **Rescue:** a facilitator adds `ecr:GetDownloadUrlForLayer` on the agent-operator repo to the `modaas-image-build` policy, a one-line change. With that, D-B works as designed, at 4 builds.

## 5. Team documents these findings contradict

- **`architecture/ARCHITECTURE.md:1683`**: "There is no other channel". In fact there are three: StartBuild env overrides, runtime env chunks and the Lambda channel.
- **`architecture/ARCHITECTURE.md:1688`**, **`architecture/work/05-feasibility-agents-runtime.md:48` (AR-03)**, **`FEATURE-MAP.md:61` (D-B)**, **`architecture/work/17a-plan-review-infra.md:155` (17A-07)** and **`IMPLEMENTATION-PLAN.md:639` (R7)**: all assume "the CodeBuild role can pull and push" the repo. It can push but **cannot pull** (no `GetDownloadUrlForLayer`).
- **AR-03's 24,049** is the figure for tag `ifabric-customer` with new-agent.sh's `EXTRA_PIP`. The planned tag with `openai==2.54.0` gives 24,149.

## 6. Reproduce (scratch: `bundle2/`)

| File | What it does |
|---|---|
| `kitspec.py` | The kit buildspec replica, byte-identical to `DRY_RUN=1` for 3 tag/pip combinations. |
| `measure.py` | Baseline and composition. |
| `experiments.py` | Experiments (a) and (b). |
| `split.py` | Sizes P-A and P-B. |
| `smoke.py` | Import smoke for every generated variant. |
| `tree/` | Read-only copies of the branch tips. |
| `out/` | The generated variants. |
| `live-*.json` | The live IAM policy documents. |
