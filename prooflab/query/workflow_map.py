"""Where each register `workflow_events` name is expected in one run (C7's E, ARCH 5.2 / 7.2). Stdlib, Python 3.9.

The register is the source of the event NAMES; this module is the one place that says WHERE each is expected. The
run's invocations come from the orchestrating script's own records (EP-5, not a graded agent): one per
`handoff.sent` (h1, h2, h3: Gateway A customer -> IT, Gateway B IT -> network, Gateway C network -> IT), plus the
first invocation h0 that no handoff precedes.

  run.started, run.finished    the orchestrator, once per run
  handoff.sent                 the orchestrator, once per handoff (hN, N >= 1)
  handoff.received             the orchestrator, once per invocation (h0 included: the script records every return)
  negotiation                  the IT agent, on the Gateway C invocation only (handoff from the network to IT)
  every other name             the invoked agent, once per invocation (invocation.received, intent, judgment, ...)
  escalation, decision         never here: conditional (escalate disposition) / per model call (ep1_deployed)

Agent events carry `at` = the invocation (hN), so C7 keys them "<agent>|<event>@<hN>" (c7.workflow_key): the IT
agent's two invocations (the trio step h1 and Gateway C h3) are expected, and missed, separately. Orchestrator
events sit in no gap stream (they span whole invocations); each invocation is one stream, in emission order.
"""
from __future__ import annotations

ORCHESTRATOR = "orchestrator"
RUN_EVENTS = ("run.started", "run.finished")
SENT, RECEIVED = "handoff.sent", "handoff.received"
NEGOTIATION = "negotiation"
CONDITIONAL_EVENTS = ("escalation", "decision")
# The order the app emits an invocation's events in (ifabric_app: received, intent, [negotiation], judgment).
INVOCATION_ORDER = ("invocation.received", "intent", NEGOTIATION, "judgment")
# Gateway C (ARCH 7.2; prooflab/adapters/orchestrator/run.py GATEWAY_C_FROM / GATEWAY_C_TO, pinned by a test).
GATEWAY_C_FROM, GATEWAY_C_TO = "ifabric-network", "ifabric-it"
OURS_PREFIX = "ifabric-"


def names_of(entry):
    """The register entry's workflow_events, in register order, minus the conditional ones."""
    return [x.strip() for x in (entry.get("workflow_events") or "").split(",")
            if x.strip() and x.strip() not in CONDITIONAL_EVENTS]


def _hn(handoff_id):
    return str(handoff_id).rsplit(":", 1)[-1] if handoff_id else "h0"


def _n(hn):
    try:
        return int(hn[1:])
    except ValueError:
        return 10 ** 6


def invocations(recs):
    """[{"at": "hN", "agent": str | None, "gateway_c": bool}] in run order, from the script's EP-5 records."""
    ours = [r for r in recs or () if r.get("authorship", "TESTIMONY") == "TESTIMONY"]
    orch = [r for r in ours if r.get("actor.id") == ORCHESTRATOR]
    sends, seen = [], set()
    for r in orch:
        if r.get("phase") == SENT and r.get("handoff.id") and _hn(r["handoff.id"]) not in seen:
            seen.add(_hn(r["handoff.id"]))
            sends.append(r)
    sends.sort(key=lambda r: _n(_hn(r["handoff.id"])))

    def is_c(r):
        return r.get("handoff.from") == GATEWAY_C_FROM and r.get("handoff.to") == GATEWAY_C_TO

    h0 = None
    if sends and not is_c(sends[0]) and _hn(sends[0]["handoff.id"]) == "h1":
        h0 = sends[0].get("handoff.from")
    if h0 is None or not str(h0).startswith(OURS_PREFIX):
        h0 = next((r["actor.id"] for r in ours if str(r.get("actor.id") or "").startswith(OURS_PREFIX)
                   and not r.get("handoff.id")), None)
    out = []
    if h0 is not None or any(r.get("phase") == RECEIVED and not r.get("handoff.id") for r in orch):
        out.append({"at": "h0", "agent": h0, "gateway_c": False})
    out += [{"at": _hn(r["handoff.id"]), "agent": r.get("handoff.to"), "gateway_c": is_c(r)} for r in sends]
    return out


def expected(names, recs):
    """C7 workflow expectations {agent, event, stream, order, at} for one run's records."""
    names = [n for n in names if n not in CONDITIONAL_EVENTS]
    invs = invocations(recs)
    out = []
    for ev in names:
        if ev in RUN_EVENTS:
            out.append({"agent": ORCHESTRATOR, "event": ev, "stream": None, "order": None, "at": None})
        elif ev == SENT:
            out += [{"agent": ORCHESTRATOR, "event": ev, "stream": None, "order": None, "at": i["at"]}
                    for i in invs if i["at"] != "h0"]
        elif ev == RECEIVED:
            out += [{"agent": ORCHESTRATOR, "event": ev, "stream": None, "order": None, "at": i["at"]} for i in invs]
    agent_names = [n for n in names if n not in RUN_EVENTS + (SENT, RECEIVED)]
    rank = dict((n, k) for k, n in enumerate(INVOCATION_ORDER))
    agent_names.sort(key=lambda n: (rank.get(n, len(INVOCATION_ORDER)), names.index(n)))
    for i in invs:
        if not i["agent"]:
            continue
        stream = "%s:%s" % (i["agent"], i["at"])
        evs = [n for n in agent_names if n != NEGOTIATION or i["gateway_c"]]
        out += [{"agent": i["agent"], "event": ev, "stream": stream, "order": k, "at": i["at"]}
                for k, ev in enumerate(evs)]
    return out
