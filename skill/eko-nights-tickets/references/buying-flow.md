# Buying tickets

Move the customer forward one step at a time. Skip steps they have already answered.

## 1. Find the event

Call `list_events`. Offer events briefly (name, date, venue, from-price). When they pick one,
show its tiers with price, perks and whether it is nearly or fully sold out. Do not show
`remaining` numbers unless 10 or fewer are left.

## 2. Quantity

Ask how many tickets. Respect `max_per_order`; if they want more, explain the limit and offer
to do a second order after the first.

## 3. Who gets the tickets (ask every time)

Ask one simple question, matched to the quantity:

- 1 ticket: "Is this ticket for you, or should I send it to someone else's WhatsApp?"
- 2 or more: "Should all the tickets come to you, go to one other number, or be split so each
  person gets their own?"

Then build `recipients`:

| Customer wants | What to pass |
| --- | --- |
| All to themselves | leave `recipients` out |
| All to one other number | one entry: `[{"phone": "0812..."}]` |
| Split between people | one entry per ticket, using `"me"` for the buyer's own ticket, e.g. `[{"phone": "me"}, {"phone": "0812...", "name": "Tobi"}, {"phone": "0701..."}]` |

The same number can appear more than once if one person holds two tickets. Names are optional.
If the number of entries does not match the quantity, ask which person gets the extra ticket(s);
do not guess. Recommend splitting when people arrive separately, because each person then has
their own code.

## 4. Buyer number

Use the WhatsApp number of the person you are chatting with as `buyer_phone`. If the channel
does not give it to you, ask once: "What WhatsApp number are you messaging from?"

## 5. Confirm and charge

Read back in one short message: event, tier, quantity, total (price × quantity), and who gets
each ticket (masked numbers are fine). Ask "Shall I get your payment link?" On yes, call
`create_order`.

Send: the payment link, the total, how many minutes the hold lasts, and "Reply *paid* once
you're done". Keep the `reference` for the rest of the conversation.

## 6. Payment

When they say they have paid (or ask what is happening), call `check_payment`.

- `paid`: send the buyer their own codes and links. Then list which other numbers received
  tickets and say those people can message this number and ask for "my tickets".
- `awaiting_payment`: tell them the payment is not showing yet, resend the link, and mention the
  minutes left.
- An error: see `tool-results.md`.

## Recipients asking for their tickets

Someone may message saying a friend bought them a ticket. Call `my_tickets` with their own number
and send what comes back. If nothing is there, ask whether the buyer has finished paying, and
suggest the buyer replies *paid* in their own chat.

## Changing their mind

Before payment, they can change anything: call `cancel_order` on the old reference, then start
again. After payment, see the policy in `business.md`.
