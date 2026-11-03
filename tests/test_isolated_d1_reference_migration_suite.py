"""Run the isolated D1 migration/guard regression suite in main's CI discovery.

This is a source-only, network-free test loader; no D1 or GitHub writes.
"""
from pathlib import Path
import sys
import unittest

ISOLATED = Path(__file__).resolve().parents[1] / 'experiments' / 'd1-reference-migration'


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):
    # The sandbox keeps the audited originals' import paths intact.
    sys.path.insert(0, str(ISOLATED))
    try:
        return loader.discover(start_dir=str(ISOLATED), pattern='test_*.py', top_level_dir=str(ISOLATED))
    finally:
        # test modules are loaded while isolated path is available.
        sys.path.remove(str(ISOLATED))
