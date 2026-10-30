"""Small HTML pages: the ticket a holder shows at the gate, and the post-payment page."""
from __future__ import annotations

import html
import io

import qrcode
import qrcode.image.svg

STYLE = """
:root{--bg:#f6f3ee;--card:#fff;--ink:#1c1a17;--muted:#6b645a;--accent:#c2410c;--ok:#15803d;--bad:#b91c1c}
@media (prefers-color-scheme:dark){:root{--bg:#141210;--card:#1f1c19;--ink:#f3efe9;--muted:#a59d92;--accent:#fb923c;--ok:#4ade80;--bad:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;display:flex;justify-content:center;padding:24px}
.card{background:var(--card);border-radius:16px;max-width:380px;width:100%;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.08)}
h1{font-size:1.25rem;margin:0 0 4px}p{margin:4px 0;color:var(--muted)}.code{font:600 1.4rem ui-monospace,monospace;
letter-spacing:.08em;text-align:center;margin:16px 0}.qr{background:#fff;padding:12px;border-radius:12px}
.qr svg{width:100%;height:auto;display:block}.badge{display:inline-block;padding:4px 10px;border-radius:999px;
font-weight:600;font-size:.85rem;margin-top:12px}.valid{background:var(--ok);color:#fff}.used{background:var(--bad);color:#fff}
.brand{color:var(--accent);font-weight:700;font-size:.85rem;text-transform:uppercase;letter-spacing:.06em}
"""


def _qr_svg(text: str) -> str:
    img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode()
    return svg[svg.find("<svg"):]


def ticket_html(ticket: dict | None) -> str:
    if not ticket:
        body = "<h1>Ticket not found</h1><p>Check the link, or message us on WhatsApp and ask for your tickets.</p>"
    else:
        e = html.escape
        status = ticket["status"]
        badge = ('<span class="badge valid">Valid</span>' if status == "valid"
                 else f'<span class="badge used">{e(status.replace("_", " ").title())}</span>')
        name = f"<p>Holder: {e(ticket['holder_name'])}</p>" if ticket.get("holder_name") else ""
        body = f"""<div class="brand">Eko Nights</div>
<h1>{e(ticket['event'])}</h1><p>{e(ticket['tier'])}</p><p>{e(ticket['starts'])}</p><p>{e(ticket['venue'])}</p>
{name}<p>Number: {e(ticket['holder'])}</p>
<div class="qr">{_qr_svg(ticket['code'])}</div><div class="code">{e(ticket['code'])}</div>{badge}
<p style="margin-top:12px;font-size:.85rem">One entry per code. Do not share screenshots: the first scan wins.</p>"""
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Eko Nights ticket</title>
<style>{STYLE}</style></head><body><main class="card">{body}</main></body></html>"""


def paid_html(ok: bool) -> str:
    msg = ("<h1>Payment received</h1><p>Go back to WhatsApp and send <b>paid</b> to get your tickets.</p>" if ok else
           "<h1>Almost there</h1><p>We could not confirm the payment yet. Go back to WhatsApp and send <b>paid</b>, "
           "and we will check again.</p>")
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Eko Nights payment</title>
<style>{STYLE}</style></head><body><main class="card"><div class="brand">Eko Nights</div>{msg}</main></body></html>"""
