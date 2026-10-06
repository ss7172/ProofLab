"""STUB adapters.runtime.tool_call (tests/bundle/stubs): PR-04's names."""
import hashlib
import json


def args_sha256(args):
    return hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class ToolCallRecorder(object):
    def __init__(self, client, ctx, declared_tools=()):
        self.client = client

    def before(self, name, args, tool_use_id=None):
        return self.client.emit({"record_kind": "action"})

    def after(self, name, args, status=None, call_id=None, result=None, error=None, suspicious=False,
              tool_use_id=None):
        return self.client.emit({"record_kind": "action"})
