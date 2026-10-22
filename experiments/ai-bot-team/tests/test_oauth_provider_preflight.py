import unittest
from oauth_provider_preflight import preflight

ISS="https://login.example.com/"
META={
 "issuer":ISS,
 "authorization_endpoint":ISS+"authorize",
 "token_endpoint":ISS+"oauth/token",
 "registration_endpoint":ISS+"oidc/register",
 "code_challenge_methods_supported":["S256"],
 "token_endpoint_auth_methods_supported":["none","private_key_jwt"],
 "client_id_metadata_document_supported":True,
 "authorization_response_iss_parameter_supported":True,
 "scopes_supported":["ai:analyze"]
}
class PreflightTests(unittest.TestCase):
    def test_cimd_metadata_pass_does_not_claim_full_connection(self):
        x=preflight(META,ISS)
        self.assertEqual(x["status"],"METADATA_COMPATIBLE_ONLY")
        self.assertFalse(x["chatgpt_connected"])
        self.assertFalse(x["real_login_tested"])
    def test_exact_issuer_comparison(self):
        x=preflight(META,ISS.rstrip("/"))
        self.assertIn("issuer_mismatch_exact",x["errors"])
    def test_pkce_s256_required(self):
        x=preflight({**META,"code_challenge_methods_supported":["plain"]},ISS)
        self.assertIn("s256_pkce_not_advertised",x["errors"])
    def test_cimd_false_fails(self):
        x=preflight({**META,"client_id_metadata_document_supported":False},ISS)
        self.assertIn("cimd_not_advertised",x["errors"])
    def test_dcr_mode_with_endpoint(self):
        x=preflight({**META,"client_id_metadata_document_supported":False},ISS,client_mode="dcr")
        self.assertEqual(x["status"],"METADATA_COMPATIBLE_ONLY")
        x=preflight({k:v for k,v in META.items() if k!="registration_endpoint"},ISS,client_mode="dcr")
        self.assertIn("missing_registration_endpoint",x["errors"])
    def test_provided_client_id_required(self):
        x=preflight(META,ISS,client_mode="provided")
        self.assertIn("missing_pre_registered_client_id",x["errors"])
        x=preflight(META,ISS,client_mode="provided",provided_client_id="registered-client-abc")
        self.assertFalse(x["errors"])
    def test_bad_endpoints_rejected(self):
        x=preflight({**META,"token_endpoint":"http://localhost/token"},ISS)
        self.assertIn("invalid_token_endpoint",x["errors"])
    def test_warns_resource_audience_requires_real_token(self):
        x=preflight(META,ISS)
        self.assertIn("resource_parameter_to_audience_requires_real_token_test",x["warnings"])
    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            preflight(META,ISS,client_mode="fake")
if __name__=="__main__":unittest.main()
