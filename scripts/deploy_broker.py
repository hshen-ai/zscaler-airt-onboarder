#!/usr/bin/env python3
"""
deploy_broker.py
================
Deploys or redeploys the Zscaler AI Red Teaming broker container on a remote
Linux/Ubuntu host over SSH, and programmatically verifies its connection status.
"""

import sys
import os
import json
import ssl
import argparse
import subprocess
import urllib.request
import urllib.parse
import time

def parse_args():
    parser = argparse.ArgumentParser(description="Redeploy Zscaler Red Teaming Broker and verify online status.")
    # SSH Target
    parser.add_argument("--ssh-host", required=True, help="SSH hostname or IP of the remote broker server")
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port")
    parser.add_argument("--ssh-user", default="ubuntu", help="SSH username")
    parser.add_argument("--ssh-pass", required=True, help="SSH password")
    # Broker Configuration
    parser.add_argument("--broker-id", required=True, help="The UUID of the broker to deploy")
    parser.add_argument("--gateway-url", default="wss://web.api.aisecurity.zscaler.com/airt-broker-gateway/ws/broker", help="Zscaler Broker WebSocket Gateway URL")
    parser.add_argument("--token-url", required=True, help="OAuth Login Realm Token URL (ZIdentity)")
    parser.add_argument("--client-id", required=True, help="Client ID for Zscaler Central Plane Access")
    parser.add_argument("--client-secret", required=True, help="Client Secret for Zscaler Central Plane Access")
    parser.add_argument("--ssl-verify", default="true", choices=["true", "false"], help="Whether the broker validates target SSL certificates")
    return parser.parse_args()

def run_ssh_cmd(host, port, user, password, cmd):
    # Run SSH command cleanly via sshpass
    ssh_cmd = [
        "sshpass", "-p", password,
        "ssh", "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "IdentityAgent=none",
        "-o", "IdentitiesOnly=yes",
        f"{user}@{host}",
        cmd
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ SSH Execution failed with code {res.returncode}:\n{res.stderr}")
        sys.exit(1)
    return res.stdout.strip()

def get_zscaler_token(token_url, client_id, client_secret):
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": "https://api.zscaler.com"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=context) as res:
        return json.loads(res.read().decode("utf-8")).get("access_token")

def verify_broker_status(token, broker_id):
    url = "https://api.zsapi.net/private/aisecurity/airt/api/v2/brokers"
    req = urllib.request.Request(url, data=b"{}", headers={
        "Authorization": f"Bearer {token}",
        "X-Api-Version": "2.0",
        "Content-Type": "application/json"
    }, method="POST")
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=context) as res:
            brokers = json.loads(res.read().decode("utf-8")).get("items", [])
            for b in brokers:
                if b.get("id") == broker_id:
                    return b.get("status") == "ONLINE" and b.get("connectionStatus") == "CONNECTED"
    except Exception as e:
        print(f"⚠️ Warning: Could not query broker API: {e}")
    return False

def main():
    args = parse_args()
    
    # 1. Redeploy container on remote server
    docker_cmd = f"""
      docker rm -f airt-broker 2>/dev/null || true
      docker run -d --name airt-broker \\
        --restart unless-stopped \\
        --network host \\
        -e GATEWAY_URL="{args.gateway-url}" \\
        -e BROKER_ID="{args.broker-id}" \\
        -e OAUTH_TOKEN_URL="{args.token-url}" \\
        -e OAUTH_CLIENT_ID="{args.client-id}" \\
        -e OAUTH_CLIENT_SECRET="{args.client-secret}" \\
        -e SSL_VERIFY="{args.ssl-verify}" \\
        -e LOG_LEVEL="INFO" \\
        -e HEALTHZ_PORT="8080" \\
        public.ecr.aws/p0c4l9q3/platform/broker:1.0.0
    """
    print(f"🔌 [1/3] Connecting to remote host {args.ssh-host}:{args.ssh-port} via SSH...")
    container_id = run_ssh_cmd(args.ssh_host, args.ssh_port, args.ssh_user, args.ssh_pass, docker_cmd)
    print(f"   ✅ Broker container successfully spawned! ID: {container_id[:12]}")
    
    # 2. Get Access Token to verify
    print("\n🔑 [2/3] Generating central plane access token...")
    try:
        zs_token = get_zscaler_token(args.token_url, args.client_id, args.client_secret)
        print("   ✅ Access token generated.")
    except Exception as e:
        print(f"   ❌ Access token generation failed: {e}")
        sys.exit(1)
        
    # 3. Poll API to verify the broker connects back to gateway
    print("\n🛰️ [3/3] Polling Zscaler central plane to verify broker status...")
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        print(f"   Attempt {attempt}/{max_attempts}: Checking connection...")
        if verify_broker_status(zs_token, args.broker_id):
            print("\n🎉 SUCCESS! The broker is ONLINE and successfully CONNECTED to the central gateway!")
            sys.exit(0)
        time.sleep(3)
        
    print("\n❌ TIMEOUT: Broker was spawned locally but did not connect to the Zscaler gateway within 15 seconds.")
    print("   Please check the container logs on the host: 'docker logs airt-broker'")
    sys.exit(1)

if __name__ == "__main__":
    main()
