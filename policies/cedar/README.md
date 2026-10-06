# customer-records Cedar texts (PR-24, SP-1, D15/DG-4)

- `customer-records.original.cedar`: the verbatim current policy (261 bytes), read-only from the ToolConfig
  `spec.access.cedarPolicy` by the ops lane (B1 read). Not invented or fetched by this PR.
- `customer-records.forbid-site-adv.cedar`: the original plus one additive, narrow `forbid` on the declared test value
  `SITE-ADV-*` (every attribute access `has`-guarded; `like` is case-sensitive, so it is a test rule, not a protection).
- `customer-records.restore.cedar`: byte-identical to the original.
- `SHA256SUMS`: check with `cd policies/cedar && shasum -a 256 -c SHA256SUMS`.

Order (ops lane only, with the captain's OK at Hold-1): apply `forbid-site-adv` (ToolConfig version 2), then poll both PDP
replicas for the new ConfigMap `modaas-system/modaas-toolconfig-customer-records` resourceVersion (the PDP reloads about every
10 min; poll up to 11 min). Keep through judging, then apply `restore` and record it as version 3.

Offline Cedar parse (cedarpy) is NOT run here (an install needs the captain's OK): pending for the orchestrator.
