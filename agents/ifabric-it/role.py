"""ifabric-it: the role source of one ifabric- agent (ARCH 7.1). tools/bundle_agent.py appends it,
as the __main__ part, to agents/ifabric-it/ifabric-it.py after the embedded modules (the c16 core,
the runtime adapters and the shared ifabric_app; never prooflab/contract). Tool: runbook-lookup (dependsOn.tools).
Judgment targets (handoff 3b Q8): S1 auto-resolve; S2 gather-evidence with a reversible step; S3 escalate.
"""
import ifabric_app

SPEC = {
    "role": "it",
    "name": "ifabric-it",
    "tool_alias": "runbook-lookup",
    "prompt": ('/no_think You are a telecom IT Resolution agent (ifabric-it). Use your runbook-lookup tool to find the incident and its runbook, then state in 3 short bullet points: the incident disposition, the action you take per the runbook, and what you need from the network team. Check the change constraints: a maintenance freeze or a restricted change means you escalate. Be factual and brief.'),
}

app = ifabric_app.build(SPEC)

if __name__ == "__main__":
    ifabric_app.main(app)
