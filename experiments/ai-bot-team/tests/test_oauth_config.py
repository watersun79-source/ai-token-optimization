import unittest
from oauth_mcp import validate_config

class OAuthConfigTests(unittest.TestCase):
    def valid(self):
        return {"AI_MCP_RESOURCE":"https://bot.example.com/mcp",
                "AI_OAUTH_ISSUER":"https://login.example.com",
                "AI_OAUTH_JWKS_URI":"https://login.example.com/jwks","AI_OAUTH_ALLOWED_SUBJECTS":"sandbox-user"}
    def test_valid_https(self):
        self.assertEqual(validate_config(self.valid())[0],"https://bot.example.com/mcp")
    def test_missing_settings_fail_closed(self):
        for k in self.valid():
            c=self.valid();del c[k]
            with self.assertRaises(RuntimeError):validate_config(c)
    def test_plain_http_disallowed(self):
        for k in ('AI_MCP_RESOURCE','AI_OAUTH_ISSUER','AI_OAUTH_JWKS_URI'):
            c=self.valid();c[k]=c[k].replace("https://","http://")
            with self.assertRaises(RuntimeError):validate_config(c)
    def test_wrong_resource_endpoint_disallowed(self):
        c=self.valid();c["AI_MCP_RESOURCE"]="https://bot.example.com/nope"
        with self.assertRaises(RuntimeError):validate_config(c)
    def test_local_test_mode_only_loopback(self):
        c={"AI_MCP_RESOURCE":"http://127.0.0.1:18084/mcp","AI_OAUTH_ISSUER":"http://127.0.0.1:18085",
           "AI_OAUTH_JWKS_URI":"http://127.0.0.1:18085/jwks","AI_OAUTH_LOCAL_TEST":"1","AI_OAUTH_ALLOWED_SUBJECTS":"sandbox-user"}
        self.assertTrue(validate_config(c)[3])
        c["AI_OAUTH_ISSUER"]="https://external.example.com"
        with self.assertRaises(RuntimeError):validate_config(c)
    def test_no_owner_allowlist_rejected(self):
        c=self.valid()
        c.pop("AI_OAUTH_ALLOWED_SUBJECTS")
        with self.assertRaises(RuntimeError):validate_config(c)
        c["AI_OAUTH_ALLOWED_SUBJECTS"]="*"
        with self.assertRaises(RuntimeError):validate_config(c)
    def test_jwks_other_host_rejected(self):
        c=self.valid()
        c["AI_OAUTH_JWKS_URI"]="https://attacker.example.com/jwks"
        with self.assertRaises(RuntimeError):validate_config(c)
    def test_no_credentials_embedded_in_url(self):
        c=self.valid();c["AI_OAUTH_JWKS_URI"]="https://user:pass@login.example.com/jwks"
        with self.assertRaises(RuntimeError):validate_config(c)
if __name__=="__main__":unittest.main()
