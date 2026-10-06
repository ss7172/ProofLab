"""ProofLab shared contracts (PR-01; ARCH §3.2, §4). Stdlib only, Python 3.9+. See README.md here.

Modules: record (ifabric.evidence/1 + validator), verdicts, clocks, ids (CIDs, session ids, baggage,
traceparent), register (register schema), pin (ifabric.pin/1), finding (Arth's finding_from_dict shape),
app_format (console pack-index / answer), rails_api, c16_hook, transports (ifabric.contract/1),
envelope (the run envelope ifabric.run/1), schemas (JSON Schema files generated from code).
"""
CONTRACT_VERSION = "ifabric.contract/1"
SCHEMA_ID = "ifabric.evidence/1"
