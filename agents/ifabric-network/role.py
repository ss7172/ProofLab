"""ifabric-network: the role source of one ifabric- agent (ARCH 7.1). tools/bundle_agent.py appends it,
as the __main__ part, to agents/ifabric-network/ifabric-network.py (two-stage, D-B: after the role loader, which
loads the ifabric-base file holding the c16 core; then the remaining adapters and ifabric_app; never prooflab/contract). Tool: network-twin (dependsOn.tools).
Judgment targets (handoff 3b Q8): S1 auto-resolve; S2 gather-evidence with a reversible step; S3 escalate.
"""
import ifabric_app

SPEC = {
    "role": "network",
    "name": "ifabric-network",
    "tool_alias": "network-twin",
    "proposes": True,   # its answer carries the structured proposal the script relays on Gateway C
    "prompt": ('/no_think You are a telecom Network Resolution agent (ifabric-network). Use your network-twin tool to predict signal quality (predict_rsrp) for the fault site, then state in 3 short bullet points: the probable root cause, your proposed resolution, and the risk of the change. If the twin returns no data for the site, do not guess: ask for the evidence that would settle it. Be factual and brief. In your JSON also give "proposed_action" (the change you propose) and "change_risk" (low, medium or high, and why).'),
}

app = ifabric_app.build(SPEC)

if __name__ == "__main__":
    ifabric_app.main(app)
