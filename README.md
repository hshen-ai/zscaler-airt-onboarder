# Zscaler AI Red Teaming (AiRT) Onboarder Skill
===============================================

An enterprise-grade, programmatic automation skill for the **Zscaler AI Red Teaming (AiRT)** platform. This skill enables engineers and AI agents to programmatically deploy brokers, execute diagnostic connectivity tests, and register active generative AI chatbot targets on the central plane.

---

## 🧭 Directory of Included Assets

*   `SKILL.md`: Core AI instructions and workflow triggers (for Gemini CLI).
*   `references/api_reference.md`: Comprehensive OneAPI gateway schemas, private namespaces, and token verification guidelines.
*   `scripts/deploy_broker.py`: Spawns/re-creates the broker container over SSH and polls the central API to verify connection status.
*   `scripts/test_connection.py`: Handshakes and tests routing paths to the target application through the broker.
*   `scripts/onboard_target.py`: Formulates target settings and registers the target under Zscaler.

---

## 📋 Prerequisites

To execute the deployment and testing scripts, the local machine must have:
1.  **Python 3.10+**
2.  **`sshpass`** (For automated SSH password injection. Install on macOS via `brew install hudochenkov/sshpass/sshpass`).
3.  **Active Docker service** running on the target remote host.

---

## ⚙️ Quick Installation

### Install globally under your user account:
```bash
gemini skills install https://github.com/your-username/zscaler-airt-onboarder.git
```

### Enable the skill in your active session:
```bash
/skills reload
```

---

## 🔑 Operational Flow

### Phase 1: Set Zscaler ZIdentity Credentials
```bash
export ZSCALER_CLIENT_ID="your-client-id"
export ZSCALER_CLIENT_SECRET="your-client-secret"
export ZSCALER_TOKEN_URL="https://<your-tenant>.zslogin.net/oauth2/v1/token"
```

### Phase 2: Programmatically Deploy and Verify a Broker
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

### Phase 3: Execute Connection Testing
```bash
python3 scripts/test_connection.py \
  --url "https://chatbot.yourdomain.local/chat" \
  --broker-id "<BROKER_UUID>" \
  --token-url "$ZSCALER_TOKEN_URL" \
  --client-id "$ZSCALER_CLIENT_ID" \
  --client-secret "$ZSCALER_CLIENT_SECRET"
```

### Phase 4: Register Target Onboarding
```bash
python3 scripts/onboard_target.py \
  --name "my-chatbot" \
  --url "https://chatbot.yourdomain.local/chat" \
  --broker-id "<BROKER_UUID>" \
  --bu-id "<BUSINESS_UNIT_UUID>" \
  --token-url "$ZSCALER_TOKEN_URL" \
  --client-id "$ZSCALER_CLIENT_ID" \
  --client-secret "$ZSCALER_CLIENT_SECRET"
```
