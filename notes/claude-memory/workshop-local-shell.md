---
name: workshop-local-shell
description: "The local stand-in for the workshop IDE that Claude built outside the repo (workshop-local/ — shell, env.sh, pinned tools, reusable scripts) and how future sessions must use it"
metadata:
  node_type: memory
  type: reference
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T02:30:38.617Z
---

`~/firstmate-homes/TrustworthyAI/workshop-local/` is Claude's local stand-in for the MoDaaS workshop's browser-IDE terminal, built 2026-10-04. It is deliberately outside the repo. Full details are in its `README.md`; read that first.

- **For people:** `~/firstmate-homes/TrustworthyAI/workshop-local/shell` opens bash with a `(hackathon)` prompt and everything loaded.
- **For Claude's Bash tool:** `bash -c 'source ~/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <cmd>'`. It must be bash, because `env.sh` uses `BASH_SOURCE`. The default shell is zsh, which also breaks unquoted globs such as `--include=*.py`.
- **`env.sh`:**
  - Sets AWS_PROFILE=hackathon and KUBECONFIG=~/.kube/hackathon-config BEFORE sourcing the kit's `rehydrate.sh`, so ~/.kube/config is never touched.
  - PATH: kubectl 1.36.5 (the guide shows v1.36.x) and Helm 3.22.0+g144ca65 in `bin/`; a Python 3.12 venv `.venv` with the starter kit's pins (strands-agents[openai] 1.57.2, bedrock-agentcore 1.24.0, mcp 1.30.0, aws-opentelemetry-distro 0.21.0); the starter kit (`incluster`).
  - Re-prepends `bin/` after rehydrate, which adds `~/bin`.
  - Sets REFERENCE_IMPL, TEAM (ConfigMap workshop-identity, currently a61f5), MODAAS_GATEWAY_ID (ConfigMap modaas-gateway) and TEAM_EVIDENCE_BUCKET.
- **`scripts/findings-recheck.sh`:** READ-ONLY. Live re-check of repo notes items #1, #3 (config only), #4, #5, #6, #8, #10, #12, #14 and #15. It does NOT cover #2, #7, #9, #11 or #13. All checked items still held at 2026-10-05 02:28 UTC.
- **`~/firstmate-homes/TrustworthyAI/workshop-static/` (2026-10-05):** sync of the event bucket's `static/` prefix (136 files, 24 MB; the day-1 `workshop-assets/` holds only `assets/`, 90 files). Holds scripts/twin-scenario.sh, cfn/, iam/ policies, agents/hackathon-helper, Lambda tests and images.
- **`digital-twin/` (Module 10, 2026-10-05):** `setup-digital-twin.sh` (the kit copy) and `shim/` (python3 → /usr/bin/python3 3.9.6; sed GNU `-i` → BSD). The MAVERIC clone is at `workshop-local/maveric` (TWIN_DIR) with its own `.venv`. RADP runs in Docker Desktop on host port 8090.
- **`scripts/pre-push-secret-scan.sh [repo]` (2026-10-05):** READ-ONLY. Pattern scan plus an exact-value scan of the real secrets (gateway key, ledger token, hackathon AWS creds, CockpitUrl/IdeUrl and their tokens), loaded into variables and never printed. It FAILS CLOSED if any value can't be loaded. Run before every push.
- **Backup in the repo:** `TrustworthyAI-iFabric/tools/workshop-local/` holds copies of README, env.sh, shell, requirements.lock.txt, scripts/, research/ and digital-twin/ (setup script, shims, query helpers). Pushed in commit 468b5e9. bin/, .venv/, maveric/ and logs are excluded.
  - The working copies here remain the live ones: re-copy (`rsync` with the same excludes) before a commit when they change.
- **`scripts/side-entrance-probe.sh`:** CREATES two throwaway pods. Ask the user before running.
- **Guide commands:** run them through this environment, never the normal zsh terminal. That terminal has kubectl 1.34, Helm 4, no workshop variables and no AWS profile.
- **Differences from the real IDE:**
  - The AWS role is WSParticipantRole, not IdeInstanceRole. The facilitators changed the IDE role's policy at 2026-10-04 22:45:47 UTC.
  - CodeBuild from the laptop WORKS (Module 7 agent image built 2026-10-05).
  - There is no ~/.modaas-bootstrap/status.
  - The Module 10 digital twin on Apple Silicon is untested.

**Why:** the user asked for a note so future Claude sessions know this shell exists and how to use it, rather than rebuilding it or running guide commands in the wrong shell.
**How to apply:** use it for every workshop command. If a tool seems missing, check `README.md` before reinstalling anything.

Related: [[workshop-aws-access]], [[workshop-progress]], [[hackathon-working-agreement]]
