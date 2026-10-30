"""Ticketing logic for the Eko Nights WhatsApp agent.

Every public method returns a plain dict. Failures come back as
{"ok": False, "error": {"code", "message", "next_step"}} rather than
exceptions, so the agent can read the problem and tell the customer
what to do next instead of going quiet.
"""
from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime, timedelta, timezone

from .paystack import PaystackError
from .phone import InvalidPhone, mask_phone, normalise_phone

LAGOS = timezone(timedelta(hours=1))
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, easier to read aloud at a gate

# Order statuses
PENDING = "pending_payment"
PAID = "paid"
EXPIRED = "expired"
FAILED = "payment_failed"
CANCELLED = "cancelled"
INIT_FAILED = "init_failed"
NEEDS_REVIEW = "needs_review"   # money received but something is wrong; a human must act

# Ticket statuses
VALID = "valid"
CHECKED_IN = "checked_in"
VOID = "void"



def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse(ts: str) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _truthy(v: str) -> bool:
    return str(v).strip().lower() in {"true", "yes", "1"}


def _naira(amount_kobo: int) -> str:
    return f"₦{amount_kobo // 100:,}"


def _lagos_time(ts: str) -> str:
    dt = _parse(ts)
    return dt.astimezone(LAGOS).strftime("%a %d %b %Y, %I:%M %p (Lagos time)") if dt else ""


def error(code: str, message: str, next_step: str, **extra) -> dict:
    return {"ok": False, "error": {"code": code, "message": message, "next_step": next_step, **extra}}


