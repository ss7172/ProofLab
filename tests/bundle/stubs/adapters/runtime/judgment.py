"""STUB adapters.runtime.judgment (tests/bundle/stubs): PR-04's names."""


def record_judgment(client, ctx, disposition, reason, evidence_ids=(), result_digests=(),
                    reversible_step=None, precedence_rule=None):
    return client.emit({"record_kind": "judgment", "judgment.disposition": disposition})


def record_intent(client, ctx, intent):
    return client.emit({"record_kind": "lifecycle", "lifecycle.event": "intent"})


def record_from_j2(client, ctx, fields, result_digests=()):
    return record_judgment(client, ctx, (fields or {}).get("disposition"), (fields or {}).get("reason") or "x")
