# 07 · Console backend: API, zero-trust controls, actuator

**Build target:** `prooflab/console/server.py`. It uses Python stdlib only (`http.server.ThreadingHTTPServer`, `hashlib`, `secrets`, `hmac`, `json`), extending the posture already proven in `prooflab/servicenow/serve.py`: loopback-only, Host check, CSP, read-only.

## 1. Process
```bash
python3 -m prooflab console --pack evidence/                 # PACK mode (judges): sealed pack, read-only, Replay instead of Live
python3 -m prooflab console --pack evidence/ --live          # LIVE mode: also tails live/events.jsonl (real-time monitor)
python3 -m prooflab console --pack evidence/ --live --operator   # P2: shows the Control Room (requests to the actuator)
```
- Binds `127.0.0.1` only (refuses any other host, like `serve.py`). Default port 8787.
- On start, it:
  1. verifies `MANIFEST.json` (status → integrity badge);
  2. loads `pack-index.json` (the allow-list);
  3. prints a **one-time URL** `http://127.0.0.1:8787/#k=<32-byte token>`.
- The token is exchanged once for a session cookie (`HttpOnly; SameSite=Strict; Path=/; Max-Age=28800`) and then invalidated.
- The process holds **no** AWS, ServiceNow or gateway secret, and never opens a network connection except its own listening socket.

## 2. Endpoints (JSON envelope `{"ok": bool, "data": …, "error": {"code","message"} | null, "meta": {…}}`)

| Method + path | Returns | Notes |
|---|---|---|
| `POST /api/v1/session` | sets the cookie | Body `{"token": …}` from the one-time URL; single use; constant-time compare |
| `GET /api/v1/pack` | `ifabric.pack-index/v1` | The console's table of contents |
| `GET /api/v1/ask?q=<text>` | `ifabric.answer/v1` | Parses with the deterministic grammar (`prooflab/query/grammar.py`) and runs the query engine **on the pack**; logs `{q, normalized, answer_id, elapsed_ms}` to `session/queries.jsonl` |
| `GET /api/v1/answer?control=16&run=FM-B` · `&from=…&to=…` · `&window=…` | `ifabric.answer/v1` | Same engine, structured form |
| `GET /api/v1/auditor/<incident-or-run>` | `ifabric.auditor/v1` | |
| `GET /api/v1/runs/<alias-or-cid>` | `ifabric.run/v1` | journey, decisions, outcome, lane |
| `GET /api/v1/records?control=&run=&actor=&verdict=&provenance=&cursor=` | page of `ifabric.evidence/v1` | 200 per page, cursor-based |
| `GET /api/v1/raw?ref=raw:<path>#L<n>` | `{line, sha256, capture}` | **Only refs listed in MANIFEST/pack-index**; returns the line, its sha256 and the capture sidecar |
| `GET /api/v1/cases` | `[ifabric.servicenow.case/v1]` | Only the snapshots listed in pack-index `cases[]` (path and sha256 checked; written by the loop, `08-…` §7.1). Unknown keys pass through unchanged |
| `GET /api/v1/integrity` | `{status, changed[], missing[], unlisted[], verified_at, submission}` | Re-verifies on request (cached 60 s) |
| `GET /api/v1/live/stream` *(LIVE)* | `text/event-stream` | Tails `live/events.jsonl` from a `Last-Event-ID` offset; heartbeat every 5 s; one connection per session |
| `GET /api/v1/live/snapshot?since=<offset>` *(LIVE)* | `{events[], offset, streams{lag_s}}` | Polling fallback (every 2 s) |
| `GET /api/v1/replay/<alias>` *(PACK)* | the recorded `live/events.jsonl` slice for that run | The Replay view plays it locally; labelled REPLAY |
| `GET /api/v1/session/queries` | the session ledger | "Every answer we showed you, with its `answer_id`" |
| `POST /api/v1/actions` *(operator, P2)* | `ifabric.console-action/v1` (REQUESTED) | Writes `control/requests/<uuid>.json` only |
| `GET /api/v1/actions` *(operator, P2)* | action records | From `evidence/console/actions.jsonl` |

Everything else → 404. In PACK mode every non-GET → 405, except `POST /api/v1/session`.

## 3. Zero-trust controls (each one is a test)

