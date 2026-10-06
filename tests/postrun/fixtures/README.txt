SYNTHETIC fixtures for PR-23 (EP-2 replay). Derived, never raw copies, from the read-only snapshot
workshop-local/evidence-snapshots/20261005T173727Z/gateway-*.log (llm lines of two reference runs):
  spans_n2_observe_breach.json  first 40 llm calls of run fault-1791177342-d3f892 (an S2-like runaway)
  spans_n3_enforce_halt.json    first 9 llm calls of run fault-1791177843-fde682
Real token counts and gateway timings; run ids and action ids relabelled (ifabric-test-..., act-N2-0001);
span rows in the aws/spans Logs Insights shape (dotted attributes.* keys, nanosecond times, strings).
pin_*.json are hand-written synthetic ifabric.pin/1 files (caps and ceiling are test values, not the register's).
