# TSG Labs Build Exercise: Eko Nights Tickets

## 1. Role and problem statement

**Role:** Technical Product Management

Lagos audiences buy tickets for friends inside WhatsApp, but event organisers lose sales to slow
replies, lose trust when screenshots are shared at the gate, and lose time reconciling payments
from scattered DMs. This agent turns that thread into a complete purchase: customers browse
verified events, choose who holds each ticket at checkout, pay through Paystack, and receive a
single-use ticket code, which gate staff check in through the same WhatsApp number. It's worth
paying for because organisers recover sales lost to slow replies, stop chasing payments by hand,
and can trust that every code at the door was paid for once.

I left organiser onboarding, refunds, moving tickets after payment, resale and offline check-in
out of scope to keep the purchase-to-entry journey reliable and demoable.

## 2. Working agent

- **Teammate name:** Eko Nights Tix
- **Simulator:** https://chat.tsglabs.dev/
- **Live test staff PIN:** `0604`
- **Test starters (3):**
  1. `Buy 3 VIP tickets for me and two friends`
  2. `What events are available?`
  3. `I'm gate staff`

## 3. Code

**Link:** [maonye/eko-nights-tickets](https://github.com/maonye/eko-nights-tickets)

See `README.md` for architecture, setup, deployment and AI usage. The service is a FastAPI app
exposing six MCP tools to Chord: `list_events`, `create_order`, `check_payment`, `my_tickets`,
`cancel_order` and `check_in`. Payments use Paystack test mode; the service refuses to start if
it sees a live key. Storage is a Google Sheet seeded with made-up events and tiers. The test
suite runs offline with 34 passing tests.

## 4. Recording

**Link:** [Eko Nights Tix - Test Chat - 5 November 2026](https://www.loom.com/share/e9416c10368245de980a747ffa048a15)

Script and conversation flow are in `docs/demo-script.md`. Step-by-step simulator test scripts
are in `docs/buyer-test-script.md` and `docs/gate-staff-test-script.md`.

## 5. Deployment field notes

### 1. Agent lost the order reference and tried to read it from the Paystack URL

**What happened.** Customers who paid and replied "paid" were told their order could not be
found, and the agent fell back to asking them for a reference. `check_payment` was returning
`ORDER_NOT_FOUND` for orders that had been created successfully moments earlier.

**How I found the cause.** I compared the `reference` argument in the failing `check_payment`
call with the orders tab in the Google Sheet. It matched nothing in the sheet, but it did match
the last segment of the Paystack checkout URL sent earlier in the same chat. Paystack checkout
URLs end with an access code, not the merchant reference, so the model had picked the
identifier that looked most like a reference instead of the `EKO-` value `create_order` returned.

**Fix.** The real fix was in the instructions: the skill and the `create_order` and
`check_payment` tool descriptions now tell the agent to keep the `EKO-` reference from
`create_order`, include it in the payment message, and never read a reference from the URL.
I also changed the offline fake to produce Paystack-style URLs so local tests match reality,
and added a regression test. That keeps the tests honest but cannot by itself stop the model
making this mistake.

**Suggestion for Chord.** Values a later tool call depends on, like an order reference, are
easy for the model to lose or confuse. A way for a tool result to mark a value as conversation
state (for example "remember `reference` for this thread") would make this class of bug much
less likely.

### 2. The simulator does not expose the user's phone number

**What happened.** The first purchase attempt in the simulator failed before a payment link was
created. `create_order` returned `INVALID_BUYER_PHONE` with the message "No phone number given",
even for a customer buying tickets for themselves.

**How I found the cause.** The error meant the agent was calling the tool with an empty
`buyer_phone`. I checked the conversation in Chord and the simulator's settings and found no
sender number exposed to the agent anywhere, then confirmed in the Chord docs that I could not
rely on the channel to supply it.

**Fix.** I updated the skill to ask "What WhatsApp number are you messaging from?" when the
channel does not provide it. I found no documented way to send WhatsApp messages to arbitrary
numbers through Chord, so I couldn't build proactive forwarding. I changed the product language
from "sending tickets" to "assigning holders at checkout", with holders collecting tickets by
messaging in or receiving the buyer's ticket link.

**Risk this creates.** Because the number is typed by the user, anyone can enter another
person's number into `my_tickets` and retrieve their ticket codes. That undercuts the
single-use-code design until the channel supplies a verified number.

**Suggestion for Chord.** Pass the sender's verified number to MCP tool calls, so tools never
have to trust what the model is told. For testing, let the simulator set a test phone number, or
document that `POST /v1/external-chat/messages` with a chosen `sender_id` is the reliable path.

### 3. Gaps in the MCP registration docs

**What happened.** Two things slowed down registration. The workspace ID the API needs is not
shown anywhere in the teammate or chat UI. And it was not obvious who supplies the bearer token:
the docs show an `auth_token` field but do not say the integrator chooses it.

**How I found the cause.** I retrieved the workspace ID from `GET /v1/teammates`. For the
token, I worked out from the registration example that Chord sends whatever `auth_token` it is
given, so I generated a random 32-byte token, set it as the service's `MCP_BEARER_TOKEN`, and
registered with the same value. I also found that re-running registration returns `CONFLICT`,
so I verified the existing registration rather than creating a duplicate.

**Suggestion for Chord.** Show `workspace_id` on the teammate settings page, and add one
sentence to the MCP guide: "The bearer token is chosen by you and must match the token your
server checks."

### 4. Registration examples assume a Unix shell

On Windows without WSL configured, bash-based registration failed with `Windows Subsystem for
Linux has no installed distributions`, then `Python was not found` in Git Bash. I completed
registration with plain `curl` commands in Git Bash. Chord's registration examples assume a Unix
shell; a PowerShell example would help Windows builders.

## 6. Go-live note for Eko Nights

**What it does.** Customers message your WhatsApp number to see what's on, pick tickets, choose
who holds each one at checkout, and pay through Paystack. Each holder gets their own ticket link
and code. At the door, staff send codes to the same number with their PIN and get ADMIT or REJECT;
a code only works once. Every order and ticket appears in your Google Sheet as it happens.

**What it doesn't do.** It doesn't give refunds, move tickets to another number after payment,
create events, or send tickets to other WhatsApp numbers automatically. Holders collect tickets by
messaging the number and asking for "my tickets", or the buyer shares their ticket link.

**Before real customers use it:**

1. **Real payments:** switch Paystack to live keys, confirm money settles into your bank account,
   and tell Paystack where to send live payment confirmations.
2. **A real WhatsApp number:** connect a WhatsApp Business number to Chord. If you later want to
   send tickets to holders automatically, get approved WhatsApp message templates and a Chord API
   that supports outbound messages to arbitrary numbers.
3. **Verified customer identity:** make sure the customer's number comes from WhatsApp itself,
   not from what the agent is told, so nobody can pull up someone else's tickets.
4. **Staff access:** give each staff member their own check-in PIN that you can switch off,
   instead of one shared PIN, so a leaked PIN can't be used to check tickets in.
5. **Failed and late payments:** decide who checks orders flagged for review in the sheet each day
   and how fast refunds are made.
6. **Alerts:** name the person who gets notified when the agent hands a chat to a human, when a
   payment needs review, or when the service is down.
7. **Scale:** move from the Google Sheet to a proper database before a big on-sale.
8. **Door plan:** test check-in on venue Wi-Fi and mobile data, keep a printed backup list, and
   agree what staff do if the system is slow.
9. **Policies:** confirm the refund, age limit and re-entry rules the agent quotes.
