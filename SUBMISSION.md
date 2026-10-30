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

Write these as you build. Two or three specific entries beat a long list.

### Template

**Problem:** what happened, with the exact error message or response.
**How I found the cause:** what I checked, in order, and what told me.
**Fix or workaround:**
**What I'd change in Chord, its docs or its API:**

### Things to watch for (from the Chord docs, not yet experienced)

These are risks worth checking during the build. Only turn one into a field note if it actually
happens.

- **Who is the customer?** Tools receive `buyer_phone` from the model. Check whether Chord passes
  the sender's WhatsApp number to the teammate or to MCP tool calls. If not, that is a security
  gap worth raising: anyone could ask the agent to look up another number.
- **Tool scope surprises.** An empty `mcp_server_ids` gives a teammate every enabled server in the
  workspace, and `set_mcp_server_ids: []` does not clear an assignment.
- **Health checks.** A failed MCP health probe can still return HTTP 200 with `status: "error"`.
- **Tool states.** A tool must be both allowed for the teammate and connected in the workspace.
- **Skill publishing.** Only published, included skill versions affect replies; check
  **Why this reply** if the agent ignores a reference file.
- **Simulator access.** The WhatsApp simulator is a separate connected app needing its own approval.
- **Cold starts.** If the host sleeps, note whether Chord retries or times out the first tool call,
  and what the customer sees.
- **Payment links.** Check the Paystack link is tappable in the simulator.

## 6. Go-live note for Eko Nights

**What it does.** Customers message your WhatsApp number to see what's on, pick tickets, choose
who receives each one, and pay through Paystack. Each person gets their own ticket link and code.
At the door, your staff send codes to the same number with their PIN and get ADMIT or REJECT; a
code only works once. Every order and ticket appears in your Google Sheet as it happens.

**What it doesn't do.** It doesn't give refunds, move tickets to another number after payment,
create events, or text recipients first (they message you to collect their tickets). Those go to
your team.

**Before real customers use it:**

1. **Real payments:** switch Paystack to live keys, confirm settlement to your bank account, and
   point the live webhook at the service.
2. **A real WhatsApp number:** connect a WhatsApp Business number to Chord and get any message
   templates approved if you want to send tickets to recipients automatically.
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
