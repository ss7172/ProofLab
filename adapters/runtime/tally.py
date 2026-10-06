"""Per-run token tally for EP-1 (ARCH section 5.1: reserve, then commit).

Stdlib only, Python 3.9 compatible. Holds NO verdict logic: it adds, reserves,
commits and releases. Whether a call may proceed is decided by the c16 core
(through model_call.guarded_check); nothing here compares a quantity to a limit.
The lock is re-entrant so the adapter can hold it across read -> evaluate ->
reserve, which makes concurrent callers in one process unable to both pass.
"""
import threading

_REGISTRY = {}
_REGISTRY_LOCK = threading.Lock()


class RunTally(object):
    def __init__(self, run_id, tier=None):
        self.run_id = run_id
        self.tier = tier
        self.lock = threading.RLock()
        self._committed = 0
        self._calls = 0
        self._unknown_calls = 0
        self._reservations = {}
        self.last_input = None
        self.last_output = None
        self.tool_result_tokens = 0
        self.halted = False
        self.halt_reason = None
        self.disposition = None
        self._own_cancel = False
        self._seq = 0
        self.seeded_tokens = 0
        self.seeded_calls = 0

    # -- seeding from the envelope (earlier agents of the same run) ----------
    def seed(self, tokens, calls):
        with self.lock:
            self._committed = int(tokens or 0)
            self._calls = int(calls or 0)
            self.seeded_tokens = self._committed
            self.seeded_calls = self._calls

    # -- reads ---------------------------------------------------------------
    @property
    def committed(self):
        with self.lock:
            return self._committed

    @property
    def reserved(self):
        with self.lock:
            return sum(self._reservations.values())

    @property
    def calls(self):
        with self.lock:
            return self._calls

    @property
    def unknown_calls(self):
        with self.lock:
            return self._unknown_calls

    def open_reservations(self):
        with self.lock:
            return dict(self._reservations)

    # -- reserve / commit / release -----------------------------------------
    def reserve(self, key, tokens):
        """Reserve `tokens` under `key`. A second reserve on the same key
        replaces the first (a retried attempt must not leak)."""
        with self.lock:
            self._reservations[key] = int(tokens)

    def release(self, key):
        with self.lock:
            return self._reservations.pop(key, 0)

    def commit(self, key, tokens_in, tokens_out, unknown=False):
        """Commit actual usage and release the reservation. `unknown=True`
        (usage 0/0 on a served call) adds nothing and is counted apart: it is
        UNKNOWN, never zero."""
        with self.lock:
            self._reservations.pop(key, None)
            self._calls += 1
            if unknown:
                self._unknown_calls += 1
                self.last_input = None
                self.last_output = None
            else:
                self._committed += int(tokens_in or 0) + int(tokens_out or 0)
                self.last_input = int(tokens_in or 0)
                self.last_output = int(tokens_out or 0)
            self.tool_result_tokens = 0

    def note_tool_result_tokens(self, n):
        with self.lock:
            self.tool_result_tokens += int(n or 0)

    # -- stop state and own-cancel flag -------------------------------------
    def mark_halt(self, reason):
        with self.lock:
            self.halted = True
            self.halt_reason = reason
            self.disposition = ("escalate", reason)

    def flag_own_cancel(self):
        with self.lock:
            self._own_cancel = True

    def consume_own_cancel(self):
        with self.lock:
            was = self._own_cancel
            self._own_cancel = False
            return was

    def next_seq(self):
        with self.lock:
            self._seq += 1
            return self._seq

    # -- what the agent returns to the script -------------------------------
    def result_fields(self):
        with self.lock:
            return {
                "tally_tokens": self._committed,
                "tally_calls": self._calls,
                "halted": self.halted,
                "disposition": (
                    {"action": self.disposition[0], "reason": self.disposition[1]}
                    if self.disposition else None
                ),
            }


def get_tally(run_id, tier=None):
    """One tally per run id / CID in this process."""
    with _REGISTRY_LOCK:
        t = _REGISTRY.get(run_id)
        if t is None:
            t = RunTally(run_id, tier)
            _REGISTRY[run_id] = t
        return t


def reset_registry():
    with _REGISTRY_LOCK:
        _REGISTRY.clear()
