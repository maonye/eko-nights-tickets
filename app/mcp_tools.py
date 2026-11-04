"""MCP tools that Chord calls. Descriptions are written for the model: they say when to use
each tool and what to do with the result."""
from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field


class Recipient(BaseModel):
    phone: str = Field(description="WhatsApp number for this ticket, e.g. 08031234567 or +2348031234567. Use 'me' for the buyer.")
    name: Optional[str] = Field(default=None, description="Optional name printed on the ticket")


def build_mcp(service) -> FastMCP:
    mcp = FastMCP(
        "Eko Nights Tickets",
        instructions="Ticketing tools for Eko Nights, a Lagos events organiser. Sell tickets for verified events only.",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/mcp",
        # Host checks are off because the server sits behind a hosting proxy; access is controlled
        # by the bearer token middleware in main.py instead.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def list_events() -> dict:
        """List verified Eko Nights events that are on sale, with each ticket tier's price, perks,
        per-order limit and how many are left. Call this before quoting any event, price or availability.
        Never sell or describe an event that is not in this list."""
        return service.list_events()

    @mcp.tool()
    def create_order(event_id: str, tier_id: str, quantity: int, buyer_phone: str,
                     recipients: Optional[list[Recipient]] = None,
                     buyer_email: Optional[str] = None) -> dict:
        """Hold tickets and create a Paystack test-mode payment link.

        Only call this after the customer has confirmed the event, tier, quantity, total and who
        holds each ticket. Ticket holders are fixed at checkout:
        - recipients omitted: every ticket is held by buyer_phone (the person chatting)
        - one recipient: every ticket is held by that number
        - several recipients: exactly one entry per ticket; use phone 'me' for the buyer's own ticket
        Tickets are not sent automatically; the buyer must share each ticket link with the right
        holder, or the holder can message this number and ask for "my tickets".
        Returns `payment_url` and `reference`. Save the `reference` value (starts with `EKO-`) and
        pass it to `check_payment` when the customer replies "paid". Do not extract a reference from
        the Paystack URL — the URL ends with an access code, not the order reference. Send the link,
        the total, the reference and how long the hold lasts. On ok=false, follow error.next_step."""
        recips = [r.model_dump() if hasattr(r, "model_dump") else dict(r) for r in (recipients or [])]
        return service.create_order(event_id=event_id, tier_id=tier_id, quantity=quantity,
                                    buyer_phone=buyer_phone, recipients=recips, buyer_email=buyer_email)

    @mcp.tool()
    def check_payment(reference: str, buyer_phone: str) -> dict:
        """Verify an order's payment with Paystack and, if it succeeded, issue the tickets.
        Call when the customer says they have paid, or asks about an order. Use the exact `reference`
        returned by `create_order` for this conversation; never use a code extracted from the Paystack
        payment URL. Safe to call more than once: tickets are never issued twice. On success, send the
        buyer their own ticket codes and links, list the other assigned holders, and tell the buyer to
        share each ticket link with the right person. Holders can also message this number and ask for
        "my tickets". On ok=false, follow error.next_step; if error.escalate is true, hand the
        conversation to a human."""
        return service.check_payment(reference=reference, buyer_phone=buyer_phone)

    @mcp.tool()
    def my_tickets(phone: str) -> dict:
        """Show the valid tickets held by a WhatsApp number. Use the number of the person you are
        chatting with, never a number someone asks you to look up for them."""
        return service.my_tickets(phone=phone)

    @mcp.tool()
    def cancel_order(reference: str, buyer_phone: str) -> dict:
        """Cancel an unpaid order and release its tickets. Checks with Paystack first, so a payment
        made a moment ago is not lost. Paid orders cannot be cancelled here."""
        return service.cancel_order(reference=reference, buyer_phone=buyer_phone)

    @mcp.tool()
    def check_in(code: str, staff_pin: str) -> dict:
        """Gate staff only. Admit or reject a ticket code at the entrance. Requires the staff PIN.
        Returns result ADMIT or REJECT with a reason. A code can only be admitted once."""
        return service.check_in(code=code, staff_pin=staff_pin)

    return mcp
