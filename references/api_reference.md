# Zscaler AI Red Teaming (AiRT) API Reference Manual
===================================================

This reference manual documents the REST specifications for interacting with the Zscaler AI Red Teaming (AiRT) central control plane. 

All API requests must route through Zscaler's OneAPI gateway (`api.zsapi.net`).

---

## 🔑 Authentication Specifications

Before calling any central plane endpoints, you must obtain an OAuth Bearer token from the ZIdentity login realm.

### 1. Zscaler ZIdentity token (Mandatory)
*   **Method:** `POST`
*   **URL:** `https://<your-tenant-domain>.zslogin.net/oauth2/v1/token`
    *(For example: `https://your-tenant.zslogin.net/oauth2/v1/token`)*
*   **Headers:**
    *   `Content-Type: application/x-www-form-urlencoded`
*   **Payload:**
    ```
    grant_type=client_credentials&client_id=<CLIENT_ID>&client_secret=<CLIENT_SECRET>&audience=https://api.zscaler.com`
    ```
*   **Response JSON:**
    ```json
    {
      "access_token": "eyJ0eXAi...",
      "token_type": "Bearer",
      "expires_in": 3600
    }
    ```

### 2. Optional Target Application Bearer Token (Azure AD Example)
If your target application requires authentication, you can programmatically generate and inject tokens into the target's request headers. Below is a reference implementation using Azure AD Client Credentials:
*   **Method:** `POST`
*   **URL:** `https://login.microsoftonline.com/<AZURE_TENANT_ID>/oauth2/v2.0/token`
*   **Headers:**
    *   `Content-Type: application/x-www-form-urlencoded`
*   **Payload:**
    ```
    grant_type=client_credentials&client_id=<AZURE_CLIENT_ID>&client_secret=<AZURE_CLIENT_SECRET>&scope=<AZURE_CLIENT_ID>/.default
    ```

---

## 🛸 Gateway Routing & Private Namespaces

Every administrative, broker-level, or app-level request made to the central plane V2 endpoints **must** adhere to these specific routing constraints:

1.  **Mandatory V2 Header:**
    You must include the following header in all requests. Without it, the gateway will return a silent `404 Not Found`.
    ```http
    X-Api-Version: 2.0
    ```

2.  **Private Namespace List Queries:**
    Standard public listing routes under `/api/v2/` are highly restricted. To query active brokers, business units, or existing applications, use the `/private` namespace under `POST` mapping with an empty JSON body:
    *   **Brokers:** `POST https://api.zsapi.net/private/aisecurity/airt/api/v2/brokers`
    *   **Business Units:** `POST https://api.zsapi.net/private/aisecurity/airt/api/v2/business-units`
    *   **AI Applications:** `POST https://api.zsapi.net/private/aisecurity/airt/api/v2/ai-apps`

---

## 📡 API Endpoints & Payload Schemas

### 1. Retrieve Active Brokers
*   **Method:** `POST`
*   **URL:** `https://api.zsapi.net/private/aisecurity/airt/api/v2/brokers`
*   **Headers:**
    *   `Authorization: Bearer <ZSCALER_TOKEN>`
    *   `X-Api-Version: 2.0`
    *   `Content-Type: application/json`
*   **Body:** `{}` (Sends empty JSON for unfiltered results)
*   **Response JSON:**
    ```json
    {
      "items": [
        {
          "id": "<BROKER_UUID>",
          "name": "my-local-broker",
          "connectionStatus": "CONNECTED",
          "status": "ONLINE",
          "lastSeenAt": "2026-07-16T12:02:11.624312Z",
          "brokerVersion": "1.0.0"
        }
      ],
      "totalItems": 1
    }
    ```

### 2. Test Connection Target (Integration Verification)
Tests routing and handshake to the private target via the broker gateway.
*   **Method:** `POST`
*   **URL:** `https://api.zsapi.net/private/aisecurity/airt/api/v2/ai-app/test-integration/rest-api`
*   **Headers:**
    *   `Authorization: Bearer <ZSCALER_TOKEN>`
    *   `X-Api-Version: 2.0`
    *   `Content-Type: application/json`
*   **Body:**
    ```json
    {
      "url": "https://chatbot.yourdomain.local/chat",
      "requestPayloadSample": "{\"messages\":[{\"role\":\"user\",\"content\":\"{message}\"}],\"mode\":\"proxy\"}",
      "responsePayload": "$.reply",
      "headers": {
        "Authorization": "Bearer <AZURE_AD_TOKEN_OR_ANY_OTHER_HEADER>"
      },
      "brokerId": "<BROKER_UUID>"
    }
    ```
