"""Local-only repro of the two earlier bugs, using Arth's own in-process FakeServiceNow (127.0.0.1)."""
import json, tempfile
from pathlib import Path
from prooflab.servicenow.client import ServiceNowClient
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import Finding
from prooflab.servicenow.notifier import notify, check_response
from prooflab.servicenow.case_view import case_view
from prooflab.tests.fake_servicenow import (CLIENT_ID, CLIENT_SECRET, INTEGRATION_USER, OWNER_USER, FakeServiceNow)

CUTOFF = "2026-10-05T12:00:00Z"
def breach():
    return Finding(control_ref="C16", control_id="ACN-COST-001", threshold_version="G-FM-v1",
                   scope_kind="run", scope_id="FM-B", verdict="BREACHED",
                   summary="10,800 tokens > cap 10,000", detected_at="2026-10-05T10:00:00Z",
                   evidence=("gateway:action-123",))
fake = FakeServiceNow().start()
try:
    client = ServiceNowClient(base_url=fake.base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    tmp = Path(tempfile.mkdtemp())
    # ---------------- (a) dry-run when the incident already exists
    log = DeliveryLog(tmp / "prod-log.jsonl")
    real = notify(breach(), client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER)
    posts_before = fake.post_count
    dry = notify(breach(), client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER, dry_run=True)
    st = [e["state"] for e in log.history(breach().finding_id)]
    print("(a) real notify ->", real.state, "| dry-run notify ->", dry.state, "reused=", dry.reused,
          "| POSTs during dry-run:", fake.post_count - posts_before)
    print("    log states:", st, "| DRY_RUN entry present:", "DRY_RUN" in st)
    # ---------------- (b) owner replied, journal hidden by ACL (200 + 0 rows), someone else updated later
    log2 = DeliveryLog(tmp / "log-b.jsonl")
    res = notify(breach(), client, log2, owner_user=OWNER_USER, integration_user=INTEGRATION_USER)
    sys_id = res.sys_id
    fake.append_work_note(sys_id, "Owner Person", OWNER_USER, "Acknowledged, investigating")  # owner replies
    fake.append_work_note(sys_id, "Other Admin", "other.admin", "triage: assignment group set")  # later update by another user
    fake.journal.clear()   # simulate the real itil ACL: sys_journal_field -> HTTP 200 with 0 rows, no error
    out = check_response(breach(), client, log2, owner_user=OWNER_USER, integration_user=INTEGRATION_USER,
                         cutoff=CUTOFF, now="2026-10-05T13:00:00Z")
    disp = fake.incidents[sys_id]["work_notes"]
    print("(b) 0-row journal (ACL) + later non-owner update ->", out.state,
          "| owner's note visible in work_notes display text:", "Acknowledged, investigating" in disp)
    case = case_view(breach(), client, log2, owner_user=OWNER_USER, cutoff=CUTOFF, integration_user=INTEGRATION_USER,
                     now="2026-10-05T13:00:00Z")
    p5 = next(c for c in case["policy_alignment"]["checks"] if c["id"] == "P5")
    print("    case_view response:", case["response"]["state"], "| P5:", p5["status"], "-", p5["detail"])
    # contrast: the 403 model used by the test suite
    fake.journal_forbidden = True
    out403 = check_response(breach(), client, DeliveryLog(tmp / "log-c.jsonl"), owner_user=OWNER_USER,
                            integration_user=INTEGRATION_USER, cutoff=CUTOFF, now="2026-10-05T13:00:00Z")
    print("    same incident but journal returns 403 (the test-suite model) ->", out403.state)
finally:
    fake.stop()
