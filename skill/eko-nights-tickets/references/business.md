# About Eko Nights

Eko Nights is a Lagos events organiser running music nights, comedy shows and pop-ups in Lekki and
Victoria Island. Most customers find events on Instagram and WhatsApp status, then message this
number to buy. Many buy for friends, partners or family, so sending tickets to other numbers is
normal and encouraged.

All data in this demo is made up.

## Why tickets work the way they do

Every ticket has its own code (format `EKO-XXXX-XXXX`) and belongs to one WhatsApp number.
At the gate, each code can be scanned once. This is why we send each friend their own ticket
instead of the buyer forwarding screenshots: a shared screenshot can be used once only, by
whoever arrives first.

## Policies (quote these accurately, do not improvise)

- Ticket holders are chosen at checkout. Once paid, tickets cannot be moved to another number
  through this chat. If someone needs a change, hand over to the team.
- Refunds: only if Eko Nights cancels or reschedules the event. For anything else, hand over to
  the team; never promise a refund yourself.
- Payment holds: tickets are held while the customer pays. The hold time comes from the
  `create_order` result. If it lapses, the tickets go back on sale.
- Age limits are set per event (see `age_limit` from `list_events`). ID may be checked at the gate.
- Doors open at the time shown by `list_events`. Re-entry is not allowed.
- Payment options are whatever the Paystack checkout page offers. Do not list methods yourself.

## Who to hand over to

The Eko Nights team handles refunds, holder changes after payment, payments that need review,
complaints, and anything at the gate that the agent cannot resolve.
