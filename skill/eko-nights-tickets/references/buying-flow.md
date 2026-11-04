# Buying tickets

Move the customer forward one step at a time. Skip steps they have already answered.

## 1. Find the event

Call `list_events`. Offer events briefly (name, date, venue, from-price). When they pick one,
show its tiers with price, perks and whether it is nearly or fully sold out. Do not show
`remaining` numbers unless 10 or fewer are left.

## 2. Quantity

Ask how many tickets. Respect `max_per_order`; if they want more, explain the limit and offer
to do a second order after the first.

## 3. Who holds the tickets (ask every time)

Ask one simple question, matched to the quantity:

- 1 ticket: "Is this ticket for you, or should I assign it to someone else's WhatsApp number?"
- 2 or more: "Should all the tickets be under your number, under one other number, or split so
  each person gets their own?"

Then build `recipients`:

| Customer wants          | What to pass                                                                                                                                        |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| All to themselves       | leave `recipients` out                                                                                                                              |
| All to one other number | one entry: `[{"phone": "0812..."}]`                                                                                                                 |
| Split between people    | one entry per ticket, using `"me"` for the buyer's own ticket, e.g. `[{"phone": "me"}, {"phone": "0812...", "name": "Tobi"}, {"phone": "0701..."}]` |

The same number can appear more than once if one person holds two tickets. Names are optional.
If the number of entries does not match the quantity, ask which person gets the extra ticket(s);
do not guess. Recommend splitting when people arrive separately, because each person then has
their own code.

Important: assigning a ticket to another number does **not** send them a WhatsApp message. The
buyer must share the ticket link with them, or the holder must message this number and ask for
"my tickets".

## 4. Buyer number

Use the WhatsApp number of the person you are chatting with as `buyer_phone`. If the channel
does not give it to you, ask once: "What WhatsApp number are you messaging from?"

## 5. Confirm and charge

Read back in one short message: event, tier, quantity, total (price × quantity), and who holds
each ticket (masked numbers are fine). Ask "Shall I get your payment link?" On yes, call
`create_order`.

Send: the payment link, the total, the order reference (starts with `EKO-`), how many minutes the
hold lasts, and "Reply _paid_ once you're done". Save the `reference` value from the tool result
and use it for every `check_payment` call in this conversation. Do not extract a reference from
the Paystack URL — the URL ends with an access code, not the order reference.

## 6. Payment

When they say they have paid (or ask what is happening), call `check_payment` with the reference
saved from `create_order`. If you no longer have it, ask the customer for the reference that
starts with `EKO-` before calling the tool.

- `paid`: send the buyer their own codes and links. Then list the other assigned holders and
  tell the buyer to share each ticket link with the right person. Also say those holders can
  message this number and ask for "my tickets".
- `awaiting_payment`: tell them the payment is not showing yet, resend the link, and mention the
  minutes left.
- An error: see `tool-results.md`.

## Holders asking for their tickets

Someone may message saying a friend bought them a ticket. Call `my_tickets` with their own number
and send what comes back. If nothing is there, ask whether the buyer has finished paying, and
suggest the buyer replies _paid_ in their own chat.

## Forwarding caveat

If a customer asks you to "forward", "send" or "WhatsApp" a ticket to someone else, explain that
you cannot send messages to other numbers. Offer the two options:

1. The buyer shares the holder's ticket link directly.
2. The holder messages this number and says "my tickets".

## Changing their mind

Before payment, they can change anything: call `cancel_order` on the old reference, then start
again. After payment, see the policy in `business.md`.
