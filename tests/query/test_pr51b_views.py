"""PR-51b: view fixes (no raw evidence edited): DENY numbers from the decision's own detail, approval time stated against the
run, C9 measured value from the stored windows, provenance tags, 'not recorded' instead of None/unknown."""
from prooflab.pack import projector as PJ
from prooflab.query import answer as A
from prooflab.query import engine as E

DENY = {"record_id": "r1", "record_kind": "decision", "verdict": "DENY", "inline.mode": "enforce", "control.ref": "C16",
        "ts": "2026-10-06T13:56:57.137Z", "inline.limit_value": 25000, "inline.bound_basis": "projected",
        "detail": "C16 inline DENY (halt): committed 19823 + reserved 0 + bound 5359 (projected) = 25182 > cap 25000; "
                  "[committed=19823 reserved=0 bound=5359 max_retries=0]"}


def test_deny_numbers_from_detail():
    n = A._decision_numbers(DENY)
    assert (n["committed"], n["reserved"], n["bound"], n["projected"], n["limit"]) == (19823, 0, 5359, 25182, 25000)
    assert n["source"].startswith("recorded")
    enf = A._enforcement("C16", [DENY], {"threshold_version": "C16-v1.1"})
    d = enf["inline_decisions"][0]
    assert d["decision"] == "DENY" and d["bound"] == 5359 and d["limit"] == 25000


RULE = {"register_version": "v1.1", "frozen_at": "2026-10-06T13:38:05Z", "date_before_scope": True,
        "owner": {"id": "annapurna@invences.com", "name": "annapurna@invences.com"},
        "approval": {"status": "APPROVED", "at": "2026-10-06T15:09:49Z", "ref": "servicenow:INC0010338",
                     "approver": {"id": "annapurna@invences.com"}}}


def test_approval_after_run_is_stated_never_vouched():
    start = "2026-10-06T13:56:15Z"
    assert not A._approved_before(RULE, start)
    t = A._authority_text(RULE, start)
    assert "15:09:49Z on INC0010338, responded from account annapurna@invences.com" in t and "approved after the run; dated before the run by S3" in t
    assert "register owner: annapurna@invences.com" in t
    v = A._tick_text({}, "VERIFIED", {}, "", RULE, run_start=start)["V"]
    assert v.startswith("not vouched") and "after the run start" in v
    early = dict(RULE, approval=dict(RULE["approval"], at="2026-10-06T13:44:39Z"))
    assert A._approved_before(early, start)
    assert A._tick_text({}, "VERIFIED", {}, "", early, run_start=start)["V"].startswith("vouched")


def test_gateway_llm_metric_is_a_model_call_not_a_c9_window():
    gw = {"record_kind": "metric", "measured.source": "gateway-figure-of-record", "detail": "gateway llm call: 562 in, 35 out tokens"}
    assert PJ.record_kind_of(gw) == "model-call"
    assert PJ.ep_of_record(gw)[0] == "EP-2"
    assert PJ.record_kind_of({"record_kind": "metric", "measured.source": "agentcore"}) == "window"


def test_txt_carries_source_tag():
    assert A._txt("x", source="recorded (actor.id)")["source"] == "recorded (actor.id)"
    assert "source" not in A._txt("x")
    assert E.NOT_RECORDED == "not recorded"


def test_none_leaks_read_not_recorded():
    assert A._clean("valid=True position=None") == "valid=True position=not recorded"
    assert A._clean("received None") == "received not recorded"
    rows = A._record_rows([{"record_id": "x", "record_kind": "handoff", "detail": "received None"}], {}, "UNVERIFIED", False)
    assert rows[0]["summary"] == "received not recorded" and rows[0]["source"].startswith("recorded")


def test_warmup_label_from_its_records():
    assert E.run_label(None, "c", "OURS-ROLE-UNDECLARED", "EXPLORATORY") == "EXPLORATORY (declared in the run's records)"
    assert E.run_label(None, "c", "LIVE_SUBJECT", "LIVE_SUBJECT") == "LIVE_SUBJECT"


