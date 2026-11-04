# TSG Labs Build Exercise: submission

## 1. Role and problem statement

**Role:** Technical Product Management

Lagos event organisers like the fictional Eko Nights sell tickets through ticketing platforms, but
their audiences discover events, ask questions and buy for friends on WhatsApp, then share ticket
screenshots that can be used more than once at the gate. This agent sells tickets for verified
events inside WhatsApp, takes payment through Paystack, and lets the buyer decide at checkout
whether tickets come to them, go to one other number, or are split so each person gets their own
single-use code, which gate staff check in through the same chat. It is worth paying for because
it brings checkout to where buyers already are, cuts the organiser's time answering DMs and
chasing payments, and closes the shared-screenshot gap, which a platform charging per ticket has
a direct interest in. I deliberately left out organiser onboarding, refunds, moving tickets after
payment, resale and offline check-in to focus on one reliable purchase-to-entry journey.

> To confirm before submitting: the volume of screenshot sharing and DM handling is a
> hypothesis, not data I have measured. Keep it framed that way unless you can source it.

## 2. Working agent

Teammate name: `<name in Chord>` · Simulator: https://chat.tsglabs.dev/
Suggested starters: "What's on this December?", "Buy 3 VIP tickets for me and two friends",
"My friend bought me a ticket", "I'm gate staff".

## 3. Code

`<repo link>`. See README.md for setup, architecture and AI usage.

## 4. Recording

`<link>`. Script in docs/demo-script.md.

## 5. Deployment field notes

### 1. GitHub push rejected with "Invalid username or token"

**Problem:** After committing locally, `git push` failed with `remote: Invalid username or token`.
**How I found the cause:** I checked GitHub's docs and confirmed password authentication was removed
in 2021; the remote URL was using HTTPS with my account password.
**Fix or workaround:** Generated a personal access token with `repo` scope and used it as the
password, then switched the remote to SSH for later pushes.
**What I'd change in Chord, its docs or its API:** Not a Chord issue, but the TSG Labs exercise
assumes the candidate can push to GitHub; a one-line reminder about PAT/SSH would save time.

### 2. WSL failed and the MCP registration script needed Git Bash workarounds

**Problem:** Running `bash scripts/register_chord_mcp.sh` on Windows first failed with
`Windows Subsystem for Linux has no installed distributions`, then with
`Please create a default UNIX user account... Catastrophic failure Error code: Wsl/Service/E_UNEXPECTED`.
After switching to Git Bash, the script failed with `Python was not found` because it called `python3`.
**How I found the cause:** I tried WSL install/update, which returned `ERROR_INSTALL_USEREXIT` (1602),
then read the script and saw the `python3` dependency. Re-running after manual registration gave a
`CONFLICT` because the server was already registered.
**Fix or workaround:** Used Git Bash, replaced `python3` with `python`, and completed registration
with the equivalent manual `curl` steps from the Chord docs.
**What I'd change in Chord, its docs or its API:** Provide a PowerShell or plain `curl` registration
example alongside the bash script, and surface the workspace ID in the Chord UI so the API call is
not needed.

### 3. Workspace ID is not visible in the Chord UI

**Problem:** `scripts/register_chord_mcp.sh` needs `WORKSPACE_ID`, but I could not find it in the
Chord teammate or chatbot UI.
**How I found the cause:** I searched the Chord docs and UI; the workspace ID is only returned by
`GET /v1/teammates`.
**Fix or workaround:** Called `curl -sS https://api.chordhq.xyz/v1/teammates -H "Authorization: Bearer $CHORD_API_KEY"`
and extracted `workspace_id` from the response.
**What I'd change in Chord, its docs or its API:** Show `workspace_id` on the teammate settings page
or in the workspace dropdown, and mention it explicitly in the MCP server registration docs.

### 4. WhatsApp simulator does not expose the user's phone number

**Problem:** The agent could not access the test user's WhatsApp number, so `buyer_phone` was empty
and even same-number orders could not be created. This also means the agent cannot proactively
"forward" tickets to other numbers because Chord has no API to send WhatsApp messages to arbitrary
recipients.
**How I found the cause:** I checked the Chord docs for simulator identity, `sender_id`, and
external-chat; the simulator is a black-box UI and does not pass a phone number to the agent or
expose a dummy number.
**Fix or workaround:** Updated the skill to require the agent to ask "What WhatsApp number are you
messaging from?" when the channel does not provide it, and changed the product language from
"sending tickets" to "assigning holders at checkout" plus sharing links.
**What I'd change in Chord, its docs or its API:** Either expose a configurable test phone number in
the simulator, or document clearly that the simulator does not provide channel identity and that
API-based testing (`POST /v1/external-chat/messages` with a chosen `sender_id`) is the reliable path.

### 5. MCP_BEARER_TOKEN is user-generated, not provided by Chord

**Problem:** I was unsure whether `MCP_BEARER_TOKEN` was a value Chord issued or one I created.
**How I found the cause:** The Chord MCP server registration docs show `auth_type: bearer` with a
`bearer_token` field in the request body, implying the caller supplies it.
**Fix or workaround:** Generated a random 32-byte token, set it as the service's `MCP_BEARER_TOKEN`,
and passed the same value in the registration payload.
**What I'd change in Chord, its docs or its API:** Add a sentence in the MCP registration guide
stating that the bearer token is chosen by the integrator and must match the server's environment.

## 6. Go-live note for Eko Nights

**What it does.** Customers message your WhatsApp number to see what's on, pick tickets, choose
who holds each one at checkout, and pay through Paystack. Each holder gets their own ticket link
and code. At the door, your staff send codes to the same number with their PIN and get ADMIT or
REJECT; a code only works once. Every order and ticket appears in your Google Sheet as it happens.

**What it doesn't do.** It doesn't give refunds, move tickets to another number after payment,
create events, or send tickets to other WhatsApp numbers automatically. Holders collect tickets by
messaging the number and asking for "my tickets", or the buyer shares their ticket link. Those go
to your team.

**Before real customers use it:**

1. **Real payments:** switch Paystack to live keys, confirm settlement to your bank account, and
   point the live webhook at the service.
2. **A real WhatsApp number:** connect a WhatsApp Business number to Chord. If you later want to
   send tickets to holders automatically, get approved WhatsApp message templates and a Chord API
   that supports outbound messages to arbitrary numbers.
3. **Verified customer identity:** make sure the customer's number comes from WhatsApp itself,
   not from what the agent is told, so nobody can pull up someone else's tickets.
4. **Failed and late payments:** decide who checks the "needs_review" rows each day (amount
   mismatches, payments that arrived after tickets sold out) and how fast refunds are made.
5. **Alerts:** name the person who gets notified when the agent hands a chat to a human, when a
   payment needs review, or when the service is down, and how (WhatsApp, email).
6. **Scale:** move from the Google Sheet to a proper database before a big on-sale, so two buyers
   can't grab the last ticket at once.
7. **Door plan:** test check-in on venue Wi-Fi and mobile data, keep a printed backup list, and
   agree what staff do if the system is slow.
8. **Policies:** confirm the refund, age limit and re-entry rules the agent quotes.
