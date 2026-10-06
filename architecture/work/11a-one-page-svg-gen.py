#!/usr/bin/env python3
"""Generate architecture/one-page.svg, phase-2 layout (self-contained, no external refs).

Every text run is measured with PIL against Helvetica Neue and Arial (the wider wins), and the
script refuses to write a file in which any line overflows the box it belongs to.
Usage: gen_v3.py <out.svg>
"""
import html
import sys

from PIL import ImageFont

OUT = sys.argv[1]
W = 1600
SANS = "Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "Menlo, Monaco, Consolas, monospace"

INK = "#1f2937"
BLUE = "#1d4ed8"
RED = "#dc2626"
DRED = "#991b1b"
GREY = "#6b7280"
DGREY = "#374151"
GREEN = "#15803d"
PURPLE = "#7c3aed"
ORANGE = "#c2410c"
AMBER = "#92400e"
TEAL = "#0f766e"
SLATE = "#334155"

HN = "/System/Library/Fonts/HelveticaNeue.ttc"
AR = "/System/Library/Fonts/Supplemental/"
FACES = {
    ("normal", "normal"): [(HN, 0), (AR + "Arial.ttf", 0)],
    ("bold", "normal"): [(HN, 1), (AR + "Arial Bold.ttf", 0)],
    ("normal", "italic"): [(HN, 2), (AR + "Arial Italic.ttf", 0)],
    ("bold", "italic"): [(HN, 3), (AR + "Arial Bold Italic.ttf", 0)],
}
_cache = {}


def measure(s, size, weight="normal", style="normal", family=SANS):
    if family == MONO:
        key = ("mono", size)
        if key not in _cache:
            _cache[key] = [ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size, index=0)]
        fonts = _cache[key]
    else:
        key = (weight, style, size)
        if key not in _cache:
            _cache[key] = [ImageFont.truetype(p, size, index=i) for p, i in FACES[(weight, style)]]
        fonts = _cache[key]
    return max(f.getlength(s) for f in fonts) * 1.03  # 3% safety margin


out = []
problems = []
MIN_SIZE = 14


def esc(s):
    return html.escape(s, quote=False)


def rect(x, y, w, h, stroke, fill, sw=2.5, dash=None, rx=12):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, s, size=14, weight="normal", fill=INK, anchor="start", style="normal", family=SANS, maxw=None):
    if size < MIN_SIZE:
        problems.append(f"size {size} < {MIN_SIZE}: {s!r}")
    if maxw is not None:
        w = measure(s, size, weight, style, family)
        if w > maxw:
            problems.append(f"overflow {w:.0f} > {maxw:.0f} px: {s!r}")
    out.append(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
               f'font-style="{style}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def arrow(points, color=INK, dash=None, width=2.5, head=True):
    path = "M" + " L".join(f"{x},{y}" for x, y in points)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#arr-{color.lstrip("#")})"' if head else ""
    out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"{d} '
               f'stroke-linecap="round" stroke-linejoin="round"{m}/>')


def chip(x_right, y, label, color):
    w = measure(label, 14, "bold") + 14
    x = x_right - w
    rect(round(x, 1), y, round(w, 1), 21, color, color, sw=1, rx=10.5)
    text(round(x + w / 2, 1), y + 15.5, label, 14, "bold", "#ffffff", "middle")
    return x - 6


LH = 19        # line height for 14 px text
TITLE_GAP = 24  # title baseline below the box top


def card(x, y, w, title, lines, stroke, fill, title_fill, chips=(), title_size=17, h=None, sw=2.5, dash=None,
         body_fill=INK):
    """A box with a title and 14 px lines. Returns (x, y, w, h)."""
    n = len(lines)
    need = TITLE_GAP + 22 + (n - 1) * LH + 14 if n else TITLE_GAP + 14
    if h is None:
        h = need
    elif h < need:
        problems.append(f"card {title!r}: height {h} < needed {need}")
    rect(x, y, w, h, stroke, fill, sw=sw, dash=dash)
    xr = x + w - 10
    for label, color in reversed(list(chips)):
        xr = chip(xr, y - 10, label, color)     # tab style: the chip sits on the top border
    text(x + 12, y + TITLE_GAP, title, title_size, "bold", title_fill, maxw=w - 24)
    for i, item in enumerate(lines):
        s, opts = (item if isinstance(item, tuple) else (item, {}))
        o = {"fill": body_fill}
        o.update(opts)
        text(x + 12, y + TITLE_GAP + 22 + i * LH, s, o.pop("size", 14), maxw=w - 24, **o)
    return x, y, w, h


def need_h(n):
    return TITLE_GAP + 22 + (n - 1) * LH + 14


