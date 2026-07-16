#!/usr/bin/env python3
"""
onboard_target.py
=================
Officially registers and onboard a generative AI chatbot target on the Zscaler
AI Red Teaming central control plane using verified connection settings.
"""

import sys
import json
import ssl
import argparse
import urllib.request
import urllib.parse
import urllib.error

def parse_args():
    parser = argparse.ArgumentParser(description="Onboard verified AI App Target on Zscaler Red Teaming.")
    # Mandatory
    parser.add_argument("--name", required=True, help="Display name of the target")
    parser.add_argument("--url", required=True, help="Target URL (e.g., https://chatbot.yourdomain.local/chat)")
    parser.add_argument("--broker-id", required=True, help="Active Broker UUID")
    parser.add_argument("--bu-id", required=True, help="AI Asset Business Unit ID")
    parser.add_argument("--token-url", required=True, help="Zscaler Token URL (ZIdentity)")
    parser.add_argument("--client-id", required=True, help="Zscaler Client ID")
    parser.add_argument("--client-secret", required=True, help="Zscaler Client Secret")
    # Configurable Schemas
    parser.add_argument("--payload-sample", default="{\"messages\":[{\"role\":\"user\",\"content\":\"{message}\"}],\"mode\":\"proxy\"}", help="JSON string representing the request body sample")
    parser.add_argument("--response-path", default="$.reply", help="JSONPath expression for extracting chatbot response (e.g. $.reply)")
    # Target Settings
    parser.add_argument("--env", default="DEV", choices=["DEV", "PROD", "STAGING"], help="Target deployment environment")
    parser.add_argument("--rate-limit", type=int, default=50, help="Rate limit per second")
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
        
    # 3. Create the AI Application Target
    print(f"\n🚀 Submitting Onboarding Request to Zscaler AI Red Teaming...")
    print(f"   Target Name: {args.name}")
    print(f"   Target URL:  {args.url}")
    print(f"   Broker ID:   {args.broker_id}")
    print(f"   BU ID:       {args.bu-id}")
    
    headers = {}
    if target_token:
        # In a real API registration, header properties are key-value with dynamic sensitive flags
        headers[args.auth_header] = {
            "value": f"Bearer {target_token}",
            "sensitive": False
        }
        
    onboarding_payload = {
        "businessUnitId": args.bu-id,
        "connection": {
            "type": "REST_API",
            "brokerId": args.broker_id,
            "config": {
                "url": args.url,
                "requestPayloadSample": args.payload_sample,
                "responsePayload": args.response_path,
                "headers": headers
            }
        },
        "settings": {
            "name": args.name,
            "description": f"Onboarded AI Target '{args.name}' via Automation",
            "environment": args.env,
            "language": "en",
            "rateLimit": args.rate_limit,
            "concurrentRequests": False,
            "multiStepAttacks": False,
            "supportedModes": [ "TEXT" ],
            "withRag": False,
            "availability": "INTERNAL"
        }
    }
    
    url = "https://api.zsapi.net/private/aisecurity/airt/api/v2/ai-apps/create"
    req = urllib.request.Request(url, data=json.dumps(onboarding_payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {zs_token}",
        "X-Api-Version": "2.0",
        "Content-Type": "application/json"
    }, method="POST")
    
    try:
        with urllib.request.urlopen(req, context=context) as res:
            print(f"   🟢 SUCCESS! Target Onboarded. Status: {res.status} {res.reason}")
            body = res.read().decode("utf-8")
            response_json = json.loads(body)
            print("\n📊 Registered AI Application Details:")
            print(json.dumps(response_json, indent=4))
            sys.exit(0)
    except urllib.error.HTTPError as e:
        print(f"   🔴 FAILED: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"   🔴 ERROR: {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()
