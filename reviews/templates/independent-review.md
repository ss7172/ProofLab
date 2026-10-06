# Independent review (the checker is never the builder)

- PR / artifact: `<>` · reviewer (label an AI reviewer as such): `<>` · date (UTC): `<>`
- Lens: no claim beyond the evidence.

| Check | Command or file | Result | Evidence |
|---|---|---|---|
| Every claim cites a file in the pack | `<>` | `<>` | `<>` |
| Diff touches owned paths only | `git diff --stat` | `<>` | `<>` |
| Secret scan | `<>` | `<>` | `<>` |
| Gate (`tools/gate.sh --no-scan`) | `<>` | `<>` | `<>` |
| Anything found outside the PR | | | `<>` |

Verdict: `<pass / fail>`. Defects found are listed with file and line; none are fixed by the reviewer in the builder's PR.
