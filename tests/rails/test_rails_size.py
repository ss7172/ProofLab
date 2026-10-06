"""Size rule (orchestrator D-A): the binding gate is the bundle's len(base64(gzip -9n(file))) <= 24,000 per agent
file; PR-05's own DONE check is rails.py gz+b64 <= 6,144 chars. The raw byte count is advisory and only printed."""
import base64, gzip, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "adapters", "runtime", "rails.py")
RAW = open(SRC, "rb").read()
PACKED = len(base64.b64encode(gzip.compress(RAW, 9, mtime=0)))
PACKED_BUDGET = 6144   # D-A: rails.py gzip -9n + base64 chars


def test_rails_packed_within_6144_chars():
    print("rails.py raw=%d bytes (advisory), gzip+b64=%d chars (budget %d)" % (len(RAW), PACKED, PACKED_BUDGET))
    assert PACKED <= PACKED_BUDGET, PACKED


def test_packed_measure_matches_gzip_cli_shape():
    """The measure is gzip -9n (no name, mtime 0) then base64 without newlines, as tools/gate.sh counts."""
    blob = gzip.compress(RAW, 9, mtime=0)
    assert blob[:2] == b"\x1f\x8b" and blob[4:8] == b"\x00\x00\x00\x00" and len(base64.b64encode(blob)) == PACKED


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
