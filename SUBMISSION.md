# TSG Labs Build Exercise: Eko Nights Tickets

## 1. Role and problem statement

**Role:** Technical Product Management

Lagos audiences discover events, ask questions and buy tickets for friends inside WhatsApp. Event
organisers like the fictional **Eko Nights** lose sales when replies are slow, lose trust when
screenshots are shared at the gate, and lose time reconciling payments from scattered DMs. This
agent turns that thread into a complete purchase: customers browse verified events, choose who
holds each ticket at checkout, pay through Paystack, and receive a single-use ticket code. Gate
staff check codes in through the same WhatsApp number. Every order and ticket is written to a
Google Sheet the organiser can watch live.

The value is speed and fraud reduction. Checkout happens where buyers already are, the organiser
stops chasing DMs, and each holder gets their own code so a screenshot cannot be reused at the
door. I deliberately left organiser onboarding, refunds, moving tickets after payment, resale and
offline check-in out of scope to keep the purchase-to-entry journey reliable and demoable.

## 2. Working agent

- **Teammate name:** `<name in Chord>`
- **Simulator:** https://chat.tsglabs.dev/
- **Test starters (3):**
  1. `What can you help me with?`
  2. `What events are available?`
  3. `I want to buy a ticket`

## 3. Code

`<repo link>`

See `README.md` for architecture, setup, deployment and AI usage. The service is a FastAPI app
exposing six MCP tools to Chord: `list_events`, `create_order`, `check_payment`, `my_tickets`,
`cancel_order` and `check_in`. Payments use Paystack test mode; the service refuses to start if
it sees a live key. Storage is a Google Sheet seeded with made-up events and tiers. The test
suite runs offline with 32 passing tests.

## 4. Recording

`<link>`

Script and conversation flow are in `docs/demo-script.md`.

## 5. Deployment field notes

### 1. GitHub push rejected with "Invalid username or token"

I initially tried to push over HTTPS using my GitHub password. GitHub removed password
authentication in 2021, so the push failed with `remote: Invalid username or token`. I checked
GitHub's authentication docs, generated a personal access token with `repo` scope, used it to
authenticate, and later switched the remote to SSH for a cleaner workflow.

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
same-number orders could not be created. I also confirmed Chord has no API to send outbound
WhatsApp messages to arbitrary numbers, so proactive "forwarding" of tickets is impossible.

I updated the skill to ask "What WhatsApp number are you messaging from?" when the channel does
not provide it, and changed the product language from "sending tickets" to "assigning holders at
checkout" plus sharing ticket links.

_Suggestion for Chord:_ expose a configurable test phone number in the simulator, or document
that API-based testing (`POST /v1/external-chat/messages` with a chosen `sender_id`) is the
reliable path.

### 5. MCP_BEARER_TOKEN is user-generated, not provided by Chord

The MCP server registration docs show `auth_type: bearer` with a `bearer_token` field in the
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
   point the live webhook at the service.
2. **A real WhatsApp number:** connect a WhatsApp Business number to Chord. If you later want to
   send tickets to holders automatically, get approved WhatsApp message templates and a Chord API
   that supports outbound messages to arbitrary numbers.
3. **Verified customer identity:** make sure the customer's number comes from WhatsApp itself,
   not from what the agent is told, so nobody can pull up someone else's tickets.
4. **Failed and late payments:** decide who checks the "needs_review" rows each day and how fast
   refunds are made.
5. **Alerts:** name the person who gets notified when the agent hands a chat to a human, when a
   payment needs review, or when the service is down.
6. **Scale:** move from the Google Sheet to a proper database before a big on-sale.
7. **Door plan:** test check-in on venue Wi-Fi and mobile data, keep a printed backup list, and
   agree what staff do if the system is slow.
8. **Policies:** confirm the refund, age limit and re-entry rules the agent quotes.
