"""FastAPI app: MCP endpoint for Chord, Paystack webhook, ticket pages and a health check."""
from __future__ import annotations

import contextlib
import json
import logging
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .mcp_tools import build_mcp
from .ticket_page import paid_html, ticket_html

log = logging.getLogger("tixchat")


class BearerAuth(BaseHTTPMiddleware):
    """Chord sends Authorization: Bearer <token> when the server is registered with auth_type bearer."""

    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp") and self.token:
            header = request.headers.get("authorization", "")
            supplied = header[7:] if header.lower().startswith("bearer ") else ""
            if not secrets.compare_digest(supplied, self.token):
                return JSONResponse({"error": "unauthorised"}, status_code=401)
        return await call_next(request)


def create_app(service, settings) -> FastAPI:
    mcp = build_mcp(service)
    mcp_app = mcp.streamable_http_app()

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Eko Nights tickets", lifespan=lifespan)
    app.add_middleware(BearerAuth, token=settings.mcp_bearer_token)

    @app.get("/health")
    def health():
        return {"ok": True, "store": settings.store_backend, "payments": settings.paystack_mode}

    @app.get("/t/{code}", response_class=HTMLResponse)
    def ticket(code: str):
        t = service.ticket_by_code(code)
        return HTMLResponse(ticket_html(t), status_code=200 if t else 404)

    @app.get("/paid", response_class=HTMLResponse)
    def paid(reference: str = "", trxref: str = ""):
        ref = reference or trxref
        result = service.confirm_from_provider(ref) if ref else {"ok": False}
        return HTMLResponse(paid_html(bool(result.get("ok"))))

    @app.post("/webhooks/paystack")
    async def paystack_webhook(request: Request):
        raw = await request.body()
        if not service.paystack.valid_signature(raw, request.headers.get("x-paystack-signature")):
            log.warning("Rejected Paystack webhook with a bad signature")
            return JSONResponse({"ok": False}, status_code=401)
        try:
            event = json.loads(raw)
        except ValueError:
            return JSONResponse({"ok": False}, status_code=400)
        if event.get("event") == "charge.success":
            ref = (event.get("data") or {}).get("reference", "")
            # Re-verify with the API rather than trusting the webhook body.
            result = service.confirm_from_provider(ref)
            log.info("Webhook charge.success %s -> %s", ref, result)
        # Always 200 for a valid signature so Paystack stops retrying.
        return {"ok": True}

    # Mounted last so the routes above win; everything under /mcp goes to the MCP server.
    app.mount("/", mcp_app)
    return app
