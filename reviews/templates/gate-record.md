# Gate record (one JSON object per line in reviews/gates.jsonl; the orchestrator appends)

Keys used by existing rows: `gate`, `pr` (merge gates), `time` (UTC, `YYYY-MM-DDTHH:MMZ`),
`builder`, `checker` (never the builder), `checks` (list of what was run and its result),
`result` (`pass`, `fail` or `merged <sha>`), `evidence` (a path or workflow id).

```json
{"gate":"merge","pr":"PR-NN","time":"<UTC>","builder":"<role>","checker":"<independent role>, verdict <pass|fail>","checks":["<command: result>"],"result":"merged <sha>","evidence":"<path or id>"}
```

Workers do not edit `gates.jsonl`; they put this content in the PR description.
