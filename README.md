# Eko Nights tickets: a WhatsApp ticket desk on Chord

A Chord teammate that sells event tickets on WhatsApp for **Eko Nights**, a fictional Lagos
events organiser. Customers browse verified events, choose who receives each ticket (themselves,
one other number, or split across several), pay through **Paystack test mode**, and every holder
gets their own single-use code. Gate staff check codes in through the same chat. Orders and
tickets land in a **Google Sheet** the organiser can watch live.

All data is made up. Only Paystack test keys are used; the app refuses to start with a live key.

## How it fits together

```
WhatsApp simulator ──► Chord teammate ──(MCP, Streamable HTTP, bearer token)──► this service
                        skill: eko-nights-tickets                                │
                                                                                 ├─► Paystack (test): initialise + verify
                                                                                 ├─► Google Sheet: events, tiers, orders, tickets
Paystack ──(webhook, HMAC SHA512)──► /webhooks/paystack ─────────────────────────┤
Holder's browser ──► /t/{code} (ticket page with QR)                             │
Buyer after paying ──► /paid (Paystack callback, re-verifies)  ◄─────────────────┘
```

Chord connects custom tools as a remote MCP server, so the "custom tool" here is one FastAPI
service exposing six MCP tools:

| Tool | What it does |
| --- | --- |
| `list_events` | Verified, on-sale events with tiers, prices, limits and stock (unverified events are never returned) |
| `create_order` | Validates quantity and recipients, holds stock, creates a Paystack payment link |
| `check_payment` | Verifies with Paystack; on success issues one ticket per holder (idempotent) |
| `my_tickets` | Tickets held by a number, so recipients can collect theirs |
| `cancel_order` | Releases an unpaid hold, checking Paystack first so a just-made payment is not lost |
| `check_in` | Gate staff only (PIN): admits a code once, rejects reuse or unknown codes |

## Repo layout

```
app/
  service.py       business logic: holds, recipients, payment settlement, check-in
  mcp_tools.py     MCP tool definitions Chord calls
  main.py          FastAPI app: /mcp, /webhooks/paystack, /t/{code}, /paid, /health
  paystack.py      Paystack client (test mode) and an offline fake for tests
  store.py         Google Sheets backend and in-memory backend
  phone.py         Nigerian phone normalisation (0803..., +234..., 234...)
  seed.py          made-up events and tiers
skill/eko-nights-tickets/   the Chord skill (SKILL.md plus references)
scripts/           seed the sheet, register with Chord, smoke test the deployment
tests/             32 tests, including MCP calls over real HTTP
docs/demo-script.md         the conversation for the 3-minute recording
SUBMISSION.md      problem statement, go-live note, field notes template
```

## Run it locally (no accounts needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q                      # all tests run offline

STORE_BACKEND=memory PAYSTACK_MODE=fake STAFF_PIN=1234 MCP_BEARER_TOKEN=dev \
  uvicorn app.asgi:app --reload
curl localhost:8000/health
```

`memory` and `fake` modes are for development only. The demo uses Sheets and Paystack test mode.

## Set up the real integrations

**1. Google Sheet**

1. Create a blank Google Sheet and copy its ID from the URL.
2. In Google Cloud, create a service account, enable the Google Sheets API, and download a JSON key.
3. Share the sheet with the service account's `client_email` as Editor.
4. Seed it: `GOOGLE_SHEET_ID=... GOOGLE_SERVICE_ACCOUNT_JSON=./key.json python scripts/seed_sheet.py`

This creates `events`, `tiers`, `orders` and `tickets` tabs. To mark an event unverified or pull it
from sale, change `verified` or `on_sale` in the sheet; the agent picks it up within 30 seconds.

**2. Paystack (test mode)**

1. Copy your `sk_test_` secret key from the Paystack dashboard.
2. In the test-mode webhook settings, set the webhook URL to `https://<your-service>/webhooks/paystack`.
3. Pay with the test cards in Paystack's documentation, including a failing one to exercise the failure path.

**3. Deploy**

`render.yaml` deploys to Render; the `Dockerfile` works anywhere that runs containers. Set the
variables in `.env.example`. For `GOOGLE_SERVICE_ACCOUNT_JSON` on a host, paste the key JSON
itself as the value. Then:

```bash
PUBLIC_BASE_URL=https://<your-service> MCP_BEARER_TOKEN=<token> python scripts/smoke_test.py
```

Free hosting tiers sleep when idle, so the first tool call after a quiet spell can be slow. Wake
the service before recording or demoing.

**4. Connect to Chord**

1. Create the teammate: zip the `skill/eko-nights-tickets` folder and upload it under
   **Teammates → Create a teammate**, then confirm `SKILL.md` is marked **Instructions** and publish.
2. Register the tool server, either in the app (**Teammate settings → Tools → Add tool**) with URL
   `https://<your-service>/mcp`, bearer auth and your `MCP_BEARER_TOKEN`, or with
   `scripts/register_chord_mcp.sh`.
3. Check the teammate shows the tools as **On**. Per the Chord docs, a tool must be both allowed for
   the teammate and connected in the workspace, and an empty `mcp_server_ids` means every enabled
   server in the workspace.
4. Test in the in-app conversation, then in the WhatsApp simulator.

## Design choices

- **Holders are fixed at checkout.** The buyer decides before paying, so each person gets their
  own code from the start and there is nothing to forward afterwards.
- **Verification before issue.** Tickets are only issued after Paystack's verify endpoint
  confirms success and the amount and currency match the order. The webhook triggers the same
  check rather than trusting its own body.
- **Holds, not optimism.** Stock is held for `HOLD_MINUTES` while the customer pays. A payment
  that arrives after the hold lapsed is honoured if stock remains, otherwise flagged
  `needs_review` for a refund instead of overselling.
- **Errors the model can act on.** Tools return `{code, message, next_step}` instead of raising,
  and the skill maps each code to what the customer should hear.
- **Privacy by default.** Check and cancel only work for the buyer's number; ticket listings mask
  phone numbers; gate check-in needs a staff PIN.

## Known limits

- **Identity comes from the model.** Tools take `buyer_phone` as an argument, so they trust the
  agent to pass the number it is chatting with. In production the number should come from the
  channel, not the model. See the field notes.
- **Recipients are not messaged automatically.** They collect tickets by messaging the number and
  asking for "my tickets". Proactive delivery would need an approved WhatsApp template.
- **Single instance.** Stock is protected by an in-process lock and a Google Sheet. That is fine
  for a demo, not for a big on-sale; production needs a database with transactions.
- **Out of scope by design:** organiser onboarding and verification workflow, refunds, holder
  changes after payment, resale, seating, offline check-in.

## How I used AI tools

<!-- Edit this to reflect what you actually did. -->
The first draft of the service, tests, skill files and docs was produced with Claude (Anthropic)
from my brief and product decisions. I reviewed it, deployed it, connected it to Chord and tested
it end to end; the field notes are my own record of what happened.
