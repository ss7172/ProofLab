"""Local end-to-end: generated agent.py (bundle A) as an 'AgentCore runtime' subprocess <- CallableAnalyzer <- run_assurance_agent."""
import json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from prooflab.servicenow.assurance_agent import run_assurance_agent
from prooflab.servicenow.case_view import case_view
from prooflab.servicenow.client import ServiceNowClient
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.nemotron import AnalyzerError, CallableAnalyzer, GatewayAnalyzer
from prooflab.servicenow.notifier import notify
from prooflab.tests.fake_gateway import API_KEY, FakeGateway, completion
from prooflab.tests.fake_servicenow import CLIENT_ID, CLIENT_SECRET, INTEGRATION_USER, OWNER_USER, FakeServiceNow
from prooflab.tests.test_servicenow_assurance_agent import ALIAS, finding, note

S = Path(sys.argv[1])
# 0) Arth's constructor refuses the URL shape the operator injects into runtimes (plain-http public ELB :8081)
try:
    GatewayAnalyzer("http://k8s-agw-0123456789.elb.us-east-1.amazonaws.com:8081/v1", ALIAS)
    print("0) GatewayAnalyzer accepted http ELB URL (unexpected)")
except ValueError as e:
    print("0) GatewayAnalyzer(http ELB URL) ->", type(e).__name__, ":", str(e)[:70])

sn, gw = FakeServiceNow().start(), FakeGateway().start()
port = (lambda s: (s.bind(("127.0.0.1", 0)), s.getsockname()[1], s.close())[1])(socket.socket())
env = {**os.environ, "PYTHONPATH": str(S / "bundle" / "stub"), "PORT": str(port),
       "OPENAI_BASE_URL": gw.base_url + "/v1", "OPENAI_API_KEY": API_KEY, "MODEL_ALIAS": ALIAS,
       "PYTHONDONTWRITEBYTECODE": "1"}
# run the generated single file from an EMPTY cwd, so nothing but the bundle can supply prooflab
runtime = subprocess.Popen([sys.executable, str(S / "bundle" / "agent_A_analyzer_only.py")], env=env,
                           cwd=tempfile.mkdtemp(), stderr=subprocess.PIPE)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=1); break
        except Exception:
            time.sleep(0.1)

    def invoke_runtime(messages):  # what our orchestrator glue does (spec 08 §5.3 step 4), here over local HTTP
        req = urllib.request.Request(f"http://127.0.0.1:{port}/invocations", method="POST",
                                     data=json.dumps({"messages": messages}).encode(),
                                     headers={"Content-Type": "application/json"})
        out = json.loads(urllib.request.urlopen(req, timeout=30).read())
        if out.get("error"):
            raise AnalyzerError("blocked" if out["error"] == "blocked" else "unavailable", out["error"], out.get("action_id"))
        return out

    analyzer = CallableAnalyzer(invoke_runtime, backend="agentcore:ifabric_assurance_agent", model_alias=ALIAS)
    client = ServiceNowClient(base_url=sn.base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    tmp = Path(tempfile.mkdtemp()); log = DeliveryLog(tmp / "delivery-log.jsonl")
    print("1) notify ->", notify(finding(), client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER).state)
    gw.replies.append(completion("<think>private chain of thought</think>\n" + note(), action_id="act-ac-1"))
    out = run_assurance_agent(finding(), client, log, analyzer, owner_user=OWNER_USER,
                              integration_user=INTEGRATION_USER, out_dir=tmp / "agent")
    print("2) run_assurance_agent via bundled runtime ->", out.state, "| reason:", out.reason)
    print("   gateway saw: model=%s auth_ok=%s requests=%d (path must be /v1/chat/completions, else fake answers 503)"
          % (gw.requests[0]["model"], gw.auth_headers[0] == f"Bearer {API_KEY}", len(gw.requests)))
    rec = json.loads(out.evidence_path.read_text())
    print("   run record: backend=%s action_id=%s think_stripped=%s" % (rec["backend"], rec["attempts"][0]["action_id"], rec["attempts"][0]["think_stripped"]))
    case = case_view(finding(), client, log, owner_user=OWNER_USER, cutoff="2026-10-05T12:00:00Z", integration_user=INTEGRATION_USER)
    print("   case outcome_validation:", case["outcome_validation"]["status"], [(c["id"], c["status"]) for c in case["outcome_validation"]["checks"]])
    # platform-real guardrail shape: HTTP 200 + finish_reason=content_filter + "Input blocked by policy."
    gw.replies.append(completion("Input blocked by policy.", finish_reason="content_filter", action_id="act-blk-200"))
    out2 = run_assurance_agent(finding(), client, log, analyzer, owner_user=OWNER_USER,
                               integration_user=INTEGRATION_USER, out_dir=tmp / "agent", force=True)
    last = [e for e in log.history(finding().finding_id) if e["state"].startswith("ANALYSIS_")][-1]
    print("3) platform-style guardrail block (200/content_filter) ->", out2.state, "| log:", last["state"], last["action_ids"])
finally:
    runtime.terminate(); err = runtime.communicate(timeout=5)[1].decode()
    sn.stop(); gw.stop()
    if err.strip():
        print("runtime stderr:", err.strip()[-400:])
