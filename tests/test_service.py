from app.service import CHECKED_IN, PAID
from tests.conftest import BUYER, FRIEND, SIS


def buy(svc, **kw):
    args = dict(event_id="EVT-AFRO", tier_id="AFRO-REG", quantity=1, buyer_phone=BUYER)
    args.update(kw)
    return svc.create_order(**args)


def test_unverified_events_are_hidden_and_unsellable(env):
    svc, *_ = env
    ids = [e["event_id"] for e in svc.list_events()["events"]]
    assert "EVT-UNVERIFIED" not in ids and "EVT-AFRO" in ids
    r = svc.create_order(event_id="EVT-UNVERIFIED", tier_id="RAVE-REG", quantity=1, buyer_phone=BUYER)
    assert r["error"]["code"] == "EVENT_NOT_AVAILABLE"


def test_all_tickets_to_buyer_by_default(env):
    svc, ps, *_ = env
    o = buy(svc, quantity=3)
    assert o["ok"] and o["total"] == "₦45,000"
    assert o["ticket_holders"] == [{"phone": "+234 803 *** 4567", "is_buyer": True, "names": [], "tickets": 3}]
    ps.pay(o["reference"])
    paid = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    assert paid["status"] == PAID and len(paid["holders"][0]["tickets"]) == 3


def test_single_alternative_number_gets_everything(env):
    svc, ps, *_ = env
    o = buy(svc, quantity=2, recipients=[{"phone": FRIEND, "name": "Tobi"}])
    assert o["ticket_holders"][0]["is_buyer"] is False and o["ticket_holders"][0]["tickets"] == 2
    ps.pay(o["reference"])
    svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    assert len(svc.my_tickets(phone=FRIEND)["tickets"]) == 2
    assert svc.my_tickets(phone=BUYER)["tickets"] == []


def test_split_across_multiple_numbers(env):
    svc, ps, *_ = env
    o = buy(svc, quantity=3, recipients=[{"phone": "me"}, {"phone": FRIEND}, {"phone": SIS, "name": "Ada"}])
    assert o["ok"] and len(o["ticket_holders"]) == 3
    ps.pay(o["reference"])
    svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    for p in (BUYER, FRIEND, SIS):
        assert len(svc.my_tickets(phone=p)["tickets"]) == 1
    codes = {t["code"] for p in (BUYER, FRIEND, SIS) for t in svc.my_tickets(phone=p)["tickets"]}
    assert len(codes) == 3  # every holder gets a unique code


def test_recipient_count_mismatch_and_bad_numbers(env):
    svc, *_ = env
    assert buy(svc, quantity=3, recipients=[{"phone": FRIEND}, {"phone": SIS}])["error"]["code"] == "RECIPIENT_COUNT_MISMATCH"
    r = buy(svc, quantity=2, recipients=[{"phone": FRIEND}, {"phone": "12345"}])
    assert r["error"]["code"] == "INVALID_RECIPIENT_PHONE" and r["error"]["invalid"] == ["12345"]


def test_quantity_limits(env):
    svc, *_ = env
    assert buy(svc, quantity=0)["error"]["code"] == "INVALID_QUANTITY"
    assert buy(svc, quantity=7)["error"]["code"] == "INVALID_QUANTITY"


def test_hold_prevents_overselling_then_expires(env):
    svc, ps, clock, _ = env
    first = buy(svc, tier_id="COMEDY-FRONT", event_id="EVT-COMEDY", quantity=2)
    assert first["ok"]
    second = buy(svc, tier_id="COMEDY-FRONT", event_id="EVT-COMEDY", quantity=1, buyer_phone=FRIEND)
    assert second["error"]["code"] == "NOT_ENOUGH_TICKETS"
    clock.advance(16)
    assert buy(svc, tier_id="COMEDY-FRONT", event_id="EVT-COMEDY", quantity=1, buyer_phone=FRIEND)["ok"]
    r = svc.check_payment(reference=first["reference"], buyer_phone=BUYER)
    assert r["error"]["code"] == "HOLD_EXPIRED"


def test_payment_pending_then_failed(env):
    svc, ps, *_ = env
    o = buy(svc)
    pending = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    assert pending["status"] == "awaiting_payment" and pending["minutes_left"] == 15
    ps.pay(o["reference"], status="failed")
    r = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    assert r["error"]["code"] == "PAYMENT_FAILED"
    assert svc.my_tickets(phone=BUYER)["tickets"] == []


def test_idempotent_issue(env):
    svc, ps, _, store = env
    o = buy(svc, quantity=2)
    ps.pay(o["reference"])
    a = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    b = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    svc.confirm_from_provider(o["reference"])
    assert a["already_confirmed"] is False and b["already_confirmed"] is True
    assert len(store.all("tickets")) == 2


