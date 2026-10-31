"""v8.3.9 finite repeated-process soak assertions; local synthetic jobs only."""
import unittest

from tools.soak_standalone_v839 import soak


class SoakTests(unittest.TestCase):
    def test_real_repeated_subprocesses_persist_all_jobs(self):
        report = soak(seconds=1, jobs_per_wave=6, per_process=3)
        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(report["waves"], 2)
        self.assertGreaterEqual(report["elapsed_seconds"], 1.0)
        self.assertEqual(report["total_jobs"], report["waves"] * 6)
        self.assertEqual(report["persisted_successes"], report["total_jobs"])
        self.assertEqual(report["duplicate_or_retry_attempts"], 0)
        self.assertEqual(report["subprocess_batch_restarts"], report["waves"] - 1)
        self.assertFalse(report["network_used"])
        self.assertFalse(report["neon_used"])
        self.assertFalse(report["always_on_24h_verified"])
        self.assertFalse(report["machine_replacement_persistence_verified"])

    def test_bounded_configuration_rejects_unsafe_values(self):
        for kw in ({"seconds": 0}, {"seconds": 31}, {"seconds": True},
                   {"jobs_per_wave": 3}, {"jobs_per_wave": 33},
                   {"per_process": 0}, {"per_process": 17}, {"per_process": True}):
            with self.assertRaises(ValueError):
                soak(**kw)
