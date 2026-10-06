"""STUB adapters.runtime.model_call (tests/bundle/stubs): PR-03's names; the model is Strands' own."""
from adapters.runtime import tally as _tally_mod
from adapters.runtime.action_id import ActionIdCapture


class FinishCapture(object):
    def record(self, value):
        pass


class ModelCallAdapter(object):
    def __init__(self, run_id, pin, tier=None, tally=None, emit=None, rails=None, identity=None,
                 capture=None, finish=None, model_id=None, max_retries=0, bound_projection=True):
        self.tally = tally if tally is not None else _tally_mod.RunTally(run_id, tier)
        self.capture, self.finish = capture or ActionIdCapture(), finish or FinishCapture()

    def register_hooks(self, registry, **kwargs):
        pass


def make_gateway_model(capture, finish, model_id, client_args=None, params=None, transport=None,
                       timeout_s=600.0):
    from strands.models.openai import OpenAIModel
    return OpenAIModel(client_args=dict(client_args or {}), model_id=model_id, params=params)