def test_amount_mismatch_needs_review(env):
    svc, ps, *_ = env
    o = buy(svc)
    ps.pay(o["reference"], amount_kobo=100)
    r = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    assert r["error"]["code"] == "NEEDS_REVIEW" and r["error"]["escalate"] is True
    assert svc.my_tickets(phone=BUYER)["tickets"] == []


def test_late_payment_after_sell_out_escalates(env):
    svc, ps, clock, _ = env
    o = buy(svc, tier_id="COMEDY-FRONT", event_id="EVT-COMEDY", quantity=2)
    clock.advance(16)
    svc.list_events()  # expires the hold
    other = buy(svc, tier_id="COMEDY-FRONT", event_id="EVT-COMEDY", quantity=2, buyer_phone=FRIEND)
    ps.pay(other["reference"])
    svc.check_payment(reference=other["reference"], buyer_phone=FRIEND)
    ps.pay(o["reference"])  # the first buyer pays late
    r = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)
    assert r["error"]["code"] == "NEEDS_REVIEW"


def test_late_payment_with_stock_left_is_honoured(env):
    svc, ps, clock, _ = env
    o = buy(svc)
    clock.advance(20)
    ps.pay(o["reference"])
    assert svc.check_payment(reference=o["reference"], buyer_phone=BUYER)["status"] == PAID


def test_only_buyer_can_check_or_cancel(env):
    svc, *_ = env
    o = buy(svc)
    assert svc.check_payment(reference=o["reference"], buyer_phone=FRIEND)["error"]["code"] == "NOT_YOUR_ORDER"
    assert svc.cancel_order(reference=o["reference"], buyer_phone=FRIEND)["error"]["code"] == "NOT_YOUR_ORDER"


def test_cancel_releases_but_not_if_just_paid(env):
    svc, ps, *_ = env
    o = buy(svc)
    assert svc.cancel_order(reference=o["reference"], buyer_phone=BUYER)["status"] == "cancelled"
    o2 = buy(svc)
    ps.pay(o2["reference"])
    assert svc.cancel_order(reference=o2["reference"], buyer_phone=BUYER)["error"]["code"] == "ALREADY_PAID"


def test_provider_outage(env):
    svc, ps, *_ = env
    ps.fail_initialize = True
    assert buy(svc)["error"]["code"] == "PAYMENT_PROVIDER_UNAVAILABLE"
    ps.fail_initialize = False
    o = buy(svc)
    ps.fail_verify = True
    assert svc.check_payment(reference=o["reference"], buyer_phone=BUYER)["error"]["code"] == "PAYMENT_PROVIDER_UNAVAILABLE"
    assert svc.cancel_order(reference=o["reference"], buyer_phone=BUYER)["error"]["code"] == "PAYMENT_PROVIDER_UNAVAILABLE"


def test_gate_check_in(env):
    svc, ps, *_ = env
    o = buy(svc)
    ps.pay(o["reference"])
    code = svc.check_payment(reference=o["reference"], buyer_phone=BUYER)["holders"][0]["tickets"][0]["code"]
    assert svc.check_in(code=code, staff_pin="0000")["error"]["code"] == "NOT_AUTHORISED"
    first = svc.check_in(code=code.lower().replace("-", " "), staff_pin="0604")
    assert first["result"] == "ADMIT" and first["ticket"]["status"] == CHECKED_IN
    again = svc.check_in(code=code, staff_pin="0604")
    assert again["result"] == "REJECT" and again["reason"] == "Already used"
    assert svc.check_in(code="EKO-FAKE-CODE", staff_pin="0604")["result"] == "REJECT"


def test_reference_is_not_extractable_from_payment_url(env):
    svc, *_ = env
    o = buy(svc)
    assert o["ok"]
    # Real Paystack URLs end with an access code, not the merchant reference. The agent must save
    # the reference from the create_order result instead of reading it from the URL.
    url_path = o["payment_url"].split("?")[0].rsplit("/", 1)[-1]
    assert url_path != o["reference"]
    assert o["reference"].startswith("EKO-")
    assert "reference=" + o["reference"] in o["payment_url"]


def test_paystack_metadata_includes_order_details(env):
    svc, ps, *_ = env
    o = buy(svc, quantity=3)
    assert o["ok"]
    assert ps.last_metadata == {
        "order_id": o["order_id"],
        "event_id": "EVT-AFRO",
        "tier_id": "AFRO-REG",
        "quantity": 3,
        "buyer_phone": "+2348031234567",
    }
