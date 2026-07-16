---
name: zscaler-airt-onboarder
description: Manage Zscaler AI Red Teaming (AiRT) brokers and chatbot targets programmatically. Deploy brokers on remote Docker-enabled hosts over SSH, verify connectivity, and register active targets under Zscaler tenants.
---

# Zscaler AI Red Teaming (AiRT) Onboarder Skill
===============================================

This skill automates and structures the entire lifecycle of onboarding generative AI targets to the Zscaler AI Red Teaming (formerly SplxAI) platform. 

It provides procedural instructions, API specifications, and parameter-driven Python scripts to deploy brokers, run diagnostic connection tests, and onboard active targets.

---

## 🧭 Directory of Bundled Resources

*   **API Reference Manual:** [references/api_reference.md](references/api_reference.md) — Endpoint URLs, gateway headers, and payload structures for Zscaler OneAPI.
*   **Broker Deployment Script:** `scripts/deploy_broker.py` — Redeploys the broker container on remote Linux hosts via SSH and verifies gateway connectivity.
*   **Connection Test Script:** `scripts/test_connection.py` — Executes real-time integration handshakes through the broker.
*   **Target Onboarder Script:** `scripts/onboard_target.py` — Officially registers verified chatbot configurations on the central plane.

---

## 🔑 Phase 1: Environment Preparation

To use this skill, the executing agent or engineer must have access to the Zscaler central plane client credentials (ZIdentity).

### 1. Mandatory Environment Variables
Ensure these credentials are set in your local session or environment:
*   `ZSCALER_CLIENT_ID` — Client ID issued by Zscaler ZIdentity.
*   `ZSCALER_CLIENT_SECRET` — Client Secret issued by Zscaler ZIdentity.
*   `ZSCALER_TOKEN_URL` — Authentication login realm URL (e.g., `https://<your-tenant>.zslogin.net/oauth2/v1/token`).

### 2. Optional Target Credentials (Azure AD Example)
If the target chatbot requires authentication, define:
*   `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` (For OAuth2 client credentials).
*   `AZURE_TOKEN_URL` (Microsoft OAuth2 endpoint).

### 🔒 3. Optional 1Password Integration (Recommended)
Rather than setting plaintext environment variables, retrieve credentials securely on-the-fly using the 1Password CLI:
```bash
# Retrieve Zscaler Central Plane credentials
export ZSCALER_CLIENT_ID=$(op item get ZscalerAIRTClient --fields username)
export ZSCALER_CLIENT_SECRET=$(op item get ZscalerAIRTClient --fields password --reveal)

# Retrieve target-specific Azure AD credentials (if required)
export AZURE_CLIENT_ID=$(op item get AzureADChatbotCredentials --fields username)
export AZURE_CLIENT_SECRET=$(op item get AzureADChatbotCredentials --fields password --reveal)
```

---

## 🐳 Phase 2: Programmatic Broker Deployment & Verification

Deploying a broker programmatically allows the central testing gateway to route traffic into private enterprise enclaves without exposing the target directly to the internet.

### Requirements:
*   **Target Host OS:** Linux (Ubuntu Server recommended).
*   **Host Runtime:** Docker Engine active and configured for standard execution.
*   **Local Tooling:** `sshpass` installed on the executing machine (e.g. `brew install hudochenkov/sshpass/sshpass`).

### Deployment Command:
Run the deployment script to redeploy the container over SSH and automatically poll the central plane to verify that the broker transitions to `ONLINE` and `CONNECTED`:
```bash
python3 scripts/deploy_broker.py \
  --ssh-host "your-broker-host.example.com" \
  --ssh-port 22 \
  --ssh-user "ubuntu" \
  --ssh-pass "<SSH_PASSWORD>" \
  --broker-id "<BROKER_UUID>" \
  --token-url "$ZSCALER_TOKEN_URL" \
  --client-id "$ZSCALER_CLIENT_ID" \
  --client-secret "$ZSCALER_CLIENT_SECRET" \
  --ssl-verify "false"
```
*Note: Use `--ssl-verify "false"` when the target chatbot on the host is using a self-signed certificate.*

---

## 🛰️ Phase 3: Programmatic Connection Testing

Before submitting the final registration, verify that the broker can successfully tunnel and process handshakes with the target.

Run `test_connection.py` to test the routing path:
```bash
python3 scripts/test_connection.py \
  --url "https://chatbot.yourdomain.local/chat" \
  --broker-id "<BROKER_UUID>" \
  --token-url "$ZSCALER_TOKEN_URL" \
  --client-id "$ZSCALER_CLIENT_ID" \
  --client-secret "$ZSCALER_CLIENT_SECRET" \
  --payload-sample "{\"messages\":[{\"role\":\"user\",\"content\":\"{message}\"}],\"mode\":\"proxy\"}" \
  --response-path "$.reply" \
  --az-token-url "$AZURE_TOKEN_URL" \
  --az-client-id "$AZURE_CLIENT_ID" \
  --az-client-secret "$AZURE_CLIENT_SECRET"
```

*Ensure `--response-path` is updated to match your application's return schema (e.g. `$.reply` or `$.response`).*

---

## 🚀 Phase 4: Programmatic Target Onboarding

Once connection testing returns a clean success status, proceed to officially register the active target in the central control plane:

```bash
python3 scripts/onboard_target.py \
  --name "chatbot.yourdomain.local" \
  --url "https://chatbot.yourdomain.local/chat" \
  --broker-id "<BROKER_UUID>" \
  --bu-id "<BUSINESS_UNIT_UUID>" \
  --token-url "$ZSCALER_TOKEN_URL" \
  --client-id "$ZSCALER_CLIENT_ID" \
  --client-secret "$ZSCALER_CLIENT_SECRET" \
  --payload-sample "{\"messages\":[{\"role\":\"user\",\"content\":\"{message}\"}],\"mode\":\"proxy\"}" \
  --response-path "$.reply" \
  --env "DEV" \
  --rate-limit 50 \
  --az-token-url "$AZURE_TOKEN_URL" \
  --az-client-id "$AZURE_CLIENT_ID" \
  --az-client-secret "$AZURE_CLIENT_SECRET"
```
The script will output the official **AI Application ID** and confirm the active `CONNECTED` lifecycle status.
