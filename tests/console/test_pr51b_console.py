"""PR-51b console: ledger headline sample is a served model call (gateway span first), never a DENY decision; a decision's
measured value is labelled a projection; DENY lines show committed + bound = projected > cap; provenance tags rendered."""
import os

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "prooflab", "console", "static", "app.js")


def _js():
    with open(APP, "r", encoding="utf-8") as fh:
        return fh.read()


def test_ledger_sample_is_a_served_call():
    js = _js()
    assert 'sample = c16[c16.length - 1];' not in js
    assert 'r.record_kind === "model-call" && r["call.id"]' in js
    assert '"LOG — as captured (gateway stdout, "' not in js
    assert 'spans: "gateway span"' in js


def test_projection_and_deny_wording():
    js = _js()
    assert '" projected (committed + bound)"' in js
    assert '" = " + fmt(d.projected) + " > cap " + fmt(d.limit)' in js


def test_provenance_tag_rendered():
    js = _js()
    assert "function srcTag(" in js and "srcTag(q.source)" in js and "srcTag(f.source)" in js
