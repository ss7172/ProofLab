"""Append-only JSONL record of every human-loop step (part of the Evidence Pack).

States written by the notifier:
  INTENT, DRY_RUN, SENT, OUTCOME_UNKNOWN, DELIVERED, FAILED,
  RESPONDED, AWAITING_RESPONSE, NO_RESPONSE_OBSERVED, RESPONSE_UNKNOWN, NOT_DELIVERED
Entries are never rewritten; a later state supersedes an earlier one.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Union


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DeliveryLog:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)

    def append(self, finding_id: str, state: str, **details) -> dict:
        entry = {"ts": utc_now_iso(), "finding_id": finding_id, "state": state, **details}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return entry

    def history(self, finding_id: str) -> List[dict]:
        if not self.path.exists():
            return []
        entries = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # torn write (e.g. crash mid-append); earlier entries stay valid
                if entry.get("finding_id") == finding_id:
                    entries.append(entry)
        return entries