class TicketService:
    def __init__(self, store, paystack, settings, clock=_now) -> None:
        self.store = store
        self.paystack = paystack
        self.settings = settings
        self.clock = clock
        # One lock around inventory changes. Fine for a single instance; see README for scaling.
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ reads

    def _events(self) -> dict[str, dict]:
        return {e["event_id"]: e for e in self.store.all("events")}

    def _tiers(self) -> dict[str, dict]:
        return {t["tier_id"]: t for t in self.store.all("tiers")}

    def _orders(self) -> list[dict]:
        return self.store.all("orders")

    def _expire_stale_holds(self, orders: list[dict]) -> list[dict]:
        now = self.clock()
        for o in orders:
            if o["status"] == PENDING:
                exp = _parse(o["expires_at"])
                if exp and exp <= now:
                    self.store.update("orders", "order_id", o["order_id"], {"status": EXPIRED})
                    o["status"] = EXPIRED
        return orders

    def _remaining(self, tier: dict, orders: list[dict], exclude_order: str | None = None) -> int:
        used = 0
        for o in orders:
            if o["tier_id"] != tier["tier_id"] or o["order_id"] == exclude_order:
                continue
            if o["status"] in (PAID, PENDING, NEEDS_REVIEW):
                used += int(o["quantity"] or 0)
        return max(int(tier["capacity"] or 0) - used, 0)

    def list_events(self) -> dict:
        events, tiers = self._events(), self._tiers()
        orders = self._expire_stale_holds(self._orders())
        out = []
        for e in events.values():
            if not (_truthy(e["verified"]) and _truthy(e["on_sale"])):
                continue  # never offer unverified events
            ev_tiers = []
            for t in tiers.values():
                if t["event_id"] != e["event_id"]:
                    continue
                left = self._remaining(t, orders)
                ev_tiers.append({
                    "tier_id": t["tier_id"], "name": t["name"],
                    "price": _naira(int(t["price_ngn"]) * 100), "price_ngn": int(t["price_ngn"]),
                    "perks": t["perks"], "max_per_order": int(t["max_per_order"]),
                    "remaining": left, "sold_out": left == 0,
                })
            out.append({
                "event_id": e["event_id"], "name": e["name"], "venue": e["venue"],
                "starts": _lagos_time(e["starts_at"]), "doors_open": e["doors_open"],
                "age_limit": e["age_limit"], "description": e["description"],
                "verified_organiser": e["organiser"], "tiers": ev_tiers,
            })
        return {"ok": True, "events": out}

    # ----------------------------------------------------------- create order

    def create_order(self, *, event_id: str, tier_id: str, quantity: int, buyer_phone: str,
                     recipients: list[dict] | None = None, buyer_email: str | None = None) -> dict:
        try:
            buyer = normalise_phone(buyer_phone)
        except InvalidPhone as exc:
            return error("INVALID_BUYER_PHONE", str(exc), "Ask the customer to confirm their WhatsApp number.")

        events, tiers = self._events(), self._tiers()
        event, tier = events.get(event_id), tiers.get(tier_id)
        if not event:
            return error("EVENT_NOT_FOUND", f"No event with id {event_id}", "Call list_events and use an event_id from it.")
        if not (_truthy(event["verified"]) and _truthy(event["on_sale"])):
            return error("EVENT_NOT_AVAILABLE", "This event is not verified or not on sale.",
                         "Tell the customer we only sell tickets for verified events and offer the ones we have.")
        if not tier or tier["event_id"] != event_id:
            return error("TIER_NOT_FOUND", f"Tier {tier_id} is not part of {event_id}", "Call list_events and pick a tier from that event.")

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return error("INVALID_QUANTITY", "Quantity must be a whole number.", "Ask how many tickets they want.")
        max_per_order = int(tier["max_per_order"])
        if quantity < 1 or quantity > max_per_order:
            return error("INVALID_QUANTITY", f"Quantity must be between 1 and {max_per_order} for {tier['name']}.",
                         f"Ask the customer to choose 1 to {max_per_order} tickets, or split into separate orders.")

        assignment = self._assign(buyer, quantity, recipients or [])
        if not assignment["ok"]:
            return assignment
        slots = assignment["slots"]

        with self._lock:
            orders = self._expire_stale_holds(self._orders())
            left = self._remaining(tier, orders)
            if left < quantity:
                return error("NOT_ENOUGH_TICKETS",
                             f"Only {left} {tier['name']} ticket(s) left." if left else f"{tier['name']} is sold out.",
                             "Offer the remaining quantity or another tier from list_events.", remaining=left)

            now = self.clock()
            order_id = "ORD-" + secrets.token_hex(4).upper()
            reference = f"EKO-{order_id[4:]}-{secrets.token_hex(2).upper()}"
            amount_kobo = int(tier["price_ngn"]) * 100 * quantity
            expires = now + timedelta(minutes=self.settings.hold_minutes)
            self.store.append("orders", {
                "order_id": order_id, "reference": reference, "event_id": event_id, "tier_id": tier_id,
                "quantity": quantity, "buyer_phone": buyer, "buyer_email": buyer_email or "",
                "recipients_json": json.dumps(slots), "amount_kobo": amount_kobo, "status": PENDING,
                "paystack_status": "", "payment_url": "", "created_at": _iso(now),
                "expires_at": _iso(expires), "paid_at": "", "note": "",
            })

        email = buyer_email or f"{buyer.lstrip('+')}@{self.settings.placeholder_email_domain}"
        try:
            url = self.paystack.initialize(
                email=email, amount_kobo=amount_kobo, reference=reference,
                callback_url=f"{self.settings.public_base_url}/paid", currency=self.settings.currency,
                metadata={"order_id": order_id, "event_id": event_id, "tier_id": tier_id,
                          "quantity": quantity, "buyer_phone": buyer},
            )
        except PaystackError as exc:
            self.store.update("orders", "order_id", order_id, {"status": INIT_FAILED, "note": str(exc)[:200]})
            return error("PAYMENT_PROVIDER_UNAVAILABLE",
                         "We could not open a payment page just now. No money has been taken and the tickets have been released.",
                         "Apologise, and offer to try again in a minute.")

        self.store.update("orders", "order_id", order_id, {"payment_url": url})
        return {
            "ok": True, "order_id": order_id, "reference": reference, "payment_url": url,
            "event": event["name"], "tier": tier["name"], "quantity": quantity,
            "total": _naira(amount_kobo), "hold_expires": _lagos_time(_iso(expires)),
            "hold_minutes": self.settings.hold_minutes,
            "ticket_holders": self._summarise_slots(slots, buyer),
        }

    def _assign(self, buyer: str, quantity: int, recipients: list[dict]) -> dict:
        """Work out who holds each ticket.

        * no recipients: every ticket goes to the buyer
        * one recipient: every ticket goes to that number
        * several recipients: one entry per ticket (the buyer can be one of them)
        """
        if not recipients:
            return {"ok": True, "slots": [{"phone": buyer, "name": ""} for _ in range(quantity)]}
        cleaned, bad = [], []
        for r in recipients:
            raw = r.get("phone") if isinstance(r, dict) else r
            name = (r.get("name") or "").strip() if isinstance(r, dict) else ""
            if isinstance(raw, str) and raw.strip().lower() in {"me", "self", "buyer", "my number"}:
                cleaned.append({"phone": buyer, "name": name})
                continue
            try:
                cleaned.append({"phone": normalise_phone(raw), "name": name})
            except InvalidPhone:
                bad.append(str(raw))
        if bad:
            return error("INVALID_RECIPIENT_PHONE", f"These numbers are not valid: {', '.join(bad)}",
                         "Ask the customer to re-send those numbers, for example 0803 123 4567.", invalid=bad)
        if len(cleaned) == 1:
            return {"ok": True, "slots": [dict(cleaned[0]) for _ in range(quantity)]}
        if len(cleaned) != quantity:
            return error("RECIPIENT_COUNT_MISMATCH",
                         f"{quantity} ticket(s) but {len(cleaned)} recipients were given.",
                         "Give exactly one number per ticket (use the buyer's number for their own), or a single number for all of them.")
        return {"ok": True, "slots": cleaned}

    @staticmethod
    def _summarise_slots(slots: list[dict], buyer: str) -> list[dict]:
        counts: dict[str, dict] = {}
        for s in slots:
            entry = counts.setdefault(s["phone"], {"phone": mask_phone(s["phone"]), "is_buyer": s["phone"] == buyer,
                                                   "names": [], "tickets": 0})
            entry["tickets"] += 1
            if s["name"]:
                entry["names"].append(s["name"])
        return list(counts.values())

    # ---------------------------------------------------------- payment check

    def _find_order(self, reference: str) -> dict | None:
        ref = (reference or "").strip().upper()
        for o in self._orders():
            if o["reference"].upper() == ref or o["order_id"].upper() == ref:
                return o
        return None

    def check_payment(self, *, reference: str, buyer_phone: str) -> dict:
        order = self._find_order(reference)
        if not order:
            return error("ORDER_NOT_FOUND", f"No order with reference {reference}.",
                         "Ask the customer for the reference from their payment message, or start a new order.")
        try:
            caller = normalise_phone(buyer_phone)
        except InvalidPhone:
            caller = ""
        if caller != order["buyer_phone"]:
            # Do not reveal ticket codes to someone other than the buyer.
            return error("NOT_YOUR_ORDER", "This order was placed from a different number.",
                         "Only the buyer can check this order. Recipients can ask for their tickets with my_tickets.")
        return self._settle(order)

    def confirm_from_provider(self, reference: str) -> dict:
        """Used by the Paystack webhook and the post-payment redirect. Never returns codes."""
        order = self._find_order(reference)
        if not order:
            return {"ok": False, "reason": "unknown reference"}
        result = self._settle(order)
        return {"ok": result.get("ok", False), "status": result.get("status") or result.get("error", {}).get("code")}

    def _settle(self, order: dict) -> dict:
        with self._lock:
            order = self._find_order(order["reference"])  # re-read inside the lock
            if order["status"] == PAID:
                return self._paid_response(order, already=True)
            if order["status"] in (CANCELLED, INIT_FAILED):
                return error("ORDER_CLOSED", f"This order is {order['status'].replace('_', ' ')}.",
                             "Offer to start a new order.")
            if order["status"] == NEEDS_REVIEW:
                return error("NEEDS_REVIEW", "Payment was received but needs a quick check by the Eko Nights team.",
                             "Reassure the customer their money is safe and hand over to a human.", escalate=True)

            try:
                result = self.paystack.verify(order["reference"])
            except PaystackError:
                return error("PAYMENT_PROVIDER_UNAVAILABLE", "We could not confirm the payment with Paystack just now.",
                             "Ask the customer to wait a minute, then check again. Do not tell them it failed.")

            self.store.update("orders", "order_id", order["order_id"], {"paystack_status": result.status})
            expected = int(order["amount_kobo"])

            if result.status == "success":
                if result.amount_kobo != expected or result.currency.upper() != self.settings.currency:
                    self.store.update("orders", "order_id", order["order_id"], {
                        "status": NEEDS_REVIEW,
                        "note": f"Amount mismatch: expected {expected} got {result.amount_kobo} {result.currency}"})
                    return error("NEEDS_REVIEW", "The amount paid does not match the order.",
                                 "Do not issue tickets. Reassure the customer and hand over to a human.", escalate=True)
                orders = self._orders()
                tier = self._tiers()[order["tier_id"]]
                if order["status"] in (EXPIRED, FAILED) and self._remaining(tier, orders, exclude_order=order["order_id"]) < int(order["quantity"]):
                    self.store.update("orders", "order_id", order["order_id"], {
                        "status": NEEDS_REVIEW, "note": "Paid after hold expired and tier is now full. Refund or upgrade."})
                    return error("NEEDS_REVIEW", "Payment arrived after the hold expired and those tickets have since sold.",
                                 "Apologise, say the team will refund or offer an alternative today, and hand over to a human.",
                                 escalate=True)
                self._issue(order)
                self.store.update("orders", "order_id", order["order_id"], {
                    "status": PAID, "paid_at": result.paid_at or _iso(self.clock())})
                order = self._find_order(order["reference"])
                return self._paid_response(order, already=False)

            if result.status in ("failed", "reversed"):
                self.store.update("orders", "order_id", order["order_id"], {"status": FAILED,
                                                                            "note": result.gateway_response[:200]})
                return error("PAYMENT_FAILED", f"Paystack reports the payment {result.status}"
                             + (f" ({result.gateway_response})." if result.gateway_response else "."),
                             "No tickets were issued. Offer to start a fresh order, perhaps with a different card or bank transfer.",
                             status=FAILED)

            # Not paid yet
            exp = _parse(order["expires_at"])
            if order["status"] == EXPIRED or (exp and exp <= self.clock()):
                self.store.update("orders", "order_id", order["order_id"], {"status": EXPIRED})
                return error("HOLD_EXPIRED", "The payment window closed before payment was completed. The tickets were released.",
                             "Offer to start a new order.", status=EXPIRED)
            minutes_left = max(int((exp - self.clock()).total_seconds() // 60), 0) if exp else 0
            return {"ok": True, "status": "awaiting_payment", "reference": order["reference"],
                    "payment_url": order["payment_url"], "minutes_left": minutes_left,
                    "message": "Payment not completed yet. The tickets are still held."}

    def _issue(self, order: dict) -> None:
        existing = [t for t in self.store.all("tickets") if t["order_id"] == order["order_id"]]
        if existing:
            return  # idempotent: never issue twice
        slots = json.loads(order["recipients_json"] or "[]")
        now = _iso(self.clock())
        rows = []
        for s in slots:
            rows.append({
                "ticket_id": "TKT-" + secrets.token_hex(4).upper(), "code": self._new_code(),
                "order_id": order["order_id"], "event_id": order["event_id"], "tier_id": order["tier_id"],
                "holder_phone": s["phone"], "holder_name": s.get("name", ""), "status": VALID,
                "issued_at": now, "checked_in_at": "",
            })
        self.store.append_many("tickets", rows)

    @staticmethod
    def _new_code() -> str:
        raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
        return f"EKO-{raw[:4]}-{raw[4:]}"

    def _ticket_view(self, t: dict, events: dict, tiers: dict) -> dict:
        e, tr = events.get(t["event_id"], {}), tiers.get(t["tier_id"], {})
        return {"code": t["code"], "event": e.get("name", ""), "tier": tr.get("name", ""),
                "starts": _lagos_time(e.get("starts_at", "")), "venue": e.get("venue", ""),
                "holder": mask_phone(t["holder_phone"]), "holder_name": t["holder_name"],
                "status": t["status"], "link": f"{self.settings.public_base_url}/t/{t['code']}"}

    def _paid_response(self, order: dict, already: bool) -> dict:
        events, tiers = self._events(), self._tiers()
        tickets = [t for t in self.store.all("tickets") if t["order_id"] == order["order_id"]]
        by_holder: dict[str, dict] = {}
        for t in tickets:
            h = by_holder.setdefault(t["holder_phone"], {
                "holder": mask_phone(t["holder_phone"]), "is_buyer": t["holder_phone"] == order["buyer_phone"],
                "tickets": []})
            h["tickets"].append(self._ticket_view(t, events, tiers))
        return {"ok": True, "status": PAID, "already_confirmed": already, "reference": order["reference"],
                "total": _naira(int(order["amount_kobo"])), "holders": list(by_holder.values()),
                "recipient_note": "Recipients who are not the buyer can message this WhatsApp number and ask for "
                                  "'my tickets' to receive theirs."}

    # --------------------------------------------------------------- tickets

    def my_tickets(self, *, phone: str) -> dict:
        try:
            holder = normalise_phone(phone)
        except InvalidPhone as exc:
            return error("INVALID_PHONE", str(exc), "Ask the customer to confirm their WhatsApp number.")
        events, tiers = self._events(), self._tiers()
        tickets = [self._ticket_view(t, events, tiers) for t in self.store.all("tickets")
                   if t["holder_phone"] == holder and t["status"] != VOID]
        if not tickets:
            return {"ok": True, "tickets": [], "message": "No tickets are held by this number."}
        return {"ok": True, "tickets": tickets}

    def cancel_order(self, *, reference: str, buyer_phone: str) -> dict:
        order = self._find_order(reference)
        if not order:
            return error("ORDER_NOT_FOUND", f"No order with reference {reference}.", "Check the reference.")
        try:
            caller = normalise_phone(buyer_phone)
        except InvalidPhone:
            caller = ""
        if caller != order["buyer_phone"]:
            return error("NOT_YOUR_ORDER", "This order was placed from a different number.", "Only the buyer can cancel it.")
        if order["status"] != PENDING:
            return error("CANNOT_CANCEL", f"The order is {order['status'].replace('_', ' ')}, so it cannot be cancelled here.",
                         "Paid orders follow the refund policy; hand over to a human if they want a refund.")
        # Make sure the customer did not pay a moment ago.
        settled = self._settle(order)
        if settled.get("status") == PAID:
            return error("ALREADY_PAID", "This order has just been paid, so it was not cancelled.",
                         "Share the tickets from this result.", tickets=settled)
        code = settled.get("error", {}).get("code")
        if code in ("NEEDS_REVIEW", "PAYMENT_PROVIDER_UNAVAILABLE"):
            # Money may have moved; never cancel blind.
            return settled
        self.store.update("orders", "order_id", order["order_id"], {"status": CANCELLED})
        return {"ok": True, "status": CANCELLED, "message": "Order cancelled and tickets released. No money was taken."}

    # --------------------------------------------------------------- gate

    def check_in(self, *, code: str, staff_pin: str) -> dict:
        if not secrets.compare_digest(str(staff_pin or ""), self.settings.staff_pin):
            return error("NOT_AUTHORISED", "Gate check-in needs a valid staff PIN.",
                         "If this is a customer, explain that only gate staff can check tickets in.")
        wanted = "".join(ch for ch in str(code).upper() if ch.isalnum())
        with self._lock:
            for t in self.store.all("tickets"):
                if "".join(ch for ch in t["code"] if ch.isalnum()) != wanted:
                    continue
                events, tiers = self._events(), self._tiers()
                view = self._ticket_view(t, events, tiers)
                if t["status"] == VOID:
                    return {"ok": True, "result": "REJECT", "reason": "Ticket has been voided.", "ticket": view}
                if t["status"] == CHECKED_IN:
                    return {"ok": True, "result": "REJECT", "reason": "Already used",
                            "checked_in_at": _lagos_time(t["checked_in_at"]), "ticket": view}
                self.store.update("tickets", "ticket_id", t["ticket_id"],
                                  {"status": CHECKED_IN, "checked_in_at": _iso(self.clock())})
                view["status"] = CHECKED_IN
                return {"ok": True, "result": "ADMIT", "ticket": view}
        return {"ok": True, "result": "REJECT", "reason": "Unknown code. Possibly fake or mistyped."}

    def ticket_by_code(self, code: str) -> dict | None:
        wanted = "".join(ch for ch in str(code).upper() if ch.isalnum())
        for t in self.store.all("tickets"):
            if "".join(ch for ch in t["code"] if ch.isalnum()) == wanted:
                return self._ticket_view(t, self._events(), self._tiers())
        return None
