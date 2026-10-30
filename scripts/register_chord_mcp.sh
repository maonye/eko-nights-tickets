#!/usr/bin/env bash
# Register the deployed tool server with Chord, following docs/mcp-servers in the Chord API docs.
# You can do the same in the Chord app (Teammate settings > Tools > Add tool) instead.
#
# Needs: CHORD_API_KEY (with mcp:create, mcp:read, mcp:manage, teammate:read, teammate:update),
#        CHORD_WORKSPACE_ID, CHORD_TEAMMATE_ID, PUBLIC_BASE_URL, MCP_BEARER_TOKEN
set -euo pipefail
: "${CHORD_BASE_URL:=https://api.chordhq.xyz}"
H=(-H "Authorization: Bearer $CHORD_API_KEY" -H "Content-Type: application/json")

echo "1. Registering (disabled) ..."
SERVER=$(curl -sS -X POST "$CHORD_BASE_URL/v1/workspaces/$CHORD_WORKSPACE_ID/mcp-servers" "${H[@]}" \
  --data "{\"name\":\"Eko Nights tickets\",\"url\":\"$PUBLIC_BASE_URL/mcp\",\"auth_type\":\"bearer\",
           \"auth_token\":\"$MCP_BEARER_TOKEN\",\"transport\":\"streamable_http\",\"enabled\":false}")
echo "$SERVER"
ID=$(echo "$SERVER" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

echo "2. Restricting the teammate to this server (an empty list means ALL enabled servers) ..."
curl -sS -X PUT "$CHORD_BASE_URL/v1/teammates/$CHORD_TEAMMATE_ID" "${H[@]}" \
  --data "{\"add_mcp_server_ids\":[\"$ID\"]}" > /dev/null

echo "3. Enabling with an explicit tool allowlist ..."
curl -sS -X PUT "$CHORD_BASE_URL/v1/workspaces/$CHORD_WORKSPACE_ID/mcp-servers/$ID" "${H[@]}" \
  --data '{"enabled":true,"enabled_tools":["list_events","create_order","check_payment","my_tickets","cancel_order","check_in"]}' > /dev/null

echo "4. Discovering tools ..."
curl -sS -X POST "$CHORD_BASE_URL/v1/workspaces/$CHORD_WORKSPACE_ID/mcp-servers/$ID/tools" \
  -H "Authorization: Bearer $CHORD_API_KEY" | python3 -c 'import sys,json;[print(" -",t["name"]) for t in json.load(sys.stdin)]'

echo "5. Health (check status, HTTP 200 can still mean failure) ..."
curl -sS -X POST "$CHORD_BASE_URL/v1/workspaces/$CHORD_WORKSPACE_ID/mcp-servers/$ID/health" \
  -H "Authorization: Bearer $CHORD_API_KEY"; echo
echo "Server id: $ID"
