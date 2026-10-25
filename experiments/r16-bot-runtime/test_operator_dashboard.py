import unittest

from operator_dashboard import build_summary


class OperatorDashboardTests(unittest.TestCase):
    def test_reviewed_nonverbatim_sources_do_not_emit_stale_gap_counts(self):
        summary = build_summary(
            {
                "status": "PASS",
                "selected_roles": 100,
                "effective_worker_cap": 4,
                "failed_or_unknown_roles": [],
            },
            {
                "counts": {"EXACT": 2, "DIFFERENT": 8, "ABSENT": 0},
                "reviewed_difference_count": 8,
                "unresolved_difference_count": 0,
                "verbatim_source_match": False,
                "full_v81_deployed": False,
            },
        )

        text = "\n".join(summary)
        self.assertIn("| Source fingerprints | EXACT 2 / DIFFERENT 8 / ABSENT 0 |", text)
        self.assertIn("| Reviewed source differences | 8 |", text)
        self.assertIn("| Unresolved source differences | 0 |", text)
        self.assertIn(
            "All source differences are reviewed; verify original deployment and native per-run ledger separately.",
            text,
        )
        self.assertNotIn("5 differing and 2 absent", text)


if __name__ == "__main__":
    unittest.main()
