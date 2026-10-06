"""STUB adapters.runtime.rails (tests/bundle/stubs): PR-05's names; every rail ALLOWs."""


def startup(prompts=()):
    return {"rail.policy_sha256": "stub", "rail.version": "stub"}


class Rails(object):
    def __init__(self, agent, mode=None):
        self.records = []

    def ingress(self, p):
        return p, False

    def tools(self, ts, name=None):
        return list(ts)

    def before_tool(self, tool, args):
        return None, args

    def after_tool(self, tool, text):
        return text

    def output(self, t, prompts=()):
        return t

    def ground(self, j):
        return j

    def summary(self):
        return {"rails.mode": "stub"}