| Control | Implementation | Test |
|---|---|---|
| Loopback only | `make_server` refuses non-loopback hosts | `test_refuses_public_bind` |
| Host allow-list (anti DNS-rebinding) | `Host` must be `127.0.0.1:<port>` or `localhost:<port>`, else 403 | AT-08 |
| Authentication | Every `/api/*` needs the session cookie (401 otherwise); static assets are public but contain no data | AT-08 |
| CSRF | Non-GET requires `Origin` = our origin **and** header `X-CSRF-Token` = the session's token (double-submit, `hmac.compare_digest`) | `test_csrf_rejected` |
| Authorization | Role is `viewer`, or `operator` (only with `--operator`); action endpoints check role + mode | `test_actions_need_operator` |
| Path allow-list | `raw`/file reads resolve **only** refs present in MANIFEST/pack-index, normalized under the pack root; no `..`, no symlinks, size cap 2 MB | `test_path_traversal`, AT-04 |
| Output safety | JSON only, `Content-Type` set, `ensure_ascii=False`; the UI renders with `textContent` | AT-09 |
| Headers | `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'` · `X-Content-Type-Options: nosniff` · `Referrer-Policy: no-referrer` · `Cross-Origin-Opener-Policy: same-origin` · `Cross-Origin-Resource-Policy: same-origin` · `Permissions-Policy: camera=(), microphone=(), geolocation=(), usb=()` · `Cache-Control: no-store` on `/api/*` | AT-07 |
| Rate limiting | Per session: 20 req/s for GET, 1 req/5 s for actions; 429 with `Retry-After` | `test_rate_limit` |
| Request limits | Body ≤ 16 KB; query string ≤ 2 KB; 10 s handler timeout | `test_limits` |
| Integrity gating | MANIFEST status ≠ VERIFIED → every answer gets `source.manifest_status`, and the UI shows PACK MODIFIED | AT-05 |
| No secrets | The server env has none; a startup self-check refuses to start if `SNOW_CLIENT_SECRET`, `MODAAS_API_KEY`, `AWS_SECRET_ACCESS_KEY` or `AUDIT_WRITE_TOKEN` is set in its environment ("run the console in a clean shell") | AT-06, `test_refuses_secret_env` |
| Logging | Access log without query values for `/raw` and without cookies; session ledger of queries; nothing from evidence is logged | review |

## 4. The actuator (P2): how "controlling capabilities" stay zero-trust
`python3 -m prooflab actuator` runs in the **operator's authenticated shell**, which holds the needed credentials. It polls `control/requests/` every second.

| Kind | Fixed argv | Shared impact → dual control? |
|---|---|---|
| `RUN_CONTROLTEST` | `python3 -m prooflab controltest <16\|7\|9> --run <alias> --pack evidence/` | no |
| `SERVICENOW_CHECK` | `python3 -m prooflab.servicenow check --finding <file> --cutoff <c>` | no |
| `PACK_SEAL` | `python3 tools/manifest.py build evidence` | no |
| `PACK_SUBMIT` | `bash ~/starter/submit.sh <team>` then readback | yes (second operator) |
| `RUN_SCENARIO` | `ifabric-run --scenario <S1\|S2\|S3> --mode <ENFORCE\|OBSERVE>` (refused if account headroom is below the configured margin) | yes |
| `KILL_SWITCH_DRILL` | `kubectl patch toolconfig <team-owned> --type merge -p '{"spec":{"paused":true}}'` (+ timed resume) | yes; team-owned assets only |

Every request:
1. is validated against `#/$defs/consoleAction` and an allow-list of parameter values (aliases from pack-index, scenarios S1–S3);
2. runs with **argv, never a shell string**;
3. records `requested_at`, `effective_at`, `finished_at`, `exit_code` and output refs.

Every transition is appended to `evidence/console/actions.jsonl` (fsync'd, like `delivery_log.py`). Dual control: the request waits (up to 120 s) for `approved_by` from a different operator session. Silence means REFUSED, never "approved by timeout".

## 5. Performance budgets
- `ask` on the pack: < 500 ms. Pre-index records by run and control at startup.
- Live event to screen: ≤ 5 s end to end (AT-20).
- Startup with MANIFEST verify of ~300 files: < 3 s.

## 6. Tests to write first (`prooflab/tests/test_console_*.py`)
Each of these runs against the `examples/` fixtures and a temporary pack copy:
- bind refusal;
- Host check;
- auth (401 without a cookie);
- one-time token reuse is rejected;
- CSRF;
- PACK mode 405;
- path traversal;
- raw ref not in the MANIFEST → 404;
- secret-env refusal;
- integrity flag when a file is changed;
- deterministic `answer_id`;
- grammar coverage (all phrases in `06-…` §6);
- the SSE heartbeat;
- the snapshot offset;
- `/api/v1/cases` serves only listed snapshots, refuses one whose sha256 changed, and passes unknown keys through;
- rate limit.
