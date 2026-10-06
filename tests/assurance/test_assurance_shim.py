"""G-01's shim, exercised inside the GENERATED bundle (a fresh interpreter, empty cwd): the /v1 suffix, the
gateway-URL shim, the token limit via config, the payload shapes, the witness line."""
import json

from assurance_support import ELB_URL, run_driver


def test_v1_suffix_is_stripped_and_the_plain_http_elb_url_is_accepted_by_the_shim_only():
    out, _ = run_driver(
        "out['base'] = g['gateway_base']()\n"
        "a = g['analyzer']()\n"
        "out['url'] = a._request([{'role': 'user', 'content': 'x'}]).full_url\n"
        "out['backend'] = a.backend\n"
        "try:\n"
        "    g['GatewayAnalyzer'](g['gateway_base'](), 'nemotron-super-120b')\n"
        "    out['arth'] = 'accepted'\n"
        "except ValueError as e:\n"
        "    out['arth'] = 'refused'\n",
        OPENAI_BASE_URL=ELB_URL, OPENAI_API_KEY="synthetic-test-key", MODEL_ALIAS="nemotron-super-120b")
    assert out["base"] == ELB_URL[:-3]
    assert out["url"] == ELB_URL[:-3] + "/v1/chat/completions"  # never /v1/v1
    assert out["backend"] == "modaas-agw:nemotron-super-120b"
    assert out["arth"] == "refused"  # Arth's unchanged check still refuses it; only our constructor differs


def test_trailing_slash_and_no_suffix_forms():
    out, _ = run_driver("out['a'] = g['gateway_base']()", OPENAI_BASE_URL=ELB_URL + "/")
    assert out["a"] == ELB_URL[:-3]
    out, _ = run_driver("out['a'] = g['gateway_base']()", OPENAI_BASE_URL=ELB_URL[:-3])
    assert out["a"] == ELB_URL[:-3]


def test_max_tokens_env_sets_nemotron_max_tokens_and_the_request_carries_it():
    snippet = ("import sys, json\n"
               "nem = sys.modules['prooflab.servicenow.nemotron']\n"
               "out['max'] = nem.MAX_TOKENS\n"
               "req = g['analyzer']()._request([{'role': 'user', 'content': 'x'}])\n"
               "out['body_max'] = json.loads(req.data)['max_tokens']\n")
    env = dict(OPENAI_BASE_URL=ELB_URL, MODEL_ALIAS="nemotron-super-120b")
    out, _ = run_driver(snippet, IFABRIC_ASSURE_MAX_TOKENS="1600", **env)
    assert out == {"max": 1600, "body_max": 1600}
    out, _ = run_driver(snippet, **env)
    assert out == {"max": 900, "body_max": 900}  # unset: Arth's own default stays
    out, stdout = run_driver(snippet, IFABRIC_ASSURE_MAX_TOKENS="lots", **env)
    assert out == {"max": 900, "body_max": 900}
    assert '"config-ignored"' in stdout


def test_bad_payloads_return_unavailable_without_a_model_call():
    out, stdout = run_driver(
        "out['empty'] = g['handle']({})\n"
        "out['none'] = g['handle'](None)\n"
        "out['nolist'] = g['handle']({'messages': 'x'})\n",
        OPENAI_BASE_URL=ELB_URL, MODEL_ALIAS="nemotron-super-120b")
    for v in out.values():
        assert v == {"error": "unavailable", "action_id": None}
    assert stdout.count('"bad_request"') == 3


def test_unreachable_gateway_is_unavailable_and_the_witness_never_holds_text():
    out, stdout = run_driver(
        "out['r'] = g['handle']({'input': {'messages': [{'role': 'user', 'content': 'SECRET-PROMPT-TEXT'}],"
        " 'cid': 'ifabric-assure-1-abcd'}})\n",
        OPENAI_BASE_URL="http://127.0.0.1:9/v1", MODEL_ALIAS="nemotron-super-120b")
    assert out["r"] == {"error": "unavailable", "action_id": None}
    witness = [json.loads(l) for l in stdout.splitlines() if l.startswith("{")]
    assert witness and witness[-1]["cid"] == "ifabric-assure-1-abcd" and witness[-1]["outcome"] == "unavailable"
    assert "SECRET-PROMPT-TEXT" not in stdout


def test_span_redaction_env_is_defaulted_never_overridden():
    out, _ = run_driver("import os\nout['v'] = os.environ.get('OTEL_SEMCONV_STABILITY_OPT_IN')")
    assert out["v"] == "gen_ai_unredacted_attributes="
    out, _ = run_driver("import os\nout['v'] = os.environ.get('OTEL_SEMCONV_STABILITY_OPT_IN')",
                        OTEL_SEMCONV_STABILITY_OPT_IN="gen_ai_unredacted_attributes=custom")
    assert out["v"] == "gen_ai_unredacted_attributes=custom"


def test_missing_model_alias_is_unavailable():
    out, _ = run_driver("out['r'] = g['handle']({'messages': [{'role': 'user', 'content': 'x'}]})",
                        OPENAI_BASE_URL=ELB_URL)
    assert out["r"] == {"error": "unavailable", "action_id": None}
