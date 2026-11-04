# Buyer simulator test script

Use this in the Chord WhatsApp simulator to walk through a full purchase.

## Setup

- Wake the deployed service first: `python scripts/smoke_test.py` or `curl <your-service>/health`.
- Have the Google Sheet open so you can see the order and ticket rows appear.

## Conversation

1. **Start:** `What events are available?`
   - Expected: agent lists only verified events (Afrobeats, Comedy). The unverified rave is not offered.

2. **Choose event and tier:** `3 VIP tickets for the Afrobeats night.`
   - Expected: agent confirms the tier, price per ticket, and asks how many.

3. **Assign holders:** `One for me, one for Tobi on 0812 000 1111, and one for my sister Ada on 0701 111 2222.`
   - Expected: agent reads back the three holders and asks to confirm.

4. **Confirm:** `Yes, go ahead.`
   - Expected: agent calls `create_order`, returns a Paystack link, the total, the order reference (starts with `EKO-`), and the hold time.
   - Check the Google Sheet: a pending `orders` row appears with the same reference.

5. **Pay:** Open the Paystack link in a browser and pay with a test card.
   - Use the no-PIN/OTP card for the smoothest demo.

6. **Reply in chat:** `paid`
   - Expected: agent calls `check_payment` with the saved `EKO-…` reference, confirms payment, and issues three tickets.
   - Check the Sheet: the order flips to `paid` and three `tickets` rows appear with different holder phones.

7. **Collect your ticket:** `my tickets`
   - Expected: agent returns the buyer's own ticket code and link.

8. **Failure path (optional):** Start a new chat, create an order, then pay with Paystack's failing test card.
   - Expected: agent says payment failed, no tickets were issued, and offers a fresh link.

## Notes

- The simulator does not expose your phone number, so the agent may ask "What WhatsApp number are you messaging from?" Reply with the same number each time.
- The agent cannot send WhatsApp messages to other numbers. To show Tobi's ticket, either share the link from the buyer's result or run `my tickets` from a message sent with Tobi's number.
