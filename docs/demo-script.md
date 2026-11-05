# 3-minute recording script

Have the Google Sheet open next to the simulator so viewers see rows appear.

For step-by-step messages and expected outcomes, see:

- `buyer-test-script.md` — the full purchase flow
- `gate-staff-test-script.md` — door check-in with the staff PIN

**0:00 Intro (15s).** Eko Nights sells tickets on WhatsApp. One job: get the right person a
valid ticket, from browsing to the gate.

**0:15 Browse (20s).** "Buy 3 VIP tickets for me and two friends." The agent confirms the
Afrobeats VIP tier and asks who holds each ticket.

**0:35 Choose and assign (40s).** "One for me, one for Tobi on 0812 000 1111, and one for my
sister Ada on 0701 111 2222." The agent reads back the event, tier, total and holders, then
asks to confirm. Note: the agent cannot WhatsApp tickets to Tobi or Ada; it assigns the tickets
to their numbers at checkout.

**1:15 Pay (35s).** Confirm. The agent sends the Paystack link and the hold time. A pending order
row appears in the sheet. Pay with a Paystack test card, reply "paid".

**1:50 The tool doing its job (30s).** `check_payment` verifies with Paystack and issues three
tickets. Show the order flip to `paid` and three ticket rows with different holders. Open the
buyer's ticket link (QR and code). The agent tells the buyer to share each holder's ticket link
with them, or the holders can message this number and ask for "my tickets".

**2:20 Gate check-in (30s).** Switch to staff: send the PIN `0604` and one of the ticket codes
for ADMIT, then the same code again for REJECT: Already used.

**2:50 Close (10s).** One failure path worth mentioning: a failed test card leaves no tickets and
offers a fresh link. Also mention that the simulator does not expose phone numbers, so the agent
asks for the user's number when needed.