def test_threshold_version_bound_by_first_carrier_register():
    bound = dict(RULE, register_version="v1", frozen_at="2026-10-06T12:40:22Z", bound_by="register v1 (first carried C7-v1)",
                 approval={"status": "APPROVED", "at": "2026-10-06T13:02:37Z", "ref": "servicenow:INC0010321",
                           "approver": {"id": "annapurna@invences.com"}})
    t = A._authority_text(bound, "2026-10-06T13:56:15Z")
    assert "bound by register v1" in t and "13:02:37Z on INC0010321" in t and "(approved before the run)" in t


def test_c9_largest_change_pct():
    top, n = A._c9_largest({"windows": [{"change_pct": "8.641", "runtime": "c"}, {"change_pct": "-41.4513", "runtime": "it"}]})
    assert top == (41.4513, "it") and n == 2
    assert A._c9_largest({}) == (None, 0)


def test_window_before_v1_approval_names_each_register_date_and_never_vouches():
    """Fix round: v1.1 (dated 13:38:05Z) must never be printed next to v1's S3 date (12:40:22Z); a window starting at
    13:00Z, before v1's approval (13:02:37Z) and v1.1's approval (15:09:49Z), is never vouched."""
    rule = dict(RULE, threshold_version="C9-v1", frozen_at="2026-10-06T12:40:22Z", t1_register="v1",
                register_t1="2026-10-06T13:38:05Z")
    start = "2026-10-06T13:00:00Z"
    t = A._authority_text(rule, start, "scope start")
    assert "threshold version C9-v1 first dated by S3 (T1) 2026-10-06T12:40:22Z in register v1, before the scope start" in t
    assert "register v1.1 (the rule shown) dated by S3 (T1) 2026-10-06T13:38:05Z, after the scope start" in t
    assert "register v1.1 dated by S3 (T1) 2026-10-06T12:40:22Z" not in t
    assert "approved after the scope start; threshold version C9-v1 (register v1) dated before the scope start by S3" in t
    v = A._tick_text({}, "VERIFIED", {}, "", rule, run_start=start, label="scope start")["V"]
    assert v.startswith("not vouched") and "after the scope start" in v and "register v1)" in v
    assert A._tick_text({}, "VERIFIED", {}, "", rule, label="scope start")["V"].startswith("not vouched")


def test_register_owner_prefers_owner_account():
    class P:
        registers = {"v1.1": {"doc": {"top": {"register_owner": "Sree", "owner": "annapurna@invences.com"}}},
                     "v1": {"doc": {"top": {"register_owner": "Sree"}}}}
    assert E._register_owner(P()) == "annapurna@invences.com"
    P.registers["v1.1"]["doc"]["top"]["owner_name"] = "Sree Annapurna Rallabandi"
    assert E._register_owner(P()) == "annapurna@invences.com (Sree Annapurna Rallabandi)"
    P.registers = {"v1": {"doc": {"top": {"register_owner": "Sree"}}}}
    assert E._register_owner(P()) == "Sree"


def test_c9_what_was_done_never_unknown():
    ctx = {"recs": [], "cid": "c", "scope_kind": "run", "scope_label": "N1", "start": "2026-10-06T13:56:15Z", "end": None,
           "manifest_status": "VERIFIED", "mval": 41.4513, "munit": "% relative change vs baseline (largest |change_pct|, runtime it)",
           "msource": "recorded (measured.windows[].change_pct of the stored assessment; largest of 3)"}
    rule = dict(RULE, threshold_version="C9-v1", statement="s", source_ref="register:x",
                observation_limit={"operator": "<=", "value": 50, "unit": "%"})
    q = A._audit_question("C9", {"verdict": "SATISFIED", "measured": {"windows": []}}, rule, ctx)
    w = q["what_was_done"]["text"]
    assert "unknown" not in w and "measured 41.4513 %" in w
    assert "change_pct" in q["what_was_done"]["source"]
