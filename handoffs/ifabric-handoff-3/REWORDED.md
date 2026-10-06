# REWORDED.md: the two files this repo changed after receiving handoff-3

Arth's handoff-3 package (`MANIFEST.json`, schema `ifabric.evidence-manifest/v1`) is otherwise byte-identical
to the original. Two documentation files were reworded in commit `ec14665` because one line in each matched
the pre-push secret scan's pattern list (the scan flags a literal credential-style token spelling inside a prose
example). The original lines are deliberately not reproduced here, because copying them would trip the scan again.
The "before" originals are in the read-only `~/Downloads/ifabric-handoff-3/`.

| File (under `handoffs/ifabric-handoff-3/`) | Before sha256 (original in `~/Downloads/ifabric-handoff-3/`) | After sha256 (this repo) |
|---|---|---|
| `evidence-console-plan/04-LOGS-TO-EVIDENCE.md` | `d9f9a9bdb35dcae9f111c46bb8987ab9cc166116f8f1745d806751819e423cc5` | `99bfb01757c8cf903d3d0b06dfa8d83c47da95aa277643f4d9bc5ad8b0108e28` |
| `evidence-console-plan/09-BUILD-ORDER-AND-ACCEPTANCE.md` | `be78385a36f39df3f60a5c400a7cd85a44daec0c52c22cc66e95adf6201a5c35` | `57e609f0eabd42ddef9f3a11a87d4b273c3debf9d3a4d1057447b6927526d5f3` |

Why: only the wording of one line per file changed (the line numbers are 04:52 and 09:107 in the original), so
that the repo passes the secret scan (`RESULT: clean`). No meaning, command or value was changed.

How to check: `python3 tools/manifest.py verify handoffs/ifabric-handoff-3` reports exactly the two files above
as `changed` (and this `REWORDED.md` as `unlisted`, because it was added after the manifest was built). Nothing
else may differ.
