"""OWASP-inspired URL parser ambiguity and source-reference integrity checks.

Metadata validation only; no HTTP fetch and no external AI provider.
"""
import unittest

from bot_team_r16 import ResearchBot, _safe_reference_url


class SourceReferencePolicyTests(unittest.TestCase):
    def test_canonical_public_repository_reference_allowed(self):
        cases = [
            "https://github.com/microsoft/agent-framework",
            "https://github.com/pydantic/pydantic-ai",
            "https://github.com/owner/repo/blob/main/README.md",
            "https://github.com/owner/.github",
        ]
        for url in cases:
            with self.subTest(url=url):
                self.assertTrue(_safe_reference_url(url))

    def test_ambiguous_and_unsafe_url_forms_rejected(self):
        cases = [
            "https://github.com",
            "https://github.com/",
            "https://github.com//repo",
            "https://github.com/owner",
            "https://github.com.evil.example/owner/repo",
            "https://github.com:443/owner/repo",
            "https://user@github.com/owner/repo",
            "https://github.com/owner/repo?token=secrets",
            "https://github.com/owner/repo#fragment",
            "http://github.com/owner/repo",
            "https://github.com/owner/repo/..",
            "https://github.com/owner/repo/%2e%2e/escape",
            "https://github.com/owner/repo/%2Fencoded",
            "https://github.com/owner/repo%5Cexample.org",
            "https://github.com/owner/repo\\evil",
            "https://github.com/owner//repo",
            "https://github.com/owner/repo/\rhidden",
            "https://github.com/owner/repo/\thidden",
            "https://github.com/owner/repo/\nhidden",
            "https://github.com/owner/repo/한글",
            " https://github.com/owner/repo",
            "https://github.com/owner/repo ",
        ]
        for url in cases:
            with self.subTest(url=repr(url)):
                self.assertFalse(_safe_reference_url(url))

    def test_research_bot_deduplicates_references(self):
        url = "https://github.com/pydantic/pydantic-ai"
        refs = [
            {"name": "Pydantic AI", "url": url},
            {"name": "Repeated reference", "url": url},
        ]
        result = ResearchBot().run({"references": refs})
        self.assertEqual(len(result["references_reviewed"]), 1)
        self.assertEqual(result["source_authenticity"], "NOT_VERIFIED_BY_OFFLINE_BOT")

    def test_research_bot_rejects_control_characters_in_titles(self):
        refs = [
            {"name": "Valid title", "url": "https://github.com/a/b"},
            {"name": "INJECT\nline", "url": "https://github.com/c/d"},
            {"name": "Tab\tname", "url": "https://github.com/e/f"},
            {"name": " trailing", "url": "https://github.com/g/h"},
        ]
        result = ResearchBot().run({"references": refs})
        self.assertEqual(len(result["references_reviewed"]), 1)
        self.assertEqual(result["references_reviewed"][0]["name"], "Valid title")

    def test_safe_metadata_never_approves_external_source_provenance(self):
        result = ResearchBot().run({"references": [
            {"name": "Agent reference", "url": "https://github.com/microsoft/agent-framework"}
        ]})
        self.assertEqual(result["source_authenticity"], "NOT_VERIFIED_BY_OFFLINE_BOT")


if __name__ == "__main__":
    unittest.main()
