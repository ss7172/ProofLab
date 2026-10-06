"""STUB c16 core for the bundler tests (tests/bundle/stubs): NOT the real core (PR-02 owns that)."""
from __future__ import annotations

from dataclasses import dataclass

CORE_NAME = "c16_core-stub"


@dataclass(frozen=True)
class Decision:
    verdict: str
    action: str


def decide_inline(q, pin):
    return Decision("ALLOW", "proceed")
