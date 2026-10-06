"""Human-loop configuration: environment variable NAMES only (T6.10, G-20). Stdlib, 3.9.

Values arrive through an injected mapping (tests) or os.environ (the runner). This module never opens
~/.prooflab-snow.env or any file: the operator sources that file into the shell, outside the tool.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

ENV_INSTANCE = "SNOW_INSTANCE"
ENV_CLIENT_ID = "SNOW_CLIENT_ID"
ENV_CLIENT_SECRET = "SNOW_CLIENT_SECRET"
ENV_OWNER = "SNOW_OWNER_USER"
ENV_INTEGRATION_USER = "SNOW_INTEGRATION_USER"
ENV_DELIVERY_LOG = "PROOFLAB_DELIVERY_LOG"
ENV_APPROVAL_LOG = "PROOFLAB_APPROVAL_DELIVERY_LOG"

DEFAULT_INTEGRATION_USER = "ifabric.integration"   # Arth's default, restated so config never imports a secret
APPROVAL_LOG_TAIL = ("evidence", "register", "approval", "delivery-log.jsonl")
WIRING_TESTS_DIR = "wiring-tests"


class ConfigError(ValueError):
    """Missing or unacceptable configuration (the runner maps it to exit code 2)."""


@dataclass(frozen=True)
class HumanLoopConfig:
    owner_user: str
    integration_user: str
    delivery_log: str                 # absolute
    approval_log: Optional[str]       # absolute, or None when no approval finding is notified

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "HumanLoopConfig":
        env = os.environ if env is None else env
        owner = (env.get(ENV_OWNER) or "").strip()
        if not owner:
            raise ConfigError("set %s explicitly (never rely on the CLI default owner)" % ENV_OWNER)
        log = (env.get(ENV_DELIVERY_LOG) or "").strip()
        if not log or not os.path.isabs(log):
            raise ConfigError("%s must be set to an ABSOLUTE path" % ENV_DELIVERY_LOG)
        approval = (env.get(ENV_APPROVAL_LOG) or "").strip() or None
        if approval is not None and not os.path.isabs(approval):
            raise ConfigError("%s must be an ABSOLUTE path" % ENV_APPROVAL_LOG)
        if approval is not None and os.path.abspath(approval) == os.path.abspath(log):
            raise ConfigError("the approval delivery log must be its own file, not the main log")
        return cls(owner_user=owner,
                   integration_user=(env.get(ENV_INTEGRATION_USER) or DEFAULT_INTEGRATION_USER).strip(),
                   delivery_log=log, approval_log=approval)


def owner_from_env(env: Optional[Mapping[str, str]] = None) -> str:
    """SNOW_OWNER_USER for the finding's register.owner; ConfigError when unset."""
    env = os.environ if env is None else env
    owner = (env.get(ENV_OWNER) or "").strip()
    if not owner:
        raise ConfigError("set %s explicitly" % ENV_OWNER)
    return owner


def under_wiring_tests(path: str) -> bool:
    """True when `path` has a `wiring-tests` directory component (the only place a dry-run may log)."""
    return WIRING_TESTS_DIR in os.path.abspath(path).split(os.sep)[:-1]