# ============================================================== header
HEAD = []
out.append("")  # placeholder for <svg ...>, set at the end once the height is known
out.append("<title>ProofLab one-page architecture (team iFabric)</title>")
out.append("<desc>The live path with the one in-path question (EP-1's C16 check, answered by the c16 core "
           "embedded in each agent) and the EP-0 pre-run gate; the platform's own enforcement points; one contract "
           "with four transports; and, off the path, the control registry, the stateless evaluators (the same c16 "
           "function again at EP-2, after the run), THE ONE STORE (the platform ledger), the stitcher, the Evidence "
           "Pack, the control test and dashboard, the ServiceNow human loop (notify, then poll), the risk register, "
           "the AI inventory, the finding loop, the five habits and the three control timing layers.</desc>")
out.append("<defs>")
for c in (INK, BLUE, RED, GREY, GREEN, PURPLE, ORANGE, TEAL, AMBER, DGREY):
    out.append(f'<marker id="arr-{c.lstrip("#")}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
               f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
out.append("</defs>")
BG_INDEX = len(out)
out.append("")  # background rect placeholder

text(24, 40, "ProofLab · team iFabric · one-page architecture", 28, "bold", maxw=1552)
text(24, 72, "Only ONE question sits in the live path: the C16 check before each model call.  "
             "Before a run, EP-0 may decline to start an assessed run.", 17, "bold", RED, maxw=1552)
text(24, 98, "Claim C-FM-01: during fault resolution, the three ifabric- agents meet our declared event-recording (C7), "
             "drift (C9) and token-spend (C16) requirements.", 15, fill=DGREY, maxw=1552)

# ============================================================== live path
LP_TOP, LP_BOTTOM = 112, 550
rect(12, LP_TOP, 1576, LP_BOTTOM - LP_TOP, "#cbd5e1", "#f8fafc", sw=2, dash="8 6", rx=14)
text(24, 136, "THE LIVE PATH   (blue = our code · grey = the platform's)", 15, "bold", SLATE, maxw=900)

ROW_TOP, ROW_H = 150, 380
# --- orchestrating script
SX, SW = 24, 270
sx, sy, sw_, sh = card(SX, ROW_TOP, SW, "Orchestrating script", [
    "laptop · prooflab run · OURS",
    "mints the CID; invokes the",
    "3 agents in sequence; carries",
    "tier, C16 tally, register v + sha",
    "EP-5 handoffs: emit(), never",
    "blocks",
], BLUE, "#eff6ff", BLUE, chips=[("PRE", GREEN), ("CONT", RED)], h=268)
card(SX + 10, ROW_TOP + 152, SW - 20, "EP-0 pre-run gate (D13)", [
    ("running version = approved?", {"fill": GREEN}),
    ("may decline to START an", {"fill": GREEN, "weight": "bold"}),
    ("assessed run; inside a run,", {"fill": GREEN}),
    ("nothing waits on it", {"fill": GREEN}),
], GREEN, "#f0fdf4", GREEN, title_size=15, sw=2)

# --- agent runtime
RX, RW = 346, 622
card(RX, ROW_TOP, RW, "AgentCore Runtime (OURS): ifabric-customer → -it → -network", [], BLUE, "#eff6ff", BLUE,
     chips=[("CONT", RED)], h=ROW_H, sw=3)
text(RX + 14, ROW_TOP + 47, "nemotron-super-120b · our only code in the model-call path", 14, fill="#1e3a8a",
     maxw=RW - 28)
EP1X, EP1Y, EP1W = RX + 14, ROW_TOP + 60, 324
card(EP1X, EP1Y, EP1W, "EP-1 · THE ONE IN-PATH QUESTION", [
    "before each model call: evaluate(C16)",
    "committed + reserved + bound ≤ cap(tier)?",
    ("enforce: a DENY halts the agent's calls", {"weight": "bold"}),
    ("observe: a DENY is recorded; only the", {"weight": "bold"}),
    ("safety ceiling halts", {"weight": "bold"}),
    "the pin: a frozen register extract,",
    "set in env at deploy",
], RED, "#fef2f2", RED, title_size=16, sw=3.5)
EP1_BOTTOM = EP1Y + need_h(7)
COREX, COREW = RX + 428, 180
card(COREX, EP1Y, COREW, "c16 core", [
    "embedded in the agent",
    "(one file per agent)",
    "same sha256 as the",
    "repo's c16_core.py",
    "returns ALLOW | DENY",
    "+ the action to take",
], DRED, "#fff1f2", DRED, title_size=16, sw=3)
CORE_BOTTOM = EP1Y + need_h(6)
gap_mid = (EP1X + EP1W + COREX) / 2
arrow([(EP1X + EP1W, EP1Y + 70), (COREX - 2, EP1Y + 70)], RED, width=3.5)
text(gap_mid, EP1Y + 61, "evaluate()", 14, "bold", RED, "middle", maxw=COREX - EP1X - EP1W - 4)
text(gap_mid, EP1Y + 89, "in process", 14, fill=RED, anchor="middle", style="italic",
     maxw=COREX - EP1X - EP1W - 4)
# EP-3 / EP-4 under EP-1 (left column); the area under the core stays free for the dashed link
B_Y = EP1_BOTTOM + 10
card(EP1X, B_Y, 158, "EP-3 tool calls", ["emit() every call,", "real status 403/404"], BLUE, "#ffffff", BLUE,
     title_size=15, sw=2)
card(EP1X + 166, B_Y, 158, "EP-4 judgment", ["emit() disposition,", "evidence, reason"], BLUE, "#ffffff", BLUE,
     title_size=15, sw=2)
B_BOTTOM = B_Y + need_h(2)
text(EP1X, B_BOTTOM + 18, "emit client: async → THE ONE STORE", 14, "bold", BLUE, maxw=COREX - EP1X - 10)
text(EP1X, B_BOTTOM + 37, "start-up fails closed without keys or pin", 14, fill=GREY, style="italic",
     maxw=COREX - EP1X - 10)
RUNTIME_BOTTOM = ROW_TOP + ROW_H
assert B_BOTTOM + 37 + 8 <= RUNTIME_BOTTOM, ("runtime overflow", B_BOTTOM + 45, RUNTIME_BOTTOM)

# --- platform EPs
PX, PW = 984, 336
card(PX, ROW_TOP, PW, "Platform EPs (not ours)", [
    ("they refuse on their own; we pull", {"style": "italic", "fill": DGREY}),
    ("their decisions into the one store", {"style": "italic", "fill": DGREY}),
    ("modaas-agw (one shared key):", {"weight": "bold"}),
    "· authz: API key, fail-closed",
    "· PDP / Cedar tool policy;",
    ("   we configure 1 forbid rule (if D15)", {"weight": "bold", "fill": BLUE}),
    "· guardrails: a block logs ALLOW",
    "· ceilings: 100 req/min, 2.5M tok/h",
    "· pause → 404 (logged ALLOW)",
    "admission (CEL + VAP) · approvals",
], GREY, "#f3f4f6", DGREY, h=ROW_H)
card(PX + 12, ROW_TOP + 288, 150, "Bedrock", ["Nemotron, via", "the gateway only"], GREY, "#ffffff", DGREY,
     title_size=15, sw=2)
card(PX + 174, ROW_TOP + 288, 150, "AgentCore GW", ["→ Lambda tools,", "never touched"], GREY, "#ffffff", DGREY,
     title_size=15, sw=2)
assert ROW_TOP + 288 + need_h(2) <= ROW_TOP + ROW_H

# --- telemetry
TX, TW = 1336, 240
card(TX, ROW_TOP, TW, "Telemetry", [
    ("(platform-written)", {"style": "italic", "fill": DGREY}),
    ("aws/spans (30 d)", {"weight": "bold"}),
    "run id · action id · tokens",
    ("= the C16 figure of record", {"style": "italic"}),
    ("/modaas/evidence (30 d)", {"weight": "bold"}),
    "decision · policy version",
    "PDP + gateway pod logs",
    "AgentCore metrics → C9",
    ("aict-invocations (7 d)", {"weight": "bold"}),
    "CID + session id per invoke",
    "CR status · approvals",
    ("never judges", {"style": "italic", "fill": GREY}),
], GREY, "#f9fafb", DGREY, h=ROW_H)

# --- live-path arrows
arrow([(SX + SW, ROW_TOP + 40), (RX - 2, ROW_TOP + 40)], BLUE)
text((SX + SW + RX) / 2, ROW_TOP + 32, "×3", 14, "bold", BLUE, "middle", maxw=RX - SX - SW)
arrow([(RX + RW, ROW_TOP + 90), (PX - 2, ROW_TOP + 90)], INK)
arrow([(PX + PW, ROW_TOP + 90), (TX - 2, ROW_TOP + 90)], GREY)

# ============================================================== contract band
CB_TOP, CB_H = 562, 124
rect(12, CB_TOP, 1576, CB_H, AMBER, "#fffbeb", sw=2.5, rx=14)
text(876, CB_TOP + 24, "ONE CONTRACT · FOUR TRANSPORTS · ONE RECORD (ifabric.evidence/1)", 15, "bold", AMBER,
     maxw=TX + TW / 2 - 876 - 12)
for i, s in enumerate(["every EP reaches us the", "same way; every adapter", "writes the same record:",
                       "control · version · run ·", "actor · verdict"]):
    text(24, CB_TOP + 24 + i * 19, s, 14, fill=AMBER, style="italic", maxw=SX + SW - 24 - 6)
PILL_Y, PILL_H = CB_TOP + 40, 66


def pill(x, w, name, sub, stroke, fill):
    rect(x, PILL_Y, w, PILL_H, stroke, fill, sw=2.5, rx=33)
    text(x + w / 2, PILL_Y + 27, name, 17, "bold", stroke, "middle", maxw=w - 30)
    text(x + w / 2, PILL_Y + 50, sub, 14, anchor="middle", maxw=w - 30)


EVX, EVW = 346, 250
EMX, EMW = 616, 236
CBX, CBW = 908, 300
PUX, PUW = 1336, 240
pill(EVX, EVW, "evaluate()", "sync · in process · C16 only", RED, "#fee2e2")
pill(EMX, EMW, "emit()", "async records · never waits", BLUE, "#dbeafe")
pill(CBX, CBW, "callback()", "later verdict: notify, then poll", PURPLE, "#ede9fe")
pill(PUX, PUW, "pull()", "by run and by window", GREEN, "#dcfce7")
CB_BOTTOM = CB_TOP + CB_H

# ============================================================== governance side
G_TOP = CB_BOTTOM + 14
R1 = G_TOP + 44
R1H = need_h(9)
R2 = R1 + R1H + 40
R2H = need_h(7)
R3 = R2 + R2H + 44
R3H = need_h(9)
G_BOTTOM = R3 + R3H + 16
rect(12, G_TOP, 1576, G_BOTTOM - G_TOP, GREEN, "#f0fdf4", sw=2, dash="8 6", rx=14)
tag_w = measure("GOVERNANCE SIDE · OFF THE PATH", 14, "bold") + 20
rect(20, G_TOP + 8, round(tag_w, 1), 24, GREEN, GREEN, sw=1, rx=6)
text(30, G_TOP + 25, "GOVERNANCE SIDE · OFF THE PATH", 14, "bold", "#ffffff")
text(round(30 + tag_w + 16, 1), G_TOP + 25, "laptop hub · always async", 14, fill=GREEN, style="italic")

# --- row 1
GX1, GW1 = 24, 270      # registry / risk register / inventory column
GX2, GW2 = 338, 214     # stitcher
GX3, GW3 = 568, 238     # THE ONE STORE
GX4, GW4 = 822, 300     # evaluators / findings loop / habits
GX5, GW5 = 1202, 374    # pull adapters / ServiceNow / INV
card(GX1, R1, GW1, "Control registry", [
    "register.yaml → frozen v1, v1.1",
    "+ sha256 · the kit's flat format",
    "each control: own version + date",
    "date proof: the S3 write-once",
    "object (T1); the owner's",
    "ServiceNow approval corroborates",
    ("hands out a pinned extract;", {"weight": "bold", "fill": GREEN}),
    ("NEVER in the path", {"weight": "bold", "fill": GREEN}),
], GREEN, "#ffffff", GREEN, chips=[("PRE", GREEN)], h=R1H)
card(GX2, R1, GW2, "Stitcher", [
    "pure join, one snapshot",
    "1 CID · 2 action id",
    "3 trace id (refusals)",
    "4 handoff id",
    "5 CID + session id on",
    "   the AWS invoke record",
    "6 finding id → register",
    "7 actor → inventory",
    ("gaps = join facts", {"style": "italic"}),
], GREEN, "#ffffff", GREEN, chips=[("POST", TEAL)], h=R1H)
card(GX3, R1, GW3, "THE ONE STORE", [
    ("platform ledger audit-store", {"weight": "bold"}),
    "append-only · any JSON",
    "every decision: ours at",
    "action time; the platform's,",
    "normalized, each pointing",
    "at its raw source",
    "no update or delete route",
    ("(D16, pending captain)", {"style": "italic", "fill": GREY}),
], ORANGE, "#fff7ed", ORANGE, h=R1H, sw=3)
card(GX4, R1, GW4, "Stateless evaluators", [
    "c16 · c7 · c9: pure functions",
    "records + pinned version → verdict",
    "no I/O · no clock · no memory",
    ("c16 core: the SAME function at", {"weight": "bold"}),
    ("EP-1 (inline) and EP-2 (post-run)", {"weight": "bold"}),
    "tester: assess_run, assess_window",
    "Decision ≠ Assessment",
    "the rechecker, written separately",
], GREEN, "#ffffff", GREEN, chips=[("CONT", RED), ("POST", TEAL)], h=R1H)
card(GX5, R1, GW5, "Pull adapters (collectors)", [
    ("EP-2 aws/spans → the C16 floor, and", {"weight": "bold"}),
    ("the same c16 core per call, post-run", {"weight": "bold"}),
    "EP-6 PDP + /modaas/evidence",
    "EP-7 real outcome (BLOCKED, 404) vs ALLOW",
    "EP-8 pause · EP-10 CR status",
    "EP-11 metrics + invocations → C9",
    "EP-12 Lambda CodeSha256",
    "by run AND by window; raw stays put",
    ("→ normalized into THE ONE STORE", {"style": "italic"}),
], GREEN, "#ffffff", GREEN, chips=[("CONT", RED), ("POST", TEAL)], h=R1H)

# --- row 2
card(GX1, R2, GW1, "Risk register", [
    "risks.yaml, frozen + dated",
    "with register.yaml",
    "R-C16 · R-C7 · R-C9 + 2 of ours",
    "likelihood × severity (5×5)",
    "→ inherent; appetite → each",
    "threshold; residual; owner",
    ("decide the risk first", {"weight": "bold", "fill": GREEN}),
], GREEN, "#ffffff", GREEN, chips=[("PRE", GREEN)], h=R2H)
PACKX, PACKW = GX2, GX3 + GW3 - GX2
card(PACKX, R2, PACKW, "Evidence Pack: exports of THE ONE STORE", [
    "per run (to S3, with a MANIFEST) + the final export",
    "store records · raw captures · derived · assessments",
    "→ the versioned team bucket · MANIFEST.json (sha256)",
    ("REDACTED: no tokens · copies, never a second store", {"weight": "bold"}),
], ORANGE, "#fff7ed", ORANGE, chips=[("POST", TEAL)], h=R2H)
card(GX4, R2, GW4, "Findings → the risk loop", [
    "a failed test → a finding:",
    "deficiency in design or operation",
    "the risk is exposed: residual",
    "back to inherent",
    "fix · compensate · or accept",
    "(named approver + expiry)",
    ("closed ONLY by a passing re-test", {"weight": "bold"}),
], PURPLE, "#f5f3ff", PURPLE, chips=[("POST", TEAL)], h=R2H)
card(GX5, R2, GW5, "ServiceNow human loop (EP-13)", [
    "finding → notify() → an incident",
    "assigned to the owner (Sree)",
    "her verdict returns by callback():",
    "check polls it, or records the silence",
    ("records only; never holds work", {"weight": "bold"}),
    "AICT: discovery of our runtimes",
    ("(observed, not built)", {"style": "italic", "fill": GREY}),
], PURPLE, "#f5f3ff", PURPLE, chips=[("POST", TEAL)], h=R2H)

# --- row 3
card(GX1, R3, GW1, "AI inventory", [
    "inventory.yaml, versioned",
    "system: customer fault",
    "resolution · owner Sree",
    "risk tier: high (our 5×5 rating);",
    "EU AI Act class unverified (OC-21)",
    "agents, models, tools, prompts:",
    "owner + approved version each",
    ("joined at query time;", {"weight": "bold", "fill": GREEN}),
    ("never in the path", {"weight": "bold", "fill": GREEN}),
], GREEN, "#ffffff", GREEN, chips=[("PRE", GREEN)], h=R3H)
card(PACKX, R3, PACKW, "Control test / query tool + dashboard (offline)", [
    ("prooflab query --control C16|C7|C9", {"family": MONO}),
    ("--run <CID>  |  --window T1..T2", {"family": MONO}),
    "recomputes every verdict from the pack · exit 0/1/2",
    "under 2 minutes; every answer names who is responsible,",
    "who acted, and the decision at each EP",
    ("dashboard = static HTML: a VIEW that sees", {"weight": "bold"}),
    ("everything and refuses nothing (not an EP)", {"weight": "bold"}),
], TEAL, "#f0fdfa", TEAL, chips=[("POST", TEAL)], h=R3H)
card(GX4, R3, GW4, "Five habits", [
    "1 the telemetry store never judges",
    "2 the evaluator never remembers",
    "3 the register is never in the path",
    "4 the ledger never interprets",
    ("5 seal where made: out of scope", {"fill": GREY}),
    ("   (a MANIFEST only)", {"fill": GREY}),
], AMBER, "#fffbeb", AMBER, h=R3H)
card(GX5, R3, GW5, "INV reconciliation (optional)", [
    "AIA-INV-001.01, scheduled; built only",
    "after C16, C7 and C9",
    "pull() hourly + before assessed runs:",
    "CRs + the AICT export vs the inventory",
    "no owner · not inventoried · unapproved",
    "version → a finding, in the same loop",
], GREEN, "#ffffff", GREEN, chips=[("CONT", RED)], h=R3H)

# --- cross-band and governance arrows
# registry -> EP-1: the pinned copy, anchored on the registry box (S-01)
DASH_X = 318
arrow([(GX1 + GW1, R1 + 60), (DASH_X, R1 + 60), (DASH_X, EP1Y + 150), (EP1X - 2, EP1Y + 150)], GREEN,
      dash="7 5", width=2.5)
# script -> emit(): handoffs
BUS_Y = LP_BOTTOM - 10
SCRIPT_BOTTOM = ROW_TOP + 268
arrow([(SX + SW - 16, SCRIPT_BOTTOM), (SX + SW - 16, BUS_Y), (EMX + 30, BUS_Y), (EMX + 30, PILL_Y - 2)], BLUE)
text(SX + 6, SCRIPT_BOTTOM + 22, "the registry's pinned copy, set", 14, fill=GREEN, style="italic",
     maxw=SW - 30)
text(SX + 6, SCRIPT_BOTTOM + 41, "at deploy, before the run", 14, fill=GREEN, style="italic", maxw=SW - 30)
text(SX + 6, SCRIPT_BOTTOM + 70, "handoffs → emit()", 14, fill=BLUE, style="italic", maxw=SW - 30)
# runtime emit client -> emit()
EMIT_FROM_X = EMX + EMW - 70
arrow([(EMIT_FROM_X, RUNTIME_BOTTOM), (EMIT_FROM_X, PILL_Y - 2)], BLUE)
# emit() -> THE ONE STORE
STORE_IN_X = EMX + EMW / 2 - 40
arrow([(STORE_IN_X, PILL_Y + PILL_H), (STORE_IN_X, R1 - 2)], BLUE)
# telemetry -> pull() -> pull adapters
arrow([(TX + TW / 2, ROW_TOP + ROW_H), (TX + TW / 2, PILL_Y - 2)], GREEN)
arrow([(PUX + PUW / 2, PILL_Y + PILL_H), (PUX + PUW / 2, R1 - 2)], GREEN)
# the c16 core in the agent  - - same function - ->  the off-path evaluators
CORE_LINK_X = COREX + COREW / 2
assert EMX + EMW < CORE_LINK_X < CBX, "the same-function link must pass between the emit() and callback() pills"
assert GX4 < CORE_LINK_X < GX4 + GW4
arrow([(CORE_LINK_X, CORE_BOTTOM), (CORE_LINK_X, R1 - 2)], DGREY, dash="3 4", width=2.5)
text(CORE_LINK_X - 8, ROW_TOP + ROW_H - 46, "same function,", 14, "bold", DGREY, anchor="end", style="italic", maxw=180)
text(CORE_LINK_X - 8, ROW_TOP + ROW_H - 27, "same sha256", 14, "bold", DGREY, anchor="end", style="italic", maxw=180)
# callback() -> emit(): a later verdict becomes a record
arrow([(CBX, PILL_Y + PILL_H / 2), (EMX + EMW + 2, PILL_Y + PILL_H / 2)], PURPLE, width=2.5)
# pull adapters (EP-2) -> evaluators: the same c16, post-run
EP2_Y = R1 + 112
arrow([(GX5, EP2_Y), (GX4 + GW4 + 2, EP2_Y)], GREEN, width=2.5)
text((GX4 + GW4 + GX5) / 2 + 6, EP2_Y - 10, "EP-2", 14, "bold", GREEN, "middle", maxw=GX5 - GX4 - GW4 - 14)
text((GX4 + GW4 + GX5) / 2 + 6, EP2_Y + 22, "same c16", 14, fill=GREEN, anchor="middle", style="italic",
     maxw=GX5 - GX4 - GW4 - 14)
# pull adapters -> THE ONE STORE: normalized records, ingested between runs
ING_Y = R1 - 22
arrow([(GX5 + 24, R1), (GX5 + 24, ING_Y), (GX3 + GW3 - 30, ING_Y), (GX3 + GW3 - 30, R1 - 2)], GREEN, width=2)
text(1000, ING_Y - 6, "normalized → THE ONE STORE", 14, fill=GREEN, anchor="middle", style="italic", maxw=260)
# store -> stitcher
arrow([(GX3, R1 + 96), (GX2 + GW2 + 2, R1 + 96)], ORANGE, width=2.5)
# stitcher -> pack; store -> pack (per-run exports)
arrow([(GX2 + GW2 / 2, R1 + R1H), (GX2 + GW2 / 2, R2 - 2)], ORANGE, width=2.5)
arrow([(GX3 + GW3 / 2, R1 + R1H), (GX3 + GW3 / 2, R2 - 2)], ORANGE, width=2.5)
text(GX3 + GW3 / 2 - 8, R2 - 12, "per-run exports", 14, fill=ORANGE, anchor="end", style="italic", maxw=200)
# risk register -> registry: appetite -> thresholds
arrow([(GX1 + 150, R2), (GX1 + 150, R1 + R1H + 2)], GREEN, width=2.5)
text(GX1 + 158, R2 - 13, "appetite → thresholds", 14, fill=GREEN, style="italic", maxw=GX2 - GX1 - 160)
# inventory -> risk register
arrow([(GX1 + 90, R3), (GX1 + 90, R2 + R2H + 2)], GREEN, width=2.5)
# evaluators -> findings -> the risk loop
arrow([(GX4 + 150, R1 + R1H), (GX4 + 150, R2 - 2)], PURPLE, width=2.5)
text(GX4 + 158, R2 - 12, "findings", 14, fill=PURPLE, style="italic", maxw=120)
# the risk loop -> ServiceNow: notify()
NOTIFY_Y = R2 + 60
arrow([(GX4 + GW4, NOTIFY_Y), (GX5 - 2, NOTIFY_Y)], PURPLE, width=2.5)
text((GX4 + GW4 + GX5) / 2, NOTIFY_Y - 9, "notify()", 14, fill=PURPLE, anchor="middle", style="italic",
     maxw=GX5 - GX4 - GW4 - 4)
# ServiceNow -> callback(): the owner's verdict, polled by check
CB_LINE_X = GX4 + GW4 + 10
assert CBX < CB_LINE_X < CBX + CBW
arrow([(GX5 + 30, R2), (GX5 + 30, R2 - 26), (CB_LINE_X, R2 - 26), (CB_LINE_X, PILL_Y + PILL_H + 2)], PURPLE,
      width=2.5)
text(GX5 + 38, R2 - 8, "her verdict, polled by check", 14, fill=PURPLE, style="italic", maxw=GW5 - 40)
# the risk loop -> risk register: residual back to inherent (routed under row 2)
LOOP_Y = R2 + R2H + 18
arrow([(GX4 + 40, R2 + R2H), (GX4 + 40, LOOP_Y), (GX1 + 230, LOOP_Y), (GX1 + 230, R2 + R2H + 2)], PURPLE,
      width=2.5)
text((GX2 + GX3 + GW3) / 2, LOOP_Y - 5, "residual back to inherent", 14, fill=PURPLE, anchor="middle",
     style="italic", maxw=300)
# pack -> control test: the control test reads the pack only
arrow([(PACKX + 70, R2 + R2H), (PACKX + 70, R3 - 2)], TEAL, width=2.5)

# ============================================================== timing layers band
T_TOP = G_BOTTOM + 14
T_H = 166
rect(12, T_TOP, 1576, T_H, SLATE, "#ffffff", sw=2, rx=12)
text(24, T_TOP + 26, "CONTROL TIMING", 15, "bold", SLATE)
text(24, T_TOP + 45, "LAYERS", 15, "bold", SLATE)
text(24, T_TOP + 72, "before · while · after", 14, fill="#475569", style="italic", maxw=220)
text(24, T_TOP + 91, "it runs [slides p13]", 14, fill="#475569", style="italic", maxw=220)
cols = [
    (262, GREEN, "PRE · before it runs: may this go live?",
     ["C16 cap from the pilots; register frozen + dated (T1)",
      "C7 spec + limits frozen; C9 baseline frozen in v1.1",
      "platform: approvals, admission, Cedar, guardrails",
      "EP-0: running = approved? may decline to start"],
     "→ APPROVED · dated thresholds · the risk decided first"),
    (708, RED, "CONTINUOUS · while it runs: allowed now?",
     ["C16 inline evaluate() before each call: the ONE wait",
      "C7 records emitted as each event happens",
      "C9 near-real-time pull every few minutes:",
      "   not in the path, not claimed as the bonus"],
     "→ the continuous-compliance bonus (C16 inline only)"),
    (1154, TEAL, "POST · after it ran: did it hold T1..T2?",
     ["C16 floor over aws/spans (the figure of record)",
      "C7 coverage + gaps · C9 per run and per window",
      "finding → ServiceNow → fix → a passing re-test",
      "query --run / --window, offline from the pack"],
     "→ Axis 1 (controls complete) · the 2-minute test"),
]
for x, color, head, body, score in cols:
    rect(x, T_TOP + 10, 3, T_H - 20, color, color, sw=0, rx=1)
    text(x + 12, T_TOP + 28, head, 15, "bold", color, maxw=420)
    for i, s in enumerate(body):
        text(x + 12, T_TOP + 52 + i * LH, s, 14, maxw=420)
    text(x + 12, T_TOP + 52 + 4 * LH + 8, score, 14, "bold", SLATE, style="italic", maxw=420)

# ============================================================== strips + legend
S_TOP = T_TOP + T_H + 14
S_H = 192
rect(12, S_TOP, 520, S_H, "#475569", "#f8fafc", sw=1.5, rx=10)
text(24, S_TOP + 26, "Five control modes → transport", 15, "bold", maxw=496)
modes = [("In transaction · C16 inline → evaluate()", "built"),
         ("Event driven · C7 → emit() (+ pull)", "built"),
         ("Continuous · C9 → pull() + alerts", "built"),
         ("Scheduled · INV + hourly pulls → pull()", "INV optional"),
         ("Static · register review → pull()", "drawn only")]
for i, (a, b) in enumerate(modes):
    y = S_TOP + 54 + i * 26
    text(24, y, a, 14, maxw=372)
    text(404, y, b, 14, "bold", GREEN if b == "built" else GREY, maxw=124)

rect(544, S_TOP, 610, S_H, "#475569", "#f8fafc", sw=1.5, rx=10)
text(556, S_TOP + 26, "Every kind of EP (slide 14) → transport", 15, "bold", maxw=586)
kinds = [("SDK interceptor in the process · EP-1 → evaluate()", "built"),
         ("Managed gateway, read its log · EP-2/6/7 → pull()", "built"),
         ("Human approval queue · EP-13 → callback()", "refuses nothing"),
         ("Scheduled batch job · EP-2 post-run → pull()", "built"),
         ("Third-party SaaS · ServiceNow check → pull()", "built"),
         ("Third-party SaaS · AICT → pull()", "observed"),
         ("Kill switch, out of band · EP-8 → emit + pull", "records only")]
for i, (a, b) in enumerate(kinds):
    y = S_TOP + 50 + i * 20.5
    text(556, y, a, 14, maxw=440)
    text(1004, y, b, 14, "bold", GREEN if b == "built" else GREY, maxw=146)

LX = 1166
rect(LX, S_TOP, 1588 - LX, S_H, "#475569", "#f8fafc", sw=1.5, rx=10)
text(LX + 12, S_TOP + 26, "Legend", 15, "bold")
legend_a = [(RED, "#fef2f2", None, "waits: the ONE question"),
            (BLUE, "#eff6ff", None, "our code: records"),
            (GREY, "#f3f4f6", None, "the platform's"),
            (GREEN, "#f0fdf4", "4 3", "off the path, async"),
            (PURPLE, "#f5f3ff", None, "the human loop"),
            (ORANGE, "#fff7ed", None, "the one store + exports")]
legend_b = [(TEAL, "#f0fdfa", None, "the control test"),
            (AMBER, "#fffbeb", None, "contract · habits")]
for i, (stroke, fill, dash, label) in enumerate(legend_a):
    y = S_TOP + 42 + i * 24
    rect(LX + 12, y, 22, 14, stroke, fill, sw=2, dash=dash, rx=3)
    text(LX + 42, y + 12, label, 14, maxw=170)
LBX = LX + 222
for i, (stroke, fill, dash, label) in enumerate(legend_b):
    y = S_TOP + 42 + i * 24
    rect(LBX, y, 22, 14, stroke, fill, sw=2, dash=dash, rx=3)
    text(LBX + 30, y + 12, label, 14, maxw=1588 - LBX - 38)
y = S_TOP + 42 + 2 * 24
xx = chip(LBX + 44, y - 3, "PRE", GREEN)
text(LBX + 52, y + 12, "· CONT · POST", 14, maxw=1588 - LBX - 60)
y += 24
arrow([(LBX, y + 7), (LBX + 24, y + 7)], GREEN, dash="5 4", width=2)
text(LBX + 30, y + 12, "pinned before run", 14, maxw=1588 - LBX - 38)
y += 24
arrow([(LBX, y + 7), (LBX + 24, y + 7)], DGREY, dash="3 4", width=2)
text(LBX + 30, y + 12, "same function", 14, maxw=1588 - LBX - 38)
y += 24
arrow([(LBX, y + 7), (LBX + 24, y + 7)], RED, width=3)
text(LBX + 30, y + 12, "the one wait", 14, maxw=1588 - LBX - 38)

H = S_TOP + S_H + 14
out[0] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
          f'role="img" aria-label="ProofLab one-page architecture, team iFabric">')
out[BG_INDEX] = f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>'
out.append("</svg>")

if problems:
    print("REFUSED: layout problems:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(o for o in out if o) + "\n")
print("wrote", OUT, f"{W}x{H}", "text runs:", sum(1 for o in out if o.startswith("<text")))
