---
name: hackathon-working-agreement
description: "How the user wants Claude to work on the hackathon — read-only by default, ask before writes (including workshop write steps), keep memory continuously updated with independent review, go through all modules before planning"
metadata:
  node_type: memory
  type: feedback
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T17:48:39.032Z
---

- **Read-only by default.** User, 2026-10-04 (CDT): "only read only access please." Ask before any write to the repo or the cluster. That includes workshop steps that apply, annotate, approve, pause or delete resources. Never delete or change a cluster resource Claude did not create without asking; other people work in this account.
- **NEVER RUN the AI Native Networks Immersion Day workshop's `cleanup-module1.sh`** (or its other cleanup scripts) in our account. Per a 2026-10-05 web review, it deletes EVERY AgentCore gateway, agent runtime, memory and runtime log group in the region, with NO name filter: it would wipe the platform's gateway, the reference agents and my-agent. Only read that workshop's material.
- **GIT: COMMIT AND PUSH AS WE GO** (user, 2026-10-05: "are you committing everything? push everything to github as well.").
  - First push: commit `03ff0bf` on `main` (repo was empty) with 289 files: notes/, gap-list.md, hackathon-context/.
  - Second push: `468b5e9` (tools/workshop-local backup, at the user's "yes copy the reusable scripts into the repo").
  - **Before every push run `bash ~/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh <repo>` (must print RESULT: clean). It does:**
    - patterns: AKIA/ASIA keys, private keys, the `tkn` query parameter with a value, bearer/ghp_/sk-
    - EXACT VALUES loaded into variables and never printed: /tmp/modaas-token, the ledger AUDIT_WRITE_TOKEN, the hackathon AWS creds, the CockpitUrl/IdeUrl and their tokens. They must appear in 0 files.
  - Commits end with the Co-Authored-By trailer.
  - workshop-local/ and memory are OUTSIDE the repo and not pushed.
- **Repo writes the user has approved so far:**
  - correcting notes #13
  - adding notes #15
  - copying the Module 4 architecture SVG into `notes/workshop-reference/` ("copy it into the repo folder into a place of your chosing")
  - adding the Module 4 claim findings (#2 and #3 additions, #16–#18) and the reference-agent guide-vs-source mismatches (#19–#23). User, 2026-10-04 CDT: "YES TO BOTH"
  - adding the 8 candidate items as #24–#31, plus cross-references in #3 and #10. User, 2026-10-04 CDT: "add them now."
  - the guide's TMF639 explanation in #17 ("add it") and #32, trace pipeline → X-Ray ("ADD")
  - #33–#35 from the Module 6 Cedar page ("add the three possible notes")
  - Module 6 Cedar step 1: ConfigMap `modaas-system/my-team-policy` (cluster write; user "OK")
  - Module 6 pause: Claude's run (user "OK"); the user then ran the polling version themselves
  - #36 added and #28 updated ("Add them")
  - #37–#40 ("add", after the Cedar check). The header coverage-line fix was disclosed with an offer to revert.
  - #41–#47 and the #19/#28/#36/#37 updates (user, on the Module 6–7 backlog: "can you run it on your end")
  - **`gap-list.md` at the REPO ROOT (the scored deliverable):** the user said "put it in gap-list.md the deliverable and any other gaps that you find" (2026-10-05). Claude created a draft with 9 entries.
    - A `notes/gaps.md` created minutes earlier, on "note it in gaps.md", was removed; its entry moved in.
    - Standing instruction: add new gaps found to gap-list.md.
  - **Cluster writes with the user's OK (2026-10-05):**
    - Module 5/6 model calls and probes
    - Module 7 set-up: the 3 AgentConfigs, their approvals and the CodeBuild image
    - the S1–S3 runs
    - the IT model swap and re-attest annotation
    - the modaas-docs pause/unpause
    - Module 9 Step 1 sections 3–5 (user: "go ahead for section 3-5. you have the cockpit url"): ONE cockpit POST /api/agents/hackathon-helper/ask (the Help panel), 3× ask-agent.sh, and 2 server-side dry runs (non-persisting) to test the helper's drafts. The cockpit stays GET-only otherwise.
    - Module 9 Step 1b (user "OK", 2026-10-05):
      - `new-agent.sh` dry run plus a no-safety server dry run (both non-persisting)
      - the real build + apply of AgentConfig `my-agent` (created by Claude 08:59 UTC)
      - the approval as `satyabratsrikumar@team`
      - then the ask and the checkpoint
    - Module 10 option B (user "run in B"): the MAVERIC twin runs locally in Docker Desktop (no cluster/AWS writes)
    - Module 9 Step 3 (user "go ahead"): the prompt attack via my-agent, and option B = pause/unpause nemotron-super-120b (not the page's nano-9b), with polling and an always-unpause trap
- **Cockpit:** the user shared the CockpitUrl host and asked "would you like to check it out?". Claude may read the token-bearing URL from the stack output without printing it, GET routes only, and delete the cookie jar afterwards.
- **Memory is the exception.** User: "yes , independent reviwer for update to memory. from now onwards always update your context and memory."
  - Update memory as facts change, without asking.
  - For substantial rewrites, run an independent review by a fresh general-purpose subagent with no access to the conversation. Give it the user's words verbatim and keep it read-only. Then apply its fixes.
  - Small progress lines can go in directly. Confirm with the user if they want every update reviewed.
- **Process.** User: "we will go over all the modules of aws and then at the end look at buildiing a complete plan."
  - Claude's practice: for each module page the user pastes, run its read-only commands as written through the workshop shell ([[workshop-local-shell]]), compare with the guide's expected output, and report differences with evidence.
  - Ask before write steps.
  - The `hackathon-context` handoff is baseline context, not the final plan.
- **Keep module steps focused.** User, 2026-10-04 CDT: "a lot of what you have written will be clear after we go over all the modules." Per step: run the commands, give a short guide-vs-live table, and note at most one or two contradictions. Park deep investigations and long write-ups until the modules are done, unless asked.
- **Stay in scope.** User: "our challenge is different than the audit response you found is not something these guys want." Don't steer toward Claude's own challenge ideas; keep observations factual; give short answers when asked.
- **Platform findings** go in repo file `notes/platform-observations.md`. Ask before editing it. The user reviews it with the platform team on 2026-10-05; it is not part of the submission.
- **Memory is mirrored.** The user approved this on 2026-10-04 CDT (≈02:07 UTC on 2026-10-05).
  - Primary: `~/.claude/projects/-/memory/` (sessions started in `/`).
  - Mirror: `~/.claude/projects/-Users-satyabratsrikumar-firstmate-homes-TrustworthyAI-TrustworthyAI-iFabric/memory/` (sessions started in the repo folder).
  - After every memory change, run `rsync -a --delete <edited>/ <other>/`. Never edit the two copies separately.

**Why:** the user corrected scope creep, asked for read-only access mid-task, and wants continuity across sessions.
**How to apply:** run read-only checks freely, ask before writes, update memory as facts change, and cite evidence for every claim.

Related: [[prooflab-project]], [[workshop-progress]], [[workshop-local-shell]]
