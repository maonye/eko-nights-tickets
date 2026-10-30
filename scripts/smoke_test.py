"""Call the deployed MCP endpoint directly, the way Chord will, before wiring up the teammate.

  PUBLIC_BASE_URL=https://your-app.onrender.com MCP_BEARER_TOKEN=... python scripts/smoke_test.py
"""
import json
import os

import httpx

base = os.environ["PUBLIC_BASE_URL"].rstrip("/")
headers = {"Authorization": f"Bearer {os.environ['MCP_BEARER_TOKEN']}",
           "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def rpc(method, params=None):
    r = httpx.post(f"{base}/mcp", headers=headers, timeout=60,
                   json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    r.raise_for_status()
    return r.json()


print("health:", httpx.get(f"{base}/health", timeout=60).json())
print("tools:", [t["name"] for t in rpc("tools/list")["result"]["tools"]])
res = rpc("tools/call", {"name": "list_events", "arguments": {}})["result"]
data = res.get("structuredContent") or json.loads(res["content"][0]["text"])
for e in data["events"]:
    print("-", e["name"], [(t["name"], t["remaining"]) for t in e["tiers"]])
