"""S-G3 / RTM-1: the corpus detection table per rail and category, every miss listed; plus a secret-shape guard."""
import hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _railpath  # noqa: F401,E402
from adapters.runtime import rails as R  # noqa: E402

CORPUS_DIR = os.path.join(_railpath.ROOT, "evidence", "adversarial", "corpus")
CORPUS = json.load(open(os.path.join(CORPUS_DIR, "corpus.json"), encoding="utf-8"))
ENV = {"envelope": "ifabric.run/1", "run_id": "ifabric-adv-1791270000-c0ffee", "tally_tokens": 0, "tally_calls": 0}


def detect(item):
    """Returns {carrier: set of rule ids that fired} on the MIN rails, enforce mode."""
    out = {}
    r = R.Rails("ifabric-it", mode="enforce")
    r.ingress({"correlation_id": "c", "context": {"question": item["text"]}, "ifabric": dict(ENV)})
    out["ticket"] = set(r.records[-1]["rail.matches"]) if r.records and r.records[-1]["rail.id"] == "I-03" else set()
    r = R.Rails("ifabric-it", mode="enforce")
    res = json.dumps({"query": "SITE-DEN-12", "total_hits": 1, "results": {"incidents": [{"note": item["text"]}]}})
    r.after_tool("runbook-lookup___lookup", res)
    t3 = [d for d in r.records if d["rail.id"] == "T-03"]
    out["tool_output"] = set(t3[0]["rail.matches"]) if t3 else set()
    r = R.Rails("ifabric-it", mode="enforce")
    cancel, args = r.before_tool("runbook-lookup___lookup", {"query": item["text"], "category": "incidents"})
    pre = {d["rail.id"] for d in r.records}
    r.after_tool("runbook-lookup___lookup", json.dumps({"query": args["query"], "category": "incidents",
                                                         "total_hits": 0, "results": {"incidents": []}}))
    t3 = [d for d in r.records if d["rail.id"] == "T-03"]
    out["tool_args"] = (set(t3[0]["rail.matches"]) if t3 else set()) | {"pre:" + x for x in pre}
    return out


def table():
    rows, misses, surprises = [], [], []
    for it in CORPUS["items"]:
        d = detect(it)
        exp = set(it["expected_rule"].split("|")) - {"miss"}
        for carrier in ("ticket", "tool_output", "tool_args"):
            got = {x for x in d[carrier] if not x.startswith("pre:")}
            hit = bool(exp & got) if exp else bool(got)
            rows.append((it["id"], it["category"], carrier, sorted(got)))
            if exp and not hit:
                misses.append((it["id"], carrier, "expected %s" % sorted(exp), sorted(got)))
            if not exp:
                (surprises if got else misses).append((it["id"], carrier, "expected miss", sorted(got)))
    return rows, misses, surprises


def test_manifest_matches_corpus():
    want = open(os.path.join(CORPUS_DIR, "manifest.sha256")).read().split()[0]
    got = hashlib.sha256(open(os.path.join(CORPUS_DIR, "corpus.json"), "rb").read()).hexdigest()
    assert want == got
    assert len(CORPUS["items"]) >= 40
    assert all(i["expected_at"] and i["expected_rule"] for i in CORPUS["items"])


def test_detection_table_and_misses_listed():
    rows, misses, surprises = table()
    cats = {}
    for _, cat, carrier, got in rows:
        c = cats.setdefault((cat, carrier), [0, 0])
        c[0] += bool(got)
        c[1] += 1
    for (cat, carrier), (h, n) in sorted(cats.items()):
        print("RTM-1 %-17s %-12s %d/%d" % (cat, carrier, h, n))
    for m in misses:
        print("RTM-1 MISS", m)
    for s in surprises:
        print("RTM-1 DETECTED (pre-registered as miss)", s)
    exp_detect = [i for i in CORPUS["items"] if i["expected_rule"] != "miss"]
    # pre-registered: every item expected to be detected is detected in the ticket and tool-output carriers
    bad = [m for m in misses if m[2] != "expected miss" and m[1] in ("ticket", "tool_output")]
    assert bad == [], bad
    assert len(exp_detect) >= 30


def test_tool_output_enveloped_in_enforce():
    # MIN: every flagged tool output is delivered inside the evidence envelope; span neutralisation is P2 (PR-05b)
    for it in CORPUS["items"]:
        r = R.Rails("ifabric-it", mode="enforce")
        out = r.after_tool("runbook-lookup___lookup", json.dumps({"total_hits": 1, "results": {"incidents": [{"note": it["text"]}]}}))
        assert out.startswith("[EVIDENCE E1 |") and out.endswith("[END E1]"), it["id"]


def test_no_secret_shapes_in_corpus_or_fixtures():
    # our own secret.* patterns over every data file we ship: 0 hits (guards accidental token-shaped strings)
    files = [os.path.join(CORPUS_DIR, "corpus.json"), os.path.join(_railpath.ROOT, "tests", "rails", "fixtures", "golden.json")]
    for f in files:
        s = open(f, encoding="utf-8").read()
        assert {k: p.findall(s) for k, p in R.SEC.items() if p.search(s)} == {}, f


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
