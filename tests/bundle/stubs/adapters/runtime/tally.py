"""STUB adapters.runtime.tally (tests/bundle/stubs): PR-03's RunTally names."""


class RunTally(object):
    def __init__(self, run_id, tier=None):
        self.run_id, self.tier, self.halted = run_id, tier, False

    def seed(self, tokens, calls):
        self.seeded = (tokens, calls)

    committed = 0
    calls = 0
