"""STUB c16 core for the bundler tests (tests/bundle/stubs): NOT the real core (PR-02 owns that).
Signature-compatible with the names ifabric_app uses: PinnedC16.from_env, decide_inline."""
from __future__ import annotations

import json
from dataclasses import dataclass

CORE_NAME = "c16_core-stub"


@dataclass(frozen=True)
class Decision:
    verdict: str
    action: str


@dataclass(frozen=True)
class PinnedC16:
    default_tier: str
    max_tokens: int

    @classmethod
    def from_env(cls, env):
        c = json.loads(env["IFABRIC_PIN_JSON"])["c16"]
        return cls(c["default_tier"], c["bound"]["max_tokens"])


def decide_inline(q, pin):
    return Decision("ALLOW", "proceed")
