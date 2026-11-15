"""Independent zero-provider tests for all ten candidate integration contracts."""
import copy
import importlib.util
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "experiments" / "oss-top10-safe-adoption"
sys.path.insert(0, str(ROOT))
from safe_adoption import SafetyBlock, load_catalog  # noqa: E402

spec = importlib.util.spec_from_file_location("ten_adapter_runtime", ROOT / "ten_adapter_runtime.py")
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)


class TestTenAdapterRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(ROOT / "catalog.json")

    def test_ten_distinct_adapters_exercised(self):
        result = rt.simulate_all(self.catalog, "Audit evidence")
        self.assertEqual(result["adapter_contracts_exercised"], 10)
        self.assertEqual(set(x["project"] for x in result["results"]), set(rt.ALL_IDS))

    def test_deterministic(self):
        self.assertEqual(rt.simulate_all(self.catalog, "same"), rt.simulate_all(self.catalog, "same"))

    def test_no_providers_no_writes(self):
        out = rt.simulate_all(self.catalog, "safe")
        for key in ("vendor_runtime_integrations_verified", "vendor_packages_installed", "external_requests", "production_writes"):
            self.assertEqual(out[key], 0)
        self.assertTrue(all(x["vendor_runtime_imported"] is False for x in out["results"]))

    def test_no_live_selection(self):
        self.assertIs(rt.simulate_all(self.catalog, "safe")["selection_is_live"], False)

    def test_flowise_reference_only(self):
        out = rt.simulate_all(self.catalog, "safe")
        flowise = next(x for x in out["results"] if x["project"] == "flowise")
        self.assertEqual(flowise["status"], "EOL_VISUAL_REFERENCE_ONLY")
        self.assertFalse(flowise["artifact"]["engine_started"])

    def test_activepieces_unpublished(self):
        x = next(x for x in rt.simulate_all(self.catalog, "safe")["results"] if x["project"] == "activepieces")
        self.assertFalse(x["artifact"]["published"])

    def test_mem0_no_d1(self):
        x = next(x for x in rt.simulate_all(self.catalog, "safe")["results"] if x["project"] == "mem0")
        self.assertFalse(x["artifact"]["d1_written"])

    def test_langfuse_no_export(self):
        x = next(x for x in rt.simulate_all(self.catalog, "safe")["results"] if x["project"] == "langfuse")
        self.assertFalse(x["artifact"]["telemetry_exported"])

    def test_openhands_no_shell_or_patch(self):
        x = next(x for x in rt.simulate_all(self.catalog, "safe")["results"] if x["project"] == "openhands")
        self.assertFalse(x["artifact"]["shell_executed"])
        self.assertFalse(x["artifact"]["patch_applied"])

    def test_crew_no_models_started(self):
        x = next(x for x in rt.simulate_all(self.catalog, "safe")["results"] if x["project"] == "crewai")
        self.assertEqual(x["artifact"]["model_agents_started"], 0)

    def test_agent_sdk_no_provider(self):
        x = next(x for x in rt.simulate_all(self.catalog, "safe")["results"] if x["project"] == "openai-agents")
        self.assertEqual(x["artifact"]["provider_calls"], 0)

    def test_reject_live_modes(self):
        for mode in ("live", "install", "deploy", "write", "connect"):
            with self.subTest(mode=mode), self.assertRaises(SafetyBlock):
                rt.simulate_all(self.catalog, "safe", mode=mode)

    def test_reject_credentials(self):
        for value in ("api_key = example", "password=wow", "sk-012345678901", "ghp_0123456789012"):
            with self.subTest(value=value), self.assertRaises(SafetyBlock):
                rt.simulate_all(self.catalog, value)

    def test_reject_control_chars(self):
        with self.assertRaises(SafetyBlock):
            rt.simulate_all(self.catalog, "test\nsecret")

    def test_reject_long_goal(self):
        with self.assertRaises(SafetyBlock):
            rt.simulate_all(self.catalog, "a" * 81)

    def test_reject_invalid_catalog(self):
        altered = copy.deepcopy(self.catalog)
        altered["guard_policy"]["allow_d1_write"] = True
        with self.assertRaises(SafetyBlock):
            rt.simulate_all(altered, "safe")

    def test_reject_missing_adapter_metadata(self):
        altered = copy.deepcopy(self.catalog)
        altered["projects"] = altered["projects"][:-1]
        with self.assertRaises(SafetyBlock):
            rt.simulate_all(altered, "safe")


if __name__ == "__main__":
    unittest.main()
