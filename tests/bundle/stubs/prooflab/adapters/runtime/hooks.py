"""STUB prooflab.adapters.runtime.hooks (tests/bundle/stubs)."""


def providers(inv):
    return []


def http_event_hooks(inv):
    async def _on_response(response):
        inv.actions.append(response.headers.get("x-modaas-action-id"))
    return {"response": [_on_response]}
