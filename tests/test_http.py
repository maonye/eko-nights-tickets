"""End-to-end over HTTP: MCP tool calls through the real Streamable HTTP transport, webhook, pages."""
import hashlib
import hmac
import json

import anyio
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.paystack import FakePaystack
from app.seed import seed_memory
from app.service import TicketService
from app.store import MemoryStore
from tests.conftest import BUYER, make_settings

HEADERS = {"Authorization": "Bearer secret-token", "Accept": "application/json, text/event-stream",
           "Content-Type": "application/json"}


@pytest.fixture
def client():
    store = MemoryStore(); seed_memory(store)
    ps = FakePaystack()
    svc = TicketService(store, ps, make_settings())
    with TestClient(create_app(svc, make_settings())) as c:
        yield c, ps


def rpc(c, method, params=None, id_=1):
    r = c.post("/mcp", headers=HEADERS, json={"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}})
    assert r.status_code == 200, r.text
    return r.json()


def call(c, name, args):
    res = rpc(c, "tools/call", {"name": name, "arguments": args})["result"]
    assert not res.get("isError"), res
    return res.get("structuredContent") or json.loads(res["content"][0]["text"])


def test_requires_bearer(client):
    c, _ = client
    r = c.post("/mcp", headers={**HEADERS, "Authorization": "Bearer wrong"}, json={})
    assert r.status_code == 401


def test_full_flow_over_mcp(client):
    c, ps = client
    init = rpc(c, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "test", "version": "1"}})
    assert init["result"]["serverInfo"]["name"] == "Eko Nights Tickets"
    names = {t["name"] for t in rpc(c, "tools/list")["result"]["tools"]}
    assert names == {"list_events", "create_order", "check_payment", "my_tickets", "cancel_order", "check_in"}

    events = call(c, "list_events", {})
    assert events["ok"]
    order = call(c, "create_order", {"event_id": "EVT-AFRO", "tier_id": "AFRO-VIP", "quantity": 2,
                                     "buyer_phone": BUYER, "recipients": [{"phone": "me"}, {"phone": "08120001111", "name": "Tobi"}]})
    assert order["ok"], order
    ps.pay(order["reference"])

    # Paystack webhook with a valid signature issues the tickets
    body = json.dumps({"event": "charge.success", "data": {"reference": order["reference"]}}).encode()
    sig = hmac.new(b"sk_test_fake", body, hashlib.sha512).hexdigest()
    assert c.post("/webhooks/paystack", content=body, headers={"x-paystack-signature": "bad"}).status_code == 401
    assert c.post("/webhooks/paystack", content=body, headers={"x-paystack-signature": sig}).status_code == 200

    paid = call(c, "check_payment", {"reference": order["reference"], "buyer_phone": BUYER})
    assert paid["already_confirmed"] is True
    code = paid["holders"][0]["tickets"][0]["code"]

    page = c.get(f"/t/{code}")
    assert page.status_code == 200 and code in page.text and "<svg" in page.text
    assert c.get("/t/EKO-NOPE-NOPE").status_code == 404
    assert "Payment received" in c.get(f"/paid?reference={order['reference']}").text

    gate = call(c, "check_in", {"code": code, "staff_pin": "4321"})
    assert gate["result"] == "ADMIT"
    assert call(c, "check_in", {"code": code, "staff_pin": "4321"})["result"] == "REJECT"