*   **Response JSON (Success):**
    ```json
    {
      "error": "Connection Successful!",
      "errorDetails": [],
      "isSuccessful": true
    }
    ```

### 3. Create AI Application Target
Creates the active red-teaming target.
*   **Method:** `POST`
*   **URL:** `https://api.zsapi.net/private/aisecurity/airt/api/v2/ai-apps/create`
*   **Headers:**
    *   `Authorization: Bearer <ZSCALER_TOKEN>`
    *   `X-Api-Version: 2.0`
    *   `Content-Type: application/json`
*   **Body:**
    ```json
    {
      "businessUnitId": "<BUSINESS_UNIT_UUID>",
      "connection": {
        "type": "REST_API",
        "brokerId": "<BROKER_UUID>",
        "config": {
          "url": "https://chatbot.yourdomain.local/chat",
          "requestPayloadSample": "{\"messages\":[{\"role\":\"user\",\"content\":\"{message}\"}],\"mode\":\"proxy\"}",
          "responsePayload": "$.reply",
          "headers": {
            "Authorization": {
              "value": "Bearer <TOKEN_OR_KEY>",
              "sensitive": false
            }
          }
        }
      },
      "settings": {
        "name": "chatbot.yourdomain.local",
        "description": "Onboarded local chatbot target via Broker",
        "environment": "DEV",
        "language": "en",
        "rateLimit": 50,
        "concurrentRequests": false,
        "multiStepAttacks": false,
        "supportedModes": [ "TEXT" ],
        "withRag": false,
        "availability": "INTERNAL"
      }
    }
    ```
*   **Response JSON (Success):**
    ```json
    {
      "id": <AI_APP_ID>,
      "name": "chatbot.yourdomain.local",
      "connectionType": "REST_API",
      "environment": "DEV",
      "lifecycleStages": [
        {
          "type": "CONNECTED",
          "completed": true
        }
      ]
    }
    ```

---

## 🔍 Discovery of Platform Identifiers & Parameters

This section explains how to retrieve or dynamically discover all required identifier UUIDs and target parameter structures manually or programmatically.

### 1. How to Discover the Broker UUID (`<BROKER_UUID>`)
The Broker ID is a unique UUID that represents your deployed tunnel service.
*   **Manual Method:**
    Log in to the Zscaler AI Red Teaming Administration portal, navigate to **Settings -> Brokers**, and locate the copy icon next to your active broker's name.
*   **Programmatic Method:**
    Submit an authenticated `POST` request to the private brokers list endpoint:
    `POST https://api.zsapi.net/private/aisecurity/airt/api/v2/brokers` with an empty JSON body `{}`. Parse the response to extract:
    `items[].id` matching the broker name.

### 2. How to Discover the AI Application ID (`<AI_APP_ID>`)
The App ID is generated dynamically when you register a new chatbot target.
*   **Creation Response:**
    When you successfully run `onboard_target.py` or invoke the `POST /private/aisecurity/airt/api/v2/ai-apps/create` endpoint, the returned payload contains the `"id"` integer representing your newly generated App ID.
*   **Programmatic List Method:**
    To query all currently onboarded applications in your tenant, submit an authenticated `POST` to `https://api.zsapi.net/private/aisecurity/airt/api/v2/ai-apps` with body `{}`. Parse the output list for the `"id"` property.

### 3. How to Define Target Connection Parameters (URL, Payloads, response path)
Before testing or onboarding, you must define the target configuration details.
*   **Target Port & Protocol Discovery:**
    SSHs to the hosting Linux server and run a port scan or container audit (e.g. `docker ps` or `ss -tulpn | grep LISTEN`) to identify which ports (usually `80` or `443`) are bound to the host network interface. Use `https://` if the target binds to port `443` or has SSL enabled.
*   **API Schema Mapping:**
    *   **Manual Mapping:** Open the chatbot's local swagger documentation (e.g., `https://<chatbot-url>/docs` or `/redoc`) to find the exact HTTP path (e.g. `/v1/chat` or `/chat`), method (`POST` expected), and the required JSON input body payload template.
    *   **Programmatic Mapping:** Inject these details directly into your automated CLI scripts via the `--url`, `--payload-sample`, and `--response-path` arguments.
