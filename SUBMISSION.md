# TSG Labs Build Exercise: Eko Nights Tickets

## 1. Role and problem statement

**Role:** Technical Product Management

Lagos audiences buy tickets for friends inside WhatsApp, but event organisers lose sales to slow
replies, lose trust when screenshots are shared at the gate, and lose time reconciling payments
from scattered DMs. This agent turns that thread into a complete purchase: customers browse
verified events, choose who holds each ticket at checkout, pay through Paystack, and receive a
single-use ticket code. Gate staff check codes in through the same WhatsApp number, and every
order is written to a Google Sheet the organiser can watch live.

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

After a refactor, the agent started failing to find payments and handing chats to manual input.
The symptom was that `check_payment` was being called with a reference that did not exist in the
sheet. I traced it to the model extracting the trailing path segment from the Paystack payment
URL and treating it as the order reference. Real Paystack URLs end with an access code, not the
merchant reference, so the lookup failed.

The fix had two parts. First, I updated the skill and tool instructions to explicitly tell the
agent to save the `EKO-…` reference returned by `create_order` and to pass that exact value to
`check_payment`, never to read it from the URL. Second, I changed `FakePaystack.initialize` to
mirror real Paystack URLs, putting an access code in the path and the reference only in the query
string, and added a regression test.

_Lesson:_ tool outputs that look like identifiers need explicit "keep this" guidance for the
model. A structured conversation-state feature in Chord would make this class of bug impossible.

### 2. MCP registration on Windows

The registration script assumed a Unix environment, and my Windows machine did not have WSL
configured. The script failed first with `Windows Subsystem for Linux has no installed
distributions`, then with a catastrophic WSL registration error, and later with `Python was not
found` because Git Bash did not have `python3` on PATH. I read the script, understood the API
calls it was making, and completed registration manually with equivalent `curl` commands in Git
Bash. I also learned that re-running registration returns `CONFLICT` once a server is already
registered, so I verified the existing registration instead of creating a duplicate.

_Suggestion for Chord:_ provide a PowerShell or plain `curl` registration example alongside the
bash script for Windows users.

### 3. Workspace ID is not visible in the Chord UI

`scripts/register_chord_mcp.sh` needs `WORKSPACE_ID`, but it is not shown in the teammate or
chatbot UI. I retrieved it from `GET /v1/teammates`.

_Suggestion for Chord:_ show `workspace_id` on the teammate settings page and mention it in the
MCP registration docs.

### 4. WhatsApp simulator does not expose the user's phone number

The simulator does not pass a phone number to the agent, so `buyer_phone` was empty and even
same-number orders could not be created. I found no documented way to send outbound WhatsApp
messages to arbitrary numbers through Chord, so proactive "forwarding" of tickets is impossible.

This creates a real identity risk: because the agent has to ask for the user's number, anyone can
type another person's phone number into `my_tickets` and retrieve their ticket codes. That
undercuts the anti-screenshot pitch until the channel itself supplies a verified number.

I updated the skill to ask "What WhatsApp number are you messaging from?" when the channel does
not provide it, and changed the product language from "sending tickets" to "assigning holders at
checkout" plus sharing ticket links.

_Suggestion for Chord:_ expose a configurable test phone number in the simulator, or document
that API-based testing (`POST /v1/external-chat/messages` with a chosen `sender_id`) is the
reliable path.

### 5. MCP_BEARER_TOKEN is user-generated, not provided by Chord

The MCP server registration docs show `auth_type: bearer` with an `auth_token` field in the
request body, implying the caller supplies the token. I generated a random 32-byte token, set it
as the service's `MCP_BEARER_TOKEN`, and passed the same value in the registration payload.

_Suggestion for Chord:_ add one sentence in the MCP registration guide stating that the bearer
token is chosen by the integrator and must match the server's environment.

## 6. Go-live note for Eko Nights

**What it does.** Customers message your WhatsApp number to see what's on, pick tickets, choose
who holds each one at checkout, and pay through Paystack. Each holder gets their own ticket link
and code. At the door, staff send codes to the same number with their PIN and get ADMIT or REJECT;
a code only works once. Every order and ticket appears in your Google Sheet as it happens.

**What it doesn't do.** It doesn't give refunds, move tickets to another number after payment,
create events, or send tickets to other WhatsApp numbers automatically. Holders collect tickets by
messaging the number and asking for "my tickets", or the buyer shares their ticket link.

**Before real customers use it:**

1. **Real payments:** switch Paystack to live keys, confirm settlement to your bank account, and
   point the live payment confirmation link at the service.
2. **A real WhatsApp number:** connect a WhatsApp Business number to Chord. If you later want to
   send tickets to holders automatically, get approved WhatsApp message templates and a Chord API
   that supports outbound messages to arbitrary numbers.
3. **Verified customer identity:** make sure the customer's number comes from WhatsApp itself,
   not from what the agent is told, so nobody can pull up someone else's tickets.
4. **Failed and late payments:** decide who checks orders flagged for review in the sheet each day
   and how fast refunds are made.
5. **Alerts:** name the person who gets notified when the agent hands a chat to a human, when a
   payment needs review, or when the service is down.
6. **Scale:** move from the Google Sheet to a proper database before a big on-sale.
7. **Door plan:** test check-in on venue Wi-Fi and mobile data, keep a printed backup list, and
   agree what staff do if the system is slow.
8. **Policies:** confirm the refund, age limit and re-entry rules the agent quotes.
