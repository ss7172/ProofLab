# Named runs (template)

Written BEFORE judging; never edited afterwards (append a dated correction instead). Companion to
`run-ids.txt`, which holds one correlation id per line and **no pilot or baseline id**.

Written at (UTC): `<YYYY-MM-DDTHH:MM:SSZ>` · Declared event window (UTC): `<WINDOW_START>` to `<WINDOW_END>`

Rule: list **every attempt** of a named run, including a failed or repeated one, with its reason.
A run that is dropped from the list stays in the table, marked `NOT COUNTED` with the cause.

| control | role (PASS / BREACH / RE-TEST / ESC) | attempt | run id (CID) | start (UTC) | end (UTC) | register version | control version | mode (enforce / observe) | condition or fault | incident (INC) | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C16 | PASS | 1 | `<CID>` | `<...>` | `<...>` | `<v>` | `<C16-v>` | `<mode>` | `<none>` | `<n/a>` | `<...>` |
| C16 | BREACH | 1 | `<CID>` | `<...>` | `<...>` | `<v>` | `<C16-v>` | `<mode>` | `<condition>` | `<INC...>` | `<...>` |
| C16 | RE-TEST | 1 | `<CID>` | `<...>` | `<...>` | `<v>` | `<C16-v>` | `<mode>` | `<same as the breach>` | `<...>` | `<...>` |
| C7 | PASS | 1 | `<CID>` | `<...>` | `<...>` | `<v>` | `<C7-v>` | `<mode>` | `<none>` | `<n/a>` | `<...>` |
| C7 | BREACH | 1 | `<CID>` | `<...>` | `<...>` | `<v>` | `<C7-v>` | `<mode>` | `<declared fault>` | `<INC...>` | `<...>` |
| C9 | PASS | 1 | `<window id>` | `<...>` | `<...>` | `<v>` | `<C9-v>` | `<mode>` | `<none>` | `<n/a>` | `<...>` |
| C9 | BREACH | 1 | `<window id>` | `<...>` | `<...>` | `<v>` | `<C9-v>` | `<mode>` | `<declared treatment>` | `<INC...>` | `<crossing>` |
| ESC | ESC | 1 | `<CID>` | `<...>` | `<...>` | `<v>` | `<n/a>` | `<mode>` | `<none>` | `<INC...>` | `<...>` |

Corrections (dated, appended below; never edit a row above):

- `<YYYY-MM-DDTHH:MM:SSZ> <what was wrong, the correct value, why>`
