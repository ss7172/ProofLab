# tools

Backup copies of the scripts and notes we use to work through the MoDaaS workshop from a laptop instead of the browser IDE.

The working copies live outside this repo, in `~/firstmate-homes/TrustworthyAI/workshop-local/`. The scripts assume that layout: `workshop-assets/`, the workshop kit synced from S3, sits next to `workshop-local/`. Run them from the working copy, not from here.

| Path | What it is |
|---|---|
| `workshop-local/README.md` | How the local environment works and how it differs from the IDE. Start here |
| `workshop-local/env.sh`, `workshop-local/shell` | Load the workshop environment (AWS profile, kubeconfig, pinned tools, kit variables) into a bash shell |
| `workshop-local/requirements.lock.txt` | Python packages pinned to match the IDE's starter kit |
| `workshop-local/scripts/findings-recheck.sh` | Read-only re-check of several platform findings against the live cluster |
| `workshop-local/scripts/pre-push-secret-scan.sh` | Read-only check run before every push: secret patterns, plus the real workshop secrets (loaded, never printed) must appear in no file |
| `workshop-local/scripts/side-entrance-probe.sh` | Probe showing a tool backend is reachable without the gateway. It **creates two pods**, so ask before running |
| `workshop-local/research/reference-agents-2026-10-05.md` | Source-cited profile of the three reference agents |
| `workshop-local/digital-twin/` | Module 10: the kit's `setup-digital-twin.sh`; shims so it runs on macOS (`shim/python3` → Python 3.9, `shim/sed` → GNU-style `-i`); `ask-feed-check.sh`; `query-tokyo-twin.py`, which queries the trained `tokyo-rf-twin` directly |

**Not copied** (large or rebuildable):
- `bin/`: kubectl 1.36.5 and Helm 3.22.0 binaries
- `.venv/`: the Python environment; rebuild it from `requirements.lock.txt`
- `maveric/`: the MAVERIC clone; `setup-digital-twin.sh` recreates it
- run logs
