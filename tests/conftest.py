"""Shared test scaffold (PR-01): put the repo root on sys.path so `prooflab` and `adapters` import."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
