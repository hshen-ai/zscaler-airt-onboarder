#!/usr/bin/env python3
"""
test_connection.py
==================
Tests target connectivity through the broker by submitting a handshake payload
to the Zscaler private connection test-integration API.
"""

import sys
import json
import ssl
import argparse
import urllib.request
import urllib.parse
import urllib.error

def parse_args():
    parser = argparse.ArgumentParser(description="Test target connection via Red Teaming Broker.")
    # Mandatory
    parser.add_argument("--url", required=True, help="Target URL (e.g., https://chatbot.yourdomain.local/chat)")
    parser.add_argument("--broker-id", required=True, help="Active Broker UUID")
    parser.add_argument("--token-url", required=True, help="Zscaler Token URL (ZIdentity)")
    parser.add_argument("--client-id", required=True, help="Zscaler Client ID")
    parser.add_argument("--client-secret", required=True, help="Zscaler Client Secret")
    # Configurable Schemas
    parser.add_argument("--payload-sample", default="{\"messages\":[{\"role\":\"user\",\"content\":\"{message}\"}],\"mode\":\"proxy\"}", help="JSON string representing the request body sample")
    parser.add_argument("--response-path", default="$.reply", help="JSONPath expression for extracting chatbot response (e.g. $.reply)")
    # Optional Target Auth (e.g., Azure AD)
    parser.add_argument("--auth-header", default="Authorization", help="Header key to inject auth token")
    parser.add_argument("--az-token-url", help="Optional: Azure AD Token URL")
    parser.add_argument("--az-client-id", help="Optional: Azure AD Client ID")
    parser.add_argument("--az-client-secret", help="Optional: Azure AD Client Secret")
    return parser.parse_args()

def get_bearer_token(url, client_id, client_secret, scope=None, audience=None):
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    if scope:
        payload["scope"] = scope
    if audience:
        payload["audience"] = audience
        
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=context) as res:
        return json.loads(res.read().decode("utf-8")).get("access_token")

def main():
    args = parse_args()
    context = ssl._create_unverified_context()
    
    # 1. Generate Target Auth Token (Optional)
    target_token = None
    if args.az_token_url and args.az_client_id and args.az_client_secret:
        print("🔐 Generating optional Azure AD access token for target authentication...")
        try:
            scope = f"{args.az_client_id}/.default"
            target_token = get_bearer_token(args.az_token_url, args.az_client_id, args.az_client_secret, scope=scope)
            print("   ✅ Target auth token successfully generated.")
        except Exception as e:
            print(f"   ❌ Target Auth Token generation failed: {e}")
            sys.exit(1)
            
    # 2. Generate Zscaler Access Token (Mandatory)
    print("\n🔑 Generating Zscaler ZIdentity access token...")
    try:
        zs_token = get_bearer_token(args.token_url, args.client_id, args.client_secret, audience="https://api.zscaler.com")
        print("   ✅ Zscaler central plane token successfully generated.")
    except Exception as e:
        print(f"   ❌ Zscaler Token generation failed: {e}")
        sys.exit(1)
        
    # 3. Submit integration test
    print(f"\n🛰️ Submitting connection test to Zscaler Private Integration Gateway...")
    print(f"   Target URL: {args.url}")
    print(f"   Broker ID:  {args.broker_id}")
    
    headers = {}
    if target_token:
        headers[args.auth-header] = f"Bearer {target_token}"
        
    test_payload = {
        "url": args.url,
        "requestPayloadSample": args.payload_sample,
        "responsePayload": args.response_path,
        "headers": headers,
        "brokerId": args.broker_id
    }
    
    url = "https://api.zsapi.net/private/aisecurity/airt/api/v2/ai-app/test-integration/rest-api"
    req = urllib.request.Request(url, data=json.dumps(test_payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {zs_token}",
        "X-Api-Version": "2.0",
        "Content-Type": "application/json"
    }, method="POST")
    
    try:
        with urllib.request.urlopen(req, context=context) as res:
            response = json.loads(res.read().decode("utf-8"))
            if response.get("isSuccessful"):
                print("\n🟢 SUCCESS! Connection Handshake Established Successfully via Broker!")
                print(f"   Message: {response.get('error')}")
                sys.exit(0)
            else:
                print("\n🔴 FAILED: Connection rejected or unreachable.")
                print(f"   Error: {response.get('error')}")
                print("   Details:")
                print(json.dumps(response.get("errorDetails", []), indent=4))
                sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"   🔴 API Gateway HTTP Error: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"   🔴 Connection Error: {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()
