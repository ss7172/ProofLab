"""PR-52a: a window answer counts stored assessments truthfully; a roll-up is never called a run, no '0 records' line."""
from prooflab.query import answer as A


def test_counted_words_names_runs_and_rollups():
    counted = [{"scope_kind": "run"}] * 6 + [{"scope_kind": "window"}] * 3
    breached = [counted[0]]
    w = A._counted_words(counted, breached)
    assert w == "1 breached of 9 counted assessments (6 runs, 3 hourly roll-ups)"
    assert A._counted_words([{"scope_kind": "window"}], []) == "0 breached of 1 counted assessment (1 hourly roll-up)"


def test_window_what_was_done_has_no_record_count_from_empty_recs():
    import inspect
    src = inspect.getsource(A.compose_window)
    assert "what_text" in src and "counted runs breached" not in src
