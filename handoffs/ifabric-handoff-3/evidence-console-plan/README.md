# ProofLab Evidence Console: design, build and integration plan (team iFabric)

**Start here.** This folder is the complete plan for the presentation dashboard: the **ProofLab Evidence Console**. It covers:
- what the judges will score, and which screen proves each criterion;
- the architecture (security, **auditability**, zero trust);
- the data contracts between the AWS-side pipeline and the console;
- what the teammate must build on the AWS side (controls, adapters, agents, logs → evidence);
- the ServiceNow + Nemotron Assurance Agent and its GUI: `08-…` is the **single source of truth** (the former "handoff 2" v3 is merged into it in full);
- the build order with hour budgets and acceptance tests;
- a working **HTML demo** and the **judging-day presentation guide**.

> **The design in one line:** the console *sees everything and can refuse nothing*. It turns the sealed Evidence Pack into answers a sceptical stranger can check in seconds, without us narrating. Every number on screen links to the raw record it came from, and every action it asks for is itself recorded as evidence.

---

## Reading order

| # | File | For | Read when |
|---|---|---|---|
| 0 | **this README** | everyone | now |
| 1 | `01-JUDGING-CRITERIA.md` | everyone | every judging criterion (slides, AWS deck, playbook) → console screen → backend artefact → owner → priority |
| 2 | `02-ARCHITECTURE.md` | teammate + coding agent | system view, enforcement points stated honestly, zero trust (NIST 800-207 mapping), auditability, **§9 corrections to the playbook** |
| 3 | `03-CONTRACTS.md` + `schemas/contracts.schema.json` + `examples/` | coding agent | the integration surface; build against the fixtures |
| 4 | `04-LOGS-TO-EVIDENCE.md` | **teammate, today** | how raw logs become evidence a stranger can check (capture → facts → bound records), per surface, with redaction |
| 5 | `05-AWS-SIDE-BUILD.md` | **teammate, today** | what to build or fix on AWS so the console has something true to show: register, C16/C7/C9, orchestrator, **agent decision records (movement, decision trace, evidence, policy alignment, outcome validation)**, adversarial cases |
| 6 | `06-UI-UX-SPEC.md` | coding agent | design system, every screen, interactions, the query grammar |
| 7 | `07-CONSOLE-API-AND-SECURITY.md` | coding agent | backend endpoints, auth, headers, actuator (operator mode) |
| 8 | `08-SERVICENOW-AND-ASSURANCE-AGENT.md` | teammate + coding agent | human loop, AICT, the Nemotron Assurance Agent (deploy, wire, display) |
| 9 | `09-BUILD-ORDER-AND-ACCEPTANCE.md` | everyone | tracks, hour budgets, cut order, acceptance tests AT-01…AT-19 |
| ▶ | `demo/index.html` | everyone | open in a browser: what the finished console looks like (synthetic data) |
| ▶ | `presentation/JUDGING-DAY-GUIDE.html` | presenters | how to run the 15-minute slot: every use case, every bonus, what to emphasize |

---

## What to give the teammate's coding agent

Paste this as its first instruction:

> Read `evidence-console-plan/README.md`, then `09-BUILD-ORDER-AND-ACCEPTANCE.md`, `03-CONTRACTS.md`, `06-UI-UX-SPEC.md` and `07-CONSOLE-API-AND-SECURITY.md`. Install the two design skills in §3 of file 09. Build **Track B P0** against `evidence-console-plan/examples/` (validate with `schemas/contracts.schema.json`), copying tokens and components from `demo/index.html`. Write tests first. Standard-library Python only at runtime; no CDN or framework in the console. Stop after P0 and run acceptance tests AT-01…AT-12 + AT-14 before anything else. Never put a secret, token or presigned URL in code, files, logs or the browser. Never show model reasoning.

For the AWS work (Track A), point it at `05-AWS-SIDE-BUILD.md` and `04-LOGS-TO-EVIDENCE.md` (plus `HACKATHON_WINNING_PLAYBOOK.md`, read with `02-ARCHITECTURE.md` §9's corrections).

---

## Status (2026-10-05)

| Item | State |
|---|---|
| Judging criteria extraction + traceability (58 criteria) | ✅ done |
| Architecture, zero trust, auditability, EP options | ✅ done |
| Contracts: 1 schema file, 14 synthetic fixtures (the demo's ServiceNow cases are built from the same story by the real prooflab checks: `demo/assurance-panel/make_cases.py`), generator; **111 instances validate, 0 errors** | ✅ done |
| Build order + acceptance tests | ✅ done |
| AWS-side build guide, logs → evidence guide | ✅ in this folder |
| UI/UX spec, console API + security | ✅ in this folder |
| ServiceNow + Assurance Agent + its GUI: **`08-…` is the single source of truth** (handoff 2 v3 merged in full, same section numbers; the old file is archived under `archive/`) | ✅ |
| HTML demo + presentation guide | ✅ in this folder |
| **Nothing in this folder is a real result.** All data is `provenance: SYNTHETIC`; every threshold value is ILLUSTRATIVE and must come from the team's own exploratory runs. | ⚠️ by design |

## Design skills used (install the same ones in the coding agent's environment)
```bash
npx -y skills@latest add https://github.com/dammyjay93/interface-design --skill interface-design -g -a claude-code -y
npx -y skills@latest add https://github.com/nextlevelbuilder/ui-ux-pro-max-skill --skill ui-ux-pro-max -g -a claude-code -y
```
- **interface-design** (≈28.6K installs): craft-first dashboards; domain exploration, signature element, rejected defaults.
- **ui-ux-pro-max** (≈384K installs): searchable UX, chart and accessibility rules.

Both passed the skills.sh security audits (Gen Agent Trust Hub, Socket, Snyk). Their scripts were checked: no network or subprocess calls. They install into the **coding agent's** machine; the workshop IDE does not need Node.
