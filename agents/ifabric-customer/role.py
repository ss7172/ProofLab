"""ifabric-customer: the role source of one ifabric- agent (ARCH 7.1). tools/bundle_agent.py appends it,
as the __main__ part, to agents/ifabric-customer/ifabric-customer.py after the embedded modules (the c16 core,
the runtime adapters and the shared ifabric_app; never prooflab/contract). Tool: customer-records (dependsOn.tools).
Judgment targets (handoff 3b Q8): S1 auto-resolve; S2 gather-evidence with a reversible step; S3 escalate.
"""
import ifabric_app

SPEC = {
    "role": "customer",
    "name": "ifabric-customer",
    "tool_alias": "customer-records",
    "prompt": ('/no_think You are a telecom Customer Experience agent (ifabric-customer). Use your customer-records tool to look up the customers impacted at the fault site, then summarize in 3 short bullet points: which customers are impacted, how, and what to tell them. Be factual and brief.'),
}

app = ifabric_app.build(SPEC)

if __name__ == "__main__":
    ifabric_app.main(app)
