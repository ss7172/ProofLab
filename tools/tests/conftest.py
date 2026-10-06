"""Puts tools/ on sys.path so the tests can import manifest and the other tool modules."""
import sys
from pathlib import Path

_TOOLS = str(Path(__file__).resolve().parents[1])
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
