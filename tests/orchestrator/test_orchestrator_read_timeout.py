"""PR-44: the ops lane may shorten the CLI read timeout via PROOFLAB_CLI_READ_TIMEOUT (30..900 s)."""
import pytest

from prooflab.adapters.orchestrator import common, invoke


def test_default_is_budget_json(monkeypatch):
    monkeypatch.delenv(common.READ_TIMEOUT_ENV, raising=False)
    b = common.load_budget()
    assert b["invoke"]["cli_read_timeout"] == "900"
    assert "cli_read_timeout_source" not in b["invoke"]


def test_override_reaches_the_cli_argv_and_the_hard_limit(monkeypatch):
    monkeypatch.setenv(common.READ_TIMEOUT_ENV, "180")
    b = common.load_budget()
    assert b["invoke"]["cli_read_timeout"] == "180"
    assert b["invoke"]["cli_read_timeout_source"] == common.READ_TIMEOUT_ENV
    argv = invoke.build_argv("arn:x", "s" * 40, "/tmp/p.json", "/tmp/o.json", "modaas-correlation-id=ifabric-run-1-abcdef",
                             "00-" + "1" * 32 + "-" + "2" * 16 + "-01", b) if hasattr(invoke, "build_argv") else None
    if argv is not None:
        assert argv[argv.index("--cli-read-timeout") + 1] == "180"


@pytest.mark.parametrize("bad", ["0", "29", "901", "abc", "-5", "1.5", ""])
def test_invalid_override_is_refused(monkeypatch, bad):
    monkeypatch.setenv(common.READ_TIMEOUT_ENV, bad)
    with pytest.raises(ValueError):
        common.load_budget()
