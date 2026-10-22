"""Offline OAuth provider discovery preflight; NEVER fetches credentials or logs tokens.

Checks published issuer discovery metadata against ChatGPT MCP auth requirements.
This is NOT an end-to-end login, consent, issued access-token, or hosting check.
"""
from __future__ import annotations
import json
from urllib.parse import urlparse

def preflight(metadata: dict, expected_issuer: str, *, client_mode: str="cimd",
              provided_client_id: str="") -> dict:
    if not isinstance(metadata,dict):
        raise TypeError("metadata must be an object")
    if client_mode not in ("cimd","dcr","provided"):
        raise ValueError("client_mode must be cimd, dcr or provided")
    errors=[]
    warnings=[]
    def https_url(field: str):
        value=metadata.get(field)
        if not isinstance(value,str) or not value:
            errors.append(f"missing_{field}");return
        p=urlparse(value)
        if p.scheme!="https" or not p.hostname or p.username or p.password or p.fragment:
            errors.append(f"invalid_{field}")
    if not expected_issuer.startswith("https://") or not urlparse(expected_issuer).hostname:
        raise ValueError("expected_issuer must be an exact HTTPS issuer string")
    if metadata.get("issuer")!=expected_issuer:
        errors.append("issuer_mismatch_exact")
    for field in ("authorization_endpoint","token_endpoint"):
        https_url(field)
    if "S256" not in metadata.get("code_challenge_methods_supported",[]):
        errors.append("s256_pkce_not_advertised")
    methods=metadata.get("token_endpoint_auth_methods_supported",[])
    if not isinstance(methods,list):
        methods=[]
    if client_mode=="cimd":
        if metadata.get("client_id_metadata_document_supported") is not True:
            errors.append("cimd_not_advertised")
        if not set(methods).intersection({"none","private_key_jwt"}):
            errors.append("cimd_no_supported_token_method")
    elif client_mode=="dcr":
        https_url("registration_endpoint")
    else:
        if not provided_client_id.strip():
            errors.append("missing_pre_registered_client_id")
    if metadata.get("authorization_response_iss_parameter_supported") is not True:
        warnings.append("callback_id_specific_redirect_needed_if_issuer_id_not_supported")
    if "ai:analyze" not in metadata.get("scopes_supported",[]):
        warnings.append("ai_analyze_scope_not_advertised_or_not_enabled")
    # There is no reliable static metadata field proving ChatGPT's required
    # resource parameter actually ends up in the issued JWT audience.
    warnings.append("resource_parameter_to_audience_requires_real_token_test")
    warnings.append("consent_pkce_callback_and_refresh_require_real_login_test")
    return {"status":"METADATA_COMPATIBLE_ONLY" if not errors else "NOT_READY",
            "errors":errors,"warnings":warnings,"client_mode":client_mode,
            "chatgpt_connected":False,"real_login_tested":False,"external_api_calls":0}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--metadata-json",required=True,help="Local IDP discovery JSON file; do not supply secrets")
    p.add_argument("--issuer",required=True)
    p.add_argument("--mode",choices=["cimd","dcr","provided"],default="cimd")
    p.add_argument("--client-id",default="")
    a=p.parse_args()
    with open(a.metadata_json,encoding="utf-8") as f:
        source=json.load(f)
    result=preflight(source,a.issuer,client_mode=a.mode,provided_client_id=a.client_id)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if not result["errors"] else 2)
