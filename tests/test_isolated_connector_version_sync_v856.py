"""No-network regression tests for v8.5.6 connector-version evidence gate."""
import unittest
from tools.isolated_connector_version_sync_v856 import reconcile_connector_versions, VERSION

NOW = "2026-11-01T00:00:00Z"

def item(component="github", status="SESSION_READ_PASS", version=None,
         source="connector_read", **overrides):
    row = {"component": component, "status": status, "source": source,
           "observed_at": NOW, "evidence": "mcp.read.123", "version": version}
    row.update(overrides)
    return row

class ConnectorInventoryTests(unittest.TestCase):
    def test_versioned_software_and_plugin_reads_are_separate(self):
        out = reconcile_connector_versions([
            item("github"), item("neon", version="18.0"),
            item("replit", status="TOOL_AVAILABLE", source="tool_inventory"),
        ], now=NOW)
        self.assertEqual(out["registry_schema"], VERSION)
        self.assertEqual(out["session_read_pass"], 2)
        self.assertIsNone(out["components"]["github"]["reported_component_version"])
        self.assertEqual(out["components"]["neon"]["reported_component_version"], "18.0")
        self.assertFalse(out["components"]["replit"]["plugin_binary_upgraded"])
        self.assertFalse(out["production_changed"])

    def test_grok_is_paused_by_default(self):
        out = reconcile_connector_versions([], now=NOW)
        self.assertEqual(out["components"]["grok_bot_control"]["status"], "PAUSED")

    def test_grok_read_cannot_be_accidentally_enabled(self):
        with self.assertRaisesRegex(ValueError, "GROK_CONNECTION_PAUSED"):
            reconcile_connector_versions([item("grok_bot_control")], now=NOW)

    def test_duplicate_provider_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_COMPONENT"):
            reconcile_connector_versions([item(), item()], now=NOW)

    def test_unknown_provider_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_CONNECTOR_METADATA"):
            reconcile_connector_versions([item("unknown")], now=NOW)

    def test_unverified_version_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_VERSION"):
            reconcile_connector_versions([item(status="TOOL_AVAILABLE", source="tool_inventory", version="8.5.6")], now=NOW)

    def test_status_cannot_claim_read_from_tool_listing(self):
        with self.assertRaisesRegex(ValueError, "READ_WITHOUT_CONNECTOR"):
            reconcile_connector_versions([item(source="tool_inventory")], now=NOW)

    def test_secret_and_external_urls_do_not_enter_evidence(self):
        for bad in ("https://somewhere/private", "api_key=abcd", "x\\nsecret", "x"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "INVALID_EVIDENCE"):
                    reconcile_connector_versions([item(evidence=bad)], now=NOW)

    def test_secret_shaped_evidence_is_rejected_without_echo(self):
        examples = (
            "sk-" + "a" * 24,
            "ghp_" + "b" * 30,
            "github_pat_" + "c" * 30,
            "xoxb-" + "d" * 28,
            "mcp.password:masked",
            "mcp.api_key:masked",
            "mcp.token:masked",
        )
        for synthetic in examples:
            with self.subTest(label=synthetic[:4]):
                with self.assertRaisesRegex(ValueError, "^INVALID_EVIDENCE$"):
                    reconcile_connector_versions(
                        [item(evidence=synthetic)], now=NOW
                    )

    def test_valid_receipt_like_evidence_still_accepted(self):
        out = reconcile_connector_versions(
            [item(evidence="mcp.ab12-ff3e.901")], now=NOW
        )
        self.assertEqual(
            out["components"]["github"]["evidence"], "mcp.ab12-ff3e.901"
        )

    def test_stale_and_future_rejected(self):
        for at in ("2026-10-28T00:00:00Z", "2026-11-01T01:00:00Z"):
            with self.subTest(at=at):
                with self.assertRaisesRegex(ValueError, "STALE_OR_FUTURE_EVIDENCE"):
                    reconcile_connector_versions([item(observed_at=at)], now=NOW)

    def test_naive_time_rejected(self):
        with self.assertRaisesRegex(ValueError, "NAIVE_TIMESTAMP"):
            reconcile_connector_versions([item()], now="2026-11-01T00:00:00")

    def test_unexpected_extra_field_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_RECORD_SHAPE"):
            reconcile_connector_versions([item(credential="never_store")], now=NOW)

    def test_failed_or_paused_observation_cannot_fake_version(self):
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_VERSION"):
            reconcile_connector_versions([item(status="UNVERIFIED", source="registry_read", version="8.5.6")], now=NOW)

    def test_no_implicit_automation_or_paid_calls(self):
        out = reconcile_connector_versions([item()], now=NOW)
        self.assertEqual(out["external_paid_calls"], 0)
        self.assertFalse(out["unattended_automation_verified"])
        self.assertFalse(out["components"]["github"]["live_cross_app_sync_verified"])

if __name__ == "__main__":
    unittest.main()
